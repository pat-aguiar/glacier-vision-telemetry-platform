from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from app.api.deps import get_broadcaster
from app.config import get_settings
from app.streaming import Broadcaster

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/stream")
async def stream_telemetry(
    websocket: WebSocket,
    broadcaster: Broadcaster = Depends(get_broadcaster),
) -> None:
    """Push a live feed of telemetry updates to a dashboard client.

    Starlette's CORSMiddleware only applies to HTTP requests, not websocket
    handshakes, so the allowed-origins check has to be done manually here.
    """
    settings = get_settings()
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in settings.cors_allow_origins:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    async with broadcaster.subscribe() as queue:
        disconnect_task = asyncio.create_task(websocket.receive_text())
        message_task = asyncio.create_task(queue.get())
        try:
            while True:
                done, _ = await asyncio.wait(
                    {disconnect_task, message_task}, return_when=asyncio.FIRST_COMPLETED
                )

                if disconnect_task in done:
                    # Raises WebSocketDisconnect when the client goes away; any
                    # other received frame is unexpected on this send-only
                    # stream, so it's discarded and we just keep listening.
                    disconnect_task.result()
                    disconnect_task = asyncio.create_task(websocket.receive_text())

                if message_task in done:
                    await websocket.send_json(message_task.result())
                    message_task = asyncio.create_task(queue.get())
        except WebSocketDisconnect:
            logger.info("Telemetry stream client disconnected")
        finally:
            disconnect_task.cancel()
            message_task.cancel()
            await asyncio.gather(disconnect_task, message_task, return_exceptions=True)
