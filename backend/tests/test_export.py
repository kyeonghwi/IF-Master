"""Tests for GET /api/logs/export."""
import csv
import io

import pytest
from httpx import AsyncClient


async def test_export_basic(client: AsyncClient, auth_headers: dict, sample_logs):
    resp = await client.get("/api/logs/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "if-logs-" in resp.headers["content-disposition"]

    lines = resp.text.splitlines()
    assert lines[0] == "id,service_name,target_org,protocol,status,called_at,responded_at,response_ms,retry_count,error_message"
    assert len(lines) == 7  # header + 6 rows


async def test_export_requires_auth(client: AsyncClient):
    resp = await client.get("/api/logs/export")
    assert resp.status_code == 401


async def test_export_filter_by_status(client: AsyncClient, auth_headers: dict, sample_logs):
    resp = await client.get("/api/logs/export", params={"status": "FAILED"}, headers=auth_headers)
    assert resp.status_code == 200
    lines = resp.text.splitlines()
    data_rows = lines[1:]
    assert len(data_rows) == 2
    reader = csv.reader(data_rows)
    for row in reader:
        assert row[4] == "FAILED"


async def test_export_null_cells(client: AsyncClient, auth_headers: dict, sample_logs):
    """Null responded_at and response_ms must appear as empty strings (REQ-010)."""
    # sample_logs contains PENDING logs with responded_at=None
    resp = await client.get("/api/logs/export", params={"status": "PENDING"}, headers=auth_headers)
    assert resp.status_code == 200
    lines = resp.text.splitlines()
    data_rows = lines[1:]
    assert len(data_rows) >= 1
    reader = csv.reader(data_rows)
    for row in reader:
        assert row[6] == ""   # responded_at column (index 6)
        assert row[7] == ""   # response_ms column (index 7)


async def test_export_x_row_limit_not_set_for_small_result(
    client: AsyncClient, auth_headers: dict, sample_logs
):
    resp = await client.get("/api/logs/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "x-row-limit-reached" not in resp.headers


async def test_export_csv_formula_injection_sanitized(
    client: AsyncClient, auth_headers: dict, session_factory
):
    """CSV formula-trigger chars in user data must be prefixed with ' (CWE-1236)."""
    from datetime import datetime
    from app.db.models import InterfaceLog
    import uuid

    formula_log = InterfaceLog(
        id=uuid.uuid4(),
        idempotency_key="FORMULA-TEST-0001",
        target_org='=HYPERLINK("http://evil.com","click")',
        protocol="REST",
        service_name="+malicious",
        status="FAILED",
        error_message="=SUM(1+1)",
        called_at=datetime.utcnow(),
        responded_at=None,
        retry_count=0,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(formula_log)

    resp = await client.get("/api/logs/export", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.text
    assert "'=HYPERLINK" in body
    assert "'+malicious" in body
    assert "'=SUM" in body
