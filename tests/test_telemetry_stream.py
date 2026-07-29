from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from httpx_ws import WebSocketDisconnect, aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from app.config import get_settings
from app.main import app
from app.models import Device
from app.streaming import broadcaster

STREAM_ENDPOINT = "/api/v1/telemetry/stream"
EVENTS_ENDPOINT = "/api/v1/telemetry/events"
ALLOWED_ORIGIN = "http://localhost:5173"


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


def _authenticated_ws_client() -> AsyncClient:
    """A client with a valid X-API-Key default, for POSTing events that the
    stream should broadcast. Its own connection to the stream still needs
    an explicit `?token=` query param, since that's checked separately from
    this header.
    """
    settings = get_settings()
    return AsyncClient(
        transport=ASGIWebSocketTransport(app=app),
        base_url="http://testserver",
        headers={"X-API-Key": settings.edge_api_key},
    )


def _stream_url(*, token: str | None) -> str:
    if token is None:
        return STREAM_ENDPOINT
    return f"{STREAM_ENDPOINT}?token={token}"


async def test_disallowed_origin_is_rejected_at_handshake() -> None:
    async with _authenticated_ws_client() as ws_client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            async with aconnect_ws(
                _stream_url(token=get_settings().dashboard_access_token),
                ws_client,
                headers={"origin": "http://evil.com"},
            ):
                pass

        assert exc_info.value.code == 1008


async def test_missing_origin_is_rejected_at_handshake() -> None:
    async with _authenticated_ws_client() as ws_client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            async with aconnect_ws(
                _stream_url(token=get_settings().dashboard_access_token), ws_client
            ):
                pass

        assert exc_info.value.code == 1008


async def test_missing_token_is_rejected_at_handshake() -> None:
    async with _authenticated_ws_client() as ws_client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            async with aconnect_ws(
                _stream_url(token=None), ws_client, headers={"origin": ALLOWED_ORIGIN}
            ):
                pass

        assert exc_info.value.code == 1008


async def test_invalid_token_is_rejected_at_handshake() -> None:
    async with _authenticated_ws_client() as ws_client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            async with aconnect_ws(
                _stream_url(token="wrong-token"),
                ws_client,
                headers={"origin": ALLOWED_ORIGIN},
            ):
                pass

        assert exc_info.value.code == 1008


async def test_successful_insert_is_delivered_to_subscriber(device: Device) -> None:
    async with _authenticated_ws_client() as ws_client:
        async with aconnect_ws(
            _stream_url(token=get_settings().dashboard_access_token),
            ws_client,
            headers={"origin": ALLOWED_ORIGIN},
        ) as ws:
            response = await ws_client.post(EVENTS_ENDPOINT, json=_valid_payload(device.id))
            assert response.status_code == 201

            delivered = await ws.receive_json()
            assert delivered["id"] == response.json()["id"]
            assert delivered["device_id"] == str(device.id)


async def test_idempotent_replay_is_not_rebroadcast(device: Device) -> None:
    payload = _valid_payload(device.id)

    async with _authenticated_ws_client() as ws_client:
        async with aconnect_ws(
            _stream_url(token=get_settings().dashboard_access_token),
            ws_client,
            headers={"origin": ALLOWED_ORIGIN},
        ) as ws:
            first = await ws_client.post(EVENTS_ENDPOINT, json=payload)
            assert first.status_code == 201
            assert (await ws.receive_json())["id"] == first.json()["id"]

            replay = await ws_client.post(EVENTS_ENDPOINT, json=payload)
            assert replay.status_code == 200

            # A distinct follow-up event proves the stream is still alive
            # and, by FIFO delivery, that the replay above produced no
            # broadcast -- if it had, this receive would surface the
            # replay's message (same id as `first`) instead of the canary's.
            canary = await ws_client.post(EVENTS_ENDPOINT, json=_valid_payload(device.id))
            assert canary.status_code == 201
            assert (await ws.receive_json())["id"] == canary.json()["id"]


async def test_multiple_subscribers_all_receive_the_broadcast(device: Device) -> None:
    async with _authenticated_ws_client() as ws_client:
        stream_url = _stream_url(token=get_settings().dashboard_access_token)
        async with (
            aconnect_ws(stream_url, ws_client, headers={"origin": ALLOWED_ORIGIN}) as ws_a,
            aconnect_ws(stream_url, ws_client, headers={"origin": ALLOWED_ORIGIN}) as ws_b,
        ):
            assert broadcaster.subscriber_count == 2

            response = await ws_client.post(EVENTS_ENDPOINT, json=_valid_payload(device.id))
            assert response.status_code == 201

            message_a = await ws_a.receive_json()
            message_b = await ws_b.receive_json()
            assert message_a["id"] == message_b["id"] == response.json()["id"]
