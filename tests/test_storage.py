import concurrent.futures
import hashlib
from pathlib import Path

import pytest

from forgevault.storage.local import LocalVaultStorage, VaultIntegrityError


def test_local_vault_storage_is_content_addressed(tmp_path):
    storage = LocalVaultStorage(tmp_path)
    sha_a, uri_a, size_a = storage.put(b"same-bytes")
    sha_b, uri_b, size_b = storage.put(b"same-bytes")

    assert sha_a == sha_b
    assert uri_a == uri_b
    assert size_a == size_b == len(b"same-bytes")
    assert storage.get(sha_a) == b"same-bytes"


def test_empty_object_round_trip(tmp_path):
    storage = LocalVaultStorage(tmp_path)
    digest, _, size = storage.put(b"")
    assert digest == hashlib.sha256(b"").hexdigest()
    assert size == 0
    assert storage.get(digest) == b""


@pytest.mark.parametrize("digest", [
    "../not-an-object", "a" * 63, "A" * 64, "x" * 64, "", None,
])
def test_invalid_digest_is_rejected_before_path_access(tmp_path, digest):
    with pytest.raises(ValueError):
        LocalVaultStorage(tmp_path).get(digest)


def test_existing_corrupt_object_is_rejected_on_read_and_write(tmp_path):
    storage = LocalVaultStorage(tmp_path)
    digest, _, _ = storage.put(b"original engineering drawing")
    target = storage._object_path(digest)
    target.write_bytes(b"tampered content")

    with pytest.raises(VaultIntegrityError, match="checksum mismatch"):
        storage.get(digest)
    with pytest.raises(VaultIntegrityError, match="checksum mismatch"):
        storage.put(b"original engineering drawing")
    assert target.read_bytes() == b"tampered content"  # never silently repair


def test_atomic_link_never_exposes_partial_destination(tmp_path, monkeypatch):
    from forgevault.storage import local

    storage = LocalVaultStorage(tmp_path)
    payload = b"CAD assembly" * 10000
    expected_digest = hashlib.sha256(payload).hexdigest()
    observed = []
    real_link = local.os.link

    def inspect_link(src, dst):
        source, target = Path(src), Path(dst)
        assert source.parent == target.parent
        assert target.name == expected_digest
        assert not target.exists()
        assert source.read_bytes() == payload
        observed.append(True)
        return real_link(src, dst)

    monkeypatch.setattr(local.os, "link", inspect_link)
    digest, _, _ = storage.put(payload)
    assert observed == [True]
    assert storage.get(digest) == payload
    assert not list(tmp_path.rglob("*.tmp"))


def test_failed_link_does_not_leave_partial_object_or_temp(tmp_path, monkeypatch):
    from forgevault.storage import local

    storage = LocalVaultStorage(tmp_path)
    payload = b"interrupted release drawing"
    digest = hashlib.sha256(payload).hexdigest()

    def failing_link(src, dst):
        raise OSError("simulated storage failure")

    monkeypatch.setattr(local.os, "link", failing_link)
    with pytest.raises(OSError, match="simulated storage failure"):
        storage.put(payload)
    assert not storage._object_path(digest).exists()
    assert not list(tmp_path.rglob("*.tmp"))


def test_concurrent_same_hash_writers_get_valid_object(tmp_path):
    storage = LocalVaultStorage(tmp_path)
    payload = b"identical revision" * 4000
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(storage.put, [payload] * 16))
    assert len({sha for sha, _, _ in results}) == 1
    assert storage.get(results[0][0]) == payload
    assert not list(tmp_path.rglob("*.tmp"))
