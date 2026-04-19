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
