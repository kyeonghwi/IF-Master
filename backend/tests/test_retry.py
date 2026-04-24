"""
Tests for single and bulk retry endpoints.
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.config import settings
from app.db.models import InterfaceLog
from app.dependencies import create_access_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def failed_logs(session_factory) -> list[InterfaceLog]:
    """Two FAILED logs ready for retry."""
    now = datetime.utcnow()
    logs = [
        InterfaceLog(
            id=uuid.uuid4(),
            idempotency_key=f"BULK-TEST-{i:04d}",
            target_org="금감원",
            protocol="REST",
            service_name="보험료납입통보",
            status="FAILED",
            error_message="Connection timeout",
            called_at=now,
            retry_count=0,
        )
        for i in range(2)
    ]
    async with session_factory() as session:
        async with session.begin():
            session.add_all(logs)
    return logs


@pytest.fixture
async def mixed_logs(session_factory) -> tuple[InterfaceLog, InterfaceLog]:
    """One FAILED log and one SUCCESS log."""
    now = datetime.utcnow()
    failed = InterfaceLog(
        id=uuid.uuid4(),
        idempotency_key="MIX-FAILED-0001",
        target_org="금감원",
        protocol="REST",
        service_name="보험료납입통보",
        status="FAILED",
        error_message="timeout",
        called_at=now,
        retry_count=0,
    )
    success = InterfaceLog(
        id=uuid.uuid4(),
        idempotency_key="MIX-SUCCESS-0001",
        target_org="금감원",
        protocol="REST",
        service_name="보험료납입통보",
        status="SUCCESS",
        called_at=now,
        retry_count=0,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add_all([failed, success])
    return failed, success


@pytest.fixture
def viewer_headers() -> dict:
    """Bearer token for a VIEWER-role user (role not in ALLOWED_ROLES)."""
    token = create_access_token({"sub": "viewer_user", "role": "VIEWER"})
    return {"Authorization": f"Bearer {token}"}


def _mock_success():
    """Return mock patches that simulate a successful external call."""
    mock_get = AsyncMock(
        status_code=200,
        json=lambda: {"status": "not_found"},
    )
    mock_post = AsyncMock(
        status_code=200,
        json=lambda: {"status": "SUCCESS"},
    )
    return mock_get, mock_post


# ---------------------------------------------------------------------------
# Single retry backward compatibility
# ---------------------------------------------------------------------------


async def test_single_retry_backward_compat(
    client: AsyncClient, auth_headers: dict, failed_logs: list[InterfaceLog]
):
    """Existing single-item retry endpoint still returns {result, message}."""
    log_id = str(failed_logs[0].id)
    mock_get, mock_post = _mock_success()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mg, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mp:
        mg.return_value = mock_get
        mp.return_value = mock_post

        resp = await client.post(f"/api/retry/{log_id}", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"] == "SUCCESS"
    assert "message" in body


# ---------------------------------------------------------------------------
# Bulk retry — success path
# ---------------------------------------------------------------------------


async def test_bulk_retry_success(
    client: AsyncClient, auth_headers: dict, failed_logs: list[InterfaceLog]
):
    """Two FAILED logs both succeed via bulk retry."""
    log_ids = [str(log.id) for log in failed_logs]
    mock_get, mock_post = _mock_success()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mg, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mp:
        mg.return_value = mock_get
        mp.return_value = mock_post

        resp = await client.post(
            "/api/retry/bulk",
            json={"log_ids": log_ids},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    assert all(r["result"] == "SUCCESS" for r in results)


# ---------------------------------------------------------------------------
# Bulk retry — partial failure (NOT_RETRYABLE)
# ---------------------------------------------------------------------------


async def test_bulk_retry_partial(
    client: AsyncClient, auth_headers: dict, mixed_logs: tuple[InterfaceLog, InterfaceLog]
):
    """FAILED log succeeds; SUCCESS log returns FAILED/NOT_RETRYABLE."""
    failed, success = mixed_logs
    log_ids = [str(failed.id), str(success.id)]
    mock_get, mock_post = _mock_success()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mg, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mp:
        mg.return_value = mock_get
        mp.return_value = mock_post

        resp = await client.post(
            "/api/retry/bulk",
            json={"log_ids": log_ids},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2

    failed_result = next(r for r in results if r["log_id"] == str(failed.id))
    success_result = next(r for r in results if r["log_id"] == str(success.id))

    assert failed_result["result"] == "SUCCESS"
    assert success_result["result"] == "FAILED"
    assert success_result["message"] == "NOT_RETRYABLE"


# ---------------------------------------------------------------------------
# Bulk retry — 51 items rejected by Pydantic (max_length=50)
# ---------------------------------------------------------------------------


async def test_bulk_retry_51_items_rejected(client: AsyncClient, auth_headers: dict):
    """51 UUIDs exceed max_length=50 and produce 422 Unprocessable Entity."""
    log_ids = [str(uuid.uuid4()) for _ in range(51)]

    resp = await client.post(
        "/api/retry/bulk",
        json={"log_ids": log_ids},
        headers=auth_headers,
    )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Bulk retry — deduplication
# ---------------------------------------------------------------------------


async def test_bulk_retry_deduplication(
    client: AsyncClient, auth_headers: dict, failed_logs: list[InterfaceLog]
):
    """Same log_id sent 3 times: first is processed, rest are ALREADY_PROCESSED."""
    log_id = str(failed_logs[0].id)
    mock_get, mock_post = _mock_success()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mg, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mp:
        mg.return_value = mock_get
        mp.return_value = mock_post

        resp = await client.post(
            "/api/retry/bulk",
            json={"log_ids": [log_id, log_id, log_id]},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 3

    assert results[0]["result"] == "SUCCESS"
    assert results[1]["result"] == "ALREADY_PROCESSED"
    assert results[1]["message"] == "중복 요청"
    assert results[2]["result"] == "ALREADY_PROCESSED"
    assert results[2]["message"] == "중복 요청"


# ---------------------------------------------------------------------------
# Bulk retry — VIEWER role forbidden
# ---------------------------------------------------------------------------


async def test_bulk_retry_forbidden(client: AsyncClient, viewer_headers: dict):
    """VIEWER role receives 403 FORBIDDEN."""
    log_ids = [str(uuid.uuid4())]

    resp = await client.post(
        "/api/retry/bulk",
        json={"log_ids": log_ids},
        headers=viewer_headers,
    )

    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# Bulk retry — empty list rejected by Pydantic (min_length=1)
# ---------------------------------------------------------------------------


async def test_bulk_retry_empty_list(client: AsyncClient, auth_headers: dict):
    """Empty log_ids list violates min_length=1 and produces 422."""
    resp = await client.post(
        "/api/retry/bulk",
        json={"log_ids": []},
        headers=auth_headers,
    )

    assert resp.status_code == 422
