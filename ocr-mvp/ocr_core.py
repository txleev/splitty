import numpy as np
from paddleocr import PaddleOCR


def build_ocr():
    return PaddleOCR(
        device="cpu",
        text_detection_model_name="PP-OCRv6_small_det",
        text_recognition_model_name="PP-OCRv6_small_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def extract_items(results):
    """Flatten PaddleOCR results into [{"text", "score", "box"}], box = [x1, y1, x2, y2]."""
    items = []
    for result in results:
        res = result.json["res"]
        boxes = res.get("rec_boxes")
        for i, (text, score) in enumerate(zip(res["rec_texts"], res["rec_scores"])):
            if boxes is not None and len(boxes):
                box = [float(v) for v in boxes[i]]
            else:
                # Fall back to the detection polygon when no recognition box is returned.
                poly = np.asarray(res["dt_polys"][i], dtype=float)
                box = [poly[:, 0].min(), poly[:, 1].min(), poly[:, 0].max(), poly[:, 1].max()]
                box = [float(v) for v in box]
            items.append({"text": text, "score": float(score), "box": box})
    return items
