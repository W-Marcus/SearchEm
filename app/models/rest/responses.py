from pydantic import BaseModel, Field

from models.common.search import QueryResult


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[QueryResult]


class IndexResponse(BaseModel):
    status: str = Field(..., description="'ok' or 'skipped'")
    files_processed: int
    files_unchanged: int
    message: str
