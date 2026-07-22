from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import DeviceNotFoundError, SortingEventNotFoundError
from app.mock_vision import MOCK_IMAGE_PATH, generate_mock_bounding_boxes
from app.models import Device
from app.repositories.telemetry import get_sorting_event_by_id, insert_sorting_event
from app.schemas import (
    ErrorResponse,
    SortingEventCreate,
    SortingEventRead,
    TelemetryEventImageRead,
)
from app.streaming import broadcaster

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
    db: AsyncSession = Depends(get_db),
) -> SortingEventRead:
    device = await db.scalar(select(Device).where(Device.id == payload.device_id))
    if device is None:
        raise DeviceNotFoundError(str(payload.device_id))

    event, created = await insert_sorting_event(db, payload, facility_id=device.facility_id)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    event_read = SortingEventRead.model_validate(event)

    if created:
        await broadcaster.publish(event_read.model_dump(mode="json"))

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
    db: AsyncSession = Depends(get_db),
) -> TelemetryEventImageRead:
    event = await get_sorting_event_by_id(db, event_id)
    if event is None:
        raise SortingEventNotFoundError(str(event_id))

    image_url = str(request.url_for("static", path=MOCK_IMAGE_PATH))
    return TelemetryEventImageRead(
        image_url=image_url,
        bounding_boxes=generate_mock_bounding_boxes(event_id),
    )