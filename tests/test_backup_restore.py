import json

import pytest

from forgevault.backup_verify import create_manifest
from forgevault.backup_restore import main, restore_files


def test_restore_roundtrip_and_cli(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "sub").mkdir()
    (source / "sub" / "drawing.txt").write_bytes(b"revision A")
    manifest = create_manifest(source)
    destination = tmp_path / "restored"
    result = restore_files(source, manifest, destination)
    assert result["ok"]
    assert (destination / "sub" / "drawing.txt").read_bytes() == b"revision A"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    assert main([str(source), str(manifest_path), str(tmp_path / "second")]) == 0


def test_rejects_modified_source_without_creating_destination(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "part").write_bytes(b"original")
    manifest = create_manifest(source)
    (source / "part").write_bytes(b"tampered")
    target = tmp_path / "restored"
    with pytest.raises(ValueError, match="verification failed"):
        restore_files(source, manifest, target)
    assert not target.exists()


def test_never_overwrites_existing_destination(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "part").write_text("backup")
    destination = tmp_path / "destination"
    destination.mkdir()
    (destination / "part").write_text("keep")
    with pytest.raises(FileExistsError):
        restore_files(source, create_manifest(source), destination)
    assert (destination / "part").read_text() == "keep"


def test_rejects_nested_destination(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ValueError, match="inside"):
        restore_files(source, create_manifest(source), source / "nested")


def test_rejects_unsafe_manifest_paths(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    manifest = {"format": "forgevault-file-backup-v1",
                "files": [{"path": "../outside", "size": 0, "sha256": "0" * 64}]}
    with pytest.raises(ValueError, match="manifest"):
        restore_files(source, manifest, tmp_path / "restored")
