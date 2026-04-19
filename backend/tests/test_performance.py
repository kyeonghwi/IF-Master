"""Smoke tests for performance API."""
import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import InterfaceLog


@pytest.fixture
async def perf_logs(session_factory):
    now = datetime.utcnow()
    logs = [
        InterfaceLog(
            id=uuid.uuid4(),
            idempotency_key=f"KB-PERF-{i:04d}",
            target_org="KB국민은행",
            protocol="REST",
            service_name="계좌이체요청",
            status="SUCCESS",
            called_at=now - timedelta(hours=1),
            responded_at=now - timedelta(hours=1) + timedelta(milliseconds=ms),
            response_ms=ms,
            retry_count=0,
        )
        for i, ms in enumerate([200, 300, 500, 800, 1200, 1500, 2000, 2500, 3500, 5000])
    ]
    async with session_factory() as session:
        async with session.begin():
            session.add_all(logs)
    return logs


@pytest.mark.asyncio
async def test_performance_returns_data(client: AsyncClient, auth_cookies: dict, perf_logs):
    resp = await client.get("/api/performance", cookies=auth_cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert "by_interface" in data
    assert "sla_summary" in data
    assert "slow_alerts" in data


@pytest.mark.asyncio
async def test_performance_sla_calculation(client: AsyncClient, auth_cookies: dict, perf_logs):
    resp = await client.get("/api/performance", cookies=auth_cookies)
    assert resp.status_code == 200
    summary = resp.json()["sla_summary"]
    assert summary["total_calls"] == 10
    # 8 records have response_ms < 3000 (200,300,500,800,1200,1500,2000,2500)
    assert summary["within_sla"] == 8
    assert abs(summary["sla_rate"] - 80.0) < 0.1


@pytest.mark.asyncio
async def test_performance_slow_alerts(client: AsyncClient, auth_cookies: dict, perf_logs):
    resp = await client.get("/api/performance", cookies=auth_cookies)
    alerts = resp.json()["slow_alerts"]
    # P95 of [200,300,500,800,1200,1500,2000,2500,3500,5000] > 3000 → should have alert
    assert len(alerts) >= 1


@pytest.mark.asyncio
async def test_performance_requires_auth(client: AsyncClient):
    resp = await client.get("/api/performance")
    assert resp.status_code == 401
