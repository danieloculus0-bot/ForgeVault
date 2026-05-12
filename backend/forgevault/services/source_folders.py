from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import utcnow
from ..source_folders_model import SourceFolder
from .folder_ingestion import ingest_folder


def normalize_source_path(path: str) -> str:
    normalized = str(Path(path).expanduser().resolve())
    if not Path(normalized).exists():
        raise ValueError(f"folder does not exist: {path}")
    if not Path(normalized).is_dir():
        raise ValueError(f"path is not a folder: {path}")
    return normalized


def default_display_name(path: str) -> str:
    name = Path(path).name
    return name or path


def list_source_folders(session: Session, *, include_inactive: bool = False) -> list[SourceFolder]:
    statement = select(SourceFolder).order_by(SourceFolder.display_name, SourceFolder.path)
    if not include_inactive:
        statement = statement.where(SourceFolder.is_active.is_(True))
    return session.scalars(statement).all()


def add_source_folder(
    session: Session,
    *,
    path: str,
    display_name: str | None,
    actor: str,
    recursive: bool = True,
    include_hidden: bool = False,
) -> SourceFolder:
    normalized = normalize_source_path(path)
    existing = session.scalar(select(SourceFolder).where(SourceFolder.path == normalized))
    if existing:
        existing.is_active = True
        existing.display_name = display_name or existing.display_name or default_display_name(normalized)
        existing.recursive = recursive
        existing.include_hidden = include_hidden
        existing.updated_at = utcnow()
        return existing
    folder = SourceFolder(
        path=normalized,
        display_name=display_name or default_display_name(normalized),
        recursive=recursive,
        include_hidden=include_hidden,
        created_by=actor,
    )
    session.add(folder)
    session.flush()
    return folder


def remove_source_folder(session: Session, *, source_folder_id: UUID, actor: str) -> SourceFolder:
    folder = session.get(SourceFolder, source_folder_id)
    if not folder:
        raise ValueError("source folder not found")
    folder.is_active = False
    folder.updated_at = utcnow()
    return folder


def index_source_folder(session: Session, *, source_folder_id: UUID, actor: str, max_files: int = 2000) -> dict:
    folder = session.get(SourceFolder, source_folder_id)
    if not folder or not folder.is_active:
        raise ValueError("active source folder not found")
    result = ingest_folder(
        session,
        folder_path=folder.path,
        actor=actor,
        internal_revision="001",
        customer_part_number=None,
        customer_revision=None,
        recursive=folder.recursive,
        include_hidden=folder.include_hidden,
        max_files=max_files,
    )
    folder.last_indexed_at = utcnow()
    return result


def setup_status(session: Session) -> dict:
    folders = list_source_folders(session)
    return {
        "mode": "local",
        "ready": len(folders) > 0,
        "source_folder_count": len(folders),
        "needs_source_folder": len(folders) == 0,
        "message": "Add a source folder to start indexing." if not folders else "Local Vault ready.",
    }
