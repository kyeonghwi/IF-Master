import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import AuditLog, Base, InterfaceConfig, InterfaceLog


@pytest.fixture(scope="session")
def engine():
    return create_async_engine(settings.database_url)


@pytest.fixture(scope="session")
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def create_tables(engine):
    """Create all tables once before any test runs."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(scope="session")
async def client(create_tables):
    """Session-scoped HTTP client with scheduler mocked out."""
    with patch("app.services.scheduler.scheduler.add_job"), patch(
        "app.services.scheduler.scheduler.start"
    ):
        import app.main as _m
        async with AsyncClient(
            transport=ASGITransport(app=_m.app), base_url="http://test"
        ) as ac:
            yield ac


@pytest.fixture(autouse=True)
async def clean_db(engine, create_tables):
    """Truncate all data before each test."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE audit_log, interface_log, mock_responses, interface_config RESTART IDENTITY CASCADE"
            )
        )
    yield


@pytest.fixture
async def auth_cookies(client: AsyncClient) -> dict:
    resp = await client.post(
        "/auth/login",
        json={"username": settings.demo_username, "password": settings.demo_password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return {"access_token": resp.cookies["access_token"]}


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Bearer token fallback for tests that set headers explicitly."""
    resp = await client.post(
        "/auth/login",
        json={"username": settings.demo_username, "password": settings.demo_password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.cookies.get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_logs(session_factory) -> list[InterfaceLog]:
    now = datetime.utcnow()
    logs = (
        [
            InterfaceLog(
                id=uuid.uuid4(),
                idempotency_key=f"KB-20260419-{i:04d}",
                target_org="KB국민은행",
                protocol="REST",
                service_name="계좌이체요청",
                status="SUCCESS",
                called_at=now,
                responded_at=now,
                retry_count=0,
            )
            for i in range(3)
        ]
        + [
            InterfaceLog(
                id=uuid.uuid4(),
                idempotency_key=f"FSS-20260419-{i:04d}",
                target_org="금감원",
                protocol="SOAP",
                service_name="보험료납입통보",
                status="FAILED",
                error_message="Connection timeout",
                stack_trace="Traceback...",
                called_at=now,
                responded_at=None,
                retry_count=0,
            )
            for i in range(2)
        ]
        + [
            InterfaceLog(
                id=uuid.uuid4(),
                idempotency_key=f"NH-20260419-{i:04d}",
                target_org="NH농협은행",
                protocol="BATCH",
                service_name="자동이체등록",
                status="PENDING",
                called_at=now,
                responded_at=None,
                retry_count=0,
            )
            for i in range(1)
        ]
    )
    async with session_factory() as session:
        async with session.begin():
            session.add_all(logs)
    return logs


@pytest.fixture
async def failed_log_with_audit(sample_logs, session_factory) -> InterfaceLog:
    failed = next(l for l in sample_logs if l.status == "FAILED")
    audit = AuditLog(
        id=uuid.uuid4(),
        interface_log_id=failed.id,
        action="RETRY_REQUEST",
        operator=settings.demo_username,
        executed_at=datetime.utcnow(),
        result="RETRY_QUEUED",
        result_payload=None,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(audit)
    return failed
