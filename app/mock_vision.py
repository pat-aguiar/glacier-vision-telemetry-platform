from __future__ import annotations

import random
import uuid

from app.schemas import BoundingBox

MOCK_MATERIAL_LABELS = [
    "PET Bottle",
    "Aluminum Can",
    "Cardboard",
    "HDPE Jug",
    "Glass Bottle",
    "Steel Can",
]

MOCK_IMAGE_PATH = "mock/sorting-event-placeholder.jpg"


class MockVisionProvider:
    """Stands in for a real vision/detection service. Stateless -- swap this
    class out (behind the same method signature) once real detections exist.
    """

    def generate_bounding_boxes(self, event_id: uuid.UUID) -> list[BoundingBox]:
        """Deterministic mock detections for a given event id: 1-3 boxes with
        varied confidence, always including one low-confidence box so the
        frontend's red-to-green color coding is exercised on every event.
        """
        rng = random.Random(event_id.int)
        box_count = rng.randint(1, 3)
        labels = rng.sample(MOCK_MATERIAL_LABELS, min(box_count, len(MOCK_MATERIAL_LABELS)))

        boxes: list[BoundingBox] = []
        for label in labels:
            x_min = round(rng.uniform(0.05, 0.55), 3)
            y_min = round(rng.uniform(0.05, 0.55), 3)
            x_max = round(min(x_min + rng.uniform(0.15, 0.35), 0.98), 3)
            y_max = round(min(y_min + rng.uniform(0.15, 0.35), 0.98), 3)
            confidence = round(rng.uniform(0.55, 0.99), 3)
            boxes.append(
                BoundingBox(
                    label=label,
                    confidence=confidence,
                    x_min=x_min,
                    y_min=y_min,
                    x_max=x_max,
                    y_max=y_max,
                )
            )

        # Force one guaranteed low-confidence box regardless of box_count, so
        # the frontend's red end of the confidence color scale always has
        # something to render.
        boxes[0] = boxes[0].model_copy(update={"confidence": round(rng.uniform(0.30, 0.55), 3)})
        return boxes
