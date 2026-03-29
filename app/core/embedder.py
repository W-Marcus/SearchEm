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


class _LoadedModel:
    def __init__(self, model_id: str) -> None:
        import torch

        logger.info("Loading model: %s", model_id)
        self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        self.model = AutoModel.from_pretrained(model_id, trust_remote_code=True)
        self.model.eval()
        self._torch = torch
        logger.info("Model loaded: %s", model_id)

    def embed(self, chunk: Chunk) -> np.ndarray:
        if chunk.is_image:
            image = Image.open(chunk.content).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
        else:
            inputs = self.processor(
                text=str(chunk.content),
                return_tensors="pt",
                truncation=True,
                padding=True,
            )
        with self._torch.no_grad():
            outputs = self.model(**inputs)
        embedding = outputs.last_hidden_state.mean(dim=1).squeeze().float().numpy()
        norm = float(np.linalg.norm(embedding))
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def embed_query(self, query: str) -> np.ndarray:
        inputs = self.processor(
            text=query,
            return_tensors="pt",
            truncation=True,
            padding=True,
        )
        with self._torch.no_grad():
            outputs = self.model(**inputs)
        embedding = outputs.last_hidden_state.mean(dim=1).squeeze().float().numpy()
        norm = float(np.linalg.norm(embedding))
        if norm > 0:
            embedding = embedding / norm
        return embedding


class ModelRegistry:
    """Process-wide cache of loaded models. Keyed by model ID."""

    _cache: dict[str, _LoadedModel] = {}

    @classmethod
    def get(cls, model_id: str) -> _LoadedModel:
        if model_id not in cls._cache:
            cls._cache[model_id] = _LoadedModel(model_id)
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

    def _embed_and_add(self, chunk: Chunk, meta: ChunkMeta) -> None:
        embedding = self._model.embed(chunk)
        self._ensure_index(embedding.shape[0])
        self._index.add(embedding.reshape(1, -1))  # type: ignore[union-attr]
        self._meta.entries.append(meta)

    def _make_meta(self, chunk: Chunk) -> ChunkMeta:
        absolute = self.directory / chunk.file_path
        stat = absolute.stat()
        return ChunkMeta(
            relative_path=str(chunk.file_path),
            extension=chunk.file_path.suffix.lower(),
            chunk_id=chunk.chunk_id,
            file_size=stat.st_size,
            timestamp=stat.st_mtime,
        )

    def embed_index(self, index: FileIndex) -> None:
        total_files = sum(len(v) for v in index.values())
        logger.info("Embedding %d file(s)...", total_files)
        processed = 0

        for ext, paths in index.items():
            logger.info("Processing %d %s file(s)", len(paths), ext)
            for relative_path in paths:
                absolute = self.directory / relative_path
                chunks = chunk_file(relative_path, absolute)
                if not chunks:
                    continue
                self._meta.remove_file(relative_path)
                for chunk in chunks:
                    try:
                        meta = self._make_meta(chunk)
                        self._embed_and_add(chunk, meta)
                    except Exception as e:
                        logger.error(
                            "Failed to embed %s [%s]: %s",
                            relative_path,
                            chunk.chunk_id,
                            e,
                        )
                processed += 1
                logger.info(
                    "(%d/%d) Embedded: %s", processed, total_files, relative_path
                )

    def commit(self) -> None:
        if self._index is None:
            logger.warning("No embeddings to commit.")
            return
        faiss.write_index(self._index, str(self.database / FAISS_FILENAME))
        self._meta.save(self.database)
        logger.info("Embedder committed — %d total chunk(s).", len(self._meta.entries))
