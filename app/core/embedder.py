# Author: Marcus Wallin

import json
import logging
from pathlib import Path

import faiss
import numpy as np
from core.chunker import chunk_file
from models.common.chunks import Chunk
from models.common.scan import ChunkMeta, FileIndex
from PIL import Image
from pydantic import BaseModel
from transformers import AutoModel, AutoProcessor

logger = logging.getLogger("searchem.core.embedder")

FAISS_FILENAME = "index.faiss"
METADATA_FILENAME = "metadata.json"
DEFAULT_BATCH_SIZE = 32
COMMIT_EVERY_N_FILES = 10


class _LoadedModel:
    def __init__(self, model_id: str, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        import torch

        self.batch_size = batch_size
        logger.info("Loading model: %s", model_id)
        self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(model_id, trust_remote_code=True)
        self.model.eval()
        self._torch = torch
        logger.info("Model loaded: %s", model_id)

    def _normalise(self, embeddings: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return (embeddings / norms).astype(np.float32)

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            inputs = self.processor(
                text=batch,
                return_tensors="pt",
                truncation=True,
                padding=True,
            )
            with self._torch.inference_mode():
                outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state.mean(dim=1).float().detach().numpy()
            all_embeddings.append(embeddings)
        return self._normalise(np.vstack(all_embeddings))

    def embed_image(self, path: Path) -> np.ndarray:
        image = Image.open(path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        with self._torch.inference_mode():
            outputs = self.model(**inputs)
        embedding = outputs.last_hidden_state.mean(dim=1).float().detach().numpy()
        return self._normalise(embedding)

    def embed_query(self, query: str) -> np.ndarray:
        return self.embed_texts([query])[0]

    def embed_chunks(self, chunks: list[Chunk]) -> np.ndarray:
        results: dict[int, np.ndarray] = {}

        text_indices = [i for i, c in enumerate(chunks) if not c.is_image]
        image_indices = [i for i, c in enumerate(chunks) if c.is_image]

        if text_indices:
            texts = [str(chunks[i].content) for i in text_indices]
            text_embeddings = self.embed_texts(texts)
            for idx, embedding in zip(text_indices, text_embeddings):
                results[idx] = embedding

        for i in image_indices:
            results[i] = self.embed_image(chunks[i].content)[0]  # type: ignore[arg-type]

        return np.stack([results[i] for i in range(len(chunks))])


class ModelRegistry:
    _cache: dict[str, _LoadedModel] = {}

    @classmethod
    def get(cls, model_id: str, batch_size: int = DEFAULT_BATCH_SIZE) -> _LoadedModel:
        if model_id not in cls._cache:
            cls._cache[model_id] = _LoadedModel(model_id, batch_size)
        return cls._cache[model_id]

    @classmethod
    def loaded(cls) -> list[str]:
        return list(cls._cache.keys())


class MetadataStore(BaseModel):
    entries: list[ChunkMeta] = []

    @classmethod
    def load(cls, database: Path) -> "MetadataStore":
        path = database / METADATA_FILENAME
        if not path.exists():
            return cls()
        with path.open("r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return cls()
        return cls.model_validate(data)

    def save(self, database: Path) -> None:
        with (database / METADATA_FILENAME).open("w") as f:
            json.dump(self.model_dump(), f, indent=2)

    def remove_file(self, relative_path: Path) -> None:
        self.entries = [
            e for e in self.entries if e.relative_path != str(relative_path)
        ]


class Embedder:
    def __init__(self, model_id: str, directory: Path, database: Path) -> None:
        self.directory = directory
        self.database = database
        self._model = ModelRegistry.get(model_id)
        self._meta = MetadataStore.load(database)
        self._index = self._load_or_create_index()

    def _load_or_create_index(self) -> faiss.Index:
        path = self.database / FAISS_FILENAME
        if path.exists():
            logger.info("Loading existing FAISS index.")
            return faiss.read_index(str(path))
        logger.info("Creating new FAISS index.")
        return None  # type: ignore[return-value]

    def _ensure_index(self, dim: int) -> None:
        if self._index is None:
            self._index = faiss.IndexFlatIP(dim)
            logger.info("Initialised FAISS index with dim=%d", dim)

    def _make_meta(self, chunk: Chunk) -> ChunkMeta:
        """Build a ChunkMeta from a Chunk, copying all location fields."""
        absolute = self.directory / chunk.file_path
        stat = absolute.stat()
        return ChunkMeta(
            relative_path=str(chunk.file_path),
            extension=chunk.file_path.suffix.lower(),
            chunk_id=chunk.chunk_id,
            file_size=stat.st_size,
            timestamp=stat.st_mtime,
            # location fields — None for types that don't populate them
            line_start=chunk.line_start,
            line_end=chunk.line_end,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            paragraph_start=chunk.paragraph_start,
            paragraph_end=chunk.paragraph_end,
            chapter=chunk.chapter,
        )

    def embed_file(self, relative_path: Path) -> int:
        absolute = self.directory / relative_path
        chunks = chunk_file(relative_path, absolute)
        if not chunks:
            return 0

        self._meta.remove_file(relative_path)

        try:
            embeddings = self._model.embed_chunks(chunks)
        except Exception as e:
            logger.error("Failed to embed %s: %s", relative_path, e)
            return 0

        metas = [self._make_meta(chunk) for chunk in chunks]
        self._ensure_index(embeddings.shape[1])

        for embedding, meta in zip(embeddings, metas):
            self._index.add(embedding.reshape(1, -1))  # type: ignore[union-attr]
            self._meta.entries.append(meta)

        return len(chunks)

    def incremental_commit(self) -> None:
        if self._index is None:
            return
        faiss.write_index(self._index, str(self.database / FAISS_FILENAME))
        self._meta.save(self.database)
        logger.debug("Incremental commit.")

    def embed_index(self, index: FileIndex) -> None:
        total_files = sum(len(v) for v in index.values())
        logger.info("Embedding %d file(s)...", total_files)
        processed = 0
        since_last_commit = 0

        for ext, paths in index.items():
            logger.info("Processing %d %s file(s)", len(paths), ext)
            for relative_path in paths:
                n_chunks = self.embed_file(relative_path)
                if n_chunks == 0:
                    continue

                processed += 1
                since_last_commit += 1
                logger.info(
                    "(%d/%d) Embedded: %s (%d chunk(s))",
                    processed,
                    total_files,
                    relative_path,
                    n_chunks,
                )

                if since_last_commit >= COMMIT_EVERY_N_FILES:
                    self.incremental_commit()
                    since_last_commit = 0

    def commit(self) -> None:
        if self._index is None:
            logger.warning("No embeddings to commit.")
            return
        faiss.write_index(self._index, str(self.database / FAISS_FILENAME))
        self._meta.save(self.database)
        logger.info("Embedder committed — %d total chunk(s).", len(self._meta.entries))
