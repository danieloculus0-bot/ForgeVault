import json

import pytest

from forgevault.storage.local import LocalVaultStorage, VaultIntegrityError
from forgevault.storage.object_snapshot import snapshot_objects, restore_objects


def test_snapshot_restore_round_trip(tmp_path):
    source = LocalVaultStorage(tmp_path / "source")
    backup = LocalVaultStorage(tmp_path / "backup")
    target = LocalVaultStorage(tmp_path / "target")
    digests = [source.put(payload)[0] for payload in (b"CAD rev A", b"", b"drawing rev B")]
    manifest = tmp_path / "manifest.json"
    assert len(snapshot_objects(source, backup, manifest)["objects"]) == 3
    assert restore_objects(backup, target, manifest) == 3
    assert [target.get(d) for d in digests] == [b"CAD rev A", b"", b"drawing rev B"]
    assert restore_objects(backup, target, manifest) == 3


def test_corrupt_snapshot_fails_before_target_writes(tmp_path):
    source = LocalVaultStorage(tmp_path / "source")
    backup = LocalVaultStorage(tmp_path / "backup")
    target = LocalVaultStorage(tmp_path / "target")
    source.put(b"first")
    broken = source.put(b"second")[0]
    manifest = tmp_path / "manifest.json"
    snapshot_objects(source, backup, manifest)
    backup._object_path(broken).write_bytes(b"tampered")
    with pytest.raises(VaultIntegrityError):
        restore_objects(backup, target, manifest)
    assert not list(target.root.rglob("*"))


def test_manifest_validation_rejects_duplicate_or_invalid_entries(tmp_path):
    source = LocalVaultStorage(tmp_path / "source")
    digest = source.put(b"data")[0]
    manifest = tmp_path / "manifest.json"
    for entries in ([{"sha256": digest, "size": 4}] * 2, [{"sha256": "../bad", "size": 4}]):
        manifest.write_text(json.dumps({"schema": "forgevault.object-snapshot.v1", "objects": entries}))
        with pytest.raises(ValueError):
            restore_objects(source, LocalVaultStorage(tmp_path / "target"), manifest)


def test_snapshot_refuses_same_store_and_existing_manifest(tmp_path):
    source = LocalVaultStorage(tmp_path / "source")
    manifest = tmp_path / "manifest.json"
    with pytest.raises(ValueError):
        snapshot_objects(source, source, manifest)
    manifest.write_text("{}")
    with pytest.raises(FileExistsError):
        snapshot_objects(source, LocalVaultStorage(tmp_path / "backup"), manifest)


def test_snapshot_rejects_nested_stores_and_in_store_manifest(tmp_path):
    source = LocalVaultStorage(tmp_path / "source")
    source.put(b"public synthetic sample")
    nested_backup = LocalVaultStorage(source.root / "backup")
    with pytest.raises(ValueError, match="non-nested"):
        snapshot_objects(source, nested_backup, tmp_path / "manifest.json")
    with pytest.raises(ValueError, match="non-nested"):
        snapshot_objects(LocalVaultStorage(source.root / "sub"), source, tmp_path / "manifest.json")
    backup = LocalVaultStorage(tmp_path / "backup")
    with pytest.raises(ValueError, match="outside"):
        snapshot_objects(source, backup, source.root / "manifest.json")
    with pytest.raises(ValueError, match="outside"):
        snapshot_objects(source, backup, backup.root / "manifest.json")
    assert not (tmp_path / "manifest.json").exists()
