from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.config import get_settings
from app.database import get_sessionmaker
from app.main import app
from app.models import Device, DeviceStatus, Facility, SortingEvent


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """An authenticated client -- sends valid edge/dashboard credentials by
    default, since most tests exercise behavior other than auth itself.
    Tests specifically covering missing/invalid credentials override these
    headers per-request.
    """
    settings = get_settings()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={
            "X-API-Key": settings.edge_api_key,
            "X-Dashboard-Token": settings.dashboard_access_token,
        },
    ) as ac:
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


@pytest.fixture
async def sorting_event(device: Device) -> SortingEvent:
    """A sorting event persisted directly via the ORM.

    Cleaned up by the `device` fixture's teardown (it deletes all
    SortingEvent rows for that device_id), so no separate teardown here.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        event = SortingEvent(
            occurred_at=datetime.now(timezone.utc),
            device_id=device.id,
            facility_id=device.facility_id,
            material_type="PET",
            confidence=0.8,
            event_id=uuid.uuid4(),
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
    return event
