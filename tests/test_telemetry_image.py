from __future__ import annotations

import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import SortingEvent

BOUNDING_BOX_FIELDS = {"label", "confidence", "x_min", "y_min", "x_max", "y_max"}


def _image_url(event_id: uuid.UUID) -> str:
    return f"/api/v1/telemetry/events/{event_id}/image"


async def test_get_image_returns_200_with_expected_structure(
    client: AsyncClient, sorting_event: SortingEvent
) -> None:
    response = await client.get(_image_url(sorting_event.id))

    assert response.status_code == 200
    body = response.json()

    assert isinstance(body["image_url"], str)
    assert body["image_url"]

    assert isinstance(body["bounding_boxes"], list)
    assert len(body["bounding_boxes"]) >= 1
    for box in body["bounding_boxes"]:
        assert BOUNDING_BOX_FIELDS.issubset(box.keys())
        assert isinstance(box["label"], str)
        assert box["label"]


async def test_bounding_box_coordinates_are_within_0_1(
    client: AsyncClient, sorting_event: SortingEvent
) -> None:
    response = await client.get(_image_url(sorting_event.id))
    boxes = response.json()["bounding_boxes"]

    assert len(boxes) >= 1
    for box in boxes:
        assert 0.0 <= box["x_min"] < box["x_max"] <= 1.0
        assert 0.0 <= box["y_min"] < box["y_max"] <= 1.0
        assert 0.0 <= box["confidence"] <= 1.0


async def test_repeated_requests_are_deterministic(
    client: AsyncClient, sorting_event: SortingEvent
) -> None:
    first = await client.get(_image_url(sorting_event.id))
    second = await client.get(_image_url(sorting_event.id))

    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


async def test_unknown_event_returns_404(client: AsyncClient) -> None:
    response = await client.get(_image_url(uuid.uuid4()))

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "sorting_event_not_found"


async def test_missing_dashboard_token_returns_401(sorting_event: SortingEvent) -> None:
    # A bare client with no default X-Dashboard-Token, unlike the `client`
    # fixture -- this specifically tests the header being entirely absent.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as bare_client:
        response = await bare_client.get(_image_url(sorting_event.id))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_dashboard_token"


async def test_invalid_dashboard_token_returns_401(
    client: AsyncClient, sorting_event: SortingEvent
) -> None:
    response = await client.get(
        _image_url(sorting_event.id), headers={"X-Dashboard-Token": "wrong-token"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_dashboard_token"
