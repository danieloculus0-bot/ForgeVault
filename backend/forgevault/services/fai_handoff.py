"""Read-only controlled PDF handoff, verified against actual released vault content."""
from __future__ import annotations

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import settings
from ..models import FileVersion, Record, ReleasePackage, ReleasePackageItem
from ..storage.local import LocalVaultStorage

SCHEMA = "forgevault.released_drawing.v1"

def released_pdf_handoff(session: Session, *, record_id: str, version_id: str) -> tuple[dict, bytes]:
    """Return a version-specific manifest and checksum-verified PDF bytes."""
    try:
        version_uuid = UUID(version_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("A valid file version UUID is required") from exc
    record = session.scalar(select(Record).where(Record.internal_record_id == record_id))
    if record is None:
        raise ValueError("controlled record not found")
    if record.lifecycle_state is None or record.lifecycle_state.name != "Released":
        raise ValueError("record must be Released")
    version = session.get(FileVersion, version_uuid)
    if version is None or version.record_id != record.id:
        raise ValueError("file version does not belong to controlled record")
    if not version.filename.lower().endswith(".pdf"):
        raise ValueError("selected version must be PDF")
    if (version.customer_revision != record.customer_revision
            or version.internal_revision != record.internal_revision):
        raise ValueError("file revision does not match released record")
    package_number = session.scalar(
        select(ReleasePackage.package_number)
        .join(ReleasePackageItem, ReleasePackageItem.release_package_id == ReleasePackage.id)
        .where(
            ReleasePackage.record_id == record.id,
            ReleasePackageItem.file_version_id == version.id,
            ReleasePackage.customer_revision == version.customer_revision,
            ReleasePackage.internal_revision == version.internal_revision,
        ).limit(1)
    )
    if not package_number:
        raise ValueError("file version is absent from matching release package")
    stored = version.file_object
    if stored.storage_adapter != "local":
        raise ValueError("local object storage is required for this handoff")
    content = LocalVaultStorage(settings.local_vault_root).get(stored.sha256)
    if len(content) != stored.byte_size:
        raise ValueError("vault file size mismatch")
    if not content.startswith(b"%PDF-"):
        raise ValueError("stored object does not contain a PDF")
    manifest = {
        "schema": SCHEMA, "source_system": "ForgeVault",
        "record_id": record.internal_record_id,
        "record_uuid": str(record.id),
        "file_version_id": str(version.id),
        "version_number": version.version_number,
        "filename": version.filename,
        "customer_part_number": record.customer_part_number,
        "customer_revision": version.customer_revision,
        "internal_revision": version.internal_revision,
        "release_package_number": package_number,
        "lifecycle": "Released", "sha256": stored.sha256,
        "byte_size": stored.byte_size, "content_type": "application/pdf",
    }
    return manifest, content
