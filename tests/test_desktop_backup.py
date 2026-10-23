"""Disaster-recovery regression using actual ForgeVault SQLite ORM schema."""
from __future__ import annotations

import sqlite3
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from forgevault.database import Base
from forgevault.models import FileObject
from forgevault.services.desktop_backup import (
    VaultSnapshotError,
    restore_to_new_home,
    snapshot_desktop,
    verify_snapshot,
)
from forgevault.storage.local import LocalVaultStorage


def _desktop_fixture(tmp_path):
    home = tmp_path / "running-vault"
    root = home / "data" / "vault"
    root.mkdir(parents=True)
    storage = LocalVaultStorage(root)
    digest, uri, size = storage.put(b"released drawing revision with immutable bytes")
    db_path = home / "data" / "forgevault.db"
    engine = create_engine("sqlite+pysqlite:///" + db_path.as_posix())
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(FileObject(
            sha256=digest, byte_size=size, storage_adapter="local",
            storage_uri=uri, mime_type="application/pdf",
        ))
        db.commit()
    engine.dispose()
    return home, digest


def test_snapshot_verifies_and_restores_without_overwriting_original(tmp_path):
    home, digest = _desktop_fixture(tmp_path)
    archive = tmp_path / "backup.zip"
    snapshot = snapshot_desktop(home, archive)
    assert archive.exists()
    assert snapshot["verified"] is True
    assert snapshot["object_count"] == 1
    assert verify_snapshot(archive)["db_sha256"] == snapshot["db_sha256"]

    restored_home = tmp_path / "recovered-vault"
    restored = restore_to_new_home(archive, restored_home)
    assert restored["verified"] is True
    assert LocalVaultStorage(restored_home / "data" / "vault").get(digest) == (
        b"released drawing revision with immutable bytes"
    )
    with sqlite3.connect(restored_home / "data" / "forgevault.db") as db:
        db_uri = db.execute("SELECT storage_uri FROM file_objects WHERE sha256=?", (digest,)).fetchone()[0]
    assert db_uri.startswith("file://")
    assert str(restored_home) in db_uri
    assert str(home) not in db_uri
    assert LocalVaultStorage(home / "data" / "vault").get(digest) == (
        b"released drawing revision with immutable bytes"
    )


def test_corrupted_referenced_object_prevents_snapshot_publication(tmp_path):
    home, digest = _desktop_fixture(tmp_path)
    obj = LocalVaultStorage(home / "data" / "vault")._object_path(digest)
    obj.write_bytes(b"this content is corrupt")
    target = tmp_path / "never-publish.zip"
    with pytest.raises(VaultSnapshotError, match="corrupt"):
        snapshot_desktop(home, target)
    assert not target.exists()


def test_archive_with_modified_object_is_rejected_before_restore(tmp_path):
    home, _digest = _desktop_fixture(tmp_path)
    original = tmp_path / "valid.zip"
    tampered = tmp_path / "tampered.zip"
    snapshot_desktop(home, original)
    with zipfile.ZipFile(original) as src, zipfile.ZipFile(tampered, "w") as dst:
        for member in src.namelist():
            data = src.read(member)
            if member.startswith("objects/"):
                data = b"malicious replacement"
            dst.writestr(member, data)
    with pytest.raises(VaultSnapshotError, match="integrity"):
        verify_snapshot(tampered)
    output = tmp_path / "should-not-exist"
    with pytest.raises(VaultSnapshotError):
        restore_to_new_home(tampered, output)
    assert not output.exists()


def test_restore_refuses_existing_target_even_if_empty(tmp_path):
    home, _digest = _desktop_fixture(tmp_path)
    archive = tmp_path / "backup.zip"
    snapshot_desktop(home, archive)
    existing = tmp_path / "existing-install"
    existing.mkdir()
    (existing / "important.txt").write_text("keep me", encoding="utf-8")
    with pytest.raises(FileExistsError, match="Refusing"):
        restore_to_new_home(archive, existing)
    assert (existing / "important.txt").read_text(encoding="utf-8") == "keep me"
