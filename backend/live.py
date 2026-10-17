"""Live view of a split. Each open socket gets a full snapshot on connect and after every change."""

import asyncio
from contextlib import suppress

import psycopg
from fastapi import WebSocket, WebSocketDisconnect

import sessions as rooms
from db import connect
from errors import ApiError

# Set by migration 004: every committed change to a split sends its id on this channel.
CHANNEL = "session_changes"
# Application-specific close code (4000-4999 is reserved for apps): the split is gone.
GONE_CODE = 4404
KEEPALIVE_SECONDS = 25


def _read(url: str, session_id: str, touch: bool):
    with connect(url) as conn:
        if touch:
            return rooms.get_view(conn, session_id)
        return rooms.read_snapshot(conn, session_id)


def _check(url: str, session_id: str) -> None:
    with connect(url) as conn:
        rooms.check_alive(conn, session_id)


async def _wake_on_change(
    listener: psycopg.AsyncConnection, session_id: str, changed: asyncio.Event
) -> None:
    async for notice in listener.notifies():
        if notice.payload == session_id:
            changed.set()


async def _send(websocket: WebSocket, view) -> None:
    await websocket.send_json({"type": "snapshot", "session": view.model_dump(mode="json")})


async def _send_snapshots(
    websocket: WebSocket, url: str, session_id: str, changed: asyncio.Event
) -> None:
    await _send(websocket, await asyncio.to_thread(_read, url, session_id, True))
    while True:
        await changed.wait()
        # Clear before reading. A change that commits during the read sets the flag again,
        # so the next loop reads once more and nothing is missed.
        changed.clear()
        await _send(websocket, await asyncio.to_thread(_read, url, session_id, False))


async def _keep_alive(websocket: WebSocket, url: str, session_id: str) -> None:
    # Checking expiry here means a socket for an expired split closes without waiting for a change.
    while True:
        await asyncio.sleep(KEEPALIVE_SECONDS)
        await asyncio.to_thread(_check, url, session_id)
        await websocket.send_json({"type": "ping"})


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    # Clients send nothing, so this only waits for the connection to close.
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return


async def serve(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    url = websocket.app.state.database_url
    changed = asyncio.Event()

    async with await psycopg.AsyncConnection.connect(url, autocommit=True) as listener:
        # Listen before the first read, so no change between the two is missed.
        await listener.execute(f"LISTEN {CHANNEL}")
        tasks = [
            asyncio.create_task(_wake_on_change(listener, session_id, changed)),
            asyncio.create_task(_send_snapshots(websocket, url, session_id, changed)),
            asyncio.create_task(_keep_alive(websocket, url, session_id)),
            asyncio.create_task(_wait_for_disconnect(websocket)),
        ]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    if any(not t.cancelled() and isinstance(t.exception(), ApiError) for t in done):
        with suppress(RuntimeError, WebSocketDisconnect):
            await websocket.send_json({"type": "gone"})
            await websocket.close(code=GONE_CODE)
        return
    with suppress(RuntimeError, WebSocketDisconnect):
        await websocket.close()
