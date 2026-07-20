from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.exceptions import DeviceNotFoundError
from app.models import Device
from app.repositories.telemetry import insert_sorting_event
from app.schemas import ErrorResponse, SortingEventCreate, SortingEventRead

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
    return SortingEventRead.model_validate(event)
