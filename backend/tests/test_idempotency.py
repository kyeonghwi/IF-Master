"""
Verifies idempotency guarantee: same log retried twice returns ALREADY_PROCESSED
on the second call regardless of mock server state.
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.config import settings
from app.db.models import InterfaceLog


@pytest.fixture
async def failed_log(session_factory) -> InterfaceLog:
    log = InterfaceLog(
        id=uuid.uuid4(),
        idempotency_key=f"FSS-20260419-idem01",
        target_org="금감원",
        protocol="REST",
        service_name="보험료납입통보",
        status="FAILED",
        error_message="Connection timeout",
        called_at=datetime.utcnow(),
        retry_count=0,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(log)
    return log


async def test_retry_idempotency_already_processed(client: AsyncClient, failed_log: InterfaceLog, auth_headers: dict):
    """Second retry of the same log must return ALREADY_PROCESSED."""
    log_id = str(failed_log.id)

    # First retry: mock returns "not_found" so actual call happens → SUCCESS
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:

        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"status": "not_found"},
        )
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"status": "SUCCESS"},
        )

        resp1 = await client.post(f"/api/retry/{log_id}", headers=auth_headers)
        assert resp1.status_code == 200
        assert resp1.json()["result"] == "SUCCESS"

    # Second retry: log.status is now SUCCESS → NOT_RETRYABLE (400)
    resp2 = await client.post(f"/api/retry/{log_id}", headers=auth_headers)
    assert resp2.status_code == 400
    assert resp2.json()["detail"]["code"] == "NOT_RETRYABLE"


async def test_retry_skip_when_mock_already_processed(client: AsyncClient, failed_log: InterfaceLog, auth_headers: dict):
    """If mock already has a result for the key, return ALREADY_PROCESSED without re-calling."""
    log_id = str(failed_log.id)

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"status": "SUCCESS", "response": {"processed_at": "2026-04-19T00:00:00"}},
        )

        resp = await client.post(f"/api/retry/{log_id}", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["result"] == "ALREADY_PROCESSED"
    assert "멱등성" in resp.json()["message"]


async def test_retry_count_cap(client: AsyncClient, session_factory, auth_headers: dict):
    """retry_count >= 3 must return 400 RETRY_LIMIT_EXCEEDED."""
    log = InterfaceLog(
        id=uuid.uuid4(),
        idempotency_key="FSS-20260419-cap01",
        target_org="금감원",
        protocol="REST",
        service_name="보험료납입통보",
        status="FAILED",
        error_message="timeout",
        called_at=datetime.utcnow(),
        retry_count=3,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(log)

    resp = await client.post(f"/api/retry/{log.id}", headers=auth_headers)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "RETRY_LIMIT_EXCEEDED"
