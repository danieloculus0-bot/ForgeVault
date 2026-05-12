from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import utcnow
from ..workflow_model import ReviewRequest
from .audit import audit
from .notifications import log_notification

VALID_REVIEW_STATUSES = {"pending", "approved", "rejected", "cancelled", "completed"}
VALID_RISK_LEVELS = {"low", "medium", "high", "critical"}


def create_review_request(
    session: Session,
    *,
    request_type: str,
    submitted_by: str,
    entity_type: str,
    entity_id: str,
    summary: str,
    reason: str | None = None,
    risk_level: str = "low",
    assigned_checker: str | None = None,
    record_id: UUID | None = None,
    file_version_id: UUID | None = None,
    source_folder_id: UUID | None = None,
    details: dict | None = None,
) -> ReviewRequest:
    if risk_level not in VALID_RISK_LEVELS:
        raise ValueError(f"invalid risk level: {risk_level}")
    review = ReviewRequest(
        request_type=request_type,
        submitted_by=submitted_by,
        assigned_checker=assigned_checker,
        entity_type=entity_type,
        entity_id=entity_id,
        record_id=record_id,
        file_version_id=file_version_id,
        source_folder_id=source_folder_id,
        summary=summary,
        reason=reason,
        risk_level=risk_level,
        details=details or {},
    )
    session.add(review)
    session.flush()
    audit(
        session,
        actor=submitted_by,
        action="review.submitted",
        entity_type="review_requests",
        entity_id=str(review.id),
        details={"request_type": request_type, "risk_level": risk_level, "summary": summary},
    )
    log_notification(
        session,
        event_type="review.requested",
        subject=f"Review requested: {summary}",
        body=reason or summary,
        entity_type="review_requests",
        entity_id=str(review.id),
        created_by=submitted_by,
        recipient=assigned_checker,
        payload={"request_type": request_type, "risk_level": risk_level, "entity_type": entity_type, "entity_id": entity_id},
    )
    return review


def list_review_requests(session: Session, *, status: str | None = "pending", assigned_checker: str | None = None, limit: int = 100) -> list[ReviewRequest]:
    statement = select(ReviewRequest).order_by(ReviewRequest.created_at.desc()).limit(limit)
    if status:
        statement = statement.where(ReviewRequest.status == status)
    if assigned_checker:
        statement = statement.where(ReviewRequest.assigned_checker == assigned_checker)
    return session.scalars(statement).all()


def get_review_request(session: Session, review_id: UUID) -> ReviewRequest:
    review = session.get(ReviewRequest, review_id)
    if not review:
        raise ValueError("review request not found")
    return review


def review_decision(session: Session, *, review_id: UUID, reviewer: str, decision: str, comment: str | None = None) -> ReviewRequest:
    if decision not in {"approved", "rejected", "cancelled"}:
        raise ValueError("decision must be approved, rejected, or cancelled")
    review = get_review_request(session, review_id)
    if review.status != "pending":
        raise ValueError(f"review request is already {review.status}")
    review.status = decision
    review.reviewed_by = reviewer
    review.reviewed_at = utcnow()
    review.review_comment = comment
    audit(
        session,
        actor=reviewer,
        action=f"review.{decision}",
        entity_type="review_requests",
        entity_id=str(review.id),
        details={"comment": comment, "request_type": review.request_type, "submitted_by": review.submitted_by},
    )
    log_notification(
        session,
        event_type=f"review.{decision}",
        subject=f"Review {decision}: {review.summary}",
        body=comment or f"Review request was {decision}.",
        entity_type="review_requests",
        entity_id=str(review.id),
        created_by=reviewer,
        recipient=review.submitted_by,
        payload={"request_type": review.request_type, "decision": decision},
    )
    return review
