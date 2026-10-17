import copy

import psycopg

from helpers import FAKE_RECEIPT, TEST_URL, host, make_ready, new_session


def members_by_name(view):
    return {m["name"]: m for m in view["members"]}


# Reading the session

def test_get_returns_items_members_and_no_problems(client, fake_ocr, clean_db):
    body = new_session(client, note="Jack and I had the salad")

    view = client.get(f"/sessions/{body['session_id']}").json()

    assert view["status"] == "draft"
    assert [m["name"] for m in view["members"]] == ["Jack"]
    assert view["members"][0]["joined"] is False
    assert view["problems"] == []
    assert "host_token" not in view


def test_unknown_session_is_404(client, clean_db):
    resp = client.get("/sessions/doesnotexist")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "This split does not exist or has expired."


def test_idle_session_is_gone_for_guests_and_host(client, fake_ocr, clean_db):
    body = new_session(client)
    sid = body["session_id"]
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(
            "update sessions set last_active_at = now() - interval '8 days' where id = %s",
            (sid,),
        )

    assert client.get(f"/sessions/{sid}").status_code == 404
    assert client.patch(f"/sessions/{sid}", json={"tip_minor": 0}, headers=host(body)).status_code == 404
    assert client.post(f"/sessions/{sid}/join", json={"name": "Jack"}).status_code == 404


def test_a_week_of_inactivity_is_still_alive(client, fake_ocr, clean_db):
    body = new_session(client)
    sid = body["session_id"]
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(
            "update sessions set last_active_at = now() - interval '6 days 23 hours' where id = %s",
            (sid,),
        )

    assert client.get(f"/sessions/{sid}").status_code == 200


def test_reading_the_session_keeps_it_alive(client, fake_ocr, clean_db):
    body = new_session(client)
    sid = body["session_id"]
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(
            "update sessions set last_active_at = now() - interval '1 day' where id = %s",
            (sid,),
        )

    view = client.get(f"/sessions/{sid}").json()

    assert view["expires_at"] > body["expires_at"]


# Host token

def test_host_actions_need_the_host_token(client, fake_ocr, clean_db):
    body = new_session(client)
    sid = body["session_id"]

    assert client.patch(f"/sessions/{sid}", json={"tip_minor": 100}).status_code == 401
    wrong = client.patch(
        f"/sessions/{sid}", json={"tip_minor": 100}, headers={"X-Host-Token": "wrong"}
    )
    assert wrong.status_code == 403


def test_guest_token_cannot_act_as_host(client, fake_ocr, clean_db):
    body = new_session(client)
    sid = body["session_id"]
    make_ready(client, body)
    joined = client.post(f"/sessions/{sid}/join", json={"name": "Maria"}).json()

    resp = client.patch(
        f"/sessions/{sid}", json={"tip_minor": 100}, headers={"X-Host-Token": joined["member_token"]}
    )

    assert resp.status_code == 403


# Editing the bill

def test_editing_totals_sends_the_split_back_to_draft(client, fake_ocr, clean_db):
    body = new_session(client)
    make_ready(client, body)
    sid = body["session_id"]

    resp = client.patch(
        f"/sessions/{sid}", json={"tip_minor": 100, "total_minor": 5050}, headers=host(body)
    )

    assert resp.json()["status"] == "draft"
    assert resp.json()["tip_minor"] == 100
    assert client.post(f"/sessions/{sid}/ready", headers=host(body)).status_code == 200


def test_changing_only_the_payment_handle_keeps_the_split_ready(client, fake_ocr, clean_db):
    body = new_session(client)
    make_ready(client, body)

    resp = client.patch(
        f"/sessions/{body['session_id']}",
        json={"host_payment_handle": "  jack-host  ", "host_payment_platform": "revolut"},
        headers=host(body),
    )

    assert resp.json()["status"] == "ready"
    assert resp.json()["host_payment_handle"] == "jack-host"
    assert resp.json()["host_payment_platform"] == "revolut"


def test_ready_reports_totals_that_do_not_add_up(client, fake_ocr, clean_db):
    body = new_session(client)
    sid = body["session_id"]
    client.patch(f"/sessions/{sid}", json={"total_minor": 5000}, headers=host(body))

    resp = client.post(f"/sessions/{sid}/ready", headers=host(body))

    assert resp.status_code == 409
    assert resp.json()["detail"]["problems"] == [
        "Subtotal, tax and tip add up to 49.50 but the total is 50.00."
    ]


def test_ready_blocks_missing_fields_until_the_host_fixes_them(client, monkeypatch, clean_db):
    receipt = copy.deepcopy(FAKE_RECEIPT)
    receipt["items"][1]["missing"] = ["qty"]
    monkeypatch.setattr("main.parse_receipt", lambda *a, **k: copy.deepcopy(receipt))
    body = new_session(client)
    sid = body["session_id"]

    blocked = client.post(f"/sessions/{sid}/ready", headers=host(body))
    assert blocked.json()["detail"]["problems"] == ["'Steak' is missing: qty."]

    steak_id = body["items"][1]["id"]
    client.patch(f"/sessions/{sid}/items/{steak_id}", json={"quantity": 2}, headers=host(body))

    assert client.post(f"/sessions/{sid}/ready", headers=host(body)).status_code == 200


