from fastapi import APIRouter, Depends, Request
from models.rest.requests import IndexRequest
from services.rest.search_service import IndexService
from starlette.responses import StreamingResponse

router = APIRouter(prefix="/index", tags=["index"])


def _get_index_service(request: Request) -> IndexService:
    return request.app.state.index_service


@router.get("", response_class=StreamingResponse)
def trigger_index(
    service: IndexService = Depends(_get_index_service),
) -> StreamingResponse:
    return service.stream(IndexRequest(force_reprocess=False))


@router.get("/full", response_class=StreamingResponse)
def trigger_full_reindex(
    service: IndexService = Depends(_get_index_service),
) -> StreamingResponse:
    return service.stream(IndexRequest(force_reprocess=True))


@router.delete("", status_code=204)
def cancel_index(
    service: IndexService = Depends(_get_index_service),
) -> None:
    if not service.cancel():
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail="No indexing operation is running.")
