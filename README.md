# ForgeVault

ForgeVault is an API-first, generic file/object Product Data Management (PDM) system for manufacturing teams that need version-controlled file management without assuming clean folder structures, clean file names, or perfect CAD metadata.

ForgeVault treats SolidWorks files, neutral CAD (STEP/DXF/etc.), PDFs, work instructions, customer documents, images, spreadsheets, and arbitrary legacy files as first-class managed objects. CAD-specific intelligence is delivered through plugins instead of hard-coded product assumptions.

## What the backbone provides

* FastAPI backend package under `backend/forgevault`.
* PostgreSQL-first schema represented by SQLAlchemy models and an Alembic migration.
* Core persisted tables: `users`, `roles`, `records`, `customer_identity_mappings`, `metadata_field_definitions`, `file_objects`, `file_versions`, `checkouts`, `lifecycle_states`, `release_packages`, `release_package_items`, `dependencies`, `plugin_executions`, `audit_log`, and `ingest_jobs`.
* Append-only file versioning: check-ins create new `file_versions` rows and never overwrite prior history.
* SHA-256 content-addressed file objects using the local vault storage adapter.
* Original source paths preserved for arbitrary-depth legacy and junk-drawer structures.
* Dual traceability: immutable internal record ID plus customer part/revision and internal revision mapping rows.
* Generic plugin architecture for parser plugins, customer naming plugins, and release package generators.
* Built-in functional plugins for generic files, neutral CAD/dependency extraction, document metadata, regex-based customer identity derivation, and immutable release manifest generation.
* Release package creation through lifecycle transition, with unresolved dependencies blocking release.
* REST APIs for ingestion, folder indexing, metadata records, checkout/versioning, lifecycle, dependencies, where-used, indexed search, metadata fields, plugin execution audit, and JobBOSS² release-package export.
* Tests that execute the API, persisted plugin runs, dependency blocking, derived naming, content-addressed storage, and immutable release manifests.

## Repository layout

```text
backend/forgevault/
  api/                 REST route modules
  plugins/             plugin protocols, registry, and built-in parser/naming/release plugins
  services/            ingestion, metadata, versioning, lifecycle, search, audit, plugin orchestration
  storage/             local vault storage adapter
  config.py            environment-driven settings
  database.py          SQLAlchemy engine/session/bootstrap
  models.py            SQLAlchemy schema backbone
  schemas.py           request/response schemas
migrations/            Alembic environment and initial schema migration
frontend/              minimal API-backed browser shell
tests/                 runnable API and storage coverage
docs/                  architecture and schema notes
```

## Easiest Windows-friendly launch

ForgeVault Desktop does **not** require a user-managed SQL Server. It starts a local web UI backed by an embedded SQLite database and a local content-addressed vault under your user profile.

```powershell
.\scripts\Launch-ForgeVault.ps1 --manage-folder "C:\Engineering\Jobs"
```

Or from `cmd.exe`:

```bat
scripts\Launch-ForgeVault.bat --manage-folder "C:\Engineering\Jobs"
```

The browser opens to ForgeVault. Point it at folders you want managed, click **Index Folder**, then search records and inspect previous versions. Files that do not match a customer naming rule are still ingested with a visible `UNMAPPED-*` identity so nothing is lost; those records are searchable and ready for cleanup/revision mapping.

## One-command Docker launch

For teams that prefer Postgres without a manual database install, Docker Compose starts the API and database together. Put folders to manage under `./managed-folders` or edit the bind mount in `docker-compose.yml`.

```bash
docker compose up --build
```

The API/UI will be available at `http://localhost:8000/ui`.

## Local development

```bash
cp .env.example .env
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn forgevault.main:app --reload --app-dir backend
```

The API is available at `http://localhost:8000`, OpenAPI docs are at `http://localhost:8000/docs`, and the web UI is at `http://localhost:8000/ui`.

## Example ingest request

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "filename": "bracket.step",
    "original_source_path": "legacy/junk drawer/customer A/bracket.step",
    "content_base64": "SVNPLTEwMzAzLTIxOw==",
    "customer_part_number": "CUST-42",
    "customer_revision": "A",
    "internal_revision": "001",
    "metadata": {"material": "6061-T6", "source": "staging"},
    "actor": "alice",
    "mime_type": "application/step"
  }'
```

If a customer-specific naming plugin can derive customer part/revision from the filename or path, `customer_part_number` and `customer_revision` may be omitted on ingest. `internal_revision` remains required because internal revision policy is controlled by ForgeVault workflows.

## Safety rules encoded in the backbone

* File hashes are required before a `file_objects` row is created.
* File versions are append-only and linked by `previous_version_id`.
* Customer and internal revision identifiers are stored together on records, mappings, and versions.
* Metadata fields discovered during ingest are persisted in `metadata_field_definitions` for search/index governance.
* Plugin runs are persisted in `plugin_executions` so parser, naming, and release package outputs are auditable.
* Release packages are immutable snapshots tied to exact file version rows and hashes.
* A release transition fails when the record has unresolved dependencies.
* Search endpoints query indexed metadata and version tables; they do not crawl the filesystem.

## JobBOSS² progress

ForgeVault now has a working JobBOSS² export path for released packages. The release export endpoint writes a durable JSON payload into the configured outbox (`FORGEVAULT_JOBBOSS2_OUTBOX_ROOT`) and records the handoff in `integration_events`. If `FORGEVAULT_JOBBOSS2_WEBHOOK_URL` is configured, the same payload can be posted to an integration gateway instead of only writing the outbox file. This keeps ForgeVault useful for both cloud and on-prem JobBOSS² environments while avoiding hard-coded ERP assumptions.

```bash
curl -X POST http://localhost:8000/api/v1/integrations/jobboss2/release-packages/<release_package_id>/export \
  -H 'Content-Type: application/json' \
  -d '{"actor":"alice","mode":"outbox"}'
```

## GUI direction

The bundled UI is intentionally dark-mode only: matte black panels, gray borders, orange action buttons, and red reserved for errors. The first-run workflow is: launch, point to a folder, index, search, inspect previous versions, check out/check in, and release. No legacy-vault install wizard, no manual SQL Server setup, and no neon clutter.

## Test

```bash
pytest
```
