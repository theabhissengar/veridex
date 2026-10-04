from pathlib import Path


class LocalFilesystemStorage:
    """Local bytes for V1. Callers pass storage keys, not absolute paths."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def path_for(self, key: str) -> str:
        return str(self._path(key))

    def _path(self, key: str) -> Path:
        relative = Path(key)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("storage key must be a relative path")
        return self.root / relative
