# Author: Marcus Wallin

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    """A single embeddable unit from a file."""

    file_path: Path   # relative path
    chunk_id: str     # e.g. "page_1", "paragraph_3", "image"
    content: str | Path  # text content or absolute path for images
    is_image: bool = False
