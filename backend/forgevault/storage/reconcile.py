"""Read-only reconciliation of a snapshot manifest against an object store.

No objects are deleted or repaired: orphan status is relative to the supplied
manifest, which must represent a consistent metadata/snapshot boundary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .local import LocalVaultStorage, VaultIntegrityError


def reconcile_manifest(storage: LocalVaultStorage, manifest_path: str | Path) -> dict:
    """Return sorted missing, orphan, corrupt and unexpected entries.

    A malformed manifest fails closed. The object store is never modified.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") != "forgevault.object-snapshot.v1":
        raise ValueError("unsupported snapshot manifest")
    entries = manifest.get("objects")
    if not isinstance(entries, list):
        raise ValueError("invalid snapshot entries")
    expected = {}
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"sha256", "size"}:
            raise ValueError("invalid snapshot entry")
        digest, size = item["sha256"], item["size"]
        storage._object_path(digest)
        if digest in expected or type(size) is not int or size < 0:
            raise ValueError("duplicate digest or invalid size")
        expected[digest] = size

    found = set()
    corrupt = set()
    unexpected = []
    if storage.root.exists():
        for path in sorted(storage.root.rglob("*")):
            if path.is_symlink():
                unexpected.append(str(path.relative_to(storage.root)))
                continue
            if not path.is_file():
                continue
            relative = str(path.relative_to(storage.root))
            digest = path.name
            try:
                canonical = storage._object_path(digest)
            except ValueError:
                unexpected.append(relative)
                continue
            if path != canonical:
                unexpected.append(relative)
                continue
            found.add(digest)
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != digest or (
                digest in expected and len(data) != expected[digest]
            ):
                corrupt.add(digest)
    return {
        "expected": len(expected),
        "found": len(found),
        "missing": sorted(set(expected) - found),
        "orphan": sorted(found - set(expected)),
        "corrupt": sorted(corrupt),
        "unexpected": sorted(unexpected),
    }
