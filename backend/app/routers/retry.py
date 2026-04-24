import logging
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import AuditLog, InterfaceLog
from app.dependencies import get_current_user
from app.schemas import BulkRetryItem, BulkRetryRequest, BulkRetryResponse

router = APIRouter()

_ALLOWED_ROLES = {"ADMIN", "OPERATOR"}

_logger = logging.getLogger(__name__)


async def _retry_one(
    log_id: uuid.UUID,
    request: Request,
    db: AsyncSession,
    operator: str,
) -> tuple[str, str]:
    """Execute a single retry inside an already-open transaction.

    Returns (result, message). Never raises. Caller owns db.begin().
    """
    stmt = (
        select(InterfaceLog)
        .where(InterfaceLog.id == log_id)
        .with_for_update()
    )
    log = (await db.execute(stmt)).scalar_one_or_none()

    if log is None:
        return ("FAILED", "LOG_NOT_FOUND")
    if log.status not in ("FAILED", "PENDING"):
        return ("FAILED", "NOT_RETRYABLE")
    if log.retry_count >= 3:
        return ("FAILED", "RETRY_LIMIT_EXCEEDED")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AuditLog(
        interface_log_id=log.id,
        action="RETRY_REQUEST",
        operator=operator,
        executed_at=now,
        result="PENDING",
    ))
    await db.flush()

    idempotency_key = log.idempotency_key

    try:
        async with httpx.AsyncClient() as client:
            base = str(request.base_url).rstrip("/")
            status_resp = await client.get(
                f"{base}/mock/status",
                params={"key": idempotency_key},
                timeout=5.0,
            )
            status_data = status_resp.json()

            if status_data.get("status") != "not_found":
                log.status = "SUCCESS"
                db.add(AuditLog(
                    interface_log_id=log.id,
                    action="RETRY_SKIP",
                    operator=operator,
                    executed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                    result="ALREADY_PROCESSED",
                ))
                api_result = "ALREADY_PROCESSED"
                api_message = "이미 처리됨 (멱등성 보장)"
            else:
                call_resp = await client.post(
                    f"{base}/mock/call",
                    params={"key": idempotency_key},
                    timeout=5.0,
                )
                call_status = call_resp.json().get("status")

                if call_status == "SUCCESS":
                    log.status = "SUCCESS"
                    db.add(AuditLog(
                        interface_log_id=log.id,
                        action="RETRY_SUCCESS",
                        operator=operator,
                        executed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        result="SUCCESS",
                    ))
                    api_result = "SUCCESS"
                    api_message = "재처리 성공"
                else:
                    log.status = "FAILED"
                    log.retry_count += 1
                    db.add(AuditLog(
                        interface_log_id=log.id,
                        action="RETRY_FAILED",
                        operator=operator,
                        executed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        result="FAILED",
                    ))
                    api_result = "FAILED"
                    api_message = "재처리 실패"

    except httpx.TimeoutException:
        log.status = "FAILED"
        log.retry_count += 1
        db.add(AuditLog(
            interface_log_id=log.id,
            action="RETRY_FAILED",
            operator=operator,
            executed_at=datetime.now(timezone.utc).replace(tzinfo=None),
            result="FAILED",
        ))
        api_result = "FAILED"
        api_message = "TIMEOUT"

    await db.flush()
    return (api_result, api_message)


# NOTE: bulk route must be registered before /{log_id} to prevent "bulk" being
# parsed as a UUID path parameter.
@router.post("/retry/bulk", response_model=BulkRetryResponse)
async def bulk_retry(
    body: BulkRetryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") not in _ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "재처리 권한이 없습니다"},
        )

    operator = current_user["sub"]
    seen: dict[uuid.UUID, int] = {}  # log_id -> first occurrence index in results
    results: list[BulkRetryItem] = []

    for log_id in body.log_ids:
        if log_id in seen:
            results.append(BulkRetryItem(
                log_id=log_id,
                result="ALREADY_PROCESSED",
                message="중복 요청",
            ))
            continue
        seen[log_id] = len(results)

        result_code = "FAILED"
        result_msg = "DB_ERROR"
        try:
            async with db.begin():
                result_code, result_msg = await _retry_one(log_id, request, db, operator)
        except SQLAlchemyError:
            result_code, result_msg = "FAILED", "DB_ERROR"

        results.append(BulkRetryItem(
            log_id=log_id,
            result=result_code,
            message=result_msg,
        ))

        # SSE per-item (fire and forget)
        try:
            request.app.state.broadcast_event(
                "retry_result",
                {"id": str(log_id), "result": result_code, "message": result_msg},
            )
        except Exception as exc:
            _logger.warning("SSE broadcast failed: %s", exc)

    return BulkRetryResponse(results=results)


@router.post("/retry/{log_id}")
async def retry_transaction(
    log_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") not in _ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "재처리 권한이 없습니다"},
        )

    operator = current_user["sub"]
    api_result: str
    api_message: str

    try:
        async with db.begin():
            api_result, api_message = await _retry_one(log_id, request, db, operator)
            if api_result == "FAILED":
                if api_message == "LOG_NOT_FOUND":
                    raise HTTPException(
                        status_code=404,
                        detail={"code": "LOG_NOT_FOUND", "message": "트랜잭션을 찾을 수 없습니다"},
                    )
                elif api_message == "NOT_RETRYABLE":
                    raise HTTPException(
                        status_code=400,
                        detail={"code": "NOT_RETRYABLE", "message": "재처리 불가 상태"},
                    )
                elif api_message == "RETRY_LIMIT_EXCEEDED":
                    raise HTTPException(
                        status_code=400,
                        detail={"code": "RETRY_LIMIT_EXCEEDED", "message": "최대 재처리 횟수 초과"},
                    )
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail={"code": "DB_ERROR", "message": "데이터베이스 오류"},
        )

    # SSE broadcast after commit (fire and forget)
    try:
        request.app.state.broadcast_event(
            "retry_result",
            {"id": str(log_id), "result": api_result, "message": api_message},
        )
    except Exception as exc:
        _logger.warning("SSE broadcast failed: %s", exc)

    return {"result": api_result, "message": api_message}
