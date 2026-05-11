from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = [
    "README.md",
    "pyproject.toml",
    "backend/forgevault/main.py",
    "backend/forgevault/desktop.py",
    "backend/forgevault/models.py",
    "backend/forgevault/services/versioning.py",
    "backend/forgevault/services/ingestion.py",
    "frontend/index.html",
    "scripts/Setup-ForgeVault.ps1",
    "scripts/Launch-ForgeVault.ps1",
    "scripts/Launch-ForgeVault.bat",
    ".github/workflows/test.yml",
]
REQUIRED_IMPORTS = [
    "forgevault.main",
    "forgevault.desktop",
    "forgevault.models",
    "forgevault.services.ingestion",
    "forgevault.services.versioning",
    "forgevault.storage.local",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"OK: {message}")


def check_paths() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        fail("Missing required paths: " + ", ".join(missing))
    ok("required files are present")


def check_imports() -> None:
    backend = str(ROOT / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    os.environ.setdefault("FORGEVAULT_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    os.environ.setdefault("FORGEVAULT_LOCAL_VAULT_ROOT", str(ROOT / ".tmp_health" / "vault"))
    os.environ.setdefault("FORGEVAULT_STAGING_ROOT", str(ROOT / ".tmp_health" / "staging"))
    os.environ.setdefault("FORGEVAULT_JOBBOSS2_OUTBOX_ROOT", str(ROOT / ".tmp_health" / "jobboss2" / "outbox"))
    os.environ.setdefault("FORGEVAULT_AUTO_CREATE_SCHEMA", "true")
    for module in REQUIRED_IMPORTS:
        importlib.import_module(module)
    ok("required modules import")


def check_pytest_available() -> None:
    if shutil.which("pytest") is None:
        print("WARN: pytest is not on PATH; install dev dependencies with python -m pip install -e .[dev]")
        return
    result = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        fail("pytest collection failed")
    ok("pytest collection passes")


def main() -> None:
    print("ForgeVault repo health check")
    print("============================")
    print(f"Root: {ROOT}")
    print(f"Python: {sys.version.split()[0]}")
    check_paths()
    check_imports()
    check_pytest_available()
    print("PASS: ForgeVault repo health check passed")


if __name__ == "__main__":
    main()
