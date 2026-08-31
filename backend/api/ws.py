"""WebSocket endpoint — streams live events to all connected browser clients."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.event_bus import subscribe, unsubscribe, subscriber_count

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = subscribe()

    # Send a welcome / connection-confirmed message immediately.
    await websocket.send_json({
        "type": "connected",
        "ts": _now_iso(),
        "message": "Revenue Autopilot real-time stream connected.",
        "subscribers": subscriber_count(),
    })

    try:
        while True:
            # Wait for the next event from the bus (with a 20 s heartbeat).
            try:
                message = await asyncio.wait_for(queue.get(), timeout=20.0)
                await websocket.send_text(message)
            except asyncio.TimeoutError:
                # Heartbeat ping so idle connections are not dropped by proxies.
                await websocket.send_json({"type": "ping", "ts": _now_iso()})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        unsubscribe(queue)


def _now_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
