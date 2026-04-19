"""
Verifies SSE /api/stream sends a ping event within 35 seconds of connection.
Uses asyncio.timeout to cap the wait.
"""
import asyncio
import json
import pytest
from httpx import AsyncClient


async def test_sse_ping_received(client: AsyncClient):
    """SSE connection must receive a ping event within 35 seconds."""
    ping_received = asyncio.Event()
    lines_seen: list[str] = []

    async with client.stream("GET", "/api/stream") as resp:
        assert resp.status_code == 200

        async def read_until_ping():
            async for line in resp.aiter_lines():
                lines_seen.append(line)
                if line.startswith("event: ping"):
                    ping_received.set()
                    return

        try:
            async with asyncio.timeout(35):
                await read_until_ping()
        except TimeoutError:
            pass

    assert ping_received.is_set(), (
        f"No ping event received within 35s. Lines seen: {lines_seen[:20]}"
    )


async def test_sse_stream_responds_200(client: AsyncClient):
    """SSE endpoint must return 200 with text/event-stream content type."""
    async with client.stream("GET", "/api/stream") as resp:
        assert resp.status_code == 200
        content_type = resp.headers.get("content-type", "")
        assert "text/event-stream" in content_type
