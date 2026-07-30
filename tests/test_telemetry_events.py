from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.config import get_settings
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


async def test_insert_sorting_event_returns_201(
    client: AsyncClient, edge_api_key_headers: dict[str, str], device: Device
) -> None:
    response = await client.post(
        ENDPOINT, json=_valid_payload(device.id), headers=edge_api_key_headers
    )

    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["id"])
    assert body["device_id"] == str(device.id)
    assert body["facility_id"] == str(device.facility_id)
    assert body["material_type"] == "PET"
    assert body["confidence"] == pytest.approx(0.87)


async def test_replaying_same_event_id_is_idempotent(
    client: AsyncClient, edge_api_key_headers: dict[str, str], device: Device
) -> None:
    payload = _valid_payload(device.id)

    first = await client.post(ENDPOINT, json=payload, headers=edge_api_key_headers)
    second = await client.post(ENDPOINT, json=payload, headers=edge_api_key_headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


async def test_unknown_device_id_returns_400(
    client: AsyncClient, edge_api_key_headers: dict[str, str]
) -> None:
    response = await client.post(
        ENDPOINT, json=_valid_payload(uuid.uuid4()), headers=edge_api_key_headers
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "device_not_found"


async def test_missing_api_key_returns_401(client: AsyncClient, device: Device) -> None:
    # `client` sends no credentials at all now -- this is the "header
    # entirely absent" case; see test_invalid_api_key_returns_401 for wrong.
    response = await client.post(ENDPOINT, json=_valid_payload(device.id))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


async def test_invalid_api_key_returns_401(client: AsyncClient, device: Device) -> None:
    response = await client.post(
        ENDPOINT, json=_valid_payload(device.id), headers={"X-API-Key": "wrong-key"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


async def test_rate_limit_exceeded_returns_429(
    client: AsyncClient,
    edge_api_key_headers: dict[str, str],
    device: Device,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "telemetry_events_rate_limit", "2/minute")

    for _ in range(2):
        response = await client.post(
            ENDPOINT, json=_valid_payload(device.id), headers=edge_api_key_headers
        )
        assert response.status_code == 201

    response = await client.post(
        ENDPOINT, json=_valid_payload(device.id), headers=edge_api_key_headers
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"


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
    edge_api_key_headers: dict[str, str],
    device: Device,
    overrides: dict,
    missing_field: str | None,
    expected_field: str,
) -> None:
    payload = _valid_payload(device.id)
    payload.update(overrides)
    if missing_field:
        del payload[missing_field]

    response = await client.post(ENDPOINT, json=payload, headers=edge_api_key_headers)

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    fields = {detail["field"] for detail in body["error"]["details"]}
    assert expected_field in fields
