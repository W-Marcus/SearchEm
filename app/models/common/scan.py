# Author: Marcus Wallin

import hashlib
import json
import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger("searchem.models.scan")

HASHES_FILENAME = "hashes.json"

FileIndex = dict[str, list[Path]]


class FileRecord(BaseModel):
    content_hash: str


class HashStore(BaseModel):
    records: dict[str, FileRecord] = {}

    @classmethod
    def load(cls, database: Path) -> "HashStore":
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
    file_size: int
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

    def commit_file(self, relative_path: Path, directory: Path, database: Path) -> None:
        """Commit a single file's hash immediately after embedding."""
        content_hash = _hash_file(directory / relative_path)
        self._hash_store.update(relative_path, content_hash)
        self._hash_store.save(database)
        logger.debug("Hash committed: %s", relative_path)

    def commit(self, directory: Path, database: Path) -> None:
        """Commit all processed files at once. Use when not doing incremental commits."""
        for paths in self.to_process.values():
            for relative_path in paths:
                content_hash = _hash_file(directory / relative_path)
                self._hash_store.update(relative_path, content_hash)
        self._hash_store.save(database)
        logger.info("Hash store committed.")


def _hash_file(path: Path) -> str:
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
