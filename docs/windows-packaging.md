# ForgeVault Windows Packaging Direction

ForgeVault should eventually ship like normal Windows software, not like a Python project the user has to understand.

## Recommended product path

ForgeVault should keep its Python backend and browser-based UI during development, but the user-facing product should become a Windows desktop app/installer.

Preferred stages:

1. Development mode
   - Python virtual environment.
   - `scripts/Launch-ForgeVault.ps1` starts the local API/UI.
   - Good for development and testing.

2. Desktop app wrapper
   - User double-clicks `ForgeVault.exe`.
   - App starts the local ForgeVault server in the background.
   - App opens its own desktop window or the default browser.
   - User never sees Python, pip, venv, uvicorn, or terminal noise.

3. Packaged Windows build
   - PyInstaller or Nuitka bundles Python runtime and dependencies.
   - Inno Setup or WiX creates a real installer.
   - Installer creates Start Menu shortcut, desktop shortcut, launcher icon, and app data folder.
   - First run defaults to local SQLite vault mode.
   - Shared shop/server mode can be configured from the GUI.

4. Future enterprise/shop install
   - Admin installs shared ForgeVault server/database once.
   - Users install lightweight clients.
   - GUI handles connection testing and config.
   - No one edits `.env` by hand unless they are intentionally doing advanced setup.

## Launcher icon

Use a normal Windows `.ico` for the packaged app.

Icon direction:

- Forge/layer/vault mark.
- Dark graphite base.
- Controlled orange accent.
- Simple enough to read at 16x16 and 32x32.
- No rainbow colors.
- No cute SaaS blob icon.

Recommended repo paths:

```text
assets/icon/forgevault-icon.svg
assets/icon/forgevault-icon.ico
assets/icon/forgevault-icon-256.png
```

## Python packaging feasibility

Yes, this is doable from Python.

Good options:

- PyInstaller: fastest path to a Windows `.exe`.
- Nuitka: potentially cleaner/faster compiled output, but slower to tune.
- pywebview: desktop window wrapper around the local web UI.
- Inno Setup: simple Windows installer after the `.exe` exists.

Recommended first build target:

```text
ForgeVault.exe
```

Behavior:

- Start local API/UI.
- Use local SQLite by default.
- Store data under `%LOCALAPPDATA%\ForgeVault`.
- Open the ForgeVault UI.
- Show setup screen for Local Vault vs Shared Shop Vault.

## Do not ship as a raw Python app

Raw Python is fine for development, but not for real users.

Do not require normal shop users to:

- install Python,
- create a venv,
- run pip,
- run uvicorn,
- edit `.env`,
- know what PostgreSQL is,
- or deploy anything from the command line.

ForgeVault's product promise is easy file control. Deployment has to match that.

## Database setup direction

The GUI should expose two plain options:

### Local Vault

Best for one person or testing.

- Uses embedded SQLite.
- Stores data under the user's app data folder.
- Requires no server.
- Default first-run option.

### Shared Shop Vault

Best for teams.

- Connects to a shared server/database.
- User enters server name, database name, username, password, and storage path.
- GUI has a Test Connection button.
- GUI saves config after validation.

The GUI must hide advanced database language by default. Terms like connection string, SQLAlchemy, Alembic, migration, and environment variables belong in advanced docs, not the first-run workflow.

## Next implementation steps

1. Add app icon source asset.
2. Add a PyInstaller build script.
3. Add a `forgevault.launcher` module that starts the server and opens the UI.
4. Add a first-run Setup / Database screen in the frontend.
5. Add a Windows installer script after the `.exe` build works.
