"""
Seed 500 mock interface_log records + pre-seed ~40 mock_responses for Case A demo.
Usage: python -m scripts.seed
"""

import asyncio
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ifmaster:ifmaster@localhost:5432/ifmaster")

TARGET_ORGS = ["금감원", "KB국민은행", "NH농협은행", "삼성화재", "현대해상", "DB손해보험", "한화생명", "교보생명"]
PROTOCOLS = ["REST", "SOAP", "BATCH", "MQ", "SFTP"]
PROTOCOL_WEIGHTS = [0.40, 0.25, 0.20, 0.10, 0.05]

# Protocol-specific response time ranges (ms)
PROTOCOL_RESPONSE_MS = {
    "REST":  (200,  2000),
    "SOAP":  (500,  3000),
    "MQ":    (100,  500),
    "BATCH": (5000, 30000),
    "SFTP":  (1000, 5000),
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

ERRORS = [
    ("Connection timeout", "requests.exceptions.ConnectTimeout: HTTPSConnectionPool(host='api.fss.or.kr', port=443): Read timed out."),
    ("502 Bad Gateway", "httpx.HTTPStatusError: Server error '502 Bad Gateway'"),
    ("SSL handshake failed", "ssl.SSLError: [SSL: HANDSHAKE_FAILURE] handshake failure"),
    ("DB connection lost", "sqlalchemy.exc.OperationalError: connection was closed in the middle of execution"),
    ("Invalid XML schema", "xml.etree.ElementTree.ParseError: syntax error: line 1, column 0"),
]

STATUS_CHOICES = ["SUCCESS", "FAILED", "PENDING"]
STATUS_WEIGHTS = [0.70, 0.20, 0.10]

NOW = datetime.now(timezone.utc)

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


def make_idempotency_key(target_org: str, called_at: datetime) -> str:
    date_str = called_at.strftime("%Y%m%d")
    uid = str(uuid.uuid4()).replace("-", "")[:8]
    org_code = ORG_MAP.get(target_org, target_org[:6])
    return f"{org_code}-{date_str}-{uid}"


def make_request_payload(protocol: str, service_name: str) -> str:
    if protocol == "SOAP":
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">\n'
            f'  <soapenv:Body>\n'
            f'    <{service_name}Request>\n'
            f'      <contractNo>{random.randint(10000000, 99999999)}</contractNo>\n'
            f'      <requestDate>{NOW.strftime("%Y%m%d")}</requestDate>\n'
            f'    </{service_name}Request>\n'
            f'  </soapenv:Body>\n'
            f'</soapenv:Envelope>'
        )
    return json.dumps({
        "service": service_name,
        "contractNo": str(random.randint(10000000, 99999999)),
        "requestDate": NOW.strftime("%Y-%m-%d"),
        "amount": random.randint(10000, 500000),
    }, ensure_ascii=False)


def make_response_payload(status: str, service_name: str, protocol: str) -> str | None:
    if status == "PENDING":
        return None
    if status == "SUCCESS":
        if protocol == "SOAP":
            return (
                f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">\n'
                f'  <soapenv:Body>\n'
                f'    <{service_name}Response>\n'
                f'      <resultCode>0000</resultCode>\n'
                f'      <resultMessage>정상처리</resultMessage>\n'
                f'      <processedAt>{NOW.isoformat()}</processedAt>\n'
                f'    </{service_name}Response>\n'
                f'  </soapenv:Body>\n'
                f'</soapenv:Envelope>'
            )
        return json.dumps({
            "resultCode": "0000",
            "resultMessage": "정상처리",
            "processedAt": NOW.isoformat(),
        }, ensure_ascii=False)
    return None


def make_record() -> dict:
    target_org = random.choice(TARGET_ORGS)
    protocol = random.choices(PROTOCOLS, weights=PROTOCOL_WEIGHTS)[0]
    service_name = random.choice(SERVICES[target_org])
    status = random.choices(STATUS_CHOICES, weights=STATUS_WEIGHTS)[0]

    offset_seconds = random.randint(0, 7 * 24 * 3600)
    called_at = NOW - timedelta(seconds=offset_seconds)
    ms_range = PROTOCOL_RESPONSE_MS.get(protocol, (200, 2000))
    response_ms_val = random.randint(*ms_range) if status != "PENDING" else None
    responded_at = (called_at + timedelta(milliseconds=response_ms_val)) if response_ms_val else None

    error_message = None
    stack_trace = None
    if status == "FAILED":
        err = random.choice(ERRORS)
        error_message, stack_trace = err

    # Cap at 2 so retry_count >= 3 (→ 400 blocked) is never pre-seeded
    retry_count = random.randint(1, 2) if status == "FAILED" and random.random() < 0.3 else 0

    return {
        "id": uuid.uuid4(),
        "idempotency_key": make_idempotency_key(target_org, called_at),
        "target_org": target_org,
        "protocol": protocol,
        "service_name": service_name,
        "status": status,
        "request_payload": make_request_payload(protocol, service_name),
        "response_payload": make_response_payload(status, service_name, protocol),
        "error_message": error_message,
        "stack_trace": stack_trace,
        "called_at": called_at,
        "responded_at": responded_at,
        "response_ms": response_ms_val,
        "retry_count": retry_count,
    }


