from sqlalchemy.orm import Session

from ..models import AuditLog


def audit(session: Session, *, actor: str, action: str, entity_type: str, entity_id: str, details: dict | None = None) -> None:
    session.add(
        AuditLog(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )
