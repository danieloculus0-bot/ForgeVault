"""Fail-closed, resumable recovery of missing objects from a verified snapshot.

Never deletes objects or overwrites corrupt target objects. The source manifest
must be reconciled cleanly before any target mutation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .local import LocalVaultStorage, VaultIntegrityError
from .reconcile import reconcile_manifest


def recover_missing(snapshot: LocalVaultStorage, target: LocalVaultStorage, manifest_path: str | Path) -> dict:
    """Restore only missing digest objects, idempotently, after full source verification."""
    src = snapshot.root.resolve()
    dst = target.root.resolve()
    if src == dst or src in dst.parents or dst in src.parents:
        raise ValueError("snapshot and target stores must be separate and non-nested")
    manifest = Path(manifest_path).resolve()
    if manifest == src or src in manifest.parents or manifest == dst or dst in manifest.parents:
        raise ValueError("manifest must be outside both stores")
    source_report = reconcile_manifest(snapshot, manifest)
    if source_report["missing"] or source_report["corrupt"] or source_report["unexpected"]:
        raise VaultIntegrityError("snapshot is incomplete, corrupt or contains unexpected files")
    target_report = reconcile_manifest(target, manifest)
    if target_report["corrupt"]:
        raise VaultIntegrityError("target has corrupt objects; refusing overwrite")
    # Validate every required source byte before any target write.
    expected = json.loads(manifest.read_text(encoding="utf-8"))["objects"]
    verified = {entry["sha256"]: snapshot.get(entry["sha256"]) for entry in expected}
    restored = []
    for digest in target_report["missing"]:
        actual, _, _ = target.put(verified[digest])
        if actual != digest:
            raise VaultIntegrityError("recovered object digest mismatch")
        restored.append(digest)
    after = reconcile_manifest(target, manifest)
    if after["missing"] or after["corrupt"]:
        raise VaultIntegrityError("post-recovery integrity verification failed")
    return {"restored": restored, "remaining_orphan": after["orphan"], "remaining_unexpected": after["unexpected"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Restore missing ForgeVault objects from a verified snapshot")
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    report = recover_missing(LocalVaultStorage(args.snapshot), LocalVaultStorage(args.target), args.manifest)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
