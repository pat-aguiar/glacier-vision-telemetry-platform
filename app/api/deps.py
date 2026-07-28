from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db  # noqa: F401
from app.mock_vision import MockVisionProvider
from app.repositories.device import DeviceRepository
from app.repositories.telemetry import SortingEventRepository
from app.services.telemetry import TelemetryService
from app.streaming import Broadcaster, get_broadcaster  # noqa: F401


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
