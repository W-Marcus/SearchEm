# Author: Marcus Wallin

import hashlib
import json
import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger("msearch.scanner")

HASHES_FILENAME = "hashes.json"


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


# extension -> list of relative paths
FileIndex = dict[str, list[Path]]


def _hash_file(path: Path) -> str:
    """Compute SHA-256 hash of file contents."""

    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _gather(directory: Path, extensions: list[str]) -> FileIndex:
    """
    Recursively gather all files under directory grouped by extension.
    Files with extensions not in the allowed set are excluded.
    """

    allowed = {e.lower() for e in extensions}
    index: FileIndex = {}

    for file in directory.rglob("*"):
        if not file.is_file():
            continue
        ext = file.suffix.lower()
        if ext not in allowed:
            continue
        relative = file.relative_to(directory)
        index.setdefault(ext, []).append(relative)

    total = sum(len(v) for v in index.values())
    logger.info("Gathered %d files across %d extension(s)", total, len(index))
    return index


def _filter_unchanged(
    index: FileIndex,
    directory: Path,
    hash_store: HashStore,
) -> tuple[FileIndex, FileIndex]:
    """
    Split index into changed and unchanged files based on content hash.
    Returns (to_process, unchanged).
    """

    to_process: FileIndex = {}
    unchanged: FileIndex = {}

    for ext, paths in index.items():
        for relative_path in paths:
            absolute = directory / relative_path
            content_hash = _hash_file(absolute)

            if hash_store.is_unchanged(relative_path, content_hash):
                unchanged.setdefault(ext, []).append(relative_path)
                logger.debug("Unchanged: %s", relative_path)
            else:
                to_process.setdefault(ext, []).append(relative_path)
                logger.debug("New or changed: %s", relative_path)

    return to_process, unchanged


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
                content_hash = _hash_file(directory / relative_path)
                self._hash_store.update(relative_path, content_hash)
        self._hash_store.save(database)
        logger.info("Hash store committed.")


class Scanner:
    def __init__(self, directory: Path, database: Path, extensions: list[str]) -> None:
        self.directory = directory
        self.database = database
        self.extensions = extensions

    def scan(self, force_reprocess: bool = False) -> ScanResult:
        """
        Scan directory and return a ScanResult.
        If force_reprocess is True, all files are marked for processing
        regardless of their hash (used for --update).
        """

        index = _gather(self.directory, self.extensions)
        hash_store = HashStore.load(self.database)

        if force_reprocess:
            logger.info("Force reprocess enabled — all files will be re-embedded.")
            return ScanResult(
                to_process=index,
                unchanged={},
                hash_store=hash_store,
            )

        to_process, unchanged = _filter_unchanged(index, self.directory, hash_store)
        return ScanResult(to_process, unchanged, hash_store)
