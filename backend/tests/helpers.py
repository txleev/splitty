import os

# Tests use their own database so the real "splitty" data is never touched.
TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://splitty:splitty@127.0.0.1:5432/splitty_test"
)

FAKE_RECEIPT = {
    "items": [
        {
            "name": "Salad",
            "qty": 1,
            "unit_price": 14.0,
            "total_price": 14.0,
            "assigned_to": ["Jack"],
            "missing": [],
        },
        {
            "name": "Steak",
            "qty": 2,
            "unit_price": 16.0,
            "total_price": 32.0,
            "assigned_to": [],
            "missing": [],
        },
    ],
    # Reconciled: 14 + 32 = 46 subtotal, 46 + 3.50 tax = 49.50 total.
    "subtotal": 46.0,
    "tax": 3.5,
    "tip": None,
    "total": 49.5,
    "currency": "KGS",
    "warnings": ["Tip not found"],
}

IMAGE = ("receipt.jpeg", b"fake-image-bytes", "image/jpeg")


def upload(client, note=None):
    data = {"note": note} if note else {}
    return client.post("/sessions", files={"file": IMAGE}, data=data)


def new_session(client, note=None) -> dict:
    resp = upload(client, note)
    assert resp.status_code == 201, resp.text
    return resp.json()


def host(body: dict) -> dict:
    return {"X-Host-Token": body["host_token"]}


def make_ready(client, body: dict) -> dict:
    resp = client.post(f"/sessions/{body['session_id']}/ready", headers=host(body))
    assert resp.status_code == 200, resp.text
    return resp.json()
