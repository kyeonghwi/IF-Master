import uuid

from httpx import AsyncClient


async def test_list_logs_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/logs", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["page"] == 1


async def test_list_logs_returns_all(client: AsyncClient, auth_headers: dict, sample_logs):
    resp = await client.get("/api/logs", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 6
    assert len(body["items"]) == 6


async def test_list_logs_failed_first(client: AsyncClient, auth_headers: dict, sample_logs):
    resp = await client.get("/api/logs", headers=auth_headers)
    items = resp.json()["items"]
    # FAILED records must appear before SUCCESS/PENDING
    statuses = [item["status"] for item in items]
    first_non_failed = next((i for i, s in enumerate(statuses) if s != "FAILED"), len(statuses))
    assert all(s == "FAILED" for s in statuses[:first_non_failed])


async def test_list_logs_filter_by_status(client: AsyncClient, auth_headers: dict, sample_logs):
    resp = await client.get("/api/logs", params={"status": "SUCCESS"}, headers=auth_headers)
    body = resp.json()
    assert body["total"] == 3
    assert all(item["status"] == "SUCCESS" for item in body["items"])


async def test_list_logs_filter_by_target_org(client: AsyncClient, auth_headers: dict, sample_logs):
    resp = await client.get("/api/logs", params={"target_org": "금감원"}, headers=auth_headers)
    body = resp.json()
    assert body["total"] == 2
    assert all(item["target_org"] == "금감원" for item in body["items"])


async def test_list_logs_pagination(client: AsyncClient, auth_headers: dict, sample_logs):
    resp = await client.get("/api/logs", params={"page": 1, "size": 2}, headers=auth_headers)
    body = resp.json()
    assert body["total"] == 6
    assert len(body["items"]) == 2
    assert body["page"] == 1

    resp2 = await client.get("/api/logs", params={"page": 3, "size": 2}, headers=auth_headers)
    assert len(resp2.json()["items"]) == 2


async def test_get_log_detail(client: AsyncClient, auth_headers: dict, sample_logs):
    log_id = str(sample_logs[0].id)
    resp = await client.get(f"/api/logs/{log_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == log_id
    assert "audit_logs" in body


async def test_get_log_detail_includes_audit(
    client: AsyncClient, auth_headers: dict, failed_log_with_audit
):
    log_id = str(failed_log_with_audit.id)
    resp = await client.get(f"/api/logs/{log_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["audit_logs"]) == 1
    assert resp.json()["audit_logs"][0]["action"] == "RETRY_REQUEST"


async def test_get_log_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.get(f"/api/logs/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "LOG_NOT_FOUND"


async def test_list_logs_requires_auth(client: AsyncClient):
    resp = await client.get("/api/logs")
    assert resp.status_code == 401


async def test_get_log_requires_auth(client: AsyncClient):
    resp = await client.get(f"/api/logs/{uuid.uuid4()}")
    assert resp.status_code == 401
