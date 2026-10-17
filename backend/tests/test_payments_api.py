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
    """A ready split with two guests. The receipt has Salad (1) and Steak (2)."""
    body = new_session(client)
    make_ready(client, body)
    return body, join(client, body, "Ana"), join(client, body, "Ben")


def item_id(client, body, name):
    return item_of(get_view(client, body), name)["id"]


def lock(client, body, ana, ben):
    claim(client, body, item_id(client, body, "Salad"), 1, ana)
    claim(client, body, item_id(client, body, "Steak"), 2, ben)
    confirm(client, body, ana)
    confirm(client, body, ben)


def share_of(view, name):
    return next(s for s in view["shares"] if s["name"] == name)


def mark_my_paid(client, body, member, paid=True):
    return client.put(
        f"/sessions/{body['session_id']}/me/paid",
        json={"paid": paid},
        headers=member_headers(member),
    )


def mark_member_paid(client, body, member_id, paid=True):
    return client.put(
        f"/sessions/{body['session_id']}/members/{member_id}/paid",
        json={"paid": paid},
        headers=host(body),
    )


def patch_bill(client, body, changes):
    return client.patch(f"/sessions/{body['session_id']}", json=changes, headers=host(body))


# Marking shares paid

def test_every_share_starts_unpaid(client, split):
    body, ana, ben = split
    lock(client, body, ana, ben)

    view = get_view(client, body)

    assert [s["payment"] for s in view["shares"]] == ["unpaid", "unpaid"]


def test_a_guest_marks_only_their_own_share_paid(client, split):
    body, ana, ben = split
    lock(client, body, ana, ben)

    resp = mark_my_paid(client, body, ana)

    assert resp.status_code == 200
    assert share_of(resp.json(), "Ana")["payment"] == "paid"
    assert share_of(resp.json(), "Ben")["payment"] == "unpaid"


def test_a_guest_can_take_their_mark_back(client, split):
    body, ana, ben = split
    lock(client, body, ana, ben)
    mark_my_paid(client, body, ana)

    view = mark_my_paid(client, body, ana, paid=False).json()

    assert share_of(view, "Ana")["payment"] == "unpaid"


def test_paying_needs_a_locked_split_but_unmarking_does_not(client, split):
    body, ana, _ = split
    claim(client, body, item_id(client, body, "Salad"), 1, ana)

    resp = mark_my_paid(client, body, ana)

    assert resp.status_code == 409
    assert resp.json()["detail"] == (
        "Shares are not final yet. Payments open once the split is locked."
    )
    assert mark_my_paid(client, body, ana, paid=False).status_code == 200


def test_recording_a_payment_keeps_the_split_locked(client, split):
    body, ana, ben = split
    lock(client, body, ana, ben)

    mark_my_paid(client, body, ana)

    view = get_view(client, body)
    assert view["locked"] is True
    assert view["blockers"] == []


def test_a_moved_share_shows_as_changed_until_paid_again(client, split):
    body, ana, ben = split
    lock(client, body, ana, ben)
    mark_my_paid(client, body, ana)

    # A new tip moves every total, so the bill goes back to draft and everyone confirms again.
    patch_bill(client, body, {"tip_minor": 100, "total_minor": 5050})
    make_ready(client, body)
    confirm(client, body, ana)
    confirm(client, body, ben)

    view = get_view(client, body)
    assert view["locked"] is True
    assert share_of(view, "Ana")["payment"] == "changed"

    view = mark_my_paid(client, body, ana).json()

    assert share_of(view, "Ana")["payment"] == "paid"


def test_the_host_marks_any_joined_guest_paid_for_cash(client, split):
    body, ana, ben = split
    lock(client, body, ana, ben)

    view = mark_member_paid(client, body, ben["member_id"]).json()

    assert share_of(view, "Ben")["payment"] == "paid"


def test_a_guest_token_cannot_use_the_host_route(client, split):
    body, ana, ben = split
    lock(client, body, ana, ben)

    resp = client.put(
        f"/sessions/{body['session_id']}/members/{ben['member_id']}/paid",
        json={"paid": True},
        headers=member_headers(ana),
    )

    assert resp.status_code == 401


def test_an_unjoined_name_has_no_share_to_pay(client, split):
    body, ana, ben = split
    lock(client, body, ana, ben)
    jack_slot = member_of(get_view(client, body), "Jack")["id"]

    resp = mark_member_paid(client, body, jack_slot)

    assert resp.status_code == 409
    assert resp.json()["detail"] == "This name has not joined, so it has no share to pay."


# Payment handle and platform

def test_the_handle_is_saved_with_its_platform_without_resetting_the_draft(client, split):
    body, _, _ = split

    resp = patch_bill(
        client, body, {"host_payment_handle": "@ana.k", "host_payment_platform": "revolut"}
    )

    assert resp.status_code == 200
    view = resp.json()
    assert view["host_payment_handle"] == "ana.k"
    assert view["host_payment_platform"] == "revolut"
    assert view["status"] == "ready"


def test_a_handle_without_a_platform_is_refused(client, split):
    body, _, _ = split

    resp = patch_bill(client, body, {"host_payment_handle": "ana.k"})

    assert resp.status_code == 422
    assert resp.json()["detail"] == "Choose Revolut or Wise for this handle."


def test_clearing_the_handle_clears_the_platform_too(client, split):
    body, _, _ = split
    patch_bill(client, body, {"host_payment_handle": "ana", "host_payment_platform": "wise"})

    view = patch_bill(client, body, {"host_payment_handle": ""}).json()

    assert view["host_payment_handle"] is None
    assert view["host_payment_platform"] is None


@pytest.mark.parametrize(
    "handle",
    ["revolut.me/ana", "ana?amount=5", "ana/../x", "an a", "https://wise.com/pay/me/ana", "-ana"],
)
def test_handles_that_are_not_usernames_are_refused(client, split, handle):
    body, _, _ = split

    resp = patch_bill(client, body, {"host_payment_handle": handle, "host_payment_platform": "wise"})

    assert resp.status_code == 422


def test_an_unknown_platform_is_refused(client, split):
    body, _, _ = split

    resp = patch_bill(client, body, {"host_payment_handle": "ana", "host_payment_platform": "paypal"})

    assert resp.status_code == 422
