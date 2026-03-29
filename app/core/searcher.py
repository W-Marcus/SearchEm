# Author: Marcus Wallin

import json
import logging
from pathlib import Path

import faiss
from core.chunker import chunk_file
from core.embedder import FAISS_FILENAME, METADATA_FILENAME, ModelRegistry
from models.common.scan import ChunkMeta
from models.common.search import QueryResult

logger = logging.getLogger("searchem.core.searcher")


class Searcher:
    def __init__(self, database: Path, directory: Path, model_id: str) -> None:
        self.directory = directory
        self.database = database
        self._model = ModelRegistry.get(model_id)

        index_path = database / FAISS_FILENAME
        if not index_path.exists():
            raise FileNotFoundError(
                f"No FAISS index found at {index_path}. "
                "Run with --refresh first to build the index."
            )
        logger.info("Loading FAISS index from %s", index_path)
        self.index = faiss.read_index(str(index_path))

        meta_path = database / METADATA_FILENAME
        if not meta_path.exists():
            raise FileNotFoundError(f"No metadata found at {meta_path}.")
        with meta_path.open("r") as f:
            data = json.load(f)
        self._metadata: list[ChunkMeta] = [
            ChunkMeta.model_validate(e) for e in data.get("entries", [])
        ]
        logger.info("Loaded %d metadata entries.", len(self._metadata))

    def _fetch_content(self, meta: ChunkMeta) -> str:
        relative_path = Path(meta.relative_path)
        absolute = self.directory / relative_path
        if not absolute.exists():
            return "(file no longer exists)"
        chunks = chunk_file(relative_path, absolute)
        for chunk in chunks:
            if chunk.chunk_id == meta.chunk_id:
                return "" if chunk.is_image else str(chunk.content)
        return "(chunk no longer found)"

    def search(self, query: str, k: int = 5) -> list[QueryResult]:
        embedding = self._model.embed_query(query)
        scores, indices = self.index.search(embedding.reshape(1, -1), k)

        results: list[QueryResult] = []
        for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
            if idx < 0 or idx >= len(self._metadata):
                continue
            meta = self._metadata[idx]
            results.append(
                QueryResult(
                    rank=rank,
                    score=float(score),
                    relative_path=meta.relative_path,
                    extension=meta.extension,
                    chunk_id=meta.chunk_id,
                    file_size=meta.file_size,
                    timestamp=meta.timestamp,
                    content=self._fetch_content(meta),
                )
            )
        return results
