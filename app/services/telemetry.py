from __future__ import annotations

import uuid

from app.exceptions import DeviceNotFoundError, SortingEventNotFoundError
from app.mock_vision import MockVisionProvider
from app.repositories.device import DeviceRepository
from app.repositories.telemetry import SortingEventRepository
from app.schemas import SortingEventCreate, SortingEventRead, TelemetryEventImageRead
from app.streaming import Broadcaster


class TelemetryService:
    def __init__(
        self,
        sorting_events: SortingEventRepository,
        devices: DeviceRepository,
        broadcaster: Broadcaster,
        vision: MockVisionProvider,
    ) -> None:
        self._sorting_events = sorting_events
        self._devices = devices
        self._broadcaster = broadcaster
        self._vision = vision

    async def ingest_sorting_event(
        self, payload: SortingEventCreate
    ) -> tuple[SortingEventRead, bool]:
        """Returns (event_read, created); publishes to the broadcaster iff created."""
        device = await self._devices.get_by_id(payload.device_id)
        if device is None:
            raise DeviceNotFoundError(str(payload.device_id))

        event, created = await self._sorting_events.insert(payload, facility_id=device.facility_id)
        event_read = SortingEventRead.model_validate(event)

        if created:
            await self._broadcaster.publish(event_read.model_dump(mode="json"))

        return event_read, created

    async def get_sorting_event_image(
        self, event_id: uuid.UUID, *, image_url: str
    ) -> TelemetryEventImageRead:
        event = await self._sorting_events.get_by_id(event_id)
        if event is None:
            raise SortingEventNotFoundError(str(event_id))

        return TelemetryEventImageRead(
            image_url=image_url,
            bounding_boxes=self._vision.generate_bounding_boxes(event_id),
        )
