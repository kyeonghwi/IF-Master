import asyncio
import json

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.get("/stream")
async def stream(request: Request):
    client_queues: set[asyncio.Queue] = request.app.state.client_queues

    async def generator():
        q: asyncio.Queue = asyncio.Queue()
        client_queues.add(q)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25)
                    yield {
                        "event": event["type"],
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            client_queues.discard(q)

    return EventSourceResponse(generator())
