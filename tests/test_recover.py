import json
import subprocess
import sys

import pytest

from forgevault.storage.local import LocalVaultStorage, VaultIntegrityError
from forgevault.storage.object_snapshot import snapshot_objects
from forgevault.storage.recover import recover_missing


def setup(tmp_path):
    source = LocalVaultStorage(tmp_path / "source")
    snapshot = LocalVaultStorage(tmp_path / "snapshot")
    target = LocalVaultStorage(tmp_path / "target")
    first = source.put(b"fictional engineering revision one")[0]
    second = source.put(b"fictional engineering revision two")[0]
    manifest = tmp_path / "manifest.json"
    snapshot_objects(source, snapshot, manifest)
    return snapshot, target, manifest, first, second


def test_recovers_missing_idempotently_and_preserves_orphans(tmp_path):
    snapshot, target, manifest, first, second = setup(tmp_path)
    target.put(snapshot.get(first))
    orphan = target.put(b"unrelated synthetic object")[0]
    result = recover_missing(snapshot, target, manifest)
    assert result["restored"] == [second]
    assert result["remaining_orphan"] == [orphan]
    assert target.get(second) == snapshot.get(second)
    assert recover_missing(snapshot, target, manifest)["restored"] == []


def test_corrupt_snapshot_fails_before_any_target_write(tmp_path):
    snapshot, target, manifest, first, second = setup(tmp_path)
    snapshot._object_path(second).write_bytes(b"tampered")
    with pytest.raises(VaultIntegrityError):
        recover_missing(snapshot, target, manifest)
    assert not target.root.exists()


def test_corrupt_target_is_not_overwritten(tmp_path):
    snapshot, target, manifest, first, second = setup(tmp_path)
    target.put(snapshot.get(first))
    target._object_path(first).write_bytes(b"damaged")
    with pytest.raises(VaultIntegrityError):
        recover_missing(snapshot, target, manifest)
    assert target._object_path(first).read_bytes() == b"damaged"
    assert not target._object_path(second).exists()


def test_cli_restores_and_reports_json(tmp_path):
    snapshot, target, manifest, first, second = setup(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-m", "forgevault.storage.recover",
         "--snapshot", str(snapshot.root), "--target", str(target.root),
         "--manifest", str(manifest)],
        capture_output=True, text=True, check=True,
    )
    assert json.loads(proc.stdout)["restored"] == sorted([first, second])
    assert target.get(first) == snapshot.get(first)


def test_rejects_nested_store(tmp_path):
    snapshot, target, manifest, *_ = setup(tmp_path)
    with pytest.raises(ValueError, match="non-nested"):
        recover_missing(snapshot, LocalVaultStorage(snapshot.root / "nested"), manifest)
