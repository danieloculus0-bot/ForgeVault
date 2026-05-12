import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .database import Base
from .models import utcnow


JsonType = JSON().with_variant(JSONB, "postgresql")


class ReviewRequest(Base):
    __tablename__ = "review_requests"
    __table_args__ = (
        Index("ix_review_requests_status", "status"),
        Index("ix_review_requests_type_status", "request_type", "status"),
        Index("ix_review_requests_entity", "entity_type", "entity_id"),
        Index("ix_review_requests_assigned_checker", "assigned_checker"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="low", nullable=False)
    submitted_by: Mapped[str] = mapped_column(String(128), nullable=False)
    assigned_checker: Mapped[str | None] = mapped_column(String(128), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    record_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    file_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    source_folder_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class NotificationEvent(Base):
    __tablename__ = "notification_events"
    __table_args__ = (
        Index("ix_notification_events_status", "status"),
        Index("ix_notification_events_type_status", "event_type", "status"),
        Index("ix_notification_events_entity", "entity_type", "entity_id"),
        Index("ix_notification_events_recipient", "recipient"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="logged", nullable=False)
    channel: Mapped[str] = mapped_column(String(32), default="app", nullable=False)
    recipient: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
