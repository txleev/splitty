import copy
import threading
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest

import sessions as rooms
from db import connect
from errors import ApiError
from helpers import (
    TEST_URL,
    claim,
    confirm,
    get_view,
    host,
    item_of,
    join,
    make_ready,
    member_headers,
    member_of,
    new_session,
)


@pytest.fixture
def split(client, fake_ocr, clean_db):
    """A ready split with two guests. The receipt has Salad (1) and Steak (2)."""
    body = new_session(client)
    make_ready(client, body)
    return body, join(client, body, "Ana"), join(client, body, "Ben")


def steak_id(client, body):
    return item_of(get_view(client, body), "Steak")["id"]


# Showing and limiting claims

def test_claim_shows_what_is_left(client, split):
    body, ana, _ = split

    resp = claim(client, body, steak_id(client, body), 1, ana)

    assert resp.status_code == 200
    steak = item_of(resp.json(), "Steak")
    assert steak["remaining"] == 1
    assert steak["claims"] == [{"member_id": ana["member_id"], "name": "Ana", "quantity": 1}]


def test_cannot_claim_more_than_is_left(client, split):
    body, ana, ben = split
    steak = steak_id(client, body)
    assert claim(client, body, steak, 2, ana).status_code == 200

    resp = claim(client, body, steak, 1, ben)

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Only 0 left of Steak."


def test_lowering_your_own_claim_makes_room_for_others(client, split):
    body, ana, ben = split
    steak = steak_id(client, body)
    claim(client, body, steak, 2, ana)
    assert claim(client, body, steak, 1, ben).status_code == 409

    assert claim(client, body, steak, 1, ana).status_code == 200
    assert claim(client, body, steak, 1, ben).status_code == 200
    assert item_of(get_view(client, body), "Steak")["remaining"] == 0


def test_claiming_the_same_amount_twice_is_safe(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)

    claim(client, body, steak, 1, ana)
    resp = claim(client, body, steak, 1, ana)

    assert item_of(resp.json(), "Steak")["claims"] == [
        {"member_id": ana["member_id"], "name": "Ana", "quantity": 1}
    ]
    assert item_of(resp.json(), "Steak")["remaining"] == 1


