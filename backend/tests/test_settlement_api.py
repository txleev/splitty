import pytest

from helpers import (
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
    """A ready split with two guests. The receipt has Salad (1, Jack's note) and Steak (2)."""
    body = new_session(client)
    make_ready(client, body)
    return body, join(client, body, "Ana"), join(client, body, "Ben")


def item_id(client, body, name):
    return item_of(get_view(client, body), name)["id"]


def claim_everything(client, body, ana, ben):
    claim(client, body, item_id(client, body, "Salad"), 1, ana)
    claim(client, body, item_id(client, body, "Steak"), 2, ben)
    confirm(client, body, ana)
    confirm(client, body, ben)


# Locking and shares

def test_split_locks_when_every_item_is_claimed_and_confirmed(client, split):
    body, ana, ben = split
    claim_everything(client, body, ana, ben)

    view = get_view(client, body)

    assert view["locked"] is True
    assert view["blockers"] == []
    # Tax 350 follows the subtotals. Ana's exact tax is 106.52, so she rounds up to 107 to make
    # the parts add up to 350.
    assert view["shares"] == [
        {
            "member_id": ana["member_id"],
            "name": "Ana",
            "subtotal_minor": 1400,
            "tax_minor": 107,
            "tip_minor": 0,
            "total_minor": 1507,
        },
        {
            "member_id": ben["member_id"],
            "name": "Ben",
            "subtotal_minor": 3200,
            "tax_minor": 243,
            "tip_minor": 0,
            "total_minor": 3443,
        },
    ]
    assert sum(s["total_minor"] for s in view["shares"]) == view["total_minor"]


def test_shares_stay_hidden_until_everyone_has_confirmed(client, split):
    body, ana, ben = split
    claim(client, body, item_id(client, body, "Salad"), 1, ana)
    claim(client, body, item_id(client, body, "Steak"), 2, ben)
    confirm(client, body, ana)

    view = get_view(client, body)

    assert view["locked"] is False
    assert view["shares"] is None
    assert view["blockers"] == ["Ben has not confirmed."]


def test_an_unclaimed_item_blocks_the_lock(client, split):
    body, ana, ben = split
    claim(client, body, item_id(client, body, "Steak"), 2, ben)
    confirm(client, body, ben)
    confirm(client, body, ana)

    view = get_view(client, body)

    assert view["blockers"] == ["Salad has 1 unclaimed."]
    assert view["shares"] is None


def test_the_host_claims_leftovers_by_joining_as_a_guest(client, split):
    body, ana, ben = split
    # "Jack" is the name from the note. The host takes that slot to claim the Salad.
    jack = join(client, body, "Jack")
    claim(client, body, item_id(client, body, "Salad"), 1, jack)
    claim(client, body, item_id(client, body, "Steak"), 2, ben)
    for guest in (jack, ben, ana):
        confirm(client, body, guest)

    view = get_view(client, body)

    assert view["locked"] is True
    assert sum(s["total_minor"] for s in view["shares"]) == view["total_minor"]


def test_an_over_claimed_item_blocks_the_lock(client, split):
    body, ana, ben = split
    claim_everything(client, body, ana, ben)
    # Steak drops from 2 to 1 while Ben still claims 2.
    client.patch(
        f"/sessions/{body['session_id']}/items/{item_id(client, body, 'Steak')}",
        json={"quantity": 1},
        headers=host(body),
    )
    make_ready(client, body)

    view = get_view(client, body)

    assert view["blockers"] == [
        "Steak is over-claimed.",
        "Ana has not confirmed.",
        "Ben has not confirmed.",
    ]
    assert view["shares"] is None


def test_editing_the_bill_after_locking_unlocks_it(client, split):
    body, ana, ben = split
    claim_everything(client, body, ana, ben)
    assert get_view(client, body)["locked"] is True

    client.patch(
        f"/sessions/{body['session_id']}",
        json={"tip_minor": 100, "total_minor": 5050},
        headers=host(body),
    )

    view = get_view(client, body)
    assert view["blockers"] == ["The host needs to mark the split ready again."]
    assert view["shares"] is None

    make_ready(client, body)
    assert get_view(client, body)["blockers"] == ["Ana has not confirmed.", "Ben has not confirmed."]


# Host releasing a name

def test_released_name_keeps_its_claims_and_rejoins_the_same_slot(client, split):
    body, ana, ben = split
    claim_everything(client, body, ana, ben)
    sid = body["session_id"]

    resp = client.post(f"/sessions/{sid}/members/{ben['member_id']}/release", headers=host(body))

    assert resp.status_code == 200
    view = resp.json()
    assert member_of(view, "Ben")["joined"] is False
    assert member_of(view, "Ben")["confirmation"] == "none"
    assert item_of(view, "Steak")["claims"] == [
        {"member_id": ben["member_id"], "name": "Ben", "quantity": 2}
    ]
    assert view["blockers"] == ["Ben has claims but has not rejoined."]
    assert view["shares"] is None
    # The old token stops working.
    assert client.get(f"/sessions/{sid}/me", headers=member_headers(ben)).status_code == 403

    rejoined = join(client, body, "ben")

    assert rejoined["member_id"] == ben["member_id"]
    assert rejoined["member_token"] != ben["member_token"]
    assert item_of(get_view(client, body), "Steak")["claims"][0]["quantity"] == 2
    confirm(client, body, rejoined)
    assert get_view(client, body)["locked"] is True


def test_release_needs_a_joined_guest_and_the_host_token(client, split):
    body, ana, _ = split
    sid = body["session_id"]
    jack_slot = member_of(get_view(client, body), "Jack")["id"]

    assert client.post(
        f"/sessions/{sid}/members/{jack_slot}/release", headers=host(body)
    ).status_code == 409
    assert client.post(
        f"/sessions/{sid}/members/{ana['member_id']}/release", headers=member_headers(ana)
    ).status_code == 401
    assert client.post(
        f"/sessions/{sid}/members/999999/release", headers=host(body)
    ).status_code == 404


# Host unlocking a guest

def test_unlock_asks_a_guest_to_confirm_again(client, split):
    body, ana, ben = split
    claim_everything(client, body, ana, ben)

    resp = client.post(
        f"/sessions/{body['session_id']}/members/{ana['member_id']}/unlock", headers=host(body)
    )

    assert resp.status_code == 200
    view = resp.json()
    assert member_of(view, "Ana")["confirmation"] == "none"
    assert item_of(view, "Salad")["claims"][0]["quantity"] == 1
    assert view["blockers"] == ["Ana has not confirmed."]
    assert view["locked"] is False
