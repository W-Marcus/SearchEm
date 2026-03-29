from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The search query string.")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return.")


class IndexRequest(BaseModel):
    force_reprocess: bool = Field(
        False,
        description=(
            "If true, re-embed all files regardless of whether they have changed. "
            "Required when switching models."
        ),
    )
    extensions: list[str] | None = Field(
        default=None,
        description="File extensions to index. Overrides stored settings when provided.",
    )