def test_zero_removes_the_claim(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    claim(client, body, steak, 2, ana)

    resp = claim(client, body, steak, 0, ana)

    assert item_of(resp.json(), "Steak")["claims"] == []
    assert item_of(resp.json(), "Steak")["remaining"] == 2


def test_claims_need_the_member_token(client, split):
    body, _, _ = split
    url = f"/sessions/{body['session_id']}/items/{steak_id(client, body)}/claim"

    assert client.put(url, json={"quantity": 1}).status_code == 401
    # The host token is not a guest token, even when sent in the member header.
    wrong = {"X-Member-Token": body["host_token"]}
    assert client.put(url, json={"quantity": 1}, headers=wrong).status_code == 403


def test_claims_on_an_expired_session_are_refused(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(
            "update sessions set last_active_at = now() - interval '8 days' where id = %s",
            (body["session_id"],),
        )

    resp = claim(client, body, steak, 1, ana)

    assert resp.status_code == 404


# Confirming

def test_changing_a_claim_clears_the_confirmation(client, split):
    body, ana, _ = split
    claim(client, body, steak_id(client, body), 1, ana)
    assert confirm(client, body, ana).status_code == 200
    assert member_of(get_view(client, body), "Ana")["confirmation"] == "confirmed"

    claim(client, body, steak_id(client, body), 2, ana)

    assert member_of(get_view(client, body), "Ana")["confirmation"] == "none"


def test_confirming_again_is_always_allowed(client, split):
    body, ana, _ = split
    claim(client, body, steak_id(client, body), 1, ana)

    first = confirm(client, body, ana)
    second = confirm(client, body, ana)

    assert first.status_code == 200
    assert second.status_code == 200
    assert member_of(second.json(), "Ana")["confirmation"] == "confirmed"


def test_confirm_waits_until_the_bill_adds_up(client, split):
    body, ana, _ = split
    client.patch(f"/sessions/{body['session_id']}", json={"total_minor": 5000}, headers=host(body))

    blocked = confirm(client, body, ana)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["problems"]

    client.patch(f"/sessions/{body['session_id']}", json={"total_minor": 4950}, headers=host(body))
    assert confirm(client, body, ana).status_code == 200


def test_me_returns_identity_and_confirmation(client, split):
    body, ana, _ = split
    url = f"/sessions/{body['session_id']}/me"

    before = client.get(url, headers=member_headers(ana)).json()
    confirm(client, body, ana)
    after = client.get(url, headers=member_headers(ana)).json()

    assert before == {"member_id": ana["member_id"], "name": "Ana", "confirmation": "none"}
    assert after["confirmation"] == "confirmed"
    assert client.get(url).status_code == 401
    assert client.get(url, headers={"X-Member-Token": body["host_token"]}).status_code == 403


# Host edits and existing claims

def test_claims_survive_a_rename(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    claim(client, body, steak, 2, ana)
    confirm(client, body, ana)

    client.patch(
        f"/sessions/{body['session_id']}/items/{steak}",
        json={"name": "Beef steak"},
        headers=host(body),
    )

    view = get_view(client, body)
    assert item_of(view, "Beef steak")["claims"] == [
        {"member_id": ana["member_id"], "name": "Ana", "quantity": 2}
    ]
    # A rename does not change what anyone owes, so the confirmation still holds.
    assert member_of(view, "Ana")["confirmation"] == "confirmed"


def test_a_price_change_keeps_claims_and_asks_for_reconfirmation(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    claim(client, body, steak, 2, ana)
    confirm(client, body, ana)
    sid = body["session_id"]

    client.patch(f"/sessions/{sid}/items/{steak}", json={"total_minor": 3300}, headers=host(body))
    client.patch(
        f"/sessions/{sid}", json={"subtotal_minor": 4700, "total_minor": 5050}, headers=host(body)
    )

    view = get_view(client, body)
    assert item_of(view, "Steak")["claims"][0]["quantity"] == 2
    assert member_of(view, "Ana")["confirmation"] == "needs_reconfirm"
    assert confirm(client, body, ana).status_code == 200


def test_host_can_lower_the_quantity_below_claims_and_the_guest_fixes_it(client, split):
    body, ana, _ = split
    sid = body["session_id"]
    steak = steak_id(client, body)
    claim(client, body, steak, 2, ana)
    assert confirm(client, body, ana).status_code == 200

    # Steak 2 -> 1 at 16.00 each, so the bill must drop to 30.00 subtotal and 33.50 total.
    client.patch(f"/sessions/{sid}/items/{steak}", json={"quantity": 1, "total_minor": 1600}, headers=host(body))
    client.patch(f"/sessions/{sid}", json={"subtotal_minor": 3000, "total_minor": 3350}, headers=host(body))

    view = get_view(client, body)
    assert item_of(view, "Steak")["remaining"] == -1
    assert item_of(view, "Steak")["claims"][0]["quantity"] == 2
    assert member_of(view, "Ana")["confirmation"] == "needs_reconfirm"

    blocked = confirm(client, body, ana)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["items"] == ["Steak"]

    assert claim(client, body, steak, 1, ana).status_code == 200
    assert confirm(client, body, ana).status_code == 200
    assert member_of(get_view(client, body), "Ana")["confirmation"] == "confirmed"


def test_deleting_a_claimed_item_removes_its_claims(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    claim(client, body, steak, 2, ana)
    confirm(client, body, ana)

    resp = client.delete(f"/sessions/{body['session_id']}/items/{steak}", headers=host(body))

    assert resp.status_code == 200
    assert [i["name"] for i in resp.json()["items"]] == ["Salad"]
    assert member_of(resp.json(), "Ana")["confirmation"] == "needs_reconfirm"


def test_fractional_quantity_blocks_marking_ready(client, split):
    body, _, _ = split
    sid = body["session_id"]
    client.patch(
        f"/sessions/{sid}/items/{steak_id(client, body)}",
        json={"quantity": 1.5},
        headers=host(body),
    )

    resp = client.post(f"/sessions/{sid}/ready", headers=host(body))

    assert resp.status_code == 409
    assert any("'Steak' has quantity 1.5" in p for p in resp.json()["detail"]["problems"])


# Concurrency

def test_concurrent_claims_never_exceed_the_quantity(client, monkeypatch, clean_db):
    cake_receipt = {
        "items": [
            {
                "name": "Cake",
                "qty": 3,
                "unit_price": 10.0,
                "total_price": 30.0,
                "assigned_to": [],
                "missing": [],
            }
        ],
        "subtotal": 30.0,
        "tax": None,
        "tip": None,
        "total": 30.0,
        "currency": "KGS",
        "warnings": [],
    }
    monkeypatch.setattr("main.parse_receipt", lambda *a, **k: copy.deepcopy(cake_receipt))
    body = new_session(client)
    make_ready(client, body)
    cake = body["items"][0]["id"]
    guests = [join(client, body, f"Guest {n}") for n in range(8)]
    start = threading.Barrier(len(guests))

    def try_claim(guest):
        with connect(TEST_URL) as conn:
            start.wait()
            try:
                rooms.set_claim(conn, body["session_id"], guest["member_token"], cake, 1)
                return "claimed"
            except ApiError as e:
                return e.status_code

    with ThreadPoolExecutor(max_workers=len(guests)) as pool:
        outcomes = list(pool.map(try_claim, guests))

    assert outcomes.count("claimed") == 3
    assert outcomes.count(409) == 5
    cake_view = item_of(get_view(client, body), "Cake")
    assert cake_view["remaining"] == 0
    assert sum(c["quantity"] for c in cake_view["claims"]) == 3
