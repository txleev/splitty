import httpx

from errors import ApiError


class OcrError(ApiError):
    """The OCR/LLM service failed. status_code is the HTTP status returned to our client."""


def parse_receipt(
    ocr_url: str,
    filename: str | None,
    content_type: str,
    data: bytes,
    note: str | None,
) -> dict:
    """Send the image (and optional note) to ocr-mvp /parse and return the "receipt" object."""
    form = {"note": note} if note else {}
    try:
        resp = httpx.post(
            f"{ocr_url}/parse",
            files={"file": (filename or "receipt", data, content_type)},
            data=form,
            # OCR on CPU plus the LLM call can take a while.
            timeout=120,
        )
    except httpx.HTTPError as e:
        raise OcrError(503, "OCR service is unavailable") from e

    if resp.status_code >= 500:
        raise OcrError(502, "OCR service failed to parse the receipt")
    if resp.status_code >= 400:
        # ocr-mvp answers 422 when it finds no text in the image.
        raise OcrError(422, _detail(resp))
    return resp.json()["receipt"]


def _detail(resp: httpx.Response) -> str:
    try:
        return str(resp.json().get("detail", "Receipt could not be read"))
    except ValueError:
        return "Receipt could not be read"
