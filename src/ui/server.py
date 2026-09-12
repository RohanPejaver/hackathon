"""FastAPI + WebSocket + a single vanilla page (39 §6). Payload-agnostic.

The runtime (the composition root, 30 §rule 4) hands this module two callables:
`snapshot()` returns the full station state as a JSON-ready dict — the same projection the
inspector reads (25 §Inspector) — and `on_action(body)` turns a worker action into a draft
event in the log (22 `WorkerDisplay`: worker actions enter the system only as events; the UI
never mutates `WorldState`). Full state is pushed at `push_hz` (5Hz; deltas are premature
optimization). Two routes: `/` worker display, `/inspector` read-only state + timeline.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

STATIC = Path(__file__).parent / "static"

Snapshot = Callable[[], dict[str, Any]]
ActionHandler = Callable[[dict[str, Any]], dict[str, Any]]


def create_app(snapshot: Snapshot, on_action: ActionHandler, push_hz: float) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/")
    def worker_display() -> FileResponse:
        return FileResponse(STATIC / "index.html")

    @app.get("/inspector")
    def inspector() -> FileResponse:
        return FileResponse(STATIC / "inspector.html")

    @app.get("/snapshot")
    def snapshot_now() -> JSONResponse:
        # The same projection the socket pushes; used by the fallback-ladder diff (37).
        return JSONResponse(snapshot())

    @app.post("/action")
    async def action(request: Request) -> JSONResponse:
        body = await request.json()
        result = on_action(body)
        return JSONResponse(result, status_code=200 if result.get("accepted") else 400)

    @app.websocket("/ws")
    async def ws(socket: WebSocket) -> None:
        await socket.accept()
        try:
            while True:
                await socket.send_json(snapshot())
                await asyncio.sleep(1.0 / push_hz)
        except WebSocketDisconnect:
            return

    return app
