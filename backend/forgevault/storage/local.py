"""Atomic, content-addressed storage for managed engineering files.

A digest filename is meaningful only if the stored bytes match it. A
partially written or tampered object must never be silently trusted.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path


class VaultIntegrityError(OSError):
    """A stored object does not match its SHA-256 identity."""


class LocalVaultStorage:
    """Local SHA-256 object store; caller-provided file names never become paths."""

    adapter_name = "local"
    _DIGEST = re.compile(r"[0-9a-f]{64}\Z")

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _object_path(self, sha256: str) -> Path:
        if not isinstance(sha256, str) or not self._DIGEST.fullmatch(sha256):
            raise ValueError("sha256 must be a 64-character lowercase hex digest")
        return self.root / sha256[:2] / sha256[2:4] / sha256

    def _verified_read(self, sha256: str, path: Path) -> bytes:
        content = path.read_bytes()
        observed = hashlib.sha256(content).hexdigest()
        if observed != sha256:
            raise VaultIntegrityError(
                f"ForgeVault stored-object checksum mismatch for {sha256}; "
                f"expected {sha256}, observed {observed}"
            )
        return content

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        """Persist a completed rename when directory fsync is supported."""
        if os.name != "posix":
            return
        fd = None
        try:
            fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            os.fsync(fd)
        except OSError:
            # Some mounted/network filesystems do not support directory fsync.
            # The object file itself was already fsynced before rename.
            pass
        finally:
            if fd is not None:
                os.close(fd)

    def put(self, content: bytes) -> tuple[str, str, int]:
        sha256 = hashlib.sha256(content).hexdigest()
        destination = self._object_path(sha256)
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists():
            # An existing digest name alone is not proof that its bytes are valid.
            self._verified_read(sha256, destination)
        else:
            temp_path = None
            try:
                # Stage on the same filesystem, flush and fsync *before* the
                # atomic name switch. Concurrent writers have identical bytes
                # for a given digest and cannot expose a partial destination.
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=destination.parent,
                    prefix=f".{sha256}.", suffix=".tmp", delete=False
                ) as staged:
                    temp_path = Path(staged.name)
                    staged.write(content)
                    staged.flush()
                    os.fsync(staged.fileno())
                if destination.exists():
                    self._verified_read(sha256, destination)
                else:
                    os.replace(temp_path, destination)
                    temp_path = None
                    self._sync_directory(destination.parent)
            finally:
                if temp_path is not None:
                    temp_path.unlink(missing_ok=True)

        return sha256, f"file://{destination}", len(content)

    def get(self, sha256: str) -> bytes:
        return self._verified_read(sha256, self._object_path(sha256))
