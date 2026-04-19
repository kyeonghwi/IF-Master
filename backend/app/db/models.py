import uuid
from datetime import datetime

from sqlalchemy import (
    UUID,
    TEXT,
    VARCHAR,
    Index,
    Integer,
    ForeignKey,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class InterfaceLog(Base):
    __tablename__ = "interface_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(VARCHAR(64), unique=True, nullable=False)
    target_org: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    protocol: Mapped[str] = mapped_column(VARCHAR(10), nullable=False)  # REST, SOAP, BATCH
    service_name: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(10), nullable=False)  # SUCCESS, FAILED, PENDING
    request_payload: Mapped[str | None] = mapped_column(TEXT)
    response_payload: Mapped[str | None] = mapped_column(TEXT)
    error_message: Mapped[str | None] = mapped_column(TEXT)
    stack_trace: Mapped[str | None] = mapped_column(TEXT)
    called_at: Mapped[datetime] = mapped_column(nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column()
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="interface_log")

    __table_args__ = (
        Index("ix_interface_log_status", "status"),
        Index("ix_interface_log_called_at", "called_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interface_log_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interface_log.id"), nullable=False)
    action: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)  # RETRY_REQUEST, RETRY_SUCCESS, etc.
    operator: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(nullable=False)
    result: Mapped[str] = mapped_column(VARCHAR(30), nullable=False)
    result_payload: Mapped[str | None] = mapped_column(TEXT)

    interface_log: Mapped["InterfaceLog"] = relationship(back_populates="audit_logs")


class MockResponse(Base):
    __tablename__ = "mock_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(VARCHAR(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(10), nullable=False)  # SUCCESS, FAILED
    response_json: Mapped[str | None] = mapped_column(TEXT)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
