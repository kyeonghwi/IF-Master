import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import AuditLog, InterfaceConfig, InterfaceLog
from app.dependencies import get_current_user
from app.schemas import (
    InterfaceConfigCreate,
    InterfaceConfigListResponse,
    InterfaceConfigResponse,
    InterfaceConfigUpdate,
)
from app.services import mock_service

router = APIRouter()

_PROTOCOLS = {"REST", "SOAP", "MQ", "BATCH", "SFTP"}


def _validate_protocol(protocol: str) -> None:
    if protocol.upper() not in _PROTOCOLS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_PROTOCOL", "message": f"프로토콜은 {', '.join(_PROTOCOLS)} 중 하나여야 합니다"},
        )


# 5-field cron: each field is *, digits, commas, hyphens, slashes
_CRON_RE = re.compile(
    r"^(?:[0-9,\-\*/]+\s+){4}[0-9,\-\*/]+$"
)


def _validate_cron(value: str | None) -> None:
    """Validates a 5-field cron expression. None/empty string is accepted (means no schedule)."""
    if not value:
        return
    if not _CRON_RE.match(value.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_CRON", "message": "cron expression invalid (e.g. 0 9 * * 1-5)"},
        )


@router.get("/interfaces", response_model=InterfaceConfigListResponse)
async def list_interfaces(
    enabled: bool | None = None,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(InterfaceConfig)
    if enabled is not None:
        stmt = stmt.where(InterfaceConfig.enabled == enabled)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(InterfaceConfig.name).offset((page - 1) * size).limit(size)
    items = (await db.execute(stmt)).scalars().all()

    return InterfaceConfigListResponse(items=list(items), total=total)


@router.post("/interfaces", response_model=InterfaceConfigResponse, status_code=201)
async def create_interface(
    body: InterfaceConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    _validate_protocol(body.protocol)
    _validate_cron(body.schedule_cron)
    cfg = InterfaceConfig(
        **body.model_dump(),
        protocol=body.protocol.upper(),
    )
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.put("/interfaces/{cfg_id}", response_model=InterfaceConfigResponse)
async def update_interface(
    cfg_id: uuid.UUID,
    body: InterfaceConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    cfg = (await db.execute(select(InterfaceConfig).where(InterfaceConfig.id == cfg_id))).scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "인터페이스를 찾을 수 없습니다"})

    for field, value in body.model_dump(exclude_none=True).items():
        if field == "protocol" and value is not None:
            _validate_protocol(value)
            value = value.upper()
        if field == "schedule_cron":
            _validate_cron(value)
        setattr(cfg, field, value)

    cfg.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.patch("/interfaces/{cfg_id}/toggle", response_model=InterfaceConfigResponse)
async def toggle_interface(
    cfg_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    cfg = (await db.execute(select(InterfaceConfig).where(InterfaceConfig.id == cfg_id))).scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "인터페이스를 찾을 수 없습니다"})

    cfg.enabled = not cfg.enabled
    cfg.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.delete("/interfaces/{cfg_id}", status_code=204)
async def delete_interface(
    cfg_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    cfg = (await db.execute(select(InterfaceConfig).where(InterfaceConfig.id == cfg_id))).scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "인터페이스를 찾을 수 없습니다"})

    await db.delete(cfg)
    await db.commit()


@router.post("/interfaces/{cfg_id}/execute")
async def execute_interface(
    cfg_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    cfg = (await db.execute(select(InterfaceConfig).where(InterfaceConfig.id == cfg_id))).scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "인터페이스를 찾을 수 없습니다"})
    if not cfg.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INTERFACE_DISABLED", "message": "비활성화된 인터페이스는 실행할 수 없습니다"},
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    date_str = now.strftime("%Y%m%d")
    uid = str(uuid.uuid4()).replace("-", "")[:8]
    idempotency_key = f"{cfg.target_org[:6]}-{date_str}-{uid}"

    log = InterfaceLog(
        idempotency_key=idempotency_key,
        target_org=cfg.target_org,
        protocol=cfg.protocol,
        service_name=cfg.name,
        status="PENDING",
        called_at=now,
        request_payload=f'{{"source": "manual_execute", "interface_id": "{cfg_id}"}}',
    )
    db.add(log)
    await db.flush()

    outcome, response_ms, response_json = await mock_service.dispatch(
        key=idempotency_key,
        protocol=cfg.protocol,
        timeout_ms=cfg.timeout_ms,
        db=db,
    )

    responded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    log.status = outcome
    log.responded_at = responded_at
    log.response_ms = response_ms
    log.response_payload = response_json

    audit = AuditLog(
        interface_log_id=log.id,
        action="MANUAL_EXECUTE",
        operator=current_user["sub"],
        executed_at=responded_at,
        result=outcome,
        result_payload=response_json,
    )
    db.add(audit)
    await db.commit()

    broadcast = getattr(request.app.state, "broadcast_event", None)
    if broadcast:
        broadcast("execution_result", {
            "id": str(log.id),
            "result": outcome,
            "service_name": cfg.name,
            "response_ms": response_ms,
        })

    return {
        "log_id": str(log.id),
        "status": outcome,
        "response_ms": response_ms,
        "message": "실행 성공" if outcome == "SUCCESS" else "실행 실패",
    }
