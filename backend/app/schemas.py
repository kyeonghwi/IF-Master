import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class AuditLogSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interface_log_id: uuid.UUID
    action: str
    operator: str
    executed_at: datetime
    result: str
    result_payload: str | None


class InterfaceLogSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    idempotency_key: str
    target_org: str
    protocol: str
    service_name: str
    status: str
    called_at: datetime
    responded_at: datetime | None
    retry_count: int
    error_message: str | None


class InterfaceLogDetail(InterfaceLogSummary):
    model_config = ConfigDict(from_attributes=True)

    request_payload: str | None
    response_payload: str | None
    stack_trace: str | None
    audit_logs: list[AuditLogSchema]


class SeriesPoint(BaseModel):
    timestamp: datetime
    success: int
    failed: int
    pending: int


class StatsResponse(BaseModel):
    total: int
    success: int
    failed: int
    pending: int
    series: list[SeriesPoint]


class LogsResponse(BaseModel):
    items: list[InterfaceLogSummary]
    total: int
    page: int
    size: int


# --- Interface Config ---

class InterfaceConfigCreate(BaseModel):
    name: str
    protocol: str
    target_org: str
    endpoint_url: str
    timeout_ms: int = 5000
    max_retry: int = 3
    enabled: bool = True
    schedule_cron: str | None = None
    description: str | None = None


class InterfaceConfigUpdate(BaseModel):
    name: str | None = None
    protocol: str | None = None
    target_org: str | None = None
    endpoint_url: str | None = None
    timeout_ms: int | None = None
    max_retry: int | None = None
    enabled: bool | None = None
    schedule_cron: str | None = None
    description: str | None = None


class InterfaceConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    protocol: str
    target_org: str
    endpoint_url: str
    timeout_ms: int
    max_retry: int
    enabled: bool
    schedule_cron: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class InterfaceConfigListResponse(BaseModel):
    items: list[InterfaceConfigResponse]
    total: int


class ExecuteResult(BaseModel):
    log_id: uuid.UUID
    status: str
    response_ms: int | None
    message: str


# --- Performance ---

class InterfacePerf(BaseModel):
    service_name: str
    protocol: str
    target_org: str
    call_count: int
    avg_ms: float
    p95_ms: float
    p99_ms: float
    sla_rate: float


class SlaSummary(BaseModel):
    total_calls: int
    within_sla: int
    sla_rate: float


class SlowAlert(BaseModel):
    service_name: str
    protocol: str
    p95_ms: float
    call_count: int


class PerformanceResponse(BaseModel):
    by_interface: list[InterfacePerf]
    sla_summary: SlaSummary
    slow_alerts: list[SlowAlert]
