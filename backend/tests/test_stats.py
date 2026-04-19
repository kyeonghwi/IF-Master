from httpx import AsyncClient


async def test_stats_empty_db(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["success"] == 0
    assert body["failed"] == 0
    assert body["pending"] == 0
    assert body["series"] == []


async def test_stats_counts_match_seeded_data(client: AsyncClient, auth_headers: dict, sample_logs):
    resp = await client.get("/api/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] == 3
    assert body["failed"] == 2
    assert body["pending"] == 1
    assert body["total"] == 6


async def test_stats_date_filter_excludes_old_records(client: AsyncClient, auth_headers: dict, sample_logs):
    # Set from_dt far in the future — should return zero
    resp = await client.get(
        "/api/stats",
        params={"from_dt": "2099-01-01T00:00:00Z", "to_dt": "2099-12-31T23:59:59Z"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


async def test_stats_requires_auth(client: AsyncClient):
    resp = await client.get("/api/stats")
    assert resp.status_code == 401
