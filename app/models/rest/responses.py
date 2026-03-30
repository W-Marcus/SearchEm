# Author: Marcus Wallin
from typing import Literal

from models.common.search import QueryResult
from pydantic import BaseModel, Field


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[QueryResult]


class IndexResponse(BaseModel):
    status: str = Field(..., description="'ok', 'skipped', or 'cancelled'")
    files_processed: int
    files_unchanged: int
    message: str


class SettingsResponse(BaseModel):
    model: str
    extensions: list[str]


class IndexProgressEvent(BaseModel):
    type: Literal["start", "file", "chunk", "done", "error", "cancelled"]
    message: str
    file: str | None = None
    file_index: int | None = None
    file_total: int | None = None
    chunk_index: int | None = None
    chunk_total: int | None = None
