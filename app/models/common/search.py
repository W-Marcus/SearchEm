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

    def display(self) -> str:
        from datetime import datetime

        ts = datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M")
        size_kb = self.file_size / 1024
        preview = self.content[:300].replace("\n", " ").strip()
        if len(self.content) > 300:
            preview += "..."

        lines = [
            f"  [{self.rank}] {self.relative_path} — {self.chunk_id}",
            f"       score: {self.score:.4f} | {self.extension} | {size_kb:.1f} KB | {ts}",
        ]
        if preview:
            lines.append(f"       {preview}")

        return "\n".join(lines)
