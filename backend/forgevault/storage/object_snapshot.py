"""Verified, object-only snapshot and restore for the local SHA-256 store.

This does not back up the metadata database. Keep the database snapshot and
object manifest from a consistent maintenance window before disaster recovery.
"""
from __future__ import annotations

import json
from pathlib import Path

from .local import LocalVaultStorage, VaultIntegrityError


def snapshot_objects(source: LocalVaultStorage, destination: LocalVaultStorage, manifest_path: Path) -> dict:
    """Copy and verify every digest object; publish a manifest only on success."""
    manifest_path = Path(manifest_path)
    if source.root.resolve() == destination.root.resolve():
        raise ValueError("snapshot destination must differ from source")
    if manifest_path.exists():
        raise FileExistsError("snapshot manifest already exists")
    objects = []
    for path in sorted(source.root.glob("*/*/*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        digest = path.name
        if path != source._object_path(digest):
            raise VaultIntegrityError(f"unexpected object path: {path}")
        data = source.get(digest)
        copied, _, size = destination.put(data)
        if copied != digest or destination.get(digest) != data:
            raise VaultIntegrityError(f"snapshot verification failed: {digest}")
        objects.append({"sha256": digest, "size": size})
    manifest = {"schema": "forgevault.object-snapshot.v1", "objects": objects}
    encoded = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("xb") as output:
        output.write(encoded)
    return manifest


def restore_objects(snapshot: LocalVaultStorage, target: LocalVaultStorage, manifest_path: Path) -> int:
    """Validate entire snapshot before writing objects to the target store."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema") != "forgevault.object-snapshot.v1":
        raise ValueError("unsupported snapshot manifest")
    entries = manifest.get("objects")
    if not isinstance(entries, list):
        raise ValueError("invalid snapshot entries")
    verified = []
    seen = set()
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"sha256", "size"}:
            raise ValueError("invalid snapshot entry")
        digest, size = item["sha256"], item["size"]
        snapshot._object_path(digest)
        if digest in seen or type(size) is not int or size < 0:
            raise ValueError("duplicate digest or invalid size")
        seen.add(digest)
        data = snapshot.get(digest)
        if len(data) != size:
            raise VaultIntegrityError(f"snapshot size mismatch: {digest}")
        verified.append((digest, data))
    for digest, data in verified:
        actual, _, _ = target.put(data)
        if actual != digest:
            raise VaultIntegrityError(f"restore digest mismatch: {digest}")
    return len(verified)
