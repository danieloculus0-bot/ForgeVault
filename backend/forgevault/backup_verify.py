"""Read-only verification of a copied ForgeVault file tree.

This verifies bytes against a manifest made from a known-good source tree.
It does not claim database consistency or a transactional backup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _files(root: Path):
    if not root.is_dir() or root.is_symlink():
        raise ValueError("root must be a real directory")
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink not supported: {path}")
        if path.is_file():
            yield path.relative_to(root).as_posix(), path


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def create_manifest(root: Path) -> dict:
    return {"format": "forgevault-file-backup-v1", "files": [
        {"path": name, "size": path.stat().st_size, "sha256": _digest(path)}
        for name, path in _files(root)
    ]}


def verify_manifest(root: Path, manifest: dict) -> dict:
    if not isinstance(manifest, dict) or manifest.get("format") != "forgevault-file-backup-v1":
        raise ValueError("unsupported manifest")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise ValueError("invalid file records")
    expected = {}
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("invalid file record")
        name, size, digest = item.get("path"), item.get("size"), item.get("sha256")
        if (not isinstance(name, str) or not name or "\\" in name
                or name.startswith("/") or any(p in ("", ".", "..") for p in name.split("/"))
                or not isinstance(size, int) or isinstance(size, bool) or size < 0
                or not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError("invalid manifest path or checksum")
        if name in expected:
            raise ValueError("duplicate manifest path")
        expected[name] = (size, digest)
    actual = dict(_files(root))
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    changed = sorted(name for name in expected.keys() & actual.keys()
                     if actual[name].stat().st_size != expected[name][0]
                     or _digest(actual[name]) != expected[name][1])
    return {"ok": not (missing or extra or changed), "checked": len(expected),
            "missing": missing, "extra": extra, "changed": changed}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify a file-tree backup manifest")
    parser.add_argument("mode", choices=("create", "verify"))
    parser.add_argument("root", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    if args.mode == "create":
        # Manifest is written outside the source tree to avoid self-inclusion.
        if args.manifest.resolve().is_relative_to(args.root.resolve()):
            parser.error("manifest must be outside the source tree")
        result = create_manifest(args.root)
        args.manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 0
    result = verify_manifest(args.root, json.loads(args.manifest.read_text(encoding="utf-8")))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
