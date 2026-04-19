import asyncio
import json
import random
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MockResponse

# Protocol-specific response profiles
_PROFILES: dict[str, dict] = {
    "REST":  {"min_ms": 200,   "max_ms": 1500,  "success_rate": 0.70},
    "SOAP":  {"min_ms": 500,   "max_ms": 3000,  "success_rate": 0.65},
    "MQ":    {"min_ms": 100,   "max_ms": 500,   "success_rate": 0.85},
    "BATCH": {"min_ms": 5000,  "max_ms": 30000, "success_rate": 0.80},
    "SFTP":  {"min_ms": 1000,  "max_ms": 5000,  "success_rate": 0.75},
}
_DEFAULT_PROFILE = {"min_ms": 200, "max_ms": 2000, "success_rate": 0.70}


async def dispatch(
    key: str,
    protocol: str,
    timeout_ms: int,
    db: AsyncSession,
) -> tuple[str, int, str]:
    """Call mock for a given protocol. Returns (outcome, response_ms, response_json)."""
    profile = _PROFILES.get(protocol.upper(), _DEFAULT_PROFILE)

    delay_ms = random.randint(profile["min_ms"], profile["max_ms"])
    # Respect timeout
    actual_ms = min(delay_ms, timeout_ms)

    await asyncio.sleep(actual_ms / 1000)

    # 10% chance of delay-induced timeout
    timed_out = delay_ms > timeout_ms
    if timed_out:
        outcome = "FAILED"
    elif random.random() < profile["success_rate"]:
        outcome = "SUCCESS"
    else:
        outcome = "FAILED"

    now = datetime.utcnow()

    if outcome == "SUCCESS":
        if protocol.upper() == "SOAP":
            response_json = json.dumps({
                "status": "SUCCESS",
                "envelope": f"<resultCode>0000</resultCode><processedAt>{now.isoformat()}</processedAt>",
            })
        elif protocol.upper() == "MQ":
            response_json = json.dumps({"status": "SUCCESS", "ack": "ACK", "msgId": key})
        elif protocol.upper() == "BATCH":
            response_json = json.dumps({"status": "SUCCESS", "jobId": key, "processedAt": now.isoformat()})
        elif protocol.upper() == "SFTP":
            response_json = json.dumps({"status": "SUCCESS", "file": f"{key}.dat", "bytes": random.randint(1024, 102400)})
        else:
            response_json = json.dumps({"status": "SUCCESS", "data": {"processed_at": now.isoformat()}})
    else:
        reason = "Connection timeout" if timed_out else random.choice([
            "Connection refused", "502 Bad Gateway", "SSL handshake failed",
        ])
        response_json = json.dumps({"status": "FAILED", "error": reason, "code": 503})

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

    return outcome, actual_ms, response_json
