# Author: Marcus Wallin

import hashlib
import json
import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger("searchem.models.scan")

HASHES_FILENAME = "hashes.json"

# extension -> list of relative paths
FileIndex = dict[str, list[Path]]


class FileRecord(BaseModel):
    content_hash: str


class HashStore(BaseModel):
    records: dict[str, FileRecord] = {}

    @classmethod
    def load(cls, database: Path) -> "HashStore":
        """Load hash store from database directory, returning empty store if not found."""
        path = database / HASHES_FILENAME
        if not path.exists():
            return cls()
        with path.open("r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("Hash store is malformed, starting fresh.")
            return cls()
        return cls.model_validate(data)

    def save(self, database: Path) -> None:
        """Persist hash store to database directory."""
        with (database / HASHES_FILENAME).open("w") as f:
            json.dump(self.model_dump(), f, indent=2)

    def is_unchanged(self, relative_path: Path, content_hash: str) -> bool:
        record = self.records.get(str(relative_path))
        return record is not None and record.content_hash == content_hash

    def update(self, relative_path: Path, content_hash: str) -> None:
        self.records[str(relative_path)] = FileRecord(content_hash=content_hash)


class ChunkMeta(BaseModel):
    relative_path: str
    extension: str
    chunk_id: str
    file_size: int  # in bytes
    timestamp: float


class ScanResult:
    def __init__(
        self,
        to_process: FileIndex,
        unchanged: FileIndex,
        hash_store: HashStore,
    ) -> None:
        self.to_process = to_process
        self.unchanged = unchanged
        self._hash_store = hash_store

        total_process = sum(len(v) for v in to_process.values())
        total_unchanged = sum(len(v) for v in unchanged.values())
        logger.info(
            "Scan complete — to process: %d, unchanged: %d",
            total_process,
            total_unchanged,
        )

    def commit(self, directory: Path, database: Path) -> None:
        """
        Update hashes for processed files and persist to disk.
        Call this only after successful embedding.
        """
        for paths in self.to_process.values():
            for relative_path in paths:
                content_hash = hash_file(directory / relative_path)
                self._hash_store.update(relative_path, content_hash)
        self._hash_store.save(database)
        logger.info("Hash store committed.")


def hash_file(path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
