from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    customer_part_number: str | None = None
    customer_revision: str | None = None
    internal_revision: str
    metadata: dict = Field(default_factory=dict)
    actor: str = "system"


class RecordRead(BaseModel):
    id: UUID
    internal_record_id: str
    customer_part_number: str | None = None
    customer_revision: str | None = None
    internal_revision: str
    lifecycle_state_id: UUID | None = None
    record_metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestRequest(BaseModel):
    filename: str
    original_source_path: str
    content_base64: str
    customer_part_number: str | None = None
    customer_revision: str | None = None
    internal_revision: str
    metadata: dict = Field(default_factory=dict)
    actor: str = "system"
    mime_type: str | None = None


class IngestJobRead(BaseModel):
    id: UUID
    status: str
    staging_uri: str
    original_source_path: str
    detected_metadata: dict
    record_id: UUID | None = None
    file_version_id: UUID | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class FileVersionRead(BaseModel):
    id: UUID
    record_id: UUID
    file_object_id: UUID
    version_number: int
    filename: str
    original_source_path: str
    customer_revision: str
    internal_revision: str
    version_metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class CheckoutCreate(BaseModel):
    actor: str
    reason: str | None = None


class LifecycleMove(BaseModel):
    to_state: str
    actor: str
    reason: str | None = None


class DependencyCreate(BaseModel):
    source_record_id: UUID
    target_record_id: UUID | None = None
    source_file_version_id: UUID | None = None
    dependency_type: str
    referenced_path: str | None = None
    resolution_status: str = "unresolved"
    confidence: int = Field(default=100, ge=0, le=100)
    evidence: dict = Field(default_factory=dict)


class SearchResult(BaseModel):
    record: RecordRead
    latest_version: FileVersionRead | None = None


class MetadataFieldRead(BaseModel):
    id: UUID
    scope: str
    field_key: str
    value_type: str
    is_searchable: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PluginExecutionRead(BaseModel):
    id: UUID
    plugin_name: str
    plugin_kind: str
    entity_type: str
    entity_id: str
    status: str
    input_summary: dict
    output: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class FolderIngestRequest(BaseModel):
    folder_path: str
    actor: str = "desktop"
    internal_revision: str = "001"
    customer_part_number: str | None = None
    customer_revision: str | None = None
    recursive: bool = True
    include_hidden: bool = False
    max_files: int = Field(default=2000, ge=1, le=50000)


class FolderIngestItem(BaseModel):
    path: str
    status: str
    record_id: UUID | None = None
    file_version_id: UUID | None = None
    detail: str | None = None


class FolderIngestRead(BaseModel):
    folder_path: str
    scanned: int
    ingested: int
    failed: int
    items: list[FolderIngestItem]


class FileObjectRead(BaseModel):
    id: UUID
    sha256: str
    byte_size: int
    mime_type: str | None = None
    storage_adapter: str
    storage_uri: str

    model_config = {"from_attributes": True}


class FileVersionDetailRead(FileVersionRead):
    file_object: FileObjectRead


class JobBoss2ExportRequest(BaseModel):
    actor: str = "system"
    mode: str = "outbox"


class IntegrationEventRead(BaseModel):
    id: UUID
    external_system: str
    event_type: str
    entity_type: str
    entity_id: str
    status: str
    payload: dict
    response: dict
    created_by: str
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
