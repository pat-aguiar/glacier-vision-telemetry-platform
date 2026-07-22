#!/usr/bin/env python
"""Seed demo devices and continuously POST synthetic telemetry events
against a running instance of the API.

Meant for manually exercising ingestion and the live dashboard stream
(`/api/v1/telemetry/stream`) without a physical sorting device.

Usage:
    python scripts/mock_event_generator.py --devices 3
    python scripts/mock_event_generator.py --devices 5 --rate 10 --count 0  # until Ctrl+C
"""

from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.database import get_sessionmaker
from app.models import Device, DeviceStatus, Facility

MATERIAL_TYPES = ["PET", "HDPE", "GLASS", "ALUMINUM", "CARDBOARD", "STEEL", "PP", "MIXED_PAPER"]


@dataclass
class Args:
    base_url: str
    devices: int
    rate: float
    count: int
    facility_slug: str


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--devices", type=int, default=3, help="Number of demo devices to seed")
    parser.add_argument(
        "--rate", type=float, default=2.0, help="Events per second, across all devices"
    )
    parser.add_argument(
        "--count", type=int, default=20, help="Total events to send; 0 means run until Ctrl+C"
    )
    parser.add_argument("--facility-slug", default="demo-facility")
    parsed = parser.parse_args()
    return Args(
        base_url=parsed.base_url,
        devices=parsed.devices,
        rate=parsed.rate,
        count=parsed.count,
        facility_slug=parsed.facility_slug,
    )


async def seed_devices(*, count: int, facility_slug: str) -> list[Device]:
    """Ensure `count` demo devices exist under a demo facility, creating
    whatever is missing. Safe to run repeatedly -- existing rows are reused.
    """
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        facility = await session.scalar(select(Facility).where(Facility.slug == facility_slug))
        if facility is None:
            facility = Facility(name="Demo Facility", slug=facility_slug)
            session.add(facility)
            await session.flush()

        devices = []
        for i in range(count):
            serial = f"DEMO-{facility_slug}-{i:03d}"
            device = await session.scalar(select(Device).where(Device.serial_number == serial))
            if device is None:
                device = Device(
                    facility_id=facility.id,
                    serial_number=serial,
                    name=f"Demo Sorter {i:03d}",
                    status=DeviceStatus.ACTIVE,
                )
                session.add(device)
                await session.flush()
            devices.append(device)

        await session.commit()
        return devices


def build_event_payload(device_id: uuid.UUID) -> dict:
    return {
        "device_id": str(device_id),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "material_type": random.choice(MATERIAL_TYPES),
        "confidence": round(random.uniform(0.5, 0.99), 3),
        "payload": {"bbox": [random.randint(0, 100) for _ in range(4)]},
        "event_id": str(uuid.uuid4()),
    }


async def run(args: Args) -> None:
    devices = await seed_devices(count=args.devices, facility_slug=args.facility_slug)
    print(f"Seeded {len(devices)} demo device(s) in facility '{args.facility_slug}'.")

    interval = 1.0 / args.rate if args.rate > 0 else 0.0
    sent = 0
    failed = 0

    async with httpx.AsyncClient(base_url=args.base_url, timeout=5.0) as client:
        try:
            while args.count <= 0 or sent < args.count:
                device = random.choice(devices)
                payload = build_event_payload(device.id)
                try:
                    response = await client.post("/api/v1/telemetry/events", json=payload)
                    sent += 1
                    if response.status_code >= 400:
                        failed += 1
                        print(f"[{response.status_code}] {response.text}")
                    else:
                        print(
                            f"[{response.status_code}] device={device.serial_number} "
                            f"material={payload['material_type']} confidence={payload['confidence']}"
                        )
                except httpx.HTTPError as exc:
                    failed += 1
                    print(f"request failed: {exc}")

                if interval:
                    await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print("\nInterrupted.")

    print(f"\nSent {sent} event(s), {failed} failed.")


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
