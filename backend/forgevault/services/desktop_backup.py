"""Verified, non-destructive snapshot/restore for the local SQLite desktop edition.

Only the ForgeVault SQLite database and immutable referenced local objects are
included. This is not a PostgreSQL, live-server, or full-machine backup system.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import zipfile

_DB_MEMBER = "database/forgevault.db"
_MANIFEST = "manifest.json"
_VERSION = 1


class VaultSnapshotError(ValueError):
    """Snapshot is incomplete, corrupt, incompatible or unsafe to restore."""


def _digest_stream(src) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    for chunk in iter(lambda: src.read(1024 * 1024), b""):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def _objects_from_database(db_path: Path) -> list[dict]:
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        with con:
            result = con.execute("PRAGMA quick_check").fetchone()
            if not result or result[0] != "ok":
                raise VaultSnapshotError("SQLite integrity check failed")
            violations = con.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise VaultSnapshotError("SQLite foreign-key integrity check failed")
            rows = con.execute(
                "SELECT sha256, byte_size, storage_adapter FROM file_objects ORDER BY sha256"
            ).fetchall()
        result = []
        for row in rows:
            digest, size, adapter = row["sha256"], row["byte_size"], row["storage_adapter"]
            if (not isinstance(digest, str) or len(digest) != 64
                    or any(c not in "0123456789abcdef" for c in digest)
                    or not isinstance(size, int) or size < 0 or adapter != "local"):
                raise VaultSnapshotError("Unsupported or invalid file object reference")
            result.append({"sha256": digest, "size": size})
        return result
    except sqlite3.DatabaseError as exc:
        raise VaultSnapshotError(f"SQLite database cannot be verified: {exc}") from exc
    finally:
        if "con" in locals():
            con.close()


def _member(digest: str) -> str:
    return f"objects/{digest[:2]}/{digest[2:4]}/{digest}"


def verify_snapshot(archive_path: str | Path) -> dict:
    """Check content hashes, SQLite integrity, and all DB-to-object references."""
    archive_path = Path(archive_path)
    with tempfile.TemporaryDirectory(prefix="forgevault-verify-") as scratch:
        try:
            with zipfile.ZipFile(archive_path, "r") as z:
                names = z.namelist()
                if len(names) != len(set(names)):
                    raise VaultSnapshotError("Archive contains duplicate member names")
                manifest = json.loads(z.read(_MANIFEST))
                if (not isinstance(manifest, dict)
                        or manifest.get("version") != _VERSION
                        or not isinstance(manifest.get("objects"), list)
                        or not isinstance(manifest.get("db_sha256"), str)):
                    raise VaultSnapshotError("Unsupported snapshot manifest")
                entries = manifest["objects"]
                hashes = [x.get("sha256") for x in entries if isinstance(x, dict)]
                if len(hashes) != len(entries) or len(set(hashes)) != len(hashes):
                    raise VaultSnapshotError("Malformed or duplicate object manifest")
                required = {_MANIFEST, _DB_MEMBER} | {_member(h) for h in hashes if isinstance(h, str) and len(h) == 64}
                if set(names) != required:
                    raise VaultSnapshotError("Archive has missing or unexpected members")

                db_copy = Path(scratch) / "forgevault.db"
                with z.open(_DB_MEMBER) as src, db_copy.open("wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
                with db_copy.open("rb") as src:
                    actual_db_hash, _ = _digest_stream(src)
                if actual_db_hash != manifest["db_sha256"]:
                    raise VaultSnapshotError("SQLite backup SHA-256 mismatch")
                if _objects_from_database(db_copy) != entries:
                    raise VaultSnapshotError("Database file-object records do not match the backup manifest")

                for entry in entries:
                    digest, expected_size = entry["sha256"], entry["size"]
                    with z.open(_member(digest)) as src:
                        actual_hash, actual_size = _digest_stream(src)
                    if actual_hash != digest or actual_size != expected_size:
                        raise VaultSnapshotError(f"Stored object integrity failure: {digest}")
                return {"verified": True, "object_count": len(entries),
                        "db_sha256": actual_db_hash}
        except (OSError, KeyError, TypeError, ValueError, zipfile.BadZipFile) as exc:
            if isinstance(exc, VaultSnapshotError):
                raise
            raise VaultSnapshotError(f"Invalid or unreadable backup archive: {exc}") from exc


def snapshot_desktop(home: str | Path, archive_path: str | Path) -> dict:
    """Take a consistent online SQLite copy, then checksum every referenced object.

    New records committed after the database snapshot do not enter this snapshot.
    A failed object read aborts publication rather than creating a partial backup.
    """
    home = Path(home).expanduser().resolve()
    source_db = home / "data" / "forgevault.db"
    root = home / "data" / "vault"
    archive_path = Path(archive_path).expanduser().resolve()
    if not source_db.is_file() or not root.is_dir():
        raise VaultSnapshotError("Local desktop database or vault object directory is missing")
    if archive_path.exists() or archive_path.is_symlink():
        raise FileExistsError("Refusing to overwrite an existing snapshot")
    if home == archive_path or home in archive_path.parents:
        raise VaultSnapshotError("Store snapshots outside the live desktop home")
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    pending = None
    with tempfile.TemporaryDirectory(prefix="forgevault-snapshot-") as scratch:
        frozen_db = Path(scratch) / "forgevault.db"
        src = sqlite3.connect(source_db)
        try:
            dst = sqlite3.connect(frozen_db)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        objects = _objects_from_database(frozen_db)
        with frozen_db.open("rb") as file:
            db_digest, _ = _digest_stream(file)
        manifest = {
            "version": _VERSION,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "db_sha256": db_digest,
            "objects": objects,
        }
        try:
            with tempfile.NamedTemporaryFile(
                prefix=".forgevault-", suffix=".tmp", dir=archive_path.parent,
                delete=False
            ) as f:
                pending = Path(f.name)
            with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as z:
                z.write(frozen_db, _DB_MEMBER)
                for entry in objects:
                    digest = entry["sha256"]
                    obj = root / digest[:2] / digest[2:4] / digest
                    if not obj.is_file() or obj.is_symlink():
                        raise VaultSnapshotError(f"Referenced local object missing: {digest}")
                    with obj.open("rb") as src, z.open(_member(digest), "w") as dst:
                        actual_hash = hashlib.sha256()
                        size = 0
                        for chunk in iter(lambda: src.read(1024 * 1024), b""):
                            actual_hash.update(chunk)
                            size += len(chunk)
                            dst.write(chunk)
                        if actual_hash.hexdigest() != digest or size != entry["size"]:
                            raise VaultSnapshotError(f"Referenced object changed or is corrupt: {digest}")
                z.writestr(_MANIFEST, json.dumps(manifest, sort_keys=True, indent=2))
            result = verify_snapshot(pending)
            if archive_path.exists() or archive_path.is_symlink():
                raise FileExistsError("Refusing to replace a snapshot created concurrently")
            os.replace(pending, archive_path)
            return {"archive": str(archive_path), **result}
        finally:
            if pending is not None:
                pending.unlink(missing_ok=True)


def restore_to_new_home(archive_path: str | Path, target_home: str | Path) -> dict:
    """Restore into a newly created location, never into an existing installation."""
    result = verify_snapshot(archive_path)
    target = Path(target_home).expanduser().resolve()
    if target.exists() or target.is_symlink():
        raise FileExistsError("Refusing to overwrite an existing home or file")
    if not target.parent.is_dir():
        raise VaultSnapshotError("The destination parent folder must already exist")
    stage = Path(tempfile.mkdtemp(prefix=".forgevault-restore-", dir=target.parent))
    try:
        with zipfile.ZipFile(archive_path) as z:
            manifest = json.loads(z.read(_MANIFEST))
            files = [(_DB_MEMBER, stage / "data" / "forgevault.db")]
            files += [
                (_member(x["sha256"]), stage / "data" / "vault" /
                 x["sha256"][:2] / x["sha256"][2:4] / x["sha256"])
                for x in manifest["objects"]
            ]
            for member, destination in files:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with z.open(member) as src, destination.open("wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)
        # File-object records store absolute file:// paths; relocate the DB
        # before exposing the restored home at its final directory.
        local_db = stage / "data" / "forgevault.db"
        with sqlite3.connect(local_db) as con:
            for entry in manifest["objects"]:
                digest = entry["sha256"]
                live_path = target / "data" / "vault" / digest[:2] / digest[2:4] / digest
                con.execute(
                    "UPDATE file_objects SET storage_uri=? WHERE sha256=?",
                    (f"file://{live_path}", digest),
                )
        if _objects_from_database(local_db) != manifest["objects"]:
            raise VaultSnapshotError("Relocated restore database failed reference verification")
        if target.exists() or target.is_symlink():
            raise FileExistsError("Restore destination appeared during extraction")
        os.replace(stage, target)
        return {"home": str(target), **result}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and snapshot ForgeVault Desktop only")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("snapshot")
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--archive", required=True, type=Path)
    p = commands.add_parser("verify")
    p.add_argument("--archive", required=True, type=Path)
    p = commands.add_parser("restore")
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--into-new-home", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "snapshot":
        result = snapshot_desktop(args.home, args.archive)
    elif args.command == "verify":
        result = verify_snapshot(args.archive)
    else:
        result = restore_to_new_home(args.archive, args.into_new_home)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
