"""Restore a verified file-tree backup into a new directory.

Never overwrites an existing destination. This is file-level restoration,
not a transactionally consistent database/object-store recovery.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from forgevault.backup_verify import verify_manifest


def restore_files(source: Path, manifest: dict, destination: Path) -> dict:
    source = Path(source)
    destination = Path(destination)
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError("destination parent must be an existing real directory")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("destination already exists")
    if source.resolve() == destination.resolve() or destination.resolve().is_relative_to(source.resolve()):
        raise ValueError("destination cannot be inside the backup source")
    check = verify_manifest(source, manifest)
    if not check["ok"]:
        raise ValueError(f"backup verification failed: {check}")
    stage = Path(tempfile.mkdtemp(prefix=".forgevault-restore-", dir=destination.parent))
    try:
        for record in manifest["files"]:
            relative = Path(*record["path"].split("/"))
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target, follow_symlinks=False)
        copied = verify_manifest(stage, manifest)
        if not copied["ok"]:
            raise ValueError(f"restored copy failed verification: {copied}")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError("destination appeared during restore")
        stage.rename(destination)
        return copied
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Restore a verified file backup into a new directory")
    parser.add_argument("source", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = restore_files(args.source, manifest, args.destination)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
