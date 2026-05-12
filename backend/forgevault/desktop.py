from __future__ import annotations

import argparse
import os
import platform
import webbrowser
from pathlib import Path
from urllib.parse import urlencode

import uvicorn


def default_home() -> Path:
    if platform.system() == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "ForgeVault"


def configure_desktop_environment(home: Path) -> None:
    data = home / "data"
    config = home / "config"
    logs = home / "logs"
    backups = home / "backups"
    vault = data / "vault"
    staging = data / "staging"
    outbox = data / "jobboss2" / "outbox"

    os.environ.setdefault("FORGEVAULT_DATABASE_URL", f"sqlite+pysqlite:///{(data / 'forgevault.db').as_posix()}")
    os.environ.setdefault("FORGEVAULT_LOCAL_VAULT_ROOT", str(vault))
    os.environ.setdefault("FORGEVAULT_STAGING_ROOT", str(staging))
    os.environ.setdefault("FORGEVAULT_JOBBOSS2_OUTBOX_ROOT", str(outbox))
    os.environ.setdefault("FORGEVAULT_AUTO_CREATE_SCHEMA", "true")
    os.environ.setdefault("FORGEVAULT_ENABLE_DESKTOP_BRIDGE", "true")

    for folder in (data, config, logs, backups, vault, staging, outbox):
        folder.mkdir(parents=True, exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch ForgeVault Desktop with an embedded local database.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host for the local web app.")
    parser.add_argument("--port", type=int, default=8765, help="Bind port for the local web app.")
    parser.add_argument("--home", type=Path, default=default_home(), help="ForgeVault desktop data directory.")
    parser.add_argument("--manage-folder", type=Path, help="Pre-fill the UI with a folder to manage.")
    parser.add_argument("--no-browser", action="store_true", help="Start the server without opening a browser.")
    args = parser.parse_args()

    configure_desktop_environment(args.home.expanduser().resolve())
    query = urlencode({"folder": str(args.manage_folder.expanduser().resolve())}) if args.manage_folder else ""
    url = f"http://{args.host}:{args.port}/ui" + (f"?{query}" if query else "")
    if not args.no_browser:
        webbrowser.open(url)
    uvicorn.run("forgevault.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
