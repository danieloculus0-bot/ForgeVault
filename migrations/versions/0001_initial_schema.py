"""initial ForgeVault schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone
import uuid
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def uuid_pk():
    return sa.Column("id", sa.Uuid(), primary_key=True)


def timestamps():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def json_col(name, nullable=False):
    return sa.Column(name, sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "users",
        uuid_pk(),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    op.create_table("roles", uuid_pk(), sa.Column("name", sa.String(64), nullable=False), sa.Column("description", sa.Text()), *timestamps())
    op.create_unique_constraint("uq_roles_name", "roles", ["name"])

    op.create_table(
        "lifecycle_states",
        uuid_pk(),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("is_release_state", sa.Boolean(), nullable=False),
        sa.Column("is_terminal", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )
    op.create_unique_constraint("uq_lifecycle_states_name", "lifecycle_states", ["name"])


    now = datetime.now(timezone.utc)
    roles_table = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("name", sa.String()), sa.column("description", sa.Text()), sa.column("created_at", sa.DateTime(timezone=True)))
    op.bulk_insert(roles_table, [
        {"id": uuid.UUID("00000000-0000-0000-0000-000000000101"), "name": "Engineering", "description": "Engineering record authors and reviewers", "created_at": now},
        {"id": uuid.UUID("00000000-0000-0000-0000-000000000102"), "name": "Manufacturing", "description": "Manufacturing release package consumers", "created_at": now},
        {"id": uuid.UUID("00000000-0000-0000-0000-000000000103"), "name": "Admin", "description": "System administrators", "created_at": now},
    ])
    lifecycle_table = sa.table(
        "lifecycle_states",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("is_release_state", sa.Boolean()),
        sa.column("is_terminal", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(lifecycle_table, [
        {"id": uuid.UUID("00000000-0000-0000-0000-000000000201"), "name": "In Work", "is_release_state": False, "is_terminal": False, "sort_order": 10},
        {"id": uuid.UUID("00000000-0000-0000-0000-000000000202"), "name": "Review", "is_release_state": False, "is_terminal": False, "sort_order": 20},
        {"id": uuid.UUID("00000000-0000-0000-0000-000000000203"), "name": "Released", "is_release_state": True, "is_terminal": False, "sort_order": 30},
        {"id": uuid.UUID("00000000-0000-0000-0000-000000000204"), "name": "Obsolete", "is_release_state": False, "is_terminal": True, "sort_order": 40},
    ])

    op.create_table(
        "user_roles",
        uuid_pk(),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.Uuid(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    op.create_table(
        "records",
        uuid_pk(),
        sa.Column("internal_record_id", sa.String(64), nullable=False),
        sa.Column("customer_part_number", sa.String(255), nullable=False),
        sa.Column("customer_revision", sa.String(64), nullable=False),
        sa.Column("internal_revision", sa.String(64), nullable=False),
        sa.Column("lifecycle_state_id", sa.Uuid(), sa.ForeignKey("lifecycle_states.id")),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id")),
        json_col("record_metadata"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_records_internal_record_id", "records", ["internal_record_id"], unique=True)
    op.create_index("ix_records_customer_lookup", "records", ["customer_part_number", "customer_revision", "internal_revision"])
    op.create_index("ix_records_metadata", "records", ["record_metadata"], postgresql_using="gin")

    op.create_table(
        "customer_identity_mappings",
        uuid_pk(),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_part_number", sa.String(255), nullable=False),
        sa.Column("customer_revision", sa.String(64), nullable=False),
        sa.Column("internal_revision", sa.String(64), nullable=False),
        sa.Column("mapping_source", sa.String(64), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("record_id", "customer_part_number", "customer_revision", "internal_revision", name="uq_customer_identity_mapping"),
    )
    op.create_index("ix_customer_identity_lookup", "customer_identity_mappings", ["customer_part_number", "customer_revision"])

    op.create_table(
        "metadata_field_definitions",
        uuid_pk(),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("field_key", sa.String(255), nullable=False),
        sa.Column("value_type", sa.String(32), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_searchable", sa.Boolean(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("scope", "field_key", name="uq_metadata_field_scope_key"),
    )

    op.create_table(
        "file_objects",
        uuid_pk(),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(255)),
        sa.Column("storage_adapter", sa.String(64), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_file_objects_sha256", "file_objects", ["sha256"], unique=True)

    op.create_table(
        "file_versions",
        uuid_pk(),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_object_id", sa.Uuid(), sa.ForeignKey("file_objects.id"), nullable=False),
        sa.Column("previous_version_id", sa.Uuid(), sa.ForeignKey("file_versions.id")),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("original_source_path", sa.Text(), nullable=False),
        sa.Column("customer_revision", sa.String(64), nullable=False),
        sa.Column("internal_revision", sa.String(64), nullable=False),
        json_col("version_metadata"),
        sa.Column("created_by", sa.String(128), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("record_id", "version_number", name="uq_file_versions_record_version"),
    )
    op.create_index("ix_file_versions_filename", "file_versions", ["filename"])
    op.create_index("ix_file_versions_source_path", "file_versions", ["original_source_path"])
    op.create_index("ix_file_versions_metadata", "file_versions", ["version_metadata"], postgresql_using="gin")

    op.create_table(
        "checkouts",
        uuid_pk(),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checked_out_by", sa.String(128), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_checkouts_record_active", "checkouts", ["record_id", "released_at"])
    op.create_index("uq_checkouts_one_active", "checkouts", ["record_id"], unique=True, postgresql_where=sa.text("released_at IS NULL"))

    op.create_table(
        "release_packages",
        uuid_pk(),
        sa.Column("package_number", sa.String(64), nullable=False),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("records.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("internal_revision", sa.String(64), nullable=False),
        sa.Column("customer_revision", sa.String(64), nullable=False),
        json_col("manifest"),
        sa.Column("created_by", sa.String(128), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("record_id", "internal_revision", "customer_revision", name="uq_release_package_revision"),
    )
    op.create_index("ix_release_packages_package_number", "release_packages", ["package_number"], unique=True)

    op.create_table(
        "release_package_items",
        uuid_pk(),
        sa.Column("release_package_id", sa.Uuid(), sa.ForeignKey("release_packages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_version_id", sa.Uuid(), sa.ForeignKey("file_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("item_role", sa.String(64), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("release_package_id", "file_version_id", name="uq_release_package_item_version"),
    )

    op.create_table(
        "dependencies",
        uuid_pk(),
        sa.Column("source_record_id", sa.Uuid(), sa.ForeignKey("records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_record_id", sa.Uuid(), sa.ForeignKey("records.id", ondelete="SET NULL")),
        sa.Column("source_file_version_id", sa.Uuid(), sa.ForeignKey("file_versions.id", ondelete="CASCADE")),
        sa.Column("dependency_type", sa.String(64), nullable=False),
        sa.Column("referenced_path", sa.Text()),
        sa.Column("resolution_status", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        json_col("evidence"),
        *timestamps(),
    )
    op.create_index("ix_dependencies_source", "dependencies", ["source_record_id"])
    op.create_index("ix_dependencies_target", "dependencies", ["target_record_id"])
    op.create_index("ix_dependencies_status", "dependencies", ["resolution_status"])

    op.create_table(
        "plugin_executions",
        uuid_pk(),
        sa.Column("plugin_name", sa.String(128), nullable=False),
        sa.Column("plugin_kind", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(128), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        json_col("input_summary"),
        json_col("output"),
        *timestamps(),
    )
    op.create_index("ix_plugin_executions_name", "plugin_executions", ["plugin_name"])
    op.create_index("ix_plugin_executions_entity", "plugin_executions", ["entity_type", "entity_id"])

    op.create_table(
        "integration_events",
        uuid_pk(),
        sa.Column("external_system", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(128), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        json_col("payload"),
        json_col("response"),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_integration_events_system_status", "integration_events", ["external_system", "status"])
    op.create_index("ix_integration_events_entity", "integration_events", ["entity_type", "entity_id"])

    op.create_table(
        "audit_log",
        uuid_pk(),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(128), nullable=False),
        sa.Column("entity_id", sa.String(128), nullable=False),
        sa.Column("request_id", sa.String(128)),
        json_col("details"),
        *timestamps(),
    )
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])

    op.create_table(
        "ingest_jobs",
        uuid_pk(),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("staging_uri", sa.Text(), nullable=False),
        sa.Column("original_source_path", sa.Text(), nullable=False),
        json_col("detected_metadata"),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("records.id", ondelete="SET NULL")),
        sa.Column("file_version_id", sa.Uuid(), sa.ForeignKey("file_versions.id", ondelete="SET NULL")),
        sa.Column("submitted_by", sa.String(128), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ingest_jobs_status", "ingest_jobs", ["status"])


def downgrade() -> None:
    for table in [
        "ingest_jobs",
        "audit_log",
        "integration_events",
        "plugin_executions",
        "dependencies",
        "release_package_items",
        "release_packages",
        "checkouts",
        "file_versions",
        "file_objects",
        "metadata_field_definitions",
        "customer_identity_mappings",
        "records",
        "user_roles",
        "lifecycle_states",
        "roles",
        "users",
    ]:
        op.drop_table(table)
