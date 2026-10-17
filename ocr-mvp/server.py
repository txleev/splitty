import logging
import os
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from lines import attach_quantity_lines, group_lines
from ocr_core import build_ocr, extract_items
from structure import ParsedReceipt, StructureError, make_client, structure_receipt

log = logging.getLogger("ocr")
logging.basicConfig(level=logging.INFO)

state = {}
# Paddle predictors are not safe to call from several threads at once.
predict_lock = threading.Lock()


class OcrLine(BaseModel):
    text: str
    score: float
    box: list[float]  # [x1, y1, x2, y2]


class OcrResponse(BaseModel):
    lines: list[OcrLine]
    grouped_lines: list[str]
    # Legacy flat lists, kept so the earlier curl flow keeps working.
    rec_texts: list[str]
    rec_scores: list[float]


class ParseResponse(BaseModel):
    receipt: ParsedReceipt
    grouped_lines: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the models once, then run a blank image through them so the first real
    # request is already warm. The server only accepts traffic after this finishes.
    start = perf_counter()
    state["ocr"] = build_ocr()
    list(state["ocr"].predict(np.full((64, 64, 3), 255, dtype=np.uint8)))
    log.info("OCR models loaded and warmed up in %.3fs", perf_counter() - start)

    # Fails fast at startup if GROQ_API_KEY is missing.
    state["llm"] = make_client()
    yield
    state.clear()


app = FastAPI(title="OCR service", lifespan=lifespan)


def ocr_upload(file: UploadFile):
    suffix = Path(file.filename or "").suffix or ".png"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    start = perf_counter()
    try:
        with predict_lock:
            results = list(state["ocr"].predict(tmp_path))
    finally:
        os.unlink(tmp_path)
    log.info("OCR on %s took %.3fs", file.filename, perf_counter() - start)

    if not results:
        raise HTTPException(status_code=422, detail="No result produced for this image")
    return results


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ocr", response_model=OcrResponse)
def run_ocr(file: UploadFile = File(...)):
    items = extract_items(ocr_upload(file))
    return OcrResponse(
        lines=items,
        grouped_lines=group_lines(items),
        rec_texts=[item["text"] for item in items],
        rec_scores=[item["score"] for item in items],
    )


@app.post("/parse", response_model=ParseResponse)
def parse_receipt(file: UploadFile = File(...), note: str | None = Form(None)):
    items = extract_items(ocr_upload(file))
    lines = attach_quantity_lines(group_lines(items))
    try:
        receipt = structure_receipt(state["llm"], lines, note=note)
    except StructureError as e:
        log.error("Structuring failed: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    return ParseResponse(receipt=receipt, grouped_lines=lines)
