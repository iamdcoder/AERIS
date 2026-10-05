"""Live operational-event replay endpoints for the AERIS demo."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ...operations import get_replay_controller


router = APIRouter()


class ReplayStartRequest(BaseModel):
    stop_at_minute: int = Field(default=19, ge=1, le=35)
    reset_first: bool = True


class ReplayStepRequest(BaseModel):
    minutes: int = Field(default=1, ge=1, le=5)


@router.get("/operations/live", summary="Current simulated operational feed state")
def get_live_operations():
    controller = get_replay_controller()
    return controller.snapshot().model_dump(mode="json")


@router.get("/operations/events", summary="Recent normalized operational events")
def get_live_events(limit: int = 20):
    if limit < 1 or limit > 120:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 120")
    controller = get_replay_controller()
    return {
        "events": [
            event.model_dump(mode="json")
            for event in controller.events(limit)
        ],
        "simulation_time_min": controller.snapshot().last_simulation_time_min,
    }


@router.post("/operations/replay/reset", summary="Reset live replay to T+00")
def reset_live_replay():
    controller = get_replay_controller()
    return controller.reset().model_dump(mode="json")


@router.post("/operations/replay/start", summary="Start deterministic live operational replay")
def start_live_replay(body: ReplayStartRequest):
    controller = get_replay_controller()
    return controller.start(
        stop_at_minute=body.stop_at_minute,
        reset_first=body.reset_first,
    ).model_dump(mode="json")


@router.post("/operations/replay/stop", summary="Stop deterministic live operational replay")
def stop_live_replay():
    controller = get_replay_controller()
    return controller.stop().model_dump(mode="json")


@router.post("/operations/replay/step", summary="Advance the operational replay manually")
def step_live_replay(body: ReplayStepRequest):
    controller = get_replay_controller()
    return controller.step(body.minutes).model_dump(mode="json")


@router.websocket("/ws/operations")
async def operations_websocket(websocket: WebSocket):
    """Stream live operational state; polling clients can use /operations/live as fallback."""
    await websocket.accept()
    controller = get_replay_controller()
    last_version = -1

    try:
        while True:
            snapshot = controller.snapshot()
            if snapshot.version != last_version:
                await websocket.send_json(snapshot.model_dump(mode="json"))
                last_version = snapshot.version
            else:
                await websocket.send_json({
                    "type": "heartbeat",
                    "version": snapshot.version,
                    "running": snapshot.running,
                    "simulation_time_min": snapshot.last_simulation_time_min,
                })
            await asyncio.sleep(0.75)
    except (WebSocketDisconnect, RuntimeError):
        return
