from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..database import get_session
from ..models import Dependency, FileVersion, IngestJob, IntegrationEvent, MetadataFieldDefinition, PluginExecution, Record
from ..schemas import (
    CheckoutCancel,
    CheckoutCreate,
    CheckoutStatusRead,
    DependencyCreate,
    FileVersionRead,
    IngestJobRead,
    IngestRequest,
    LifecycleMove,
    RecordCreate,
    RecordRead,
    RuntimeConfigRead,
    SearchResult,
    MetadataFieldRead,
    PluginExecutionRead,
    FolderIngestRequest,
    FolderIngestRead,
    FileVersionDetailRead,
    JobBoss2ExportRequest,
    IntegrationEventRead,
)
from ..services.folder_ingestion import ingest_folder as run_folder_ingest
from ..services.ingestion import ingest_file as run_ingest
from ..services.integrations import export_release_package_to_jobboss2
from ..services.lifecycle import transition_record
from ..services.metadata import create_record
from ..services.search import search_records
from ..services.versioning import active_checkout, cancel_checkout, check_out

router = APIRouter()


def get_record_by_internal_id(session: Session, internal_record_id: str) -> Record:
    record = session.scalar(select(Record).where(Record.internal_record_id == internal_record_id))
    if not record:
        raise HTTPException(status_code=404, detail="record not found")
    return record


@router.get("/runtime/config", response_model=RuntimeConfigRead)
def runtime_config():
    database_url = settings.database_url
    database_mode = "sqlite" if database_url.startswith("sqlite") else "server"
    safe_database_url = database_url
    if "@" in safe_database_url and "://" in safe_database_url:
        prefix, rest = safe_database_url.split("://", 1)
        if "@" in rest:
            safe_database_url = f"{prefix}://***:***@{rest.split('@', 1)[1]}"
    return RuntimeConfigRead(
        database_url=safe_database_url,
        database_mode=database_mode,
        local_vault_root=settings.local_vault_root,
        staging_root=settings.staging_root,
        jobboss2_outbox_root=settings.jobboss2_outbox_root,
        auto_create_schema=settings.auto_create_schema,
    )


@router.post("/records", response_model=RecordRead, status_code=status.HTTP_201_CREATED)
def create_managed_record(payload: RecordCreate, session: Session = Depends(get_session)):
    if not payload.customer_part_number or not payload.customer_revision:
        raise HTTPException(status_code=422, detail="customer_part_number and customer_revision are required when creating records directly")
    record = create_record(
        session,
        customer_part_number=payload.customer_part_number,
        customer_revision=payload.customer_revision,
        internal_revision=payload.internal_revision,
        metadata=payload.metadata,
        actor=payload.actor,
    )
    session.commit()
    return record


@router.get("/records/{internal_record_id}", response_model=RecordRead)
def get_record(internal_record_id: str, session: Session = Depends(get_session)):
    return get_record_by_internal_id(session, internal_record_id)


@router.post("/ingest", response_model=FileVersionRead, status_code=status.HTTP_201_CREATED)
def ingest_file(payload: IngestRequest, session: Session = Depends(get_session)):
    try:
        _, _, version = run_ingest(
            session,
            filename=payload.filename,
            original_source_path=payload.original_source_path,
            content_base64=payload.content_base64,
            customer_part_number=payload.customer_part_number,
            customer_revision=payload.customer_revision,
            internal_revision=payload.internal_revision,
            metadata=payload.metadata,
            actor=payload.actor,
            mime_type=payload.mime_type,
        )
        session.commit()
        return version
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/ingest-jobs/{job_id}", response_model=IngestJobRead)
def get_ingest_job(job_id: UUID, session: Session = Depends(get_session)):
    job = session.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="ingest job not found")
    return job


@router.get("/records/{internal_record_id}/checkout", response_model=CheckoutStatusRead)
def checkout_status(internal_record_id: str, session: Session = Depends(get_session)):
    record = get_record_by_internal_id(session, internal_record_id)
    checkout = active_checkout(session, record.id)
    return CheckoutStatusRead(internal_record_id=record.internal_record_id, is_checked_out=checkout is not None, checkout=checkout)


