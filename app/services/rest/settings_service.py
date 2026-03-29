# Author: Marcus Wallin
import logging
from pathlib import Path

from config.settings import Settings
from models.rest.requests import SettingsRequest
from models.rest.responses import SettingsResponse

logger = logging.getLogger("searchem.services.rest.settings")


class SettingsService:
    def __init__(self, database: Path) -> None:
        self._database = database

    def get(self) -> SettingsResponse:
        settings = Settings.load(self._database)
        return SettingsResponse(model=settings.model, extensions=settings.extensions)

    def patch(self, request: SettingsRequest) -> SettingsResponse:
        settings = Settings.load(self._database)
        if request.model is not None:
            settings.model = request.model
        if request.extensions is not None:
            settings.extensions = request.extensions
        settings.save(self._database)
        logger.info(
            "Settings saved: model=%s extensions=%s",
            settings.model,
            settings.extensions,
        )
        return SettingsResponse(model=settings.model, extensions=settings.extensions)
