from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".github",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "data",
    "node_modules",
}

SKIP_SUFFIXES = {
    ".db",
    ".exe",
    ".ico",
    ".jpg",
    ".jpeg",
    ".png",
    ".pyc",
    ".sqlite",
    ".zip",
}

BANNED_PATTERNS = [
    ("TODO", re.compile(r"\bTODO\b", re.IGNORECASE)),
    ("FIXME", re.compile(r"\bFIXME\b", re.IGNORECASE)),
    ("placeholder", re.compile(r"\bplaceholder\b", re.IGNORECASE)),
    ("mock", re.compile(r"\bmock(?:ed|up)?\b", re.IGNORECASE)),
    ("stub", re.compile(r"\bstub\b", re.IGNORECASE)),
    ("fake", re.compile(r"\bfake\b", re.IGNORECASE)),
    ("coming soon", re.compile(r"coming soon", re.IGNORECASE)),
    ("not implemented", re.compile(r"not implemented", re.IGNORECASE)),
    ("lorem", re.compile(r"\blorem\b", re.IGNORECASE)),
    ("ipsum", re.compile(r"\bipsum\b", re.IGNORECASE)),
    ("tbd", re.compile(r"\bTBD\b", re.IGNORECASE)),
    ("dummy", re.compile(r"\bdummy\b", re.IGNORECASE)),
]

ALLOWLIST = {
    Path("scripts/placeholder_audit.py"),
    Path("README.md"),
    Path("docs/INSTALL_WINDOWS.md"),
}

ALLOWLIST_LINE_PATTERNS = [
    re.compile(r"SAMPLE-MCM-001"),
    re.compile(r"sample generated output", re.IGNORECASE),
    re.compile(r"demo_source"),
    re.compile(r"cloud demo", re.IGNORECASE),
    re.compile(r"demo/dev", re.IGNORECASE),
    re.compile(r"demo mode", re.IGNORECASE),
    re.compile(r"ForgeVault CI demo", re.IGNORECASE),
    re.compile(r"placeholder assembly", re.IGNORECASE),
]


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    return path.suffix.lower() in SKIP_SUFFIXES


def line_allowed(path: Path, line: str) -> bool:
    rel = path.relative_to(ROOT)
    if rel in ALLOWLIST:
        return True
    return any(pattern.search(line) for pattern in ALLOWLIST_LINE_PATTERNS)


def main() -> None:
    failures: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(ROOT)
        for lineno, line in enumerate(text.splitlines(), start=1):
            if line_allowed(path, line):
                continue
            for label, pattern in BANNED_PATTERNS:
                if pattern.search(line):
                    failures.append(f"{rel}:{lineno}: banned placeholder term '{label}': {line.strip()}")

    if failures:
        print("Placeholder audit failed. Remove or justify these lines:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)

    print("Placeholder audit OK")


if __name__ == "__main__":
    main()
