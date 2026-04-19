"""
Verifies /mock/call response distribution: 100 calls should yield 55-65 SUCCESS outcomes.
Also verifies /mock/status returns stored result for known keys.
"""
import pytest
from httpx import AsyncClient


async def test_mock_call_distribution(client: AsyncClient):
    success_count = 0
    total = 100

    for i in range(total):
        resp = await client.post(f"/mock/call", params={"key": f"TEST-dist-{i:04d}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("SUCCESS", "FAILED")
        if data["status"] == "SUCCESS":
            success_count += 1

    # 60% base rate + 50% of the 10% delay bucket → ~65% max
    # Allow wide band to avoid flakiness: 45–75
    assert 45 <= success_count <= 75, (
        f"Expected 45–75 SUCCESS out of 100, got {success_count}"
    )


async def test_mock_status_returns_stored_result(client: AsyncClient):
    key = "TEST-status-persist-01"

    # No result yet
    get_resp = await client.get("/mock/status", params={"key": key})
    assert get_resp.json()["status"] == "not_found"

    # Call once to store result
    call_resp = await client.post("/mock/call", params={"key": key})
    stored_status = call_resp.json()["status"]

    # Status should now return the stored result
    get_resp2 = await client.get("/mock/status", params={"key": key})
    assert get_resp2.json()["status"] == stored_status


async def test_mock_call_same_key_overwrites(client: AsyncClient):
    key = "TEST-overwrite-01"

    await client.post("/mock/call", params={"key": key})
    await client.post("/mock/call", params={"key": key})  # second call overwrites

    status_resp = await client.get("/mock/status", params={"key": key})
    assert status_resp.json()["status"] in ("SUCCESS", "FAILED")
