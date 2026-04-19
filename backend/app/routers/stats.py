from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import InterfaceLog
from app.schemas import SeriesPoint, StatsResponse

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    from_dt: datetime | None = Query(default=None),
    to_dt: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    now = datetime.utcnow()
    effective_from = (from_dt.replace(tzinfo=None) if from_dt is not None else now - timedelta(hours=24))
    effective_to = (to_dt.replace(tzinfo=None) if to_dt is not None else now)

    summary_stmt = (
        select(InterfaceLog.status, func.count().label("cnt"))
        .where(
            InterfaceLog.called_at >= effective_from,
            InterfaceLog.called_at <= effective_to,
        )
        .group_by(InterfaceLog.status)
    )
    result = await db.execute(summary_stmt)
    counts: dict[str, int] = {"SUCCESS": 0, "FAILED": 0, "PENDING": 0}
    for status, cnt in result.all():
        if status in counts:
            counts[status] = cnt

    series_stmt = (
        select(
            func.date_trunc("hour", InterfaceLog.called_at).label("bucket"),
            InterfaceLog.status,
            func.count().label("cnt"),
        )
        .where(
            InterfaceLog.called_at >= effective_from,
            InterfaceLog.called_at <= effective_to,
        )
        .group_by("bucket", InterfaceLog.status)
        .order_by("bucket")
    )
    series_result = await db.execute(series_stmt)

    buckets: dict[datetime, dict[str, int]] = {}
    for bucket, status, cnt in series_result.all():
        if bucket not in buckets:
            buckets[bucket] = {"SUCCESS": 0, "FAILED": 0, "PENDING": 0}
        if status in buckets[bucket]:
            buckets[bucket][status] = cnt

    series = [
        SeriesPoint(
            timestamp=bucket,
            success=b["SUCCESS"],
            failed=b["FAILED"],
            pending=b["PENDING"],
        )
        for bucket, b in sorted(buckets.items())
    ]

    return StatsResponse(
        total=sum(counts.values()),
        success=counts["SUCCESS"],
        failed=counts["FAILED"],
        pending=counts["PENDING"],
        series=series,
    )
