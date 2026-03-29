# Author: Marcus Wallin

# TODO:
# 1) Add more chunking strategies (function-based for code, sections for markdown, etc.)
# 2) Consider making chunking strategy configurable.

import logging
from pathlib import Path

from models.common.chunks import Chunk

logger = logging.getLogger("searchem.core.chunker")


def chunk_text(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """Split .txt / .md by non-empty paragraphs (double newline)."""
    text = absolute_path.read_text(encoding="utf-8", errors="ignore")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = [
        Chunk(
            file_path=relative_path,
            chunk_id=f"paragraph_{i}",
            content=paragraph,
        )
        for i, paragraph in enumerate(paragraphs)
    ]
    logger.debug("%s → %d paragraph chunk(s)", relative_path, len(chunks))
    return chunks


def chunk_pdf(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """Split PDF by page using pypdf."""
    import pypdf

    chunks: list[Chunk] = []
    with absolute_path.open("rb") as f:
        reader = pypdf.PdfReader(f)
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            chunks.append(
                Chunk(
                    file_path=relative_path,
                    chunk_id=f"page_{i}",
                    content=text.strip(),
                )
            )
    logger.debug("%s → %d page chunk(s)", relative_path, len(chunks))
    return chunks


def chunk_docx(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """Split .docx by non-empty paragraphs using python-docx."""
    import docx

    doc = docx.Document(str(absolute_path))
    chunks: list[Chunk] = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text:
            continue
        chunks.append(
            Chunk(
                file_path=relative_path,
                chunk_id=f"paragraph_{i}",
                content=text,
            )
        )
    logger.debug("%s → %d paragraph chunk(s)", relative_path, len(chunks))
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
