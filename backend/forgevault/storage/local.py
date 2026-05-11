import hashlib
from pathlib import Path


class LocalVaultStorage:
    """Content-addressed local vault storage.

    The adapter never overwrites by caller-provided filename. Objects are stored under their SHA-256 digest,
    making it safe to deduplicate and later replace this adapter with S3-compatible storage.
    """

    adapter_name = "local"

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def put(self, content: bytes) -> tuple[str, str, int]:
        sha256 = hashlib.sha256(content).hexdigest()
        destination = self.root / sha256[:2] / sha256[2:4] / sha256
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            destination.write_bytes(content)
        return sha256, f"file://{destination}", len(content)

    def get(self, sha256: str) -> bytes:
        path = self.root / sha256[:2] / sha256[2:4] / sha256
        return path.read_bytes()
