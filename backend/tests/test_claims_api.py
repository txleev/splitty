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


# Equal split

def mark_split_equally(client, body, item_id, value=True):
    resp = client.patch(
        f"/sessions/{body['session_id']}/items/{item_id}",
        json={"split_equally": value},
        headers=host(body),
    )
    assert resp.status_code == 200, resp.text
    make_ready(client, body)
    return resp


def test_equal_split_item_needs_one_person_then_is_claimed(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    mark_split_equally(client, body, steak)
    assert item_of(get_view(client, body), "Steak")["remaining"] == 1

    resp = claim(client, body, steak, 1, ana)

    assert resp.status_code == 200
    assert item_of(resp.json(), "Steak")["remaining"] == 0


def test_equal_split_lets_any_number_of_guests_join_but_only_as_one(client, split):
    body, ana, ben = split
    steak = steak_id(client, body)
    mark_split_equally(client, body, steak)

    assert claim(client, body, steak, 1, ana).status_code == 200
    assert claim(client, body, steak, 1, ben).status_code == 200
    resp = claim(client, body, steak, 2, ana)

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Steak is split equally. Join it or leave it."
    view = get_view(client, body)
    assert item_of(view, "Steak")["remaining"] == 0
    assert len(item_of(view, "Steak")["claims"]) == 2


def test_equal_split_gives_each_guest_the_same_share(client, split):
    body, ana, ben = split
    steak = steak_id(client, body)
    salad = item_of(get_view(client, body), "Salad")["id"]
    mark_split_equally(client, body, steak)
    claim(client, body, salad, 1, ana)
    claim(client, body, steak, 1, ana)
    claim(client, body, steak, 1, ben)
    confirm(client, body, ana)
    confirm(client, body, ben)

    view = get_view(client, body)

    assert view["locked"] is True
    subtotals = {s["name"]: s["subtotal_minor"] for s in view["shares"]}
    # Steak is 32.00, so 16.00 each. Ana also has the 14.00 salad.
    assert subtotals == {"Ana": 3000, "Ben": 1600}


def test_equal_split_allows_a_fractional_quantity(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    client.patch(
        f"/sessions/{body['session_id']}/items/{steak}",
        json={"quantity": 0.5, "split_equally": True},
        headers=host(body),
    )

    resp = client.post(f"/sessions/{body['session_id']}/ready", headers=host(body))

    assert resp.status_code == 200, resp.text


def test_changing_the_split_mode_clears_that_items_claims(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    claim(client, body, steak, 2, ana)

    mark_split_equally(client, body, steak)
    assert item_of(get_view(client, body), "Steak")["claims"] == []

    claim(client, body, steak, 1, ana)
    mark_split_equally(client, body, steak, value=False)
    steak_view = item_of(get_view(client, body), "Steak")

    assert steak_view["claims"] == []
    assert steak_view["remaining"] == 2


def test_equal_split_blocks_locking_until_someone_joins_it(client, split):
    body, ana, ben = split
    steak = steak_id(client, body)
    salad = item_of(get_view(client, body), "Salad")["id"]
    mark_split_equally(client, body, steak)
    claim(client, body, salad, 1, ana)
    confirm(client, body, ana)
    confirm(client, body, ben)

    view = get_view(client, body)

    assert view["locked"] is False
    assert "Steak needs at least one person to split it." in view["blockers"]


# Equal split with a set number of people

def split_between(client, body, item_id, count):
    resp = client.patch(
        f"/sessions/{body['session_id']}/items/{item_id}",
        json={"split_equally": True, "split_count": count},
        headers=host(body),
    )
    assert resp.status_code == 200, resp.text
    make_ready(client, body)
    return resp


def test_a_set_head_count_shows_the_free_spots(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    split_between(client, body, steak, 4)
    assert item_of(get_view(client, body), "Steak")["remaining"] == 4

    resp = claim(client, body, steak, 1, ana)

    assert item_of(resp.json(), "Steak")["remaining"] == 3
    assert item_of(resp.json(), "Steak")["split_count"] == 4


def test_nobody_can_join_once_every_spot_is_taken(client, split):
    body, ana, ben = split
    steak = steak_id(client, body)
    split_between(client, body, steak, 2)
    jack = join(client, body, "Jack")
    assert claim(client, body, steak, 1, ana).status_code == 200
    assert claim(client, body, steak, 1, ben).status_code == 200

    resp = claim(client, body, steak, 1, jack)

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Steak already has all 2 people."
    # Someone who is already in can repeat the call, and leaving frees the spot.
    assert claim(client, body, steak, 1, ana).status_code == 200
    assert claim(client, body, steak, 0, ben).status_code == 200
    assert claim(client, body, steak, 1, jack).status_code == 200


def test_each_person_pays_their_fixed_share_before_the_rest_have_joined(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    split_between(client, body, steak, 4)
    claim(client, body, steak, 1, ana)
    confirm(client, body, ana)

    view = get_view(client, body)

    # Steak is 32.00 between 4 people, so Ana owes 8.00 now and still will when the rest join.
    assert {s["name"]: s["subtotal_minor"] for s in view["shares"]} == {"Ana": 800}
    assert view["locked"] is False
    assert "Steak is waiting for 3 more people to split it." in view["blockers"]


def test_a_set_head_count_must_be_filled_to_lock(client, split):
    body, ana, ben = split
    steak = steak_id(client, body)
    salad = item_of(get_view(client, body), "Salad")["id"]
    split_between(client, body, steak, 2)
    claim(client, body, salad, 1, ana)
    claim(client, body, steak, 1, ana)
    claim(client, body, steak, 1, ben)
    confirm(client, body, ana)
    confirm(client, body, ben)

    view = get_view(client, body)

    assert view["locked"] is True
    assert {s["name"]: s["subtotal_minor"] for s in view["shares"]} == {"Ana": 3000, "Ben": 1600}


def test_lowering_the_head_count_below_the_people_in_over_claims_the_item(client, split):
    body, ana, ben = split
    steak = steak_id(client, body)
    split_between(client, body, steak, 3)
    jack = join(client, body, "Jack")
    for guest in (ana, ben, jack):
        claim(client, body, steak, 1, guest)
        confirm(client, body, guest)

    split_between(client, body, steak, 2)
    view = get_view(client, body)

    assert item_of(view, "Steak")["remaining"] == -1
    assert "Steak is over-claimed." in view["blockers"]
    # The amounts changed, so everyone has to confirm again, and nobody can until it is fixed.
    assert member_of(view, "Ana")["confirmation"] == "needs_reconfirm"
    assert confirm(client, body, ana).status_code == 409
    # One person leaving fixes it.
    claim(client, body, steak, 0, jack)
    assert confirm(client, body, ana).status_code == 200


def test_clearing_the_head_count_goes_back_to_whoever_joins(client, split):
    body, ana, _ = split
    steak = steak_id(client, body)
    split_between(client, body, steak, 3)
    claim(client, body, steak, 1, ana)

    client.patch(
        f"/sessions/{body['session_id']}/items/{steak}",
        json={"split_count": None},
        headers=host(body),
    )

    view = item_of(get_view(client, body), "Steak")
    assert view["split_count"] is None
    assert view["split_equally"] is True
    assert view["remaining"] == 0


def test_a_head_count_needs_an_equal_split(client, split):
    body, _, _ = split
    steak = steak_id(client, body)

    resp = client.patch(
        f"/sessions/{body['session_id']}/items/{steak}",
        json={"split_count": 3},
        headers=host(body),
    )

    assert resp.status_code == 422
    added = client.post(
        f"/sessions/{body['session_id']}/items",
        json={"name": "Tea", "total_minor": 300, "split_count": 3},
        headers=host(body),
    )
    assert added.status_code == 422


def test_turning_the_equal_split_off_drops_the_head_count(client, split):
    body, _, _ = split
    steak = steak_id(client, body)
    split_between(client, body, steak, 3)

    resp = client.patch(
        f"/sessions/{body['session_id']}/items/{steak}",
        json={"split_equally": False},
        headers=host(body),
    )

    assert resp.status_code == 200
    assert item_of(resp.json(), "Steak")["split_count"] is None
    assert item_of(resp.json(), "Steak")["remaining"] == 2


def test_a_head_count_is_at_least_two(client, split):
    body, _, _ = split
    steak = steak_id(client, body)

    resp = client.patch(
        f"/sessions/{body['session_id']}/items/{steak}",
        json={"split_equally": True, "split_count": 1},
        headers=host(body),
    )

    assert resp.status_code == 422
