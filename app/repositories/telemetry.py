from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import translate_integrity_error
from app.models import SortingEvent
from app.schemas import SortingEventCreate

_CONFLICT_TARGET = ("event_id", "occurred_at")


async def insert_sorting_event(
    db: AsyncSession, payload: SortingEventCreate, *, facility_id: uuid.UUID
) -> tuple[SortingEvent, bool]:
    """Insert a sorting event, returning (event, created).

    created=False means `event_id` matched an existing row (idempotent replay of a
    retried edge-device payload) and no new row was written.
    """
    stmt = (
        pg_insert(SortingEvent)
        .values(**payload.model_dump(), facility_id=facility_id)
        .on_conflict_do_nothing(index_elements=_CONFLICT_TARGET)
        .returning(SortingEvent)
    )
    try:
        result = await db.execute(stmt)
    except IntegrityError as exc:
        await db.rollback()
        raise translate_integrity_error(exc, device_id=str(payload.device_id)) from exc

    row = result.scalar_one_or_none()
    if row is not None:
        await db.commit()
        return row, True

    await db.rollback()
    existing = await db.execute(
        select(SortingEvent).where(
            SortingEvent.event_id == payload.event_id,
            SortingEvent.occurred_at == payload.occurred_at,
        )
    )
    return existing.scalar_one(), False
