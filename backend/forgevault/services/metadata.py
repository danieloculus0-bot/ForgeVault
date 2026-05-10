import uuid
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CustomerIdentityMapping, LifecycleState, MetadataFieldDefinition, Record
from .audit import audit

INITIAL_STATE_NAME = "In Work"


def ensure_lifecycle_states(session: Session) -> None:
    existing = {name for (name,) in session.execute(select(LifecycleState.name)).all()}
    seed = [
        ("In Work", False, False, 10),
        ("Review", False, False, 20),
        ("Released", True, False, 30),
        ("Obsolete", False, True, 40),
    ]
    for name, is_release, is_terminal, sort_order in seed:
        if name not in existing:
            session.add(LifecycleState(name=name, is_release_state=is_release, is_terminal=is_terminal, sort_order=sort_order))
    session.flush()


def next_internal_record_id() -> str:
    return f"FV-{uuid.uuid4().hex[:12].upper()}"


def get_initial_lifecycle_state(session: Session) -> LifecycleState:
    ensure_lifecycle_states(session)
    state = session.scalar(select(LifecycleState).where(LifecycleState.name == INITIAL_STATE_NAME))
    if state is None:
        raise RuntimeError("initial lifecycle state seed failed")
    return state


def flatten_metadata_keys(metadata: Mapping, prefix: str = "") -> list[tuple[str, object]]:
    keys: list[tuple[str, object]] = []
    for key, value in metadata.items():
        field_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            keys.extend(flatten_metadata_keys(value, field_key))
        else:
            keys.append((field_key, value))
    return keys


def infer_value_type(value: object) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, (list, tuple)):
        return "array"
    if value is None:
        return "null"
    return "string"


def ensure_metadata_field_definitions(session: Session, *, scope: str, metadata: dict) -> None:
    for field_key, value in flatten_metadata_keys(metadata):
        existing = session.scalar(
            select(MetadataFieldDefinition).where(MetadataFieldDefinition.scope == scope, MetadataFieldDefinition.field_key == field_key)
        )
        if existing is None:
            session.add(MetadataFieldDefinition(scope=scope, field_key=field_key, value_type=infer_value_type(value)))


def find_record_by_identity(session: Session, *, customer_part_number: str, customer_revision: str, internal_revision: str) -> Record | None:
    return session.scalar(
        select(Record).where(
            Record.customer_part_number == customer_part_number,
            Record.customer_revision == customer_revision,
            Record.internal_revision == internal_revision,
        )
    )


def create_record(session: Session, *, customer_part_number: str, customer_revision: str, internal_revision: str, metadata: dict, actor: str) -> Record:
    state = get_initial_lifecycle_state(session)
    ensure_metadata_field_definitions(session, scope="record", metadata=metadata)
    record = Record(
        internal_record_id=next_internal_record_id(),
        customer_part_number=customer_part_number,
        customer_revision=customer_revision,
        internal_revision=internal_revision,
        lifecycle_state_id=state.id,
        record_metadata=metadata,
    )
    session.add(record)
    session.flush()
    add_customer_identity_mapping(
        session,
        record=record,
        customer_part_number=customer_part_number,
        customer_revision=customer_revision,
        internal_revision=internal_revision,
        actor=actor,
        source="ingestion",
    )
    audit(session, actor=actor, action="record.created", entity_type="records", entity_id=record.internal_record_id, details=metadata)
    return record


def add_customer_identity_mapping(
    session: Session,
    *,
    record: Record,
    customer_part_number: str,
    customer_revision: str,
    internal_revision: str,
    actor: str,
    source: str,
) -> CustomerIdentityMapping:
    mapping = CustomerIdentityMapping(
        record_id=record.id,
        customer_part_number=customer_part_number,
        customer_revision=customer_revision,
        internal_revision=internal_revision,
        mapping_source=source,
        created_by=actor,
    )
    session.add(mapping)
    return mapping
