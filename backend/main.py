import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, Header, Request, UploadFile, WebSocket
from fastapi.responses import JSONResponse
from pydantic import ValidationError

import sessions as rooms
from db import connect, run_migrations
from errors import ApiError
from live import serve as serve_live
from ocr_client import parse_receipt
from schemas import (
    ClaimIn,
    ItemIn,
    ItemPatch,
    JoinOut,
    MeOut,
    MemberIn,
    PaidIn,
    ParsedReceipt,
    SessionCreated,
    SessionPatch,
    SessionView,
)

log = logging.getLogger("splitty")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = os.environ["DATABASE_URL"]
    applied = run_migrations(database_url)
    if applied:
        log.info("Applied migrations: %s", ", ".join(applied))
    app.state.database_url = database_url
    app.state.ocr_url = os.environ.get("OCR_URL", "http://ocr:8000")
    yield


app = FastAPI(title="Splitty backend", lifespan=lifespan)


@app.exception_handler(ApiError)
def api_error(request: Request, exc: ApiError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def get_conn(request: Request):
    with connect(request.app.state.database_url) as conn:
        yield conn


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sessions", response_model=SessionCreated, status_code=201)
def create(request: Request, file: UploadFile = File(...), note: str | None = Form(None)):
    """Parse a receipt photo and create a draft session from it."""
    if not (file.content_type or "").startswith("image/"):
        raise ApiError(415, "Upload an image file")
    data = file.file.read()
    if not data:
        raise ApiError(400, "The uploaded file is empty")

    raw = parse_receipt(request.app.state.ocr_url, file.filename, file.content_type, data, note)
    try:
        receipt = ParsedReceipt.model_validate(raw)
    except ValidationError:
        raise ApiError(502, "OCR service returned an unexpected format")

    # Connect only now, so no database connection is held during the slow OCR call.
    with connect(request.app.state.database_url) as conn:
        return rooms.create_session(conn, receipt)


@app.get("/sessions/{session_id}", response_model=SessionView)
def get_session(session_id: str, conn=Depends(get_conn)):
    return rooms.get_view(conn, session_id)


@app.patch("/sessions/{session_id}", response_model=SessionView)
def patch_session(
    session_id: str,
    body: SessionPatch,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.update_session(conn, session_id, x_host_token, body.model_dump(exclude_unset=True))


@app.post("/sessions/{session_id}/items", response_model=SessionView)
def post_item(
    session_id: str,
    body: ItemIn,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.add_item(conn, session_id, x_host_token, body)


@app.patch("/sessions/{session_id}/items/{item_id}", response_model=SessionView)
def patch_item(
    session_id: str,
    item_id: int,
    body: ItemPatch,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.update_item(
        conn, session_id, item_id, x_host_token, body.model_dump(exclude_unset=True)
    )


@app.delete("/sessions/{session_id}/items/{item_id}", response_model=SessionView)
def remove_item(
    session_id: str,
    item_id: int,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.delete_item(conn, session_id, item_id, x_host_token)


@app.post("/sessions/{session_id}/members", response_model=SessionView)
def post_member(
    session_id: str,
    body: MemberIn,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.add_member(conn, session_id, x_host_token, body.name)


@app.delete("/sessions/{session_id}/members/{member_id}", response_model=SessionView)
def remove_member(
    session_id: str,
    member_id: int,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.remove_member(conn, session_id, x_host_token, member_id)


@app.post("/sessions/{session_id}/members/{member_id}/release", response_model=SessionView)
def release_member(
    session_id: str,
    member_id: int,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.release_member(conn, session_id, x_host_token, member_id)


@app.post("/sessions/{session_id}/members/{member_id}/unlock", response_model=SessionView)
def unlock_member(
    session_id: str,
    member_id: int,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.unlock_member(conn, session_id, x_host_token, member_id)


@app.post("/sessions/{session_id}/ready", response_model=SessionView)
def post_ready(
    session_id: str,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.mark_ready(conn, session_id, x_host_token)


@app.post("/sessions/{session_id}/join", response_model=JoinOut, status_code=201)
def post_join(session_id: str, body: MemberIn, conn=Depends(get_conn)):
    return rooms.join(conn, session_id, body.name)


@app.get("/sessions/{session_id}/me", response_model=MeOut)
def get_me(
    session_id: str,
    x_member_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.get_me(conn, session_id, x_member_token)


@app.put("/sessions/{session_id}/items/{item_id}/claim", response_model=SessionView)
def put_claim(
    session_id: str,
    item_id: int,
    body: ClaimIn,
    x_member_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.set_claim(conn, session_id, x_member_token, item_id, body.quantity)


@app.post("/sessions/{session_id}/confirm", response_model=SessionView)
def post_confirm(
    session_id: str,
    x_member_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.confirm(conn, session_id, x_member_token)


@app.put("/sessions/{session_id}/me/paid", response_model=SessionView)
def put_my_paid(
    session_id: str,
    body: PaidIn,
    x_member_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.set_my_paid(conn, session_id, x_member_token, body.paid)


@app.put("/sessions/{session_id}/members/{member_id}/paid", response_model=SessionView)
def put_member_paid(
    session_id: str,
    member_id: int,
    body: PaidIn,
    x_host_token: str | None = Header(default=None),
    conn=Depends(get_conn),
):
    return rooms.set_member_paid(conn, session_id, x_host_token, member_id, body.paid)


@app.websocket("/ws/sessions/{session_id}")
async def session_socket(websocket: WebSocket, session_id: str):
    """Live view of a split. Sends a snapshot on connect and after every change."""
    await serve_live(websocket, session_id)
