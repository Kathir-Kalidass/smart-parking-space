from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .events import EventBus
from .models import EventRequest, ParkingEvent
from .simulator import ParkingSimulator
from .state import ParkingStateManager


def create_app(
    manager: ParkingStateManager | None = None,
    bus: EventBus | None = None,
) -> FastAPI:
    manager = manager or ParkingStateManager()
    bus = bus or EventBus()
    app = FastAPI(title="Smart Parking API", version="0.1.0")
    app.state.manager = manager
    app.state.bus = bus

    @app.get("/api/state")
    async def state():
        return manager.snapshot()

    @app.get("/api/events")
    async def events(limit: int = Query(50, ge=1, le=500)):
        return manager.recent_events(limit)

    @app.get("/api/graph")
    async def graph(limit: int = Query(100, ge=1, le=500)):
        return manager.graph(limit)

    @app.post("/api/events", status_code=201)
    async def add_event(request: EventRequest):
        event = ParkingEvent(
            vehicle_type=request.vehicle_type,
            direction=request.direction,
            source=request.source,
            timestamp=request.timestamp or datetime.now(timezone.utc),
        )
        try:
            state = manager.apply(event)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        await bus.publish({"event": event, "state": state})
        return {"event": event, "state": state}

    @app.post("/api/vehicle/{direction}", status_code=201)
    async def add_vehicle(direction: str, request: EventRequest):
        if request.direction.value != direction:
            raise HTTPException(status_code=422, detail="direction does not match URL")
        return await add_event(request)

    @app.post("/api/simulate")
    async def simulate(count: int = Query(10, ge=0, le=500), seed: int = 1):
        simulator = ParkingSimulator(seed)
        accepted = []
        for event in simulator.generate(count):
            try:
                state = manager.apply(event)
            except ValueError:
                continue
            accepted.append({"event": event, "state": state})
            await bus.publish({"event": event, "state": state})
        return accepted

    @app.websocket("/ws/events")
    async def websocket(websocket: WebSocket):
        await websocket.accept()
        queue: asyncio.Queue = asyncio.Queue()

        async def enqueue(message):
            await queue.put(message)

        await bus.subscribe(enqueue)
        try:
            await websocket.send_json(
                jsonable_encoder({"event": None, "state": manager.snapshot()})
            )
            while True:
                await websocket.send_json(jsonable_encoder(await queue.get()))
        except WebSocketDisconnect:
            pass
        finally:
            await bus.unsubscribe(enqueue)

    @app.websocket("/ws")
    async def dashboard_websocket(websocket: WebSocket):
        await websocket_endpoint(websocket)

    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        queue: asyncio.Queue = asyncio.Queue()

        async def enqueue(message):
            await queue.put(message)

        await bus.subscribe(enqueue)
        try:
            await websocket.send_json(
                jsonable_encoder({"event": None, "state": manager.snapshot()})
            )
            while True:
                await websocket.send_json(jsonable_encoder(await queue.get()))
        except WebSocketDisconnect:
            pass
        finally:
            await bus.unsubscribe(enqueue)

    @app.post("/api/control/{action}")
    async def control(action: str):
        if action not in {"start", "stop"}:
            raise HTTPException(status_code=404, detail="unknown control action")
        return {"running": action == "start"}

    web_root = Path(__file__).resolve().parents[2] / "web"
    if web_root.is_dir():
        app.mount("/assets", StaticFiles(directory=web_root), name="assets")

        @app.get("/", include_in_schema=False)
        async def dashboard():
            return FileResponse(web_root / "index.html")

        @app.get("/app.js", include_in_schema=False)
        async def dashboard_script():
            return FileResponse(web_root / "app.js")

        @app.get("/style.css", include_in_schema=False)
        async def dashboard_style():
            return FileResponse(web_root / "style.css")

    return app


app = create_app()
