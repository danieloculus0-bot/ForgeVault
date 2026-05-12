# ForgeVault Dependency and Install Audit

This document separates what ForgeVault needs for development, local desktop use, shared SQL backend use, and a future packaged Windows installer.

## Install modes

ForgeVault should support three deployment modes.

### 1. Local Desktop Vault

For one user, testing, demos, and small solo workflows.

Expected user experience:

- Double-click ForgeVault.
- App starts local server/UI.
- App uses embedded SQLite.
- App stores data under `%LOCALAPPDATA%\ForgeVault`.
- No database install.
- No command line.

Required runtime components:

- Packaged Python runtime, bundled inside the app.
- FastAPI backend.
- Uvicorn server.
- SQLAlchemy.
- SQLite, provided by Python standard library.
- Local file storage under app data.

External dependencies required from user:

- None, once packaged.

### 2. Shared Shop Vault

For multiple users sharing a controlled shop vault.

Expected user experience:

- Admin installs/points ForgeVault to a shared backend.
- Users connect from the ForgeVault GUI.
- GUI provides Test Connection and Save Settings.
- Users do not edit `.env` or write connection strings unless using advanced setup.

Required runtime components:

- PostgreSQL server or another explicitly supported SQL backend.
- Network-accessible vault storage path or object storage adapter.
- ForgeVault server/API service.
- Client launcher/UI.

Backend/database dependencies:

- PostgreSQL driver: `psycopg[binary]`.
- SQLAlchemy.
- Alembic migrations.

Install questions the GUI should collect:

- Local Vault or Shared Shop Vault.
- Server/host.
- Port.
- Database name.
- Username.
- Password.
- Vault storage path.
- JobBOSS² outbox path, optional.
- Whether to create schema automatically.

The GUI should generate and validate the database settings internally. Normal users should never need to hand-write `FORGEVAULT_DATABASE_URL`.

### 3. Development Mode

For contributors and internal build work.

Required developer tools:

- Python 3.11+.
- pip.
- venv.
- Git.
- pytest.
- optional Docker/Docker Compose for Postgres testing.

## Current Python dependencies

Declared in `pyproject.toml`:

```text
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
sqlalchemy>=2.0.30
psycopg[binary]>=3.1.18
pydantic-settings>=2.2.1
alembic>=1.13.0
python-multipart>=0.0.9
```

Development dependencies:

```text
pytest>=8.2.0
httpx>=0.27.0
```

## Current dependency assessment

### Good

- FastAPI and Uvicorn are appropriate for the API/UI server.
- SQLAlchemy is appropriate for SQLite and PostgreSQL support.
- Alembic is appropriate for schema migrations.
- `psycopg[binary]` is appropriate for a packaged/server PostgreSQL path.
- `pydantic-settings` is appropriate for environment/config loading.
- `python-multipart` is useful once file upload endpoints are added.

### Missing or future dependencies

These should not all be added blindly yet. Add when the related feature is implemented.

#### Desktop wrapper

Optional later:

```text
pywebview
```

Use if ForgeVault should open in a native-looking desktop window instead of the default browser.

#### Windows executable build

Build-time only:

```text
pyinstaller
```

Alternative:

```text
nuitka
```

PyInstaller should be first because it is faster to get working.

#### Windows installer

External build tools, not Python package dependencies:

```text
Inno Setup
WiX Toolset
```

Inno Setup is likely the fastest first installer path.

#### File preview support

Add only when preview features are implemented:

```text
pillow
pypdf or pymupdf
python-magic-bin or filetype
```

Possible use:

- Pillow for image thumbnails.
- PyMuPDF for PDF preview thumbnails.
- filetype detection for unknown files.

#### CAD preview/metadata support

Add carefully later. CAD parsing can get heavy.

Possible future options:

```text
cadquery
OCP
trimesh
ezdxf
```

Recommended early lightweight choice:

```text
ezdxf
```

Use for DXF metadata/preview experiments before trying full 3D CAD preview.

#### Auth/security

Add when login/roles become real:

```text
passlib[bcrypt]
python-jose[cryptography]
```

Do not add until authentication is implemented.

## SQL backend notes

ForgeVault currently defaults to PostgreSQL in `config.py`, but desktop launch overrides this to SQLite.

Recommended product behavior:

- Desktop installer defaults to SQLite local mode.
- Server/shop mode uses PostgreSQL.
- GUI setup writes validated configuration.
- App can show current database mode through `/api/v1/runtime/config`.

Supported SQL backends should stay intentionally narrow at first:

1. SQLite for local desktop mode.
2. PostgreSQL for shared/server mode.

Avoid adding MySQL, SQL Server, Oracle, or random ODBC support until there is a real reason. Too many backends too early will turn setup into a maintenance swamp.

## Windows installer requirements

A real Windows install should include:

- `ForgeVault.exe` launcher.
- bundled Python runtime and dependencies.
- app icon `.ico`.
- Start Menu shortcut.
- optional desktop shortcut.
- app data folder under `%LOCALAPPDATA%\ForgeVault` for local mode.
- config file path under `%LOCALAPPDATA%\ForgeVault\config`.
- vault data path under `%LOCALAPPDATA%\ForgeVault\data\vault` for local mode.
- logs under `%LOCALAPPDATA%\ForgeVault\logs`.
- uninstall entry.

## GUI setup requirements

The GUI should have a Setup / Database screen with plain-language choices.

### Local Vault

Fields:

- Vault name.
- Local data location.
- Managed folder path.

Actions:

- Create local vault.
- Open vault folder.
- Reset local vault, guarded.

### Shared Shop Vault

Fields:

- Server name.
- Port.
- Database name.
- Username.
- Password.
- Shared vault storage path.

Actions:

- Test connection.
- Save settings.
- Run/create schema, admin-only.

User-facing wording should avoid:

- SQLAlchemy.
- connection string.
- migrations.
- environment variables.
- Postgres jargon unless in advanced details.

## Immediate next recommendations

1. Add a config writer service for local settings.
2. Add API endpoint to test database/storage configuration.
3. Add GUI Setup / Database screen.
4. Add PyInstaller build script after setup behavior is stable.
5. Add icon assets before packaging.
