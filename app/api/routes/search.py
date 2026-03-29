# Author: Marcus Wallin

from fastapi import APIRouter, Depends, Request
from models.rest.requests import SearchRequest
from models.rest.responses import SearchResponse
from services.rest.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


def _get_search_service(request: Request) -> SearchService:
    return request.app.state.search_service


@router.post("", response_model=SearchResponse)
def search(
    body: SearchRequest,
    service: SearchService = Depends(_get_search_service),
) -> SearchResponse:
    """Perform a semantic search over the indexed files."""
    return service.search(body)
