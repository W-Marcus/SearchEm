import asyncio
import logging
from pathlib import Path

from config.settings import Settings
from core.chunker import chunk_file
from core.embedder import COMMIT_EVERY_N_FILES, Embedder
from core.scanner import IndexLockError, Scanner
from core.searcher import Searcher
from fastapi import HTTPException
from models.rest.requests import IndexRequest, SearchRequest
from models.rest.responses import IndexProgressEvent, IndexResponse, SearchResponse
from starlette.responses import StreamingResponse

logger = logging.getLogger("searchem.services.rest")


def _sse(event: IndexProgressEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"


class SearchService:
    def __init__(
        self,
        searcher: Searcher | None,
        database: Path,
        directory: Path,
        model_id: str,
    ) -> None:
        self._searcher = searcher
        self._database = database
        self._directory = directory
        self._model_id = model_id

    def search(self, request: SearchRequest) -> SearchResponse:
        if self._searcher is None:
            # Try to load now in case index was built after startup
            try:
                self._searcher = Searcher(
                    database=self._database,
                    directory=self._directory,
                    model_id=self._model_id,
                )
            except FileNotFoundError:
                raise HTTPException(
                    status_code=503,
                    detail="Search index not ready. Run /index first.",
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
        self._cancel_event: asyncio.Event | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def cancel(self) -> bool:
        if self._cancel_event is None or not self._running:
            return False
        self._cancel_event.set()
        return True

    def stream(self, request: IndexRequest) -> StreamingResponse:
        return StreamingResponse(
            self._run_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    async def _run_stream(self, request: IndexRequest):
        if self._running:
            yield _sse(
                IndexProgressEvent(
                    type="error",
                    message="Another indexing operation is already running.",
                )
            )
            return

        self._running = True
        self._cancel_event = asyncio.Event()
        extensions = request.extensions or self._extensions

        try:
            scanner = Scanner(self._directory, self._database, extensions)
            try:
                result = scanner.scan(force_reprocess=request.force_reprocess)
            except IndexLockError as e:
                yield _sse(IndexProgressEvent(type="error", message=str(e)))
                return

            total_files = sum(len(v) for v in result.to_process.values())

            if not result.to_process:
                yield _sse(
                    IndexProgressEvent(
                        type="done",
                        message="No new or changed files found.",
                    )
                )
                return

            yield _sse(
                IndexProgressEvent(
                    type="start",
                    message=f"Starting — {total_files} file(s) to embed.",
                    file_total=total_files,
                )
            )

            embedder = Embedder(self._model_id, self._directory, self._database)
            file_index = 0

            for ext, paths in result.to_process.items():
                for relative_path in paths:
                    if self._cancel_event.is_set():
                        embedder.incremental_commit()
                        yield _sse(
                            IndexProgressEvent(
                                type="cancelled",
                                message=f"Cancelled after {file_index} of {total_files} file(s).",
                                file_index=file_index,
                                file_total=total_files,
                            )
                        )
                        return

                    # Get chunk count for progress reporting without embedding yet
                    chunks = chunk_file(relative_path, self._directory / relative_path)
                    chunk_total = len(chunks)

                    if chunk_total == 0:
                        file_index += 1
                        continue

                    # Yield per-chunk progress during embedding
                    embedder._meta.remove_file(relative_path)
                    try:
                        embeddings = embedder._model.embed_chunks(chunks)
                    except Exception as e:
                        logger.error("Failed to embed %s: %s", relative_path, e)
                        file_index += 1
                        continue

                    metas = [embedder._make_meta(chunk) for chunk in chunks]
                    embedder._ensure_index(embeddings.shape[1])

                    for chunk_index, (embedding, meta) in enumerate(
                        zip(embeddings, metas)
                    ):
                        embedder._index.add(embedding.reshape(1, -1))  # type: ignore[union-attr]
                        embedder._meta.entries.append(meta)

                        yield _sse(
                            IndexProgressEvent(
                                type="chunk",
                                message=f"{relative_path} — chunk {chunk_index + 1}/{chunk_total}",
                                file=str(relative_path),
                                file_index=file_index,
                                file_total=total_files,
                                chunk_index=chunk_index + 1,
                                chunk_total=chunk_total,
                            )
                        )
                        await asyncio.sleep(0)

                    # Commit hash immediately so resume skips this file if cancelled
                    result.commit_file(relative_path, self._directory, self._database)

                    file_index += 1
                    yield _sse(
                        IndexProgressEvent(
                            type="file",
                            message=f"({file_index}/{total_files}) Embedded: {relative_path}",
                            file=str(relative_path),
                            file_index=file_index,
                            file_total=total_files,
                        )
                    )

                    # Incremental FAISS/metadata commit every N files
                    if file_index % COMMIT_EVERY_N_FILES == 0:
                        embedder.incremental_commit()
                        await asyncio.sleep(0)

            embedder.commit()

            if request.extensions:
                settings = Settings.load(self._database)
                settings.extensions = request.extensions
                settings.save(self._database)
                self._extensions = request.extensions

            self._search_service._searcher = Searcher(
                database=self._database,
                directory=self._directory,
                model_id=self._model_id,
            )

            yield _sse(
                IndexProgressEvent(
                    type="done",
                    message=f"Done — {file_index} file(s) embedded.",
                    file_index=file_index,
                    file_total=total_files,
                )
            )

        finally:
            self._running = False
            self._cancel_event = None
