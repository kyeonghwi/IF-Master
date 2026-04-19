import pytest
from httpx import AsyncClient

from app.config import settings


async def test_login_success(client: AsyncClient):
    resp = await client.post(
        "/auth/login",
        json={"username": settings.demo_username, "password": settings.demo_password},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert "access_token" in resp.cookies


async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post(
        "/auth/login",
        json={"username": settings.demo_username, "password": "wrongpass"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"


async def test_login_wrong_username(client: AsyncClient):
    resp = await client.post(
        "/auth/login",
        json={"username": "nobody", "password": settings.demo_password},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"


async def test_protected_route_without_token(client: AsyncClient):
    resp = await client.get("/api/stats")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "MISSING_TOKEN"


async def test_protected_route_with_invalid_token(client: AsyncClient):
    resp = await client.get("/api/stats", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_TOKEN"


async def test_cookie_allows_access(client: AsyncClient):
    login_resp = await client.post(
        "/auth/login",
        json={"username": settings.demo_username, "password": settings.demo_password},
    )
    token = login_resp.cookies["access_token"]
    resp = await client.get("/api/stats", cookies={"access_token": token})
    assert resp.status_code == 200


async def test_logout_clears_cookie(client: AsyncClient):
    await client.post(
        "/auth/login",
        json={"username": settings.demo_username, "password": settings.demo_password},
    )
    resp = await client.post("/auth/logout")
    assert resp.status_code == 200
    assert resp.cookies.get("access_token", "") == ""
