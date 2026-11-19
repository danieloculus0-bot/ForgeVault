import json

import pytest

from forgevault.backup_verify import create_manifest, verify_manifest, main


def test_clean_copy(tmp_path):
    src, dst = tmp_path / "source", tmp_path / "copy"
    src.mkdir()
    dst.mkdir()
    (src / "nested").mkdir()
    (dst / "nested").mkdir()
    for root in (src, dst):
        (root / "nested" / "drawing.pdf").write_bytes(b"sample PDF bytes")
    manifest = create_manifest(src)
    assert verify_manifest(dst, manifest) == {
        "ok": True, "checked": 1, "missing": [], "extra": [], "changed": []
    }


def test_detects_changed_missing_extra(tmp_path):
    root = tmp_path / "files"
    root.mkdir()
    (root / "a").write_bytes(b"123")
    (root / "b").write_bytes(b"456")
    manifest = create_manifest(root)
    (root / "a").write_bytes(b"789")
    (root / "b").unlink()
    (root / "c").write_bytes(b"extra")
    result = verify_manifest(root, manifest)
    assert result == {"ok": False, "checked": 2, "missing": ["b"],
                      "extra": ["c"], "changed": ["a"]}


@pytest.mark.parametrize("path", ["../escape", "/absolute", "a/../b", "a//b", "a\\b"])
def test_rejects_unsafe_manifest_paths(tmp_path, path):
    tmp_path.joinpath("data").mkdir()
    with pytest.raises(ValueError):
        verify_manifest(tmp_path / "data", {"format": "forgevault-file-backup-v1",
            "files": [{"path": path, "size": 0, "sha256": "0" * 64}]})


def test_rejects_duplicates(tmp_path):
    record = {"path": "a", "size": 0, "sha256": "0" * 64}
    with pytest.raises(ValueError):
        verify_manifest(tmp_path, {"format": "forgevault-file-backup-v1", "files": [record, record]})


def test_cli_roundtrip(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "part.txt").write_text("test")
    manifest = tmp_path / "manifest.json"
    assert main(["create", str(root), str(manifest)]) == 0
    assert json.loads(manifest.read_text())["files"][0]["path"] == "part.txt"
    assert main(["verify", str(root), str(manifest)]) == 0
    (root / "part.txt").write_text("changed")
    assert main(["verify", str(root), str(manifest)]) == 1
