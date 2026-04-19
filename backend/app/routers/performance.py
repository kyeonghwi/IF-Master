from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import InterfaceLog
from app.schemas import InterfacePerf, PerformanceResponse, SlaSummary, SlowAlert

router = APIRouter()

_SLA_THRESHOLD_MS = 3000


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance(
    from_dt: datetime | None = Query(default=None),
    to_dt: datetime | None = Query(default=None),
    protocol: str | None = Query(default=None),
    target_org: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    effective_from = from_dt.replace(tzinfo=None) if from_dt else now - timedelta(hours=24)
    effective_to = to_dt.replace(tzinfo=None) if to_dt else now

    # Per-interface aggregation using percentile_cont
    perf_sql = text("""
        SELECT
            service_name,
            protocol,
            target_org,
            COUNT(*) AS call_count,
            COALESCE(AVG(response_ms), 0) AS avg_ms,
            COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_ms), 0) AS p95_ms,
            COALESCE(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_ms), 0) AS p99_ms,
            COALESCE(
                COUNT(*) FILTER (WHERE response_ms < :sla_ms) * 100.0 / NULLIF(COUNT(*) FILTER (WHERE response_ms IS NOT NULL), 0),
                100.0
            ) AS sla_rate
        FROM interface_log
        WHERE called_at BETWEEN :from_dt AND :to_dt
          AND (:protocol IS NULL OR protocol = :protocol)
          AND (:target_org IS NULL OR target_org = :target_org)
        GROUP BY service_name, protocol, target_org
        ORDER BY p95_ms DESC NULLS LAST
    """)

    rows = (await db.execute(perf_sql, {
        "from_dt": effective_from,
        "to_dt": effective_to,
        "protocol": protocol,
        "target_org": target_org,
        "sla_ms": _SLA_THRESHOLD_MS,
    })).mappings().all()

    by_interface = [
        InterfacePerf(
            service_name=r["service_name"],
            protocol=r["protocol"],
            target_org=r["target_org"],
            call_count=r["call_count"],
            avg_ms=float(r["avg_ms"]),
            p95_ms=float(r["p95_ms"]),
            p99_ms=float(r["p99_ms"]),
            sla_rate=float(r["sla_rate"]),
        )
        for r in rows
    ]

    # SLA summary
    sla_sql = text("""
        SELECT
            COUNT(*) FILTER (WHERE response_ms IS NOT NULL) AS total_calls,
            COUNT(*) FILTER (WHERE response_ms < :sla_ms) AS within_sla
        FROM interface_log
        WHERE called_at BETWEEN :from_dt AND :to_dt
          AND (:protocol IS NULL OR protocol = :protocol)
          AND (:target_org IS NULL OR target_org = :target_org)
    """)
    sla_row = (await db.execute(sla_sql, {
        "from_dt": effective_from,
        "to_dt": effective_to,
        "protocol": protocol,
        "target_org": target_org,
        "sla_ms": _SLA_THRESHOLD_MS,
    })).mappings().one()

    total_calls = sla_row["total_calls"] or 0
    within_sla = sla_row["within_sla"] or 0
    sla_rate = (within_sla / total_calls * 100) if total_calls > 0 else 100.0

    slow_alerts = [
        SlowAlert(
            service_name=r.service_name,
            protocol=r.protocol,
            p95_ms=r.p95_ms,
            call_count=r.call_count,
        )
        for r in by_interface
        if r.p95_ms > _SLA_THRESHOLD_MS
    ]

    return PerformanceResponse(
        by_interface=by_interface,
        sla_summary=SlaSummary(total_calls=total_calls, within_sla=within_sla, sla_rate=sla_rate),
        slow_alerts=slow_alerts,
    )
