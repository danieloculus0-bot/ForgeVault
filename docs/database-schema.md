# Database Schema Backbone

ForgeVault uses PostgreSQL as the source of truth. The Alembic migration creates the schema represented by `backend/forgevault/models.py`.

## Core tables

* `records`: immutable internal record ID plus current customer part/revision, internal revision, lifecycle state, owner, and JSON metadata.
* `customer_identity_mappings`: customer revision to internal revision mappings with source and creator.
* `metadata_field_definitions`: discovered/searchable metadata keys by scope.
* `file_objects`: SHA-256 content-addressed blobs with byte size, MIME type, storage adapter, and URI.
* `file_versions`: append-only record versions linked to file objects and previous versions.
* `checkouts`: active and historical locks.
* `dependencies`: source-to-target relationships with unresolved/resolved status, confidence, referenced path, and evidence.
* `release_packages` and `release_package_items`: immutable released snapshots tied to exact file versions.
* `plugin_executions`: audit trail of parser, naming, and release package generator outputs.
* `integration_events`: durable external system handoffs, including JobBOSS² release package exports and responses.
* `ingest_jobs`: staging/ingestion status, original source path, detected metadata, and failure details.
* `audit_log`: user/system actions across managed entities.
* `users`, `roles`, and `user_roles`: role-based access backbone.

## Indexing

Identity, revision, filename, source path, dependency status, ingest status, plugin execution, and JSON metadata indexes are defined to support database-backed search and operational queries without filesystem crawling.
