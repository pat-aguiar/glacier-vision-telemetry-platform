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


class SortingEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def insert(
        self, payload: SortingEventCreate, *, facility_id: uuid.UUID
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
            result = await self._db.execute(stmt)
        except IntegrityError as exc:
            await self._db.rollback()
            raise translate_integrity_error(exc, device_id=str(payload.device_id)) from exc

        row = result.scalar_one_or_none()
        if row is not None:
            await self._db.commit()
            return row, True

        await self._db.rollback()
        existing = await self._db.execute(
            select(SortingEvent).where(
                SortingEvent.event_id == payload.event_id,
                SortingEvent.occurred_at == payload.occurred_at,
            )
        )
        return existing.scalar_one(), False

    async def get_by_id(self, event_id: uuid.UUID) -> SortingEvent | None:
        """Look up a sorting event by its id, or None if no such event exists.

        `id` isn't the partition key on this table, so this scans every
        partition rather than pruning to one -- acceptable for a single-row
        lookup, but not a pattern to repeat for bulk queries.
        """
        result = await self._db.execute(select(SortingEvent).where(SortingEvent.id == event_id))
        return result.scalar_one_or_none()
