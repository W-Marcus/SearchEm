import logging
from pathlib import Path

from core.embedder import Embedder
from core.scanner import IndexLockError, Scanner
from core.searcher import Searcher
from fastapi import HTTPException
from models.rest.requests import IndexRequest, SearchRequest
from models.rest.responses import IndexResponse, SearchResponse

logger = logging.getLogger("searchem.services.rest")


class SearchService:
    def __init__(self, searcher: Searcher | None) -> None:
        self._searcher = searcher

    def search(self, request: SearchRequest) -> SearchResponse:
        if self._searcher is None:
            raise HTTPException(
                status_code=503, detail="Search index not ready. Run POST /index first."
            )
        results = self._searcher.search(request.query, k=request.top_k)
        return SearchResponse(
            query=request.query,
            total=len(results),
            results=results,
        )


class IndexService:
    def __init__(
        self,
        directory: Path,
        database: Path,
        model_id: str,
        extensions: list[str],
        search_service: SearchService,
    ) -> None:
        self._directory = directory
        self._database = database
        self._model_id = model_id
        self._extensions = extensions
        self._search_service = search_service

    def run(self, request: IndexRequest) -> IndexResponse:
        extensions = request.extensions or self._extensions
        scanner = Scanner(self._directory, self._database, extensions)

        try:
            result = scanner.scan(force_reprocess=request.force_reprocess)
        except IndexLockError as e:
            raise HTTPException(status_code=409, detail=str(e))

        total_process = sum(len(v) for v in result.to_process.values())
        total_unchanged = sum(len(v) for v in result.unchanged.values())

        if not result.to_process:
            logger.info("No new or changed files found.")
            return IndexResponse(
                status="skipped",
                files_processed=0,
                files_unchanged=total_unchanged,
                message="No new or changed files found.",
            )

        embedder = Embedder(self._model_id, self._directory, self._database)
        embedder.embed_index(result.to_process)
        embedder.commit()
        result.commit(self._directory, self._database)

        # Reinitialise searcher now that index exists
        self._search_service._searcher = Searcher(
            database=self._database,
            directory=self._directory,
            model_id=self._model_id,
        )

        return IndexResponse(
            status="ok",
            files_processed=total_process,
            files_unchanged=total_unchanged,
            message=f"Successfully embedded {total_process} file(s).",
        )
