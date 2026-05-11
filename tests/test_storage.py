from forgevault.storage.local import LocalVaultStorage


def test_local_vault_storage_is_content_addressed(tmp_path):
    storage = LocalVaultStorage(tmp_path)
    sha_a, uri_a, size_a = storage.put(b"same-bytes")
    sha_b, uri_b, size_b = storage.put(b"same-bytes")

    assert sha_a == sha_b
    assert uri_a == uri_b
    assert size_a == size_b == len(b"same-bytes")
    assert storage.get(sha_a) == b"same-bytes"
