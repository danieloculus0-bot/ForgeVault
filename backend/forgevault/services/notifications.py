from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..workflow_model import NotificationEvent
from .audit import audit


def log_notification(
    session: Session,
    *,
    event_type: str,
    subject: str,
    body: str,
    entity_type: str,
    entity_id: str,
    created_by: str,
    recipient: str | None = None,
    channel: str = "app",
    payload: dict | None = None,
) -> NotificationEvent:
    event = NotificationEvent(
        event_type=event_type,
        subject=subject,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        created_by=created_by,
        recipient=recipient,
        channel=channel,
        payload=payload or {},
    )
    session.add(event)
    session.flush()
    audit(
        session,
        actor=created_by,
        action="notification.logged",
        entity_type="notification_events",
        entity_id=str(event.id),
        details={"event_type": event_type, "target_entity_type": entity_type, "target_entity_id": entity_id, "channel": channel},
    )
    return event


def list_notifications(session: Session, *, status: str | None = None, limit: int = 100) -> list[NotificationEvent]:
    statement = select(NotificationEvent).order_by(NotificationEvent.created_at.desc()).limit(limit)
    if status:
        statement = statement.where(NotificationEvent.status == status)
    return session.scalars(statement).all()
