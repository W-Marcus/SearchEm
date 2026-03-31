# Author: Marcus Wallin

from pydantic import BaseModel


class QueryResult(BaseModel):
    rank: int
    score: float
    relative_path: str
    extension: str
    chunk_id: str
    file_size: int
    timestamp: float
    content: str

    line_start: int | None = None
    line_end: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    paragraph_start: int | None = None
    paragraph_end: int | None = None
    chapter: str | None = None

    def display(self) -> str:
        from datetime import datetime

        ts = datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M")
        size_kb = self.file_size / 1024
        preview = self.content[:300].replace("\n", " ").strip()
        if len(self.content) > 300:
            preview += "..."

        location = self._location_str()

        lines = [
            f"  [{self.rank}] {self.relative_path} — {self.chunk_id}",
            f"       score: {self.score:.4f} | {self.extension} | {size_kb:.1f} KB | {ts}",
        ]
        if location:
            lines.append(f"       {location}")
        if preview:
            lines.append(f"       {preview}")

        return "\n".join(lines)

    def _location_str(self) -> str:
        """Return a compact human-readable location string, or empty string."""
        if self.page_start is not None:
            if self.page_end is not None and self.page_end != self.page_start:
                return f"pages {self.page_start}–{self.page_end}"
            return f"page {self.page_start}"

        if self.line_start is not None:
            if self.line_end is not None and self.line_end != self.line_start:
                return f"lines {self.line_start}–{self.line_end}"
            return f"line {self.line_start}"

        if self.paragraph_start is not None:
            if (
                self.paragraph_end is not None
                and self.paragraph_end != self.paragraph_start
            ):
                return f"paragraphs {self.paragraph_start}–{self.paragraph_end}"
            return f"paragraph {self.paragraph_start}"

        if self.chapter is not None:
            return f"chapter: {self.chapter}"

        return ""
