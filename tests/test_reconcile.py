import json

import pytest

from forgevault.storage.local import LocalVaultStorage
from forgevault.storage.object_snapshot import snapshot_objects
from forgevault.storage.reconcile import reconcile_manifest


def test_reconcile_detects_missing_orphan_corruption_and_strays(tmp_path):
    source = LocalVaultStorage(tmp_path / "source")
    backup = LocalVaultStorage(tmp_path / "backup")
    first = source.put(b"first")[0]
    second = source.put(b"second")[0]
    manifest = tmp_path / "manifest.json"
    snapshot_objects(source, backup, manifest)
    orphan = backup.put(b"unreferenced")[0]
    backup._object_path(first).write_bytes(b"corrupted")
    backup._object_path(second).unlink()
    (backup.root / "stray.txt").write_text("stray")
    report = reconcile_manifest(backup, manifest)
    assert report == {
        "expected": 2, "found": 2, "missing": [second],
        "orphan": [orphan], "corrupt": [first],
        "unexpected": ["stray.txt"],
    }
    assert backup._object_path(first).read_bytes() == b"corrupted"


def test_reconcile_clean_and_rejects_invalid_manifest(tmp_path):
    source = LocalVaultStorage(tmp_path / "source")
    backup = LocalVaultStorage(tmp_path / "backup")
    source.put(b"synthetic")
    manifest = tmp_path / "manifest.json"
    snapshot_objects(source, backup, manifest)
    report = reconcile_manifest(backup, manifest)
    assert report["expected"] == report["found"] == 1
    assert all(not report[k] for k in ("missing", "orphan", "corrupt", "unexpected"))
    entry = json.loads(manifest.read_text())["objects"][0]
    manifest.write_text(json.dumps({"schema": "forgevault.object-snapshot.v1", "objects": [entry, entry]}))
    with pytest.raises(ValueError, match="duplicate"):
        reconcile_manifest(backup, manifest)


def test_reconcile_does_not_follow_symlink(tmp_path):
    source = LocalVaultStorage(tmp_path / "source")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema": "forgevault.object-snapshot.v1", "objects": []}))
    source.root.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("private")
    link = source.root / "link"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    assert reconcile_manifest(source, manifest)["unexpected"] == ["link"]
