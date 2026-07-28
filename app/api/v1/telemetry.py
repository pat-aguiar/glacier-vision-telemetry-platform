from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.deps import get_telemetry_service
from app.mock_vision import MOCK_IMAGE_PATH
from app.schemas import (
    ErrorResponse,
    SortingEventCreate,
    SortingEventRead,
    TelemetryEventImageRead,
)
from app.services.telemetry import TelemetryService

router = APIRouter()


@router.post(
    "/events",
    response_model=SortingEventRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {
            "model": SortingEventRead,
            "description": "Event already existed for this event_id/occurred_at (idempotent replay).",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Request failed validation, or device_id does not reference a known device.",
        },
    },
)
async def ingest_sorting_event(
    payload: SortingEventCreate,
    response: Response,
    service: TelemetryService = Depends(get_telemetry_service),
) -> SortingEventRead:
    event_read, created = await service.ingest_sorting_event(payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return event_read


@router.get(
    "/events/{event_id}/image",
    response_model=TelemetryEventImageRead,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "No sorting event exists with the given id.",
        },
    },
)
async def get_sorting_event_image(
    event_id: uuid.UUID,
    request: Request,
    service: TelemetryService = Depends(get_telemetry_service),
) -> TelemetryEventImageRead:
    image_url = str(request.url_for("static", path=MOCK_IMAGE_PATH))
    return await service.get_sorting_event_image(event_id, image_url=image_url)
