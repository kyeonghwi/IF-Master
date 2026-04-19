import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

TARGET_ORGS = ["금감원", "KB국민은행", "NH농협은행", "삼성화재", "현대해상", "DB손해보험", "한화생명", "교보생명"]

ORG_MAP = {
    "금감원": "FSS",
    "KB국민은행": "KB",
    "NH농협은행": "NH",
    "삼성화재": "SAMSUNG",
    "현대해상": "HYUNDAI",
    "DB손해보험": "DB",
    "한화생명": "HANWHA",
    "교보생명": "KYOBO",
}

SERVICES = {
    "금감원": ["보험료납입통보", "계약사항보고", "사고통보"],
    "KB국민은행": ["계좌이체요청", "잔액조회", "보험료납입"],
    "NH농협은행": ["계좌이체요청", "자동이체등록", "보험료납입"],
    "삼성화재": ["보험금청구", "계약조회", "보험료조회"],
    "현대해상": ["보험금청구", "계약조회", "갱신처리"],
    "DB손해보험": ["보험금청구", "계약변경", "해지처리"],
    "한화생명": ["계약조회", "보험료납입", "수익자변경"],
    "교보생명": ["계약조회", "보험금청구", "계약변경"],
}

PROTOCOLS = ["REST", "SOAP", "BATCH"]
PROTOCOL_WEIGHTS = [0.6, 0.3, 0.1]
STATUS_CHOICES = ["SUCCESS", "FAILED", "PENDING"]
STATUS_WEIGHTS = [0.70, 0.20, 0.10]
ERRORS = [
    ("Connection timeout", "requests.exceptions.ConnectTimeout: HTTPSConnectionPool(host='api.fss.or.kr', port=443): Read timed out."),
    ("502 Bad Gateway", "httpx.HTTPStatusError: Server error '502 Bad Gateway'"),
    ("SSL handshake failed", "ssl.SSLError: [SSL: HANDSHAKE_FAILURE] handshake failure"),
]


def _make_key(target_org: str, called_at: datetime) -> str:
    date_str = called_at.strftime("%Y%m%d")
    uid = str(uuid.uuid4()).replace("-", "")[:8]
    return f"{ORG_MAP.get(target_org, target_org[:6])}-{date_str}-{uid}"


def start_scheduler(app) -> None:
    from app.db.database import AsyncSessionLocal
    from app.db.models import InterfaceLog

    loop = asyncio.get_running_loop()

    def generate_transactions() -> None:
        count = random.randint(1, 3)

        async def _work() -> None:
            now = datetime.utcnow()
            records: list[InterfaceLog] = []

            for _ in range(count):
                target_org = random.choice(TARGET_ORGS)
                protocol = random.choices(PROTOCOLS, weights=PROTOCOL_WEIGHTS)[0]
                service_name = random.choice(SERVICES[target_org])
                status = random.choices(STATUS_CHOICES, weights=STATUS_WEIGHTS)[0]
                called_at = now - timedelta(seconds=random.randint(0, 5))
                responded_at = (
                    called_at + timedelta(milliseconds=random.randint(80, 3000))
                    if status != "PENDING"
                    else None
                )
                error_message, stack_trace = (random.choice(ERRORS) if status == "FAILED" else (None, None))

                records.append(InterfaceLog(
                    id=uuid.uuid4(),
                    idempotency_key=_make_key(target_org, called_at),
                    target_org=target_org,
                    protocol=protocol,
                    service_name=service_name,
                    status=status,
                    error_message=error_message,
                    stack_trace=stack_trace,
                    called_at=called_at,
                    responded_at=responded_at,
                    retry_count=0,
                ))

            async with AsyncSessionLocal() as session:
                async with session.begin():
                    session.add_all(records)

            for record in records:
                event = {
                    "type": "transaction",
                    "data": {
                        "id": str(record.id),
                        "status": record.status,
                        "target_org": record.target_org,
                        "called_at": record.called_at.isoformat(),
                    },
                }
                for q in list(app.state.client_queues):
                    q.put_nowait(event)

        fut = asyncio.run_coroutine_threadsafe(_work(), loop)
        fut.add_done_callback(
            lambda f: print(f"[scheduler] error: {f.exception()}") if f.exception() else None
        )

    scheduler.add_job(generate_transactions, "interval", seconds=30)
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
