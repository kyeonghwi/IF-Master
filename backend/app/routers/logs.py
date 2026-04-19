import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import InterfaceLog
from app.schemas import InterfaceLogDetail, InterfaceLogSummary, LogsResponse

router = APIRouter()

# FAILED rows first, then called_at DESC
_FAILED_FIRST = case((InterfaceLog.status == "FAILED", 0), else_=1)


@router.get("/logs", response_model=LogsResponse)
async def list_logs(
    status: str | None = Query(default=None),
    target_org: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> LogsResponse:
    filters = []
    if status is not None:
        filters.append(InterfaceLog.status == status)
    if target_org is not None:
        filters.append(InterfaceLog.target_org == target_org)

    count_stmt = select(func.count()).select_from(InterfaceLog)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    items_stmt = (
        select(InterfaceLog)
        .order_by(_FAILED_FIRST, InterfaceLog.called_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    if filters:
        items_stmt = items_stmt.where(*filters)
    items = (await db.execute(items_stmt)).scalars().all()

    return LogsResponse(
        items=[InterfaceLogSummary.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/logs/{log_id}", response_model=InterfaceLogDetail)
async def get_log(
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(InterfaceLog)
        .options(selectinload(InterfaceLog.audit_logs))
        .where(InterfaceLog.id == log_id)
    )
    log = (await db.execute(stmt)).scalar_one_or_none()

    if log is None:
        return JSONResponse(
            status_code=404,
            content={"code": "LOG_NOT_FOUND", "message": "트랜잭션을 찾을 수 없습니다"},
        )

    return InterfaceLogDetail.model_validate(log)
