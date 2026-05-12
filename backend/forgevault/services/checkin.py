from __future__ import annotations

import base64
from pathlib import Path

from sqlalchemy.orm import Session

from ..file_types import file_type_metadata
from ..models import Record
from .audit import audit
from .reviews import create_review_request
from .versioning import active_checkout, append_version_bytes


def _decode_base64(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64, validate=True)
    except Exception as exc:
        raise ValueError("content_base64 must be valid base64") from exc


def check_in_bytes(
    session: Session,
    *,
    record: Record,
    filename: str,
    original_source_path: str,
    content: bytes,
    actor: str,
    note: str | None = None,
    customer_revision: str | None = None,
    internal_revision: str | None = None,
    submit_for_review: bool = True,
    assigned_checker: str | None = None,
    risk_level: str = "low",
    metadata: dict | None = None,
) -> dict:
    checkout = active_checkout(session, record.id)
    if not checkout:
        raise ValueError("record must be checked out before check-in")
    if checkout.checked_out_by != actor:
        raise ValueError(f"record is checked out by {checkout.checked_out_by}; {actor} cannot check in this file")

    version_metadata = {
        "checkin": {
            "note": note,
            "submitted_by": actor,
            "source": "checkin",
        },
        "file_type": file_type_metadata(filename or original_source_path),
    }
    if metadata:
        version_metadata.update(metadata)

    version = append_version_bytes(
        session,
        record=record,
        filename=filename,
        original_source_path=original_source_path,
        content=content,
        customer_revision=customer_revision or record.customer_revision,
        internal_revision=internal_revision or record.internal_revision,
        metadata=version_metadata,
        actor=actor,
    )

    audit(
        session,
        actor=actor,
        action="checkin.completed",
        entity_type="records",
        entity_id=record.internal_record_id,
        details={"file_version_id": str(version.id), "filename": version.filename, "submit_for_review": submit_for_review},
    )

    review = None
    if submit_for_review:
        review = create_review_request(
            session,
            request_type="pending_checkin",
            submitted_by=actor,
            assigned_checker=assigned_checker,
            entity_type="records",
            entity_id=record.internal_record_id,
            record_id=record.id,
            file_version_id=version.id,
            summary=f"Review check-in: {version.filename}",
            reason=note or "New file version checked in for review.",
            risk_level=risk_level,
            details={
                "source": "checkin",
                "filename": version.filename,
                "original_source_path": original_source_path,
                "version_number": version.version_number,
                "file_type": version_metadata.get("file_type", {}),
            },
        )

    return {"record": record, "file_version": version, "review": review}


def check_in_base64(session: Session, *, record: Record, content_base64: str, **kwargs) -> dict:
    return check_in_bytes(session, record=record, content=_decode_base64(content_base64), **kwargs)


def check_in_from_path(session: Session, *, record: Record, file_path: str, actor: str, **kwargs) -> dict:
    path = Path(file_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        raise ValueError(f"check-in file does not exist: {file_path}")
    return check_in_bytes(
        session,
        record=record,
        filename=kwargs.pop("filename", None) or path.name,
        original_source_path=str(path),
        content=path.read_bytes(),
        actor=actor,
        **kwargs,
    )
