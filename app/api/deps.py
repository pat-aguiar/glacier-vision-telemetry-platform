import secrets

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db  # noqa: F401
from app.exceptions import InvalidApiKeyError, InvalidDashboardTokenError
from app.mock_vision import MockVisionProvider
from app.repositories.device import DeviceRepository
from app.repositories.telemetry import SortingEventRepository
from app.services.telemetry import TelemetryService
from app.streaming import Broadcaster, get_broadcaster  # noqa: F401


async def verify_edge_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency authenticating edge sorting devices for ingestion.

    Missing and invalid keys raise the same error, deliberately -- an
    attacker probing the endpoint shouldn't be able to distinguish "no key
    sent" from "wrong key sent" from the response.
    """
    settings = get_settings()
    if x_api_key is None or not secrets.compare_digest(x_api_key, settings.edge_api_key):
        raise InvalidApiKeyError()


def is_valid_dashboard_token(token: str | None) -> bool:
    """Constant-time dashboard token check.

    Split out from `verify_dashboard_token` below so the WebSocket route can
    reuse the same comparison logic -- it can't use a raising FastAPI
    dependency the same way an HTTP route can, since a rejected WebSocket
    handshake needs to close the socket rather than return an HTTP error
    response.
    """
    settings = get_settings()
    return token is not None and secrets.compare_digest(token, settings.dashboard_access_token)


async def verify_dashboard_token(x_dashboard_token: str | None = Header(default=None)) -> None:
    """FastAPI dependency authenticating dashboard clients for read endpoints."""
    if not is_valid_dashboard_token(x_dashboard_token):
        raise InvalidDashboardTokenError()


def get_sorting_event_repository(db: AsyncSession = Depends(get_db)) -> SortingEventRepository:
    return SortingEventRepository(db)


def get_device_repository(db: AsyncSession = Depends(get_db)) -> DeviceRepository:
    return DeviceRepository(db)


def get_mock_vision_provider() -> MockVisionProvider:
    return MockVisionProvider()


def get_telemetry_service(
    sorting_events: SortingEventRepository = Depends(get_sorting_event_repository),
    devices: DeviceRepository = Depends(get_device_repository),
    broadcaster: Broadcaster = Depends(get_broadcaster),
    vision: MockVisionProvider = Depends(get_mock_vision_provider),
) -> TelemetryService:
    return TelemetryService(sorting_events, devices, broadcaster, vision)
