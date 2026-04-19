"""Tests for Interface Registry CRUD and execute endpoint."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.fixture
async def sample_config(client: AsyncClient, auth_cookies: dict):
    resp = await client.post(
        "/api/interfaces",
        json={
            "name": "테스트 REST API",
            "protocol": "REST",
            "target_org": "테스트기관",
            "endpoint_url": "https://api.test.com/v1/check",
            "timeout_ms": 3000,
            "max_retry": 2,
            "enabled": True,
        },
        cookies=auth_cookies,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_interface(client: AsyncClient, auth_cookies: dict):
    resp = await client.post(
        "/api/interfaces",
        json={
            "name": "금감원 계약조회",
            "protocol": "REST",
            "target_org": "금감원",
            "endpoint_url": "https://api.fss.or.kr/v1/contract",
            "timeout_ms": 5000,
            "max_retry": 3,
            "enabled": True,
        },
        cookies=auth_cookies,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "금감원 계약조회"
    assert data["protocol"] == "REST"


@pytest.mark.asyncio
async def test_list_interfaces(client: AsyncClient, auth_cookies: dict, sample_config: dict):
    resp = await client.get("/api/interfaces", cookies=auth_cookies)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(c["id"] == sample_config["id"] for c in data["items"])


@pytest.mark.asyncio
async def test_update_interface(client: AsyncClient, auth_cookies: dict, sample_config: dict):
    resp = await client.put(
        f"/api/interfaces/{sample_config['id']}",
        json={"timeout_ms": 8000, "description": "수정된 설명"},
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    assert resp.json()["timeout_ms"] == 8000


@pytest.mark.asyncio
async def test_toggle_interface(client: AsyncClient, auth_cookies: dict, sample_config: dict):
    resp = await client.patch(
        f"/api/interfaces/{sample_config['id']}/toggle",
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    resp2 = await client.patch(
        f"/api/interfaces/{sample_config['id']}/toggle",
        cookies=auth_cookies,
    )
    assert resp2.json()["enabled"] is True


@pytest.mark.asyncio
async def test_delete_interface(client: AsyncClient, auth_cookies: dict, sample_config: dict):
    resp = await client.delete(
        f"/api/interfaces/{sample_config['id']}",
        cookies=auth_cookies,
    )
    assert resp.status_code == 204

    resp2 = await client.get("/api/interfaces", cookies=auth_cookies)
    assert all(c["id"] != sample_config["id"] for c in resp2.json()["items"])


@pytest.mark.asyncio
async def test_execute_disabled_returns_400(client: AsyncClient, auth_cookies: dict, sample_config: dict):
    # Disable first
    await client.patch(
        f"/api/interfaces/{sample_config['id']}/toggle",
        cookies=auth_cookies,
    )
    resp = await client.post(
        f"/api/interfaces/{sample_config['id']}/execute",
        cookies=auth_cookies,
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INTERFACE_DISABLED"


@pytest.mark.asyncio
async def test_execute_success(client: AsyncClient, auth_cookies: dict, sample_config: dict):
    with patch(
        "app.services.mock_service.dispatch",
        new_callable=AsyncMock,
        return_value=("SUCCESS", 342, '{"status":"SUCCESS"}'),
    ):
        resp = await client.post(
            f"/api/interfaces/{sample_config['id']}/execute",
            cookies=auth_cookies,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["response_ms"] == 342


@pytest.mark.asyncio
async def test_invalid_protocol_returns_422(client: AsyncClient, auth_cookies: dict):
    resp = await client.post(
        "/api/interfaces",
        json={
            "name": "잘못된 프로토콜",
            "protocol": "INVALID",
            "target_org": "기관",
            "endpoint_url": "https://example.com",
        },
        cookies=auth_cookies,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_requires_auth(client: AsyncClient):
    resp = await client.get("/api/interfaces")
    assert resp.status_code == 401
