from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

limiter = Limiter(key_func=get_remote_address)


def telemetry_events_rate_limit() -> str:
    """Read at request time (via slowapi's dynamic-limit support) rather
    than baked into the decorator at import time, so it stays in sync with
    whatever `TELEMETRY_EVENTS_RATE_LIMIT` Settings resolves to.
    """
    return get_settings().telemetry_events_rate_limit
