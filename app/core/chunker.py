# Author: Marcus Wallin

# TODO:
# 1) Add more chunking strategies (function-based for code, sections for markdown, etc.)
# 2) Consider making chunking strategy configurable.

import logging
from pathlib import Path

from models.common.chunks import Chunk

logger = logging.getLogger("searchem.core.chunker")

CHUNK_SIZE = 300
CHUNK_OVERLAP = 50


def _sliding_window(text: str) -> list[str]:
    """
    Split text into overlapping chunks of CHUNK_SIZE words
    with CHUNK_OVERLAP words of overlap between consecutive chunks.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        chunk = words[start : start + CHUNK_SIZE]
        chunks.append(" ".join(chunk))
        if start + CHUNK_SIZE >= len(words):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def _text_to_chunks(relative_path: Path, text: str, id_prefix: str) -> list[Chunk]:
    """Convert raw text to sliding window chunks."""
    windows = _sliding_window(text)
    return [
        Chunk(
            file_path=relative_path,
            chunk_id=f"{id_prefix}_{i}",
            content=window,
        )
        for i, window in enumerate(windows)
    ]


def chunk_text(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """Split .txt / .md into overlapping word-level chunks."""
    text = absolute_path.read_text(encoding="utf-8", errors="ignore").strip()
    chunks = _text_to_chunks(relative_path, text, "chunk")
    logger.debug("%s → %d chunk(s)", relative_path, len(chunks))
    return chunks


def chunk_pdf(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """
    Extract text per page, then apply sliding window across the
    full document so chunks aren't artificially broken at page boundaries.
    """
    import pypdf

    with absolute_path.open("rb") as f:
        reader = pypdf.PdfReader(f)
        full_text = " ".join(page.extract_text() or "" for page in reader.pages).strip()

    chunks = _text_to_chunks(relative_path, full_text, "chunk")
    logger.debug("%s → %d chunk(s)", relative_path, len(chunks))
    return chunks


def chunk_docx(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """
    Extract all paragraph text from .docx, then apply sliding window
    across the full document.
    """
    import docx

    doc = docx.Document(str(absolute_path))
    full_text = " ".join(
        para.text.strip() for para in doc.paragraphs if para.text.strip()
    )

    chunks = _text_to_chunks(relative_path, full_text, "chunk")
    logger.debug("%s → %d chunk(s)", relative_path, len(chunks))
    return chunks


def chunk_image(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """Treat each image as a single chunk."""
    return [
        Chunk(
            file_path=relative_path,
            chunk_id="image",
            content=absolute_path,
            is_image=True,
        )
    ]


CHUNKERS: dict[str, object] = {
    ".txt": chunk_text,
    ".md": chunk_text,
    ".pdf": chunk_pdf,
    ".docx": chunk_docx,
    ".jpg": chunk_image,
    ".jpeg": chunk_image,
    ".png": chunk_image,
    ".gif": chunk_image,
    ".webp": chunk_image,
}


def chunk_file(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """Dispatch to the correct chunker based on file extension."""
    ext = relative_path.suffix.lower()
    chunker = CHUNKERS.get(ext)
    if chunker is None:
        logger.warning("No chunker for extension %s, skipping %s", ext, relative_path)
        return []
    return chunker(relative_path, absolute_path)  # type: ignore[operator]
