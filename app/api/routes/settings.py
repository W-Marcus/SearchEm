# Author: Marcus Wallin

from fastapi import APIRouter, Depends, Request
from models.rest.requests import SettingsRequest
from models.rest.responses import SettingsResponse
from services.rest.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_settings_service(request: Request) -> SettingsService:
    return request.app.state.settings_service


@router.get("", response_model=SettingsResponse)
def get_settings(
    service: SettingsService = Depends(_get_settings_service),
) -> SettingsResponse:
    return service.get()


@router.patch("", response_model=SettingsResponse)
def patch_settings(
    body: SettingsRequest,
    service: SettingsService = Depends(_get_settings_service),
) -> SettingsResponse:
    return service.patch(body)
