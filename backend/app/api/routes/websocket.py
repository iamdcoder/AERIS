"""Realtime simulated airspace stream for the AERIS command center."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ...engine import public as engine

router = APIRouter()


@router.websocket("/ws/airspace")
async def airspace_stream(websocket: WebSocket) -> None:
    """Stream deterministic airspace snapshots and accept lightweight control messages."""
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({
                "type": "AIRSPACE_SNAPSHOT",
                "data": engine.get_airspace_state(),
            })

            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            except asyncio.TimeoutError:
                continue

            if raw.lower().strip() == "ping":
                await websocket.send_json({"type": "PONG"})
                continue

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "ERROR",
                    "message": "Expected JSON control message or 'ping'.",
                })
                continue

            if message.get("action") == "advance":
                minutes = int(message.get("minutes", 1))
                minutes = max(1, min(minutes, 10))
                state = engine.advance_simulation(minutes)
                await websocket.send_json({
                    "type": "AIRSPACE_ADVANCED",
                    "data": state,
                })
            elif message.get("action") == "snapshot":
                await websocket.send_json({
                    "type": "AIRSPACE_SNAPSHOT",
                    "data": engine.get_airspace_state(),
                })
            else:
                await websocket.send_json({
                    "type": "ERROR",
                    "message": "Unsupported websocket action.",
                })
    except WebSocketDisconnect:
        return
