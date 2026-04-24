import asyncio
import json
import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import MockResponse

router = APIRouter(prefix="/mock")
# No authentication: intentional internal harness. The retry router and
# execute_interface call these endpoints internally via httpx. Adding auth
# would require threading the bearer token through those internal calls.


@router.get("/status")
async def mock_status(key: str, db: AsyncSession = Depends(get_db)):
    stmt = select(MockResponse).where(MockResponse.idempotency_key == key)
    row = (await db.execute(stmt)).scalar_one_or_none()

    if row is None:
        return {"status": "not_found"}
    return {"status": row.status, "response": json.loads(row.response_json)}


@router.post("/call")
async def mock_call(key: str, db: AsyncSession = Depends(get_db)):
    roll = random.random()

    if roll < 0.6:
        outcome = "SUCCESS"
    elif roll < 0.9:
        outcome = "FAILED"
    else:
        await asyncio.sleep(3)
        outcome = "SUCCESS" if random.random() < 0.5 else "FAILED"

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if outcome == "SUCCESS":
        response_json = json.dumps({"status": "SUCCESS", "data": {"processed_at": now.isoformat()}})
        payload = {"status": "SUCCESS", "data": {"processed_at": now.isoformat()}}
    else:
        response_json = json.dumps({"status": "FAILED", "error": "Connection timeout", "code": 503})
        payload = {"status": "FAILED", "error": "Connection timeout", "code": 503}

    stmt = (
        insert(MockResponse)
        .values(idempotency_key=key, status=outcome, response_json=response_json)
        .on_conflict_do_update(
            index_elements=["idempotency_key"],
            set_={"status": outcome, "response_json": response_json},
        )
    )
    async with db.begin():
        await db.execute(stmt)

    return payload
