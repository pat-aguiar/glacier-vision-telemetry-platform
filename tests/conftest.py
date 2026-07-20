from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.database import get_sessionmaker
from app.main import app
from app.models import Device, DeviceStatus, Facility, SortingEvent


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.fixture
async def facility() -> AsyncIterator[Facility]:
    """A facility persisted directly via the ORM.

    There's no facility-creation endpoint yet, so integration tests seed
    fixtures straight into the (real, dockerized) Postgres the app talks to.
    """
    session_factory = get_sessionmaker()
    unique = uuid.uuid4().hex[:10]
    async with session_factory() as session:
        fac = Facility(name=f"Test Facility {unique}", slug=f"test-facility-{unique}")
        session.add(fac)
        await session.commit()
        await session.refresh(fac)

    yield fac

    async with session_factory() as session:
        await session.execute(delete(Facility).where(Facility.id == fac.id))
        await session.commit()


@pytest.fixture
async def device(facility: Facility) -> AsyncIterator[Device]:
    session_factory = get_sessionmaker()
    unique = uuid.uuid4().hex[:10]
    async with session_factory() as session:
        dev = Device(
            facility_id=facility.id,
            serial_number=f"SN-TEST-{unique}",
            name=f"Test Device {unique}",
            status=DeviceStatus.ACTIVE,
        )
        session.add(dev)
        await session.commit()
        await session.refresh(dev)

    yield dev

    async with session_factory() as session:
        # sorting_events has a RESTRICT FK to devices, so events created
        # against this device during the test must go first.
        await session.execute(delete(SortingEvent).where(SortingEvent.device_id == dev.id))
        await session.execute(delete(Device).where(Device.id == dev.id))
        await session.commit()
