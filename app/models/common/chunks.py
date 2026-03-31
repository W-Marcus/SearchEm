# Author: Marcus Wallin

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Chunk:
    """A single embeddable unit from a file, with optional location metadata.

    Location fields are populated by each chunker where applicable and are
    intended to support an integrated viewer that can jump directly to the
    relevant position in the source file.

    """

    file_path: Path  # relative path from the watched directory
    chunk_id: str  # stable identifier, e.g. "page_3_chunk_1"
    content: str | Path  # text content or absolute image path

    is_image: bool = False

    # text / code
    line_start: int | None = None  # first line of this chunk in the file
    line_end: int | None = None  # last  line of this chunk in the file

    # PDF
    page_start: int | None = None  # first PDF page covered by this chunk
    page_end: int | None = None  # last  PDF page covered by this chunk

    # DOCX
    paragraph_start: int | None = None  # index of first paragraph (1-based)
    paragraph_end: int | None = None  # index of last  paragraph (1-based)

    # EPUB
    chapter: str | None = None  # chapter title or spine item id
