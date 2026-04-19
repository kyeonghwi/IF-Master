import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import AsyncSessionLocal, engine
from app.db.models import Base, InterfaceConfig
from app.dependencies import require_auth
from app.routers import auth, interfaces, logs, mock_router, performance, retry, stats, stream
from app.services.scheduler import start_scheduler, stop_scheduler


_INTERFACE_CONFIGS = [
    {"name": "금감원 보험계약 조회",  "protocol": "REST",  "target_org": "금감원",     "endpoint_url": "https://api.fss.or.kr/v1/contract/query",     "timeout_ms": 5000,   "max_retry": 3, "description": "금감원 보험계약 현황 조회 API"},
    {"name": "금감원 사고통보",       "protocol": "SOAP",  "target_org": "금감원",     "endpoint_url": "https://ws.fss.or.kr/services/AccidentNotify", "timeout_ms": 8000,   "max_retry": 2, "description": "금감원 사고 발생 통보 SOAP 서비스"},
    {"name": "KB 계좌이체 요청",      "protocol": "REST",  "target_org": "KB국민은행", "endpoint_url": "https://api.kbstar.com/v2/transfer",           "timeout_ms": 3000,   "max_retry": 3, "description": "KB국민은행 보험료 자동이체 API"},
    {"name": "KB 잔액조회",          "protocol": "REST",  "target_org": "KB국민은행", "endpoint_url": "https://api.kbstar.com/v2/balance",            "timeout_ms": 2000,   "max_retry": 1, "description": "출금계좌 잔액 사전 확인"},
    {"name": "NH 자동이체 등록",      "protocol": "SOAP",  "target_org": "NH농협은행", "endpoint_url": "https://ws.nhbank.or.kr/AutoTransfer",         "timeout_ms": 6000,   "max_retry": 2, "description": "NH농협 자동이체 등록 서비스"},
    {"name": "손해율 일괄 배치",      "protocol": "BATCH", "target_org": "내부",       "endpoint_url": "/batch/jobs/loss-ratio-daily",                 "timeout_ms": 60000,  "max_retry": 1, "schedule_cron": "0 2 * * *", "description": "전일 손해율 집계 야간 배치"},
    {"name": "계약 갱신 배치",       "protocol": "BATCH", "target_org": "내부",       "endpoint_url": "/batch/jobs/contract-renewal",                 "timeout_ms": 120000, "max_retry": 1, "schedule_cron": "0 1 * * *", "description": "만기 도래 계약 자동 갱신 배치"},
    {"name": "MQ 보험료납입 통보",    "protocol": "MQ",    "target_org": "삼성화재",   "endpoint_url": "mq://SAMSUNG.PREMIUM.NOTIFY",                 "timeout_ms": 2000,   "max_retry": 5, "description": "ActiveMQ 보험료 납입 완료 메시지"},
    {"name": "SFTP 계약파일 수신",    "protocol": "SFTP",  "target_org": "한화생명",   "endpoint_url": "sftp://hanwha-life.co.kr/contracts/inbound/",  "timeout_ms": 30000,  "max_retry": 2, "description": "한화생명 계약 데이터 파일 수신"},
    {"name": "현대해상 갱신처리",     "protocol": "REST",  "target_org": "현대해상",   "endpoint_url": "https://api.hi.co.kr/v1/renewal",             "timeout_ms": 5000,   "max_retry": 3, "enabled": False, "description": "현대해상 계약 갱신 API"},
]


async def _seed_interface_configs() -> None:
    from sqlalchemy import func, select
    async with AsyncSessionLocal() as session:
        count = (await session.execute(select(func.count()).select_from(InterfaceConfig))).scalar_one()
    if count > 0:
        return
    async with AsyncSessionLocal() as session:
        async with session.begin():
            for data in _INTERFACE_CONFIGS:
                session.add(InterfaceConfig(**data))


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_interface_configs()

    app.state.client_queues: set[asyncio.Queue] = set()

    def broadcast_event(event_type: str, data: dict) -> None:
        event = {"type": event_type, "data": data}
        for q in list(app.state.client_queues):
            q.put_nowait(event)

    app.state.broadcast_event = broadcast_event

    start_scheduler(app)

    yield

    stop_scheduler()


app = FastAPI(title="IF-Master API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "https://if-master.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(stats.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(logs.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(retry.router, prefix="/api")  # auth injected per-route (needs username)
app.include_router(interfaces.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(performance.router, prefix="/api", dependencies=[Depends(require_auth)])
app.include_router(stream.router, prefix="/api")  # excluded: browser EventSource cannot set headers
app.include_router(mock_router.router)  # excluded: internal harness


@app.get("/health")
async def health():
    return {"status": "ok"}
