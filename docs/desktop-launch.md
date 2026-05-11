# ForgeVault Desktop Launch Plan

ForgeVault must be usable without an Autodesk Vault-style installation project. The desktop path uses the same FastAPI backend, but starts it with an embedded SQLite database, local vault storage, and the bundled dark UI.

## Current working path

1. Run `scripts\Launch-ForgeVault.bat` or `scripts\Launch-ForgeVault.ps1` on Windows.
2. The launcher configures a user-profile ForgeVault home directory, starts the API, opens the browser, and pre-fills an optional folder path.
3. The UI indexes a selected folder through `/api/v1/ingest-folder`.
4. Users search records, inspect previous versions, and use checkout/release rules through the same API as server deployments.

## Team deployment path

`docker compose up --build` starts Postgres and ForgeVault together. Users do not install or configure SQL Server/Postgres manually; Compose owns the database service and persistent volumes.

## UI rules

* Dark mode is forced through `color-scheme: dark` and dark CSS variables.
* Orange is reserved for primary actions.
* Red is reserved for error text.
* Layout stays sparse: folder ingest, search, records, and previous versions first.
