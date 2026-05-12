# ForgeVault

ForgeVault is an open-source manufacturing file vault and lightweight PDM backbone for shops that need control over drawings, CAD files, revisions, work instructions, releases, and customer documents without buying into a bloated enterprise vault.

It is built for real manufacturing file chaos: old job folders, inconsistent names, mixed CAD formats, PDFs, DXFs, STEP files, spreadsheets, inspection documents, customer uploads, screenshots, and tribal-knowledge folder structures that somehow became production-critical.

ForgeVault does not assume perfect metadata, perfect file names, or one blessed CAD platform. It stores files as managed objects, preserves source paths, tracks versions, supports customer/internal revision mapping, and leaves CAD-specific intelligence to plugins.

## What it does

- Indexes folders and turns loose files into searchable managed records.
- Preserves original source paths so legacy folder structures are not destroyed.
- Stores file objects by SHA-256 hash using content-addressed vault storage.
- Keeps file versions append-only so old revisions are not overwritten.
- Tracks customer part/revision and internal revision identity separately.
- Supports checkout, check-in, lifecycle state changes, dependencies, where-used, review routing, notifications, and release packages.
- Blocks release when unresolved dependencies exist.
- Provides plugin hooks for file parsing, naming rules, customer identity extraction, CAD/document metadata, and release package generation.
- Includes a browser UI, local desktop launcher, REST API, CI smoke test, and Windows executable build workflow.
- Includes a JobBOSS² release export path for manufacturing/ERP handoff experiments.

## Why ForgeVault exists

Most small and mid-size manufacturers do not have clean PDM. They have shared drives, old job folders, customer naming weirdness, revision confusion, and a lot of expensive knowledge hiding in file paths.

ForgeVault is meant to sit between that mess and a real controlled system. It should help a shop start managing files without forcing a painful all-at-once migration.

The goal is practical control first:

- What file is this?
- What revision is current?
- Where did it come from?
- What changed?
- Who checked it out?
- What depends on it?
- Can this package be released?
- What needs to go to ERP, purchasing, quality, or the floor?

## Repository layout

```text
backend/forgevault/
  api/                 REST route modules
  plugins/             plugin protocols, registry, and built-in plugins
  services/            ingestion, metadata, versioning, lifecycle, search, audit, integrations
  storage/             local content-addressed vault storage
  config.py            environment-driven settings
  database.py          SQLAlchemy engine/session/bootstrap
  models.py            SQLAlchemy schema backbone
  schemas.py           request/response schemas
migrations/            Alembic environment and initial schema migration
frontend/              API-backed browser shell and desktop UI helpers
scripts/               launch, smoke, and build helpers
docs/                  architecture, desktop launch, and schema notes
tests/                 API and storage tests
.github/workflows/     automated smoke and Windows desktop build workflows
```

## Windows-friendly launch

ForgeVault Desktop starts a local web UI backed by SQLite and a local content-addressed vault under your user profile. No user-managed SQL Server is required.

```powershell
.\scripts\Launch-ForgeVault.ps1 --manage-folder "C:\Engineering\Jobs"
```

Or from `cmd.exe`:

```bat
scripts\Launch-ForgeVault.bat --manage-folder "C:\Engineering\Jobs"
```

The browser opens to ForgeVault. Point it at a folder, index it, search records, inspect versions, check files out, check replacement files back in, submit checked-in versions for review, and start cleaning up uncontrolled files without losing the original folder context.

## Build the Windows desktop executable locally

From PowerShell:

```powershell
.\scripts\build_windows_desktop.ps1
```

The script creates/uses `.venv`, installs ForgeVault with development dependencies, runs the smoke test, builds `dist\ForgeVaultDesktop.exe` with PyInstaller, and fails fast if the smoke test or packaging step breaks.

## Automated builds

ForgeVault currently includes two GitHub Actions workflows:

- `ForgeVault CI` installs the app and runs `scripts/ci_smoke.py` on push, pull request, and manual dispatch.
- `ForgeVault Desktop Build` runs the smoke test, builds a Windows `ForgeVaultDesktop.exe`, and uploads it as an Actions artifact.

## Docker launch

For server-style testing with Postgres:

```bash
docker compose up --build
```

The API/UI will be available at:

```text
http://localhost:8000/ui
```

## Local development

```bash
cp .env.example .env
python -m pip install -e '.[dev]'
alembic upgrade head
uvicorn forgevault.main:app --reload --app-dir backend
```

Useful local URLs:

```text
API:      http://localhost:8000
Docs:     http://localhost:8000/docs
Web UI:   http://localhost:8000/ui
```

## Example ingest request

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "filename": "bracket.step",
    "original_source_path": "legacy/customer-a/old-job-folder/bracket.step",
    "content_base64": "SVNPLTEwMzAzLTIxOw==",
    "customer_part_number": "CUST-42",
    "customer_revision": "A",
    "internal_revision": "001",
    "metadata": {"material": "6061-T6", "source": "staging"},
    "actor": "alice",
    "mime_type": "application/step"
  }'
```

If a naming plugin can derive customer part/revision from the filename or path, `customer_part_number` and `customer_revision` can be omitted. Internal revision remains controlled by ForgeVault workflow policy.

## Core safety rules

- File hashes are required before file objects are created.
- File versions are append-only and linked to previous versions.
- Release packages are immutable snapshots tied to exact file version rows and hashes.
- Customer revision, internal revision, and original source path are preserved.
- Plugin executions are recorded so parser, naming, and release outputs are auditable.
- Search uses indexed metadata and version tables instead of repeatedly crawling the filesystem.
- Release transitions fail when unresolved dependencies exist.
- Check-in requires an active checkout by the same actor.
- Desktop source-folder removal removes only ForgeVault index state. It never deletes disk files.

## JobBOSS² integration path

ForgeVault includes an early JobBOSS² export path for released packages. The release export endpoint writes a durable JSON payload into the configured outbox and records the handoff in integration events.

```bash
curl -X POST http://localhost:8000/api/v1/integrations/jobboss2/release-packages/<release_package_id>/export \
  -H 'Content-Type: application/json' \
  -d '{"actor":"alice","mode":"outbox"}'
```

This is intentionally structured as an integration handoff instead of hard-coding ERP assumptions into the vault.

## Current status

ForgeVault is in early deployable-backbone stage. The repo currently includes the backend schema, API routes, storage/versioning services, plugin structure, migration, browser UI, desktop bridge, launch scripts, Docker setup, smoke tests, CI automation, local Windows packaging script, and automated Windows desktop executable workflow.

It is not production-ready yet. The next work should focus on installer polish, UI workflow depth, file preview, permissions, better folder indexing feedback, release package UX, and real-world testing against ugly manufacturing folders.

## Test

```bash
python scripts/ci_smoke.py
pytest
```
