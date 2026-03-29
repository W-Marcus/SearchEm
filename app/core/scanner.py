# Author: Marcus Wallin

import logging
from pathlib import Path

from filelock import FileLock, Timeout
from models.common.scan import FileIndex, HashStore, ScanResult, hash_file

logger = logging.getLogger("searchem.core.scanner")


LOCK_FILENAME = "index.lock"
LOCK_TIMEOUT = 0  # fail immediately. Needed to avoid both CLI and REST making change at the same time. Even with this, issues could arise if used on same directory. TODO


def _gather(directory: Path, extensions: list[str]) -> FileIndex:
    """
    Recursively gather all files under directory grouped by extension.
    Files with extensions not in the allowed set are excluded.
    Hidden files and directories (starting with '.') are ignored.
    """
    allowed = {e.lower() for e in extensions}
    index: FileIndex = {}

    for file in directory.rglob("*"):
        if any(part.startswith(".") for part in file.relative_to(directory).parts):
            continue

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
            content_hash = hash_file(absolute)

            if hash_store.is_unchanged(relative_path, content_hash):
                unchanged.setdefault(ext, []).append(relative_path)
                logger.debug("Unchanged: %s", relative_path)
            else:
                to_process.setdefault(ext, []).append(relative_path)
                logger.debug("New or changed: %s", relative_path)

    return to_process, unchanged


class IndexLockError(RuntimeError):
    """Raised when the index lock cannot be acquired."""


class Scanner:
    def __init__(self, directory: Path, database: Path, extensions: list[str]) -> None:
        self.directory = directory
        self.database = database
        self.extensions = extensions
        self._lock = FileLock(database / LOCK_FILENAME, timeout=LOCK_TIMEOUT)

    def scan(self, force_reprocess: bool = False) -> ScanResult:
        """
        Scan directory and return a ScanResult.
        If force_reprocess is True, all files are marked for processing
        regardless of their hash (used for --update).
        Raises IndexLockError if another indexing operation is already running.
        """
        try:
            with self._lock:
                return self._scan(force_reprocess)
        except Timeout:
            raise IndexLockError(
                "Another indexing operation is already running. "
                "Only one process may index at a time."
            ) from None

    def _scan(self, force_reprocess: bool) -> ScanResult:
        index = _gather(self.directory, self.extensions)
        hash_store = HashStore.load(self.database)

        if force_reprocess:
            logger.info("Force reprocess enabled. All files will be re-embedded.")
            return ScanResult(to_process=index, unchanged={}, hash_store=hash_store)

        to_process, unchanged = _filter_unchanged(index, self.directory, hash_store)
        return ScanResult(to_process, unchanged, hash_store)
