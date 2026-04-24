import csv
import io
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import InterfaceLog
from app.dependencies import get_current_user
from app.schemas import InterfaceLogDetail, InterfaceLogSummary, LogsResponse

router = APIRouter()


def _csv_safe(value: str | None) -> str:
    """Prefix cells starting with formula-trigger chars to prevent spreadsheet injection (CWE-1236)."""
    if value is None:
        return ""
    s = str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


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


@router.get("/logs/export")
async def export_logs(
    status: str | None = Query(default=None),
    protocol: str | None = Query(default=None),
    target_org: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),  # REQ-011: auth required
):
    # Build filters (reuse list_logs pattern)
    filters = []
    if status is not None:
        filters.append(InterfaceLog.status == status)
    if protocol is not None:
        filters.append(InterfaceLog.protocol == protocol)
    if target_org is not None:
        filters.append(InterfaceLog.target_org == target_org)
    if start_date is not None:
        filters.append(InterfaceLog.called_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date is not None:
        # end_date is inclusive: < end_date + 1 day
        filters.append(InterfaceLog.called_at < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))

    # Count to detect truncation — run before streaming so header can be set
    count_stmt = select(func.count(InterfaceLog.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total_count = (await db.execute(count_stmt)).scalar_one()
    row_limit_reached = total_count > 10000

    # Date for filename
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    response_headers = {
        "Content-Disposition": f'attachment; filename="if-logs-{date_str}.csv"',
    }
    if row_limit_reached:
        response_headers["X-Row-Limit-Reached"] = "true"

    # Async generator for streaming CSV
    async def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        # Header row
        writer.writerow([
            "id", "service_name", "target_org", "protocol", "status",
            "called_at", "responded_at", "response_ms", "retry_count", "error_message"
        ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        stmt = (
            select(InterfaceLog)
            .order_by(InterfaceLog.called_at.desc())
            .limit(10000)
        )
        if filters:
            stmt = stmt.where(*filters)

        result = await db.execute(stmt.execution_options(yield_per=500))
        async for row in result.scalars():
            writer.writerow([
                str(row.id),
                _csv_safe(row.service_name),
                _csv_safe(row.target_org),
                row.protocol,           # enum-constrained, no sanitization needed
                row.status,             # enum-constrained
                row.called_at.isoformat() if row.called_at else "",
                row.responded_at.isoformat() if row.responded_at else "",  # null -> empty
                "" if row.response_ms is None else row.response_ms,        # null -> empty (REQ-010)
                row.retry_count,
                _csv_safe(row.error_message),
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers=response_headers,
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
