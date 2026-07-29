from __future__ import annotations

import json

from starlette.exceptions import HTTPException
from starlette.requests import ClientDisconnect
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_SIZE = 2 * 1024 * 1024  # 2 MB

_TOO_LARGE_DETAIL = f"Request body exceeds the {MAX_BODY_SIZE // (1024 * 1024)}MB limit."


class BodySizeLimitMiddleware:
    """Pure ASGI middleware rejecting HTTP request bodies over `max_body_size`.

    Two layers of defense:
    1. `Content-Length` is checked upfront, before a single byte of body is
       read -- rejects the obvious case cheaply, before `self.app` is even
       called, so the response is sent directly at the raw ASGI level here.
    2. Bytes are also counted as they actually stream in, as a backstop --
       `Content-Length` can be absent, wrong, or bypassed entirely via
       chunked transfer encoding, so the running total is the only thing
       that can't be lied to by the client. This path can't send a raw
       response the same way: by the time the overage is detected, control
       is deep inside the downstream app's own body-reading code (e.g.
       FastAPI's request-parsing, which wraps body reads in a broad
       `except Exception` that would otherwise swallow and reword any
       generic exception raised here). Raising `starlette.HTTPException` is
       what survives that -- FastAPI explicitly re-raises `HTTPException`
       instead of swallowing it, so it reaches Starlette's own exception
       handling and comes back out as a real 413.

    Only wraps `http` scopes; websocket and lifespan scopes pass through
    untouched.
    """

    def __init__(self, app: ASGIApp, max_body_size: int = MAX_BODY_SIZE) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                declared_size = None
            if declared_size is not None and declared_size > self.max_body_size:
                await self._send_413(send)
                return

        total_size = 0

        async def limited_receive() -> Message:
            nonlocal total_size
            message = await receive()
            if message["type"] == "http.request":
                total_size += len(message.get("body", b""))
                if total_size > self.max_body_size:
                    raise HTTPException(status_code=413, detail=_TOO_LARGE_DETAIL)
            return message

        try:
            await self.app(scope, limited_receive, send)
        except ClientDisconnect:
            # Client hung up mid-upload; nothing left to respond to.
            pass

    @staticmethod
    async def _send_413(send: Send) -> None:
        body = json.dumps(
            {"error": {"code": "payload_too_large", "message": _TOO_LARGE_DETAIL, "details": None}}
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
