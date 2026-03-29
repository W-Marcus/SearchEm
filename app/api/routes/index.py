# Author: Marcus Wallin

from fastapi import APIRouter, Depends, Request
from models.rest.requests import IndexRequest
from models.rest.responses import IndexResponse
from services.rest.search_service import IndexService

router = APIRouter(prefix="/index", tags=["index"])


def _get_index_service(request: Request) -> IndexService:
    return request.app.state.index_service


@router.post("", response_model=IndexResponse)
def trigger_index(
    body: IndexRequest,
    service: IndexService = Depends(_get_index_service),
) -> IndexResponse:
    """Scan and embed new or changed files."""
    return service.run(body)


@router.post("/full", response_model=IndexResponse)
def trigger_full_reindex(
    service: IndexService = Depends(_get_index_service),
) -> IndexResponse:
    """Force re-embed all files regardless of change state."""
    return service.run(IndexRequest(force_reprocess=True))
