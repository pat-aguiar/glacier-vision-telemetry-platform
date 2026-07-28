from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

DEFAULT_QUEUE_SIZE = 100


class Broadcaster:
    """In-memory async pub/sub broadcaster for fan-out to dashboard clients.

    Each subscriber owns a bounded queue. A slow or stalled subscriber must
    never block publishing to the rest -- if its queue is full, the message
    is dropped for that subscriber only (logged, not raised).
    """

    def __init__(self, *, maxsize: int = DEFAULT_QUEUE_SIZE) -> None:
        self._maxsize = maxsize
        self._subscribers: dict[str, asyncio.Queue[Any]] = {}
        self._lock = asyncio.Lock()

    async def publish(self, message: Any) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.items())

        for subscriber_id, queue in subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning(
                    "Dropping message for subscriber %s: queue full (maxsize=%d)",
                    subscriber_id,
                    self._maxsize,
                )

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[Any]]:
        subscriber_id = uuid4().hex
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=self._maxsize)

        async with self._lock:
            self._subscribers[subscriber_id] = queue

        try:
            yield queue
        finally:
            async with self._lock:
                self._subscribers.pop(subscriber_id, None)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Process-wide singleton: dashboard websocket clients subscribe to this, and
# ingestion paths publish telemetry updates to it.
broadcaster = Broadcaster()


def get_broadcaster() -> Broadcaster:
    return broadcaster
