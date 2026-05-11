from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from .ingestion import ingest_file

IGNORED_DIRS = {".git", ".svn", "__pycache__", "node_modules", ".venv", "venv"}
IGNORED_SUFFIXES = {".tmp", ".bak", ".swp", ".lock"}


def iter_managed_files(root: Path, *, recursive: bool, include_hidden: bool, max_files: int) -> list[Path]:
    if not root.exists() or not root.is_dir():
        raise ValueError(f"folder does not exist or is not a directory: {root}")
    pattern = "**/*" if recursive else "*"
    files: list[Path] = []
    for path in root.glob(pattern):
        parts = set(path.parts)
        if not include_hidden and any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if parts & IGNORED_DIRS:
            continue
        if path.is_file() and path.suffix.lower() not in IGNORED_SUFFIXES:
            files.append(path)
            if len(files) >= max_files:
                break
    return sorted(files)


def unmapped_identity_for(path: Path) -> tuple[str, str, dict]:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:10].upper()
    return (
        f"UNMAPPED-{digest}",
        "UNMAPPED",
        {
            "identity_status": "unmapped_requires_review",
            "identity_note": "ForgeVault assigned a temporary searchable customer identity during folder ingest because no naming plugin matched.",
        },
    )


def ingest_folder(
    session: Session,
    *,
    folder_path: str,
    actor: str,
    internal_revision: str,
    customer_part_number: str | None,
    customer_revision: str | None,
    recursive: bool,
    include_hidden: bool,
    max_files: int,
) -> dict:
    root = Path(folder_path).expanduser().resolve()
    files = iter_managed_files(root, recursive=recursive, include_hidden=include_hidden, max_files=max_files)
    items: list[dict] = []
    for file_path in files:
        try:
            content = file_path.read_bytes()
            metadata = {"folder_ingest": {"root": str(root), "relative_path": str(file_path.relative_to(root))}}
            part_number = customer_part_number
            revision = customer_revision
            if not part_number or not revision:
                part_number, revision, identity_metadata = unmapped_identity_for(file_path)
                metadata.update(identity_metadata)
            _, record, version = ingest_file(
                session,
                filename=file_path.name,
                original_source_path=str(file_path),
                content_base64=base64.b64encode(content).decode("ascii"),
                customer_part_number=part_number,
                customer_revision=revision,
                internal_revision=internal_revision,
                metadata=metadata,
                actor=actor,
            )
            session.commit()
            items.append({"path": str(file_path), "status": "ingested", "record_id": record.id, "file_version_id": version.id})
        except Exception as exc:
            session.rollback()
            items.append({"path": str(file_path), "status": "failed", "detail": str(exc)})
    return {
        "folder_path": str(root),
        "scanned": len(files),
        "ingested": sum(1 for item in items if item["status"] == "ingested"),
        "failed": sum(1 for item in items if item["status"] == "failed"),
        "items": items,
    }
