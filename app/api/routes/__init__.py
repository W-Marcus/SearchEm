from .file import router as file_router
from .index import router as index_router
from .search import router as search_router
from .settings import router as settings_router

__all__ = ["file_router", "index_router", "search_router", "settings_router"]