def test_items_can_be_added_renamed_and_deleted(client, fake_ocr, clean_db):
    body = new_session(client)
    sid = body["session_id"]

    added = client.post(
        f"/sessions/{sid}/items",
        json={"name": "Tea", "quantity": 1, "total_minor": 300},
        headers=host(body),
    ).json()
    assert added["items"][-1]["name"] == "Tea"
    assert added["items"][-1]["position"] == 3
    tea_id = added["items"][-1]["id"]

    renamed = client.patch(
        f"/sessions/{sid}/items/{tea_id}", json={"name": "  Green   tea "}, headers=host(body)
    ).json()
    assert renamed["items"][-1]["name"] == "Green tea"

    deleted = client.delete(f"/sessions/{sid}/items/{tea_id}", headers=host(body)).json()
    assert len(deleted["items"]) == 2
    assert client.delete(f"/sessions/{sid}/items/{tea_id}", headers=host(body)).status_code == 404


def test_items_cannot_be_blanked_or_nulled(client, fake_ocr, clean_db):
    body = new_session(client)
    sid = body["session_id"]
    item_id = body["items"][0]["id"]

    assert client.patch(
        f"/sessions/{sid}/items/{item_id}", json={"total_minor": None}, headers=host(body)
    ).status_code == 422
    assert client.patch(
        f"/sessions/{sid}/items/{item_id}", json={"name": "   "}, headers=host(body)
    ).status_code == 422


def test_editing_an_unknown_item_is_404(client, fake_ocr, clean_db):
    body = new_session(client)

    resp = client.patch(
        f"/sessions/{body['session_id']}/items/999999", json={"name": "x"}, headers=host(body)
    )

    assert resp.status_code == 404


# Members and joining

def test_join_needs_a_ready_split(client, fake_ocr, clean_db):
    body = new_session(client, note="Jack and I had the salad")

    resp = client.post(f"/sessions/{body['session_id']}/join", json={"name": "Jack"})

    assert resp.status_code == 409
    assert "not ready" in resp.json()["detail"]


def test_guest_takes_the_note_slot_ignoring_case(client, fake_ocr, clean_db):
    body = new_session(client, note="Jack and I had the salad")
    sid = body["session_id"]
    make_ready(client, body)

    resp = client.post(f"/sessions/{sid}/join", json={"name": "  jack "})

    assert resp.status_code == 201
    joined = resp.json()
    assert joined["name"] == "Jack"
    assert len(joined["member_token"]) > 20
    assert members_by_name(client.get(f"/sessions/{sid}").json())["Jack"] == {
        "id": joined["member_id"],
        "name": "Jack",
        "joined": True,
        "confirmation": "none",
    }
    assert client.post(f"/sessions/{sid}/join", json={"name": "JACK"}).status_code == 409


def test_member_token_is_stored_only_as_a_hash(client, fake_ocr, clean_db):
    body = new_session(client, note="Jack and I had the salad")
    make_ready(client, body)
    joined = client.post(f"/sessions/{body['session_id']}/join", json={"name": "Jack"}).json()

    with psycopg.connect(TEST_URL) as conn:
        (stored,) = conn.execute(
            "select token_hash from members where id = %s", (joined["member_id"],)
        ).fetchone()
    assert stored is not None
    assert stored != joined["member_token"]


def test_guest_can_join_with_a_new_name(client, fake_ocr, clean_db):
    body = new_session(client)
    sid = body["session_id"]
    make_ready(client, body)

    resp = client.post(f"/sessions/{sid}/join", json={"name": "Maria"})

    assert resp.status_code == 201
    assert members_by_name(client.get(f"/sessions/{sid}").json())["Maria"]["joined"] is True


def test_blank_join_name_is_rejected(client, fake_ocr, clean_db):
    body = new_session(client)
    make_ready(client, body)

    resp = client.post(f"/sessions/{body['session_id']}/join", json={"name": "   "})

    assert resp.status_code == 422


def test_host_adds_and_removes_unjoined_members(client, fake_ocr, clean_db):
    body = new_session(client, note="Jack and I had the salad")
    sid = body["session_id"]

    added = client.post(
        f"/sessions/{sid}/members", json={"name": "Aigerim"}, headers=host(body)
    ).json()
    assert [m["name"] for m in added["members"]] == ["Jack", "Aigerim"]
    aigerim_id = added["members"][1]["id"]

    duplicate = client.post(f"/sessions/{sid}/members", json={"name": "jack"}, headers=host(body))
    assert duplicate.status_code == 409

    removed = client.delete(f"/sessions/{sid}/members/{aigerim_id}", headers=host(body))
    assert removed.status_code == 200
    assert [m["name"] for m in removed.json()["members"]] == ["Jack"]


def test_host_cannot_remove_a_member_who_has_joined(client, fake_ocr, clean_db):
    body = new_session(client, note="Jack and I had the salad")
    sid = body["session_id"]
    make_ready(client, body)
    jack = client.post(f"/sessions/{sid}/join", json={"name": "Jack"}).json()

    resp = client.delete(f"/sessions/{sid}/members/{jack['member_id']}", headers=host(body))

    assert resp.status_code == 409