@router.post("/records/{internal_record_id}/checkout", status_code=status.HTTP_201_CREATED)
def checkout_record(internal_record_id: str, payload: CheckoutCreate, session: Session = Depends(get_session)):
    record = get_record_by_internal_id(session, internal_record_id)
    try:
        checkout = check_out(session, record_id=record.id, actor=payload.actor, reason=payload.reason)
        session.commit()
        return {"checkout_id": str(checkout.id), "internal_record_id": record.internal_record_id, "checked_out_by": payload.actor}
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/records/{internal_record_id}/checkout")
def cancel_record_checkout(internal_record_id: str, payload: CheckoutCancel, session: Session = Depends(get_session)):
    record = get_record_by_internal_id(session, internal_record_id)
    try:
        checkout = cancel_checkout(session, record_id=record.id, actor=payload.actor, reason=payload.reason, force=payload.force)
        session.commit()
        return {"checkout_id": str(checkout.id), "internal_record_id": record.internal_record_id, "cancelled_by": payload.actor}
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/records/{internal_record_id}/lifecycle")
def transition_lifecycle(internal_record_id: str, payload: LifecycleMove, session: Session = Depends(get_session)):
    record = get_record_by_internal_id(session, internal_record_id)
    try:
        package = transition_record(session, record=record, to_state_name=payload.to_state, actor=payload.actor, reason=payload.reason)
        session.commit()
        return {
            "internal_record_id": record.internal_record_id,
            "state": payload.to_state,
            "release_package_id": str(package.id) if package else None,
            "package_number": package.package_number if package else None,
        }
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/dependencies", status_code=status.HTTP_201_CREATED)
def create_dependency(payload: DependencyCreate, session: Session = Depends(get_session)):
    dependency = Dependency(**payload.model_dump())
    session.add(dependency)
    session.commit()
    return {"dependency_id": str(dependency.id)}


@router.get("/records/{record_id}/where-used")
def where_used(record_id: UUID, session: Session = Depends(get_session)):
    dependencies = session.scalars(select(Dependency).where(Dependency.target_record_id == record_id)).all()
    return [
        {
            "source_record_id": str(dep.source_record_id),
            "dependency_type": dep.dependency_type,
            "resolution_status": dep.resolution_status,
            "confidence": dep.confidence,
            "evidence": dep.evidence,
        }
        for dep in dependencies
    ]


@router.get("/search", response_model=list[SearchResult])
def search(q: str, session: Session = Depends(get_session)):
    return [SearchResult(record=record, latest_version=latest) for record, latest in search_records(session, q)]


@router.get("/metadata-fields", response_model=list[MetadataFieldRead])
def list_metadata_fields(scope: str | None = None, session: Session = Depends(get_session)):
    statement = select(MetadataFieldDefinition).order_by(MetadataFieldDefinition.scope, MetadataFieldDefinition.field_key)
    if scope:
        statement = select(MetadataFieldDefinition).where(MetadataFieldDefinition.scope == scope).order_by(MetadataFieldDefinition.field_key)
    return session.scalars(statement).all()


@router.get("/plugin-executions", response_model=list[PluginExecutionRead])
def list_plugin_executions(entity_type: str | None = None, entity_id: str | None = None, session: Session = Depends(get_session)):
    statement = select(PluginExecution).order_by(PluginExecution.created_at.desc())
    if entity_type:
        statement = statement.where(PluginExecution.entity_type == entity_type)
    if entity_id:
        statement = statement.where(PluginExecution.entity_id == entity_id)
    return session.scalars(statement).all()


@router.get("/records/{internal_record_id}/versions", response_model=list[FileVersionDetailRead])
def list_record_versions(internal_record_id: str, session: Session = Depends(get_session)):
    record = get_record_by_internal_id(session, internal_record_id)
    return session.scalars(
        select(FileVersion)
        .options(selectinload(FileVersion.file_object))
        .where(FileVersion.record_id == record.id)
        .order_by(FileVersion.version_number.desc())
    ).all()


@router.post("/ingest-folder", response_model=FolderIngestRead)
def ingest_folder(payload: FolderIngestRequest, session: Session = Depends(get_session)):
    try:
        result = run_folder_ingest(
            session,
            folder_path=payload.folder_path,
            actor=payload.actor,
            internal_revision=payload.internal_revision,
            customer_part_number=payload.customer_part_number,
            customer_revision=payload.customer_revision,
            recursive=payload.recursive,
            include_hidden=payload.include_hidden,
            max_files=payload.max_files,
        )
        session.commit()
        return result
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/integrations/jobboss2/release-packages/{release_package_id}/export", response_model=IntegrationEventRead)
def export_jobboss2_release_package(release_package_id: UUID, payload: JobBoss2ExportRequest, session: Session = Depends(get_session)):
    try:
        event = export_release_package_to_jobboss2(session, release_package_id=release_package_id, actor=payload.actor, mode=payload.mode)
        session.commit()
        return event
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
