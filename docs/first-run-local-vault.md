# ForgeVault First-Run Local Vault Design

ForgeVault local SQLite setup should be ridiculously easy. The user should not need to understand databases, ports, services, migrations, Python, or connection strings.

The default product behavior is:

1. Launch ForgeVault.
2. Choose Local Vault or Shared Shop Vault.
3. For Local Vault, ask what folders should be included.
4. Create the SQLite database and vault storage automatically.
5. Start indexing.
6. Show the file tree/table/preview workflow.

Everything else is advanced.

## Product principle

If the software can logically choose a good default, it should choose the default.

Users should not configure things that ForgeVault can safely infer.

## Local Vault default behavior

On first launch, ForgeVault should automatically create:

```text
%LOCALAPPDATA%\ForgeVault\
  config\
    settings.json
  data\
    forgevault.db
    vault\
    staging\
    jobboss2\
      outbox\
  logs\
```

The user should not be asked where to put this unless they click Advanced.

## First-run wizard

### Screen 1: Choose vault type

Plain language choices:

```text
Local Vault
Use this computer. Best for testing, solo use, or a small local vault.

Shared Shop Vault
Connect this computer to a shared company vault/server.
```

Default selection:

```text
Local Vault
```

Primary action:

```text
Continue
```

### Screen 2: Choose source folders

Main question:

```text
Point ForgeVault to the folders you want included.
```

Actions:

```text
Browse for Source Folder
Add Another Folder
Remove Selected Folder
Continue
```

The user can add multiple folders.

Examples:

```text
P:\Blue Prints
P:\Customer Drawings
C:\Engineering\Jobs
```

Behavior:

- Source folders are not moved.
- Source folders are not reorganized.
- ForgeVault indexes them and preserves original paths.
- Indexing can be recursive by default.
- Hidden/system files should be skipped by default.

### Screen 3: Review and Start

Show:

```text
Vault location: %LOCALAPPDATA%\ForgeVault
Database: Local SQLite
Folders to index:
- P:\Blue Prints
- C:\Engineering\Jobs
```

Actions:

```text
Start Indexing
Back
Advanced Settings
```

### Screen 4: Index progress

Show:

```text
Scanning folders...
Files found
Files indexed
Files skipped
Errors
```

Do not block the user from entering the main app after indexing starts. Indexing should become a background job later.

## Adding folders later

The main app should always have a simple source-folder workflow:

```text
Add Source Folder
Browse for New Source Folder
Index Now
Remove From Vault Index
```

Removing a source folder from the index should not delete files from disk.

## Source folder model

A future table should track configured source folders:

```text
source_folders
  id
  path
  display_name
  is_active
  recursive
  include_hidden
  created_by
  created_at
  last_indexed_at
```

This allows ForgeVault to remember what to index without asking every launch.

## Local SQLite behavior

SQLite should be treated as the default embedded local database.

Rules:

- App creates the database automatically.
- App creates schema automatically.
- App repairs missing local folders automatically.
- App shows database status in plain language.
- App stores settings in a simple local config file.

Plain language status examples:

```text
Local Vault Ready
Database Ready
3 source folders configured
Last indexed 12 minutes ago
```

Avoid showing:

```text
sqlite+pysqlite:///...
SQLAlchemy
Alembic
migration head
connection URL
```

unless the user opens Advanced Details.

## Shared Shop Vault behavior

Shared mode should also be GUI-driven.

The setup screen should ask for normal terms:

```text
Server name
Database name
User name
Password
Shared storage folder
```

Actions:

```text
Test Connection
Save and Connect
```

ForgeVault should generate the technical database URL internally.

## Server or desktop launch logic

ForgeVault should support both:

### Desktop mode

- Local app starts local server automatically.
- Uses SQLite by default.
- Best for solo/local use.

### Server mode

- Server/API runs on a shared machine.
- Client/browser connects to it.
- Uses PostgreSQL by default.
- Best for multi-user shop use.

The GUI should make this feel like a choice between:

```text
Use this computer
Connect to company vault
```

not:

```text
configure runtime backend mode
```

## Automation rules

ForgeVault should automatically:

- create app data folders,
- create local SQLite database,
- create schema,
- create local vault/staging/log folders,
- remember selected source folders,
- restore last-opened vault,
- start local server in desktop mode,
- open the UI,
- detect whether it is in local or server mode,
- show human-readable setup status.

## Advanced settings

Advanced settings can include:

- custom vault data path,
- custom database location,
- include hidden files,
- max files per indexing run,
- JobBOSS² outbox folder,
- raw database URL,
- schema/migration status.

Advanced settings should not be required for a normal first launch.

## Immediate implementation steps

1. Add local settings file service.
2. Add source folder persistence model.
3. Add API endpoints:
   - get setup status,
   - save local vault settings,
   - list source folders,
   - add source folder,
   - remove source folder,
   - index configured source folder.
4. Add first-run UI flow.
5. Add simple local mode health text.
