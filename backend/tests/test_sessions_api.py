import psycopg

from helpers import FAKE_RECEIPT, IMAGE, host, new_session, upload
from ids import hash_token
from ocr_client import OcrError
from schemas import ParsedReceipt


def test_create_session_stores_items_and_totals(client, fake_ocr, clean_db):
    resp = upload(client)

    assert resp.status_code == 201
    body = resp.json()
    assert len(body["session_id"]) == 11
    assert body["status"] == "draft"
    assert body["currency"] == "KGS"
    assert body["subtotal_minor"] == 4600
    assert body["tax_minor"] == 350
    assert body["tip_minor"] is None
    assert body["total_minor"] == 4950
    assert body["warnings"] == ["Tip not found"]
    assert [i["total_minor"] for i in body["items"]] == [1400, 3200]
    assert [i["unit_price_minor"] for i in body["items"]] == [1400, 1600]

    with psycopg.connect(clean_db) as conn:
        rows = conn.execute(
            "select name, quantity, total_minor from session_items "
            "where session_id = %s order by position",
            (body["session_id"],),
        ).fetchall()
    assert [(r[0], float(r[1]), r[2]) for r in rows] == [("Salad", 1.0, 1400), ("Steak", 2.0, 3200)]


def test_host_token_is_returned_once_and_only_its_hash_is_stored(client, fake_ocr, clean_db):
    body = new_session(client)

    with psycopg.connect(clean_db) as conn:
        (stored_hash,) = conn.execute(
            "select host_token_hash from sessions where id = %s", (body["session_id"],)
        ).fetchone()
    assert stored_hash == hash_token(body["host_token"])
    assert stored_hash != body["host_token"]


def test_note_is_forwarded_to_ocr_and_pre_assignments_are_stored(client, fake_ocr, clean_db):
    body = new_session(client, note="Jack and I had the salad")

    assert fake_ocr[0]["note"] == "Jack and I had the salad"
    assert body["items"][0]["preassigned_names"] == ["Jack"]


def test_note_names_become_member_slots(client, fake_ocr, clean_db):
    body = new_session(client, note="Jack and I had the salad")

    assert body["members"] == [
        {"id": body["members"][0]["id"], "name": "Jack", "joined": False, "confirmation": "none"}
    ]


def test_ocr_unavailable_returns_503_and_creates_nothing(client, monkeypatch, clean_db):
    def unavailable(*args, **kwargs):
        raise OcrError(503, "OCR service is unavailable")

    monkeypatch.setattr("main.parse_receipt", unavailable)

    assert upload(client).status_code == 503
    with psycopg.connect(clean_db) as conn:
        (count,) = conn.execute("select count(*) from sessions").fetchone()
    assert count == 0


def test_no_text_found_returns_422(client, monkeypatch, clean_db):
    def no_text(*args, **kwargs):
        raise OcrError(422, "No result produced for this image")

    monkeypatch.setattr("main.parse_receipt", no_text)

    assert upload(client).status_code == 422


def test_unexpected_ocr_output_returns_502(client, monkeypatch, clean_db):
    monkeypatch.setattr("main.parse_receipt", lambda *a, **k: {"items": "not a list"})

    assert upload(client).status_code == 502


def test_non_image_upload_is_rejected(client, fake_ocr, clean_db):
    resp = client.post("/sessions", files={"file": ("notes.txt", b"hello", "text/plain")})

    assert resp.status_code == 415
    assert fake_ocr == []


def test_empty_upload_is_rejected(client, fake_ocr, clean_db):
    resp = client.post("/sessions", files={"file": ("empty.jpeg", b"", "image/jpeg")})

    assert resp.status_code == 400


def test_parsed_receipt_schema_ignores_extra_fields():
    receipt = ParsedReceipt.model_validate({**FAKE_RECEIPT, "unexpected": 1})
    assert len(receipt.items) == 2
