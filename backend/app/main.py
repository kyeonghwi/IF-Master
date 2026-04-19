import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import engine
from app.db.models import Base
from app.dependencies import require_auth
from app.routers import auth, logs, mock_router, retry, stats, stream
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
app.include_router(stream.router, prefix="/api")  # excluded: browser EventSource cannot set headers
app.include_router(mock_router.router)  # excluded: internal harness


@app.get("/health")
async def health():
    return {"status": "ok"}
