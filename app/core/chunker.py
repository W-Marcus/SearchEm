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


def _sliding_window(words: list[str]) -> list[tuple[str, int, int]]:
    """
    Split a flat word list into overlapping chunks.

    Returns a list of (text, word_start_index, word_end_index) tuples
    where the indices are into the original ``words`` list (0-based, inclusive).
    """
    if not words:
        return []

    chunks: list[tuple[str, int, int]] = []
    start = 0
    while start < len(words):
        end = min(start + CHUNK_SIZE - 1, len(words) - 1)
        chunks.append((" ".join(words[start : end + 1]), start, end))
        if end == len(words) - 1:
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def _word_index_to_line(word_line_map: list[int], word_index: int) -> int:
    """Return the 1-based line number for a given word index."""
    if word_index >= len(word_line_map):
        return word_line_map[-1] if word_line_map else 1
    return word_line_map[word_index]


def chunk_text(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """Split plain text or code into overlapping word-level chunks with line numbers."""
    raw = absolute_path.read_text(encoding="utf-8", errors="ignore")
    lines = raw.splitlines()

    words: list[str] = []
    word_line_map: list[int] = []  # word_index → 1-based line number

    for line_no, line in enumerate(lines, start=1):
        for word in line.split():
            words.append(word)
            word_line_map.append(line_no)

    windows = _sliding_window(words)
    chunks: list[Chunk] = []

    for i, (text, w_start, w_end) in enumerate(windows):
        chunks.append(
            Chunk(
                file_path=relative_path,
                chunk_id=f"chunk_{i}",
                content=text,
                line_start=_word_index_to_line(word_line_map, w_start),
                line_end=_word_index_to_line(word_line_map, w_end),
            )
        )

    logger.debug("%s → %d chunk(s)", relative_path, len(chunks))
    return chunks


def chunk_pdf(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """
    Extract text per page then apply a sliding window across the full document.
    Each chunk records which PDF pages it spans.
    """
    import pypdf

    with absolute_path.open("rb") as f:
        reader = pypdf.PdfReader(f)
        # Build a per-word page map alongside the flat word list
        words: list[str] = []
        word_page_map: list[int] = []  # word_index → 1-based page number

        for page_no, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            for word in page_text.split():
                words.append(word)
                word_page_map.append(page_no)

    windows = _sliding_window(words)
    chunks: list[Chunk] = []

    for i, (text, w_start, w_end) in enumerate(windows):
        p_start = word_page_map[w_start] if w_start < len(word_page_map) else 1
        p_end = word_page_map[min(w_end, len(word_page_map) - 1)]
        chunks.append(
            Chunk(
                file_path=relative_path,
                chunk_id=f"chunk_{i}",
                content=text,
                page_start=p_start,
                page_end=p_end,
            )
        )

    logger.debug("%s → %d chunk(s)", relative_path, len(chunks))
    return chunks


def chunk_docx(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """
    Extract paragraph text from .docx and apply a sliding window.
    Each chunk records which paragraphs (1-based) it spans.
    """
    import docx

    doc = docx.Document(str(absolute_path))
    non_empty = [
        (i + 1, p.text.strip()) for i, p in enumerate(doc.paragraphs) if p.text.strip()
    ]

    words: list[str] = []
    word_para_map: list[int] = []  # word_index → 1-based paragraph number

    for para_no, text in non_empty:
        for word in text.split():
            words.append(word)
            word_para_map.append(para_no)

    windows = _sliding_window(words)
    chunks: list[Chunk] = []

    for i, (text, w_start, w_end) in enumerate(windows):
        p_start = word_para_map[w_start] if w_start < len(word_para_map) else 1
        p_end = word_para_map[min(w_end, len(word_para_map) - 1)]
        chunks.append(
            Chunk(
                file_path=relative_path,
                chunk_id=f"chunk_{i}",
                content=text,
                paragraph_start=p_start,
                paragraph_end=p_end,
            )
        )

    logger.debug("%s → %d chunk(s)", relative_path, len(chunks))
    return chunks


def chunk_epub(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """
    Extract text chapter-by-chapter from an EPUB.
    Each chunk is tagged with the chapter title (or spine id).
    #Vibe-coded
    """
    import zipfile
    from xml.etree import ElementTree as ET

    NS = {
        "opf": "http://www.idpf.org/2007/opf",
        "dc": "http://purl.org/dc/elements/1.1/",
        "xhtml": "http://www.w3.org/1999/xhtml",
    }

    def _text_from_xhtml(xml_bytes: bytes) -> str:
        try:
            root = ET.fromstring(xml_bytes)
            return " ".join(root.itertext())
        except ET.ParseError:
            return xml_bytes.decode("utf-8", errors="ignore")

    chunks: list[Chunk] = []

    with zipfile.ZipFile(absolute_path) as zf:
        # Locate container → OPF
        try:
            container = ET.fromstring(zf.read("META-INF/container.xml"))
            opf_path = container.find(
                ".//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile"
            ).get(
                "full-path"
            )  # type: ignore[union-attr]
        except Exception:
            logger.warning("Could not parse EPUB container for %s", relative_path)
            return []

        opf_dir = str(Path(opf_path).parent)
        opf_root = ET.fromstring(zf.read(opf_path))

        # Build id→href map from manifest
        manifest: dict[str, str] = {}
        for item in opf_root.findall(".//opf:item", NS):
            manifest[item.get("id", "")] = item.get("href", "")

        # Walk spine in order
        spine = opf_root.find(".//opf:spine", NS)
        if spine is None:
            return []

        chunk_index = 0
        for itemref in spine.findall("opf:itemref", NS):
            idref = itemref.get("idref", "")
            href = manifest.get(idref, "")
            if not href:
                continue

            full_href = f"{opf_dir}/{href}" if opf_dir and opf_dir != "." else href
            try:
                raw = zf.read(full_href)
            except KeyError:
                continue

            text = _text_from_xhtml(raw)
            words = text.split()
            if not words:
                continue

            windows = _sliding_window(words)
            for text_chunk, _, _ in windows:
                chunks.append(
                    Chunk(
                        file_path=relative_path,
                        chunk_id=f"chunk_{chunk_index}",
                        content=text_chunk,
                        chapter=idref,
                    )
                )
                chunk_index += 1

    logger.debug("%s → %d chunk(s)", relative_path, len(chunks))
    return chunks


def chunk_image(relative_path: Path, absolute_path: Path) -> list[Chunk]:
    """Treat each image as a single chunk (no location metadata needed)."""
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
    ".py": chunk_text,
    ".java": chunk_text,
    ".pdf": chunk_pdf,
    ".docx": chunk_docx,
    ".epub": chunk_epub,
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
