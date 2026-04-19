from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas import InterfacePerf, PerformanceResponse, SlaSummary, SlowAlert

router = APIRouter()

_SLA_THRESHOLD_MS = 3000


@router.get("/performance")
async def get_performance(
    from_dt: datetime | None = Query(default=None),
    to_dt: datetime | None = Query(default=None),
    protocol: str | None = Query(default=None),
    target_org: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    now = datetime.utcnow()
    effective_from = from_dt.replace(tzinfo=None) if from_dt else now - timedelta(hours=24)
    effective_to = to_dt.replace(tzinfo=None) if to_dt else now

    params: dict = {"from_dt": effective_from, "to_dt": effective_to, "sla_ms": _SLA_THRESHOLD_MS}
    filters = "called_at BETWEEN :from_dt AND :to_dt"

    if protocol:
        filters += " AND protocol = :protocol"
        params["protocol"] = protocol
    if target_org:
        filters += " AND target_org = :target_org"
        params["target_org"] = target_org

    perf_sql = text(f"""
        SELECT
            service_name,
            protocol,
            target_org,
            COUNT(*) AS call_count,
            COALESCE(AVG(response_ms), 0) AS avg_ms,
            COALESCE(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_ms), 0) AS p95_ms,
            COALESCE(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_ms), 0) AS p99_ms,
            COALESCE(
                COUNT(*) FILTER (WHERE response_ms < :sla_ms) * 100.0
                    / NULLIF(COUNT(*) FILTER (WHERE response_ms IS NOT NULL), 0),
                100.0
            ) AS sla_rate
        FROM interface_log
        WHERE {filters}
        GROUP BY service_name, protocol, target_org
        ORDER BY p95_ms DESC NULLS LAST
    """)

    rows = (await db.execute(perf_sql, params)).mappings().all()

    by_interface = [
        {
            "service_name": r["service_name"],
            "protocol": r["protocol"],
            "target_org": r["target_org"],
            "call_count": int(r["call_count"]),
            "avg_ms": float(r["avg_ms"]),
            "p95_ms": float(r["p95_ms"]),
            "p99_ms": float(r["p99_ms"]),
            "sla_rate": float(r["sla_rate"]),
        }
        for r in rows
    ]

    sla_sql = text(f"""
        SELECT
            COUNT(*) FILTER (WHERE response_ms IS NOT NULL) AS total_calls,
            COUNT(*) FILTER (WHERE response_ms < :sla_ms)   AS within_sla
        FROM interface_log
        WHERE {filters}
    """)
    sla_row = (await db.execute(sla_sql, params)).mappings().one()

    total_calls = int(sla_row["total_calls"] or 0)
    within_sla  = int(sla_row["within_sla"]  or 0)
    sla_rate    = (within_sla / total_calls * 100) if total_calls > 0 else 100.0

    slow_alerts = [
        {
            "service_name": r["service_name"],
            "protocol": r["protocol"],
            "p95_ms": r["p95_ms"],
            "call_count": r["call_count"],
        }
        for r in by_interface
        if r["p95_ms"] > _SLA_THRESHOLD_MS
    ]

    return {
        "by_interface": by_interface,
        "sla_summary": {"total_calls": total_calls, "within_sla": within_sla, "sla_rate": sla_rate},
        "slow_alerts": slow_alerts,
    }
