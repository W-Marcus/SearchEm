# Author: Marcus Wallin
import argparse
import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import uvicorn
from api.routes import index_router, search_router, settings_router
from config.args import CommonArgs, add_common_args, resolve_common_paths
from config.settings import Settings, _setup_logging
from core.searcher import Searcher
from fastapi import FastAPI
from services.rest.search_service import IndexService, SearchService
from services.rest.settings_service import SettingsService

logger = logging.getLogger("searchem.rest")


class RestArgs(CommonArgs):
    host: str
    port: int
    reload: bool


def _parse_args() -> RestArgs:
    parser = argparse.ArgumentParser(description="SearchEm REST API server.")
    add_common_args(parser)
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to.")
    parser.add_argument("--port", default=8000, type=int, help="Port to listen on.")
    parser.add_argument(
        "--reload", action="store_true", help="Enable uvicorn auto-reload."
    )
    parsed = parser.parse_args(namespace=RestArgs())
    resolve_common_paths(parsed)
    return parsed


def create_app(directory: Path, database: Path, model_id: str) -> FastAPI:
    settings = Settings.load(database)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        search_service = SearchService(
            searcher=None,
            database=database,
            directory=directory,
            model_id=model_id,
        )

        try:
            searcher = Searcher(
                database=database, directory=directory, model_id=model_id
            )
            search_service._searcher = searcher
        except FileNotFoundError as e:
            logger.warning(
                "No index found. Search will be unavailable until indexing runs. (%s)",
                e,
            )

        app.state.search_service = search_service
        app.state.settings_service = SettingsService(database=database)
        app.include_router(settings_router)
        app.state.index_service = IndexService(
            directory=directory,
            database=database,
            model_id=model_id,
            extensions=settings.extensions,
            search_service=search_service,
        )

        yield

    app = FastAPI(
        title="SearchEm",
        description="Semantic search over local files.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(search_router)
    app.include_router(index_router)
    app.include_router(settings_router)

    return app


def main() -> None:
    args = _parse_args()
    assert args.database is not None
    args.database.mkdir(parents=True, exist_ok=True)
    assert args.logging_path is not None
    _setup_logging(args.logging_path)
    logger.info("Starting SearchEm REST API")

    app = create_app(
        directory=args.dir,
        database=args.database,
        model_id=args.model,
    )

    uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
