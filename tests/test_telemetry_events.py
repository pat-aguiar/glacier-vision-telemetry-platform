from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.models import Device

ENDPOINT = "/api/v1/telemetry/events"


def _valid_payload(device_id: uuid.UUID, **overrides: object) -> dict:
    payload = {
        "device_id": str(device_id),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "material_type": "PET",
        "confidence": 0.87,
        "payload": {"bbox": [1, 2, 3, 4]},
        "event_id": str(uuid.uuid4()),
    }
    payload.update(overrides)
    return payload


async def test_insert_sorting_event_returns_201(client: AsyncClient, device: Device) -> None:
    response = await client.post(ENDPOINT, json=_valid_payload(device.id))

    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["id"])
    assert body["device_id"] == str(device.id)
    assert body["facility_id"] == str(device.facility_id)
    assert body["material_type"] == "PET"
    assert body["confidence"] == pytest.approx(0.87)


async def test_replaying_same_event_id_is_idempotent(client: AsyncClient, device: Device) -> None:
    payload = _valid_payload(device.id)

    first = await client.post(ENDPOINT, json=payload)
    second = await client.post(ENDPOINT, json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


async def test_unknown_device_id_returns_400(client: AsyncClient) -> None:
    response = await client.post(ENDPOINT, json=_valid_payload(uuid.uuid4()))

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "device_not_found"


@pytest.mark.parametrize(
    "overrides,missing_field,expected_field",
    [
        pytest.param(
            {"occurred_at": datetime.now().isoformat()},
            None,
            "occurred_at",
            id="naive-timestamp",
        ),
        pytest.param({"confidence": 1.5}, None, "confidence", id="confidence-above-range"),
        pytest.param({"confidence": -0.1}, None, "confidence", id="confidence-below-range"),
        pytest.param({"device_id": "not-a-uuid"}, None, "device_id", id="malformed-device-id"),
        pytest.param({}, "device_id", "device_id", id="missing-device-id"),
    ],
)
async def test_invalid_payload_returns_400(
    client: AsyncClient,
    device: Device,
    overrides: dict,
    missing_field: str | None,
    expected_field: str,
) -> None:
    payload = _valid_payload(device.id)
    payload.update(overrides)
    if missing_field:
        del payload[missing_field]

    response = await client.post(ENDPOINT, json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    fields = {detail["field"] for detail in body["error"]["details"]}
    assert expected_field in fields