INTERFACE_CONFIGS = [
    {"name": "금감원 보험계약 조회",    "protocol": "REST",  "target_org": "금감원",     "endpoint_url": "https://api.fss.or.kr/v1/contract/query",       "timeout_ms": 5000,  "max_retry": 3, "description": "금감원 보험계약 현황 조회 API"},
    {"name": "금감원 사고통보",         "protocol": "SOAP",  "target_org": "금감원",     "endpoint_url": "https://ws.fss.or.kr/services/AccidentNotify",   "timeout_ms": 8000,  "max_retry": 2, "description": "금감원 사고 발생 통보 SOAP 서비스"},
    {"name": "KB 계좌이체 요청",        "protocol": "REST",  "target_org": "KB국민은행", "endpoint_url": "https://api.kbstar.com/v2/transfer",             "timeout_ms": 3000,  "max_retry": 3, "description": "KB국민은행 보험료 자동이체 API"},
    {"name": "KB 잔액조회",            "protocol": "REST",  "target_org": "KB국민은행", "endpoint_url": "https://api.kbstar.com/v2/balance",              "timeout_ms": 2000,  "max_retry": 1, "description": "출금계좌 잔액 사전 확인"},
    {"name": "NH 자동이체 등록",        "protocol": "SOAP",  "target_org": "NH농협은행", "endpoint_url": "https://ws.nhbank.or.kr/AutoTransfer",           "timeout_ms": 6000,  "max_retry": 2, "description": "NH농협 자동이체 등록 서비스"},
    {"name": "손해율 일괄 배치",        "protocol": "BATCH", "target_org": "내부",       "endpoint_url": "/batch/jobs/loss-ratio-daily",                   "timeout_ms": 60000, "max_retry": 1, "schedule_cron": "0 2 * * *", "description": "전일 손해율 집계 야간 배치 (매일 02:00)"},
    {"name": "계약 갱신 배치",         "protocol": "BATCH", "target_org": "내부",       "endpoint_url": "/batch/jobs/contract-renewal",                   "timeout_ms": 120000,"max_retry": 1, "schedule_cron": "0 1 * * *", "description": "만기 도래 계약 자동 갱신 배치 (매일 01:00)"},
    {"name": "MQ 보험료납입 통보",      "protocol": "MQ",    "target_org": "삼성화재",   "endpoint_url": "mq://SAMSUNG.PREMIUM.NOTIFY",                   "timeout_ms": 2000,  "max_retry": 5, "description": "ActiveMQ 보험료 납입 완료 메시지 발행"},
    {"name": "SFTP 계약파일 수신",      "protocol": "SFTP",  "target_org": "한화생명",   "endpoint_url": "sftp://hanwha-life.co.kr/contracts/inbound/",    "timeout_ms": 30000, "max_retry": 2, "description": "한화생명 계약 데이터 파일 일괄 수신"},
    {"name": "현대해상 갱신처리",       "protocol": "REST",  "target_org": "현대해상",   "endpoint_url": "https://api.hi.co.kr/v1/renewal",               "timeout_ms": 5000,  "max_retry": 3, "description": "현대해상 계약 만기 갱신 처리 API", "enabled": False},
]


async def seed():
    from app.db.models import Base, InterfaceConfig, InterfaceLog, MockResponse

    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    records = [make_record() for _ in range(500)]

    async with session_factory() as session:
        async with session.begin():
            session.add_all([InterfaceLog(**r) for r in records])

    # Pre-seed mock_responses for ~40 FAILED records so Case A (멱등성) fires on first click.
    failed_records = [r for r in records if r["status"] == "FAILED"]
    preseed_targets = random.sample(failed_records, min(40, len(failed_records)))
    mock_rows = [
        MockResponse(
            idempotency_key=r["idempotency_key"],
            status="SUCCESS",
            response_json=json.dumps({
                "resultCode": "0000",
                "resultMessage": "정상처리",
                "processedAt": NOW.isoformat(),
            }, ensure_ascii=False),
        )
        for r in preseed_targets
    ]

    async with session_factory() as session:
        async with session.begin():
            session.add_all(mock_rows)

    # Seed interface_config
    async with session_factory() as session:
        async with session.begin():
            for cfg_data in INTERFACE_CONFIGS:
                cfg = InterfaceConfig(**{k: v for k, v in cfg_data.items()})
                session.add(cfg)

    await engine.dispose()

    status_counts: dict[str, int] = {}
    for r in records:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    print(f"Seeded {len(records)} interface_log records:")
    for s, c in sorted(status_counts.items()):
        print(f"  {s}: {c} ({c / len(records) * 100:.1f}%)")
    print(f"Pre-seeded {len(mock_rows)} mock_responses (Case A 데모용)")
    print(f"Seeded {len(INTERFACE_CONFIGS)} interface_config entries")


if __name__ == "__main__":
    asyncio.run(seed())
