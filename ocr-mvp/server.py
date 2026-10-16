import logging
import os
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from paddleocr import PaddleOCR

log = logging.getLogger("ocr")
logging.basicConfig(level=logging.INFO)

state = {}
# Paddle predictors are not safe to call from several threads at once.
predict_lock = threading.Lock()


def build_ocr():
    return PaddleOCR(
        device="cpu",
        text_detection_model_name="PP-OCRv6_small_det",
        text_recognition_model_name="PP-OCRv6_small_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the models once, then run a blank image through them so the first real
    # request is already warm. The server only accepts traffic after this finishes.
    start = perf_counter()
    state["ocr"] = build_ocr()
    list(state["ocr"].predict(np.full((64, 64, 3), 255, dtype=np.uint8)))
    log.info("OCR models loaded and warmed up in %.3fs", perf_counter() - start)
    yield
    state.clear()


app = FastAPI(title="OCR service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ocr")
def run_ocr(file: UploadFile = File(...)):
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

    rec_texts = []
    rec_scores = []
    for result in results:
        res = result.json["res"]
        rec_texts.extend(res["rec_texts"])
        rec_scores.extend(res["rec_scores"])

    return {"rec_texts": rec_texts, "rec_scores": rec_scores}
