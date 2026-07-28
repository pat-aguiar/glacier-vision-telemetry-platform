from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device


class DeviceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, device_id: uuid.UUID) -> Device | None:
        return await self._db.scalar(select(Device).where(Device.id == device_id))
