from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_validators import AfterValidator

from app.models import DeviceStatus


def _ensure_timezone_aware(value: datetime) -> datetime:
    """Reject naive datetimes and normalize aware ones to UTC.

    Devices report from facilities in different timezones; accepting naive
    timestamps risks silently misinterpreting local time as UTC.
    """
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(
            "Timestamp must include timezone information (e.g. a 'Z' or '+00:00' offset)."
        )
    return value.astimezone(timezone.utc)


TzAwareDatetime = Annotated[datetime, AfterValidator(_ensure_timezone_aware)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Facility -----------------------------------------------------------


class FacilityBase(BaseModel):
    name: str = Field(max_length=255)
    slug: str = Field(max_length=100)
    timezone: str = Field(default="UTC", max_length=64)


class FacilityCreate(FacilityBase):
    pass


class FacilityRead(FacilityBase, ORMModel):
    id: uuid.UUID
    created_at: TzAwareDatetime
    updated_at: TzAwareDatetime


# --- Device ---------------------------------------------------------------


class DeviceBase(BaseModel):
    name: str = Field(max_length=255)
    status: DeviceStatus = DeviceStatus.ACTIVE
    installed_at: TzAwareDatetime | None = None


class DeviceCreate(DeviceBase):
    facility_id: uuid.UUID
    serial_number: str = Field(max_length=128)


class DeviceRead(DeviceBase, ORMModel):
    id: uuid.UUID
    facility_id: uuid.UUID
    serial_number: str
    created_at: TzAwareDatetime
    updated_at: TzAwareDatetime


# --- SortingEvent -----------------------------------------------------------


class SortingEventBase(BaseModel):
    occurred_at: TzAwareDatetime
    material_type: str = Field(max_length=64)
    confidence: float = Field(ge=0.0, le=1.0)
    payload: dict | None = None
    event_id: uuid.UUID | None = None


class SortingEventCreate(SortingEventBase):
    device_id: uuid.UUID


class SortingEventRead(SortingEventBase, ORMModel):
    id: uuid.UUID
    device_id: uuid.UUID
    facility_id: uuid.UUID
    created_at: TzAwareDatetime


# --- Error Response Schemas -------------------------------------------------


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody

