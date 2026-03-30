from fastapi import APIRouter, Depends, HTTPException, Request
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
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Search index not ready. Run POST /index first.",
        )
    return service.search(body)
