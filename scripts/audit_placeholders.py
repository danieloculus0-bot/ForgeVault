from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "data",
    "node_modules",
}

TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".html",
    ".css",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".ps1",
    ".bat",
    ".env",
    ".example",
}

BLOCKED_PATTERNS = [
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\bHACK\b",
    r"\bmock\b",
    r"\bstub\b",
    r"\bfake\b",
    r"\blorem\b",
    r"\bcoming soon\b",
    r"\bnot implemented\b",
    r"\bplaceholder\b",
    r"alert\s*\(",
    r"console\.log\s*\(",
    r"NotImplementedError",
]

ALLOWLIST = {
    "scripts/audit_placeholders.py": [
        "TODO",
        "FIXME",
        "HACK",
        "mock",
        "stub",
        "fake",
        "lorem",
        "coming soon",
        "not implemented",
        "placeholder",
        "alert\\s*\\(",
        "console\\.log\\s*\\(",
        "NotImplementedError",
    ],
}


def should_scan(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.name == ".env.example":
        return True
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {".replit"}


def allowed(path: Path, pattern: str) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return pattern in ALLOWLIST.get(rel, [])


def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    findings: list[str] = []
    for pattern in BLOCKED_PATTERNS:
        if allowed(path, pattern):
            continue
        regex = re.compile(pattern, re.IGNORECASE)
        for match in regex.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line = text.splitlines()[line_no - 1].strip()
            findings.append(f"{path.relative_to(ROOT)}:{line_no}: matched {pattern!r}: {line}")
    return findings


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if path.is_file() and should_scan(path):
            findings.extend(scan_file(path))

    if findings:
        print("ForgeVault placeholder audit failed:\n")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("ForgeVault placeholder audit OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
