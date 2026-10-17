import threading
import time

import psycopg
import pytest
from starlette.websockets import WebSocketDisconnect

from helpers import (
    TEST_URL,
    claim,
    get_view,
    host,
    item_of,
    join,
    make_ready,
    new_session,
)


@pytest.fixture
def ready(client, fake_ocr, clean_db):
    """A ready split with one guest, Ana. The receipt has Salad (1) and Steak (2)."""
    body = new_session(client)
    make_ready(client, body)
    return body, join(client, body, "Ana")


def receive(ws, timeout=5):
    """Next message from the socket. TestClient cannot time out a receive, so use a thread."""
    box = {}

    def run():
        try:
            box["message"] = ws.receive_json()
        except Exception as error:
            box["error"] = error

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout)
    assert box, f"no message within {timeout} seconds"
    if "error" in box:
        raise box["error"]
    return box["message"]


def receive_until(ws, predicate, limit=5):
    for _ in range(limit):
        message = receive(ws)
        if predicate(message):
            return message
    raise AssertionError("no matching snapshot arrived")


def has_claim_on(name):
    def predicate(message):
        return message["type"] == "snapshot" and item_of(message["session"], name)["remaining"] == 0

    return predicate


def listener_count():
    with psycopg.connect(TEST_URL) as conn:
        return conn.execute(
            "select count(*) from pg_stat_activity "
            "where datname = current_database() and query = 'LISTEN session_changes'"
        ).fetchone()[0]


def salad_id(client, body):
    return item_of(get_view(client, body), "Salad")["id"]


# Sockets

def test_a_socket_gets_a_snapshot_on_connect(client, ready):
    body, _ = ready

    with client.websocket_connect(f"/ws/sessions/{body['session_id']}") as ws:
        message = receive(ws)

    assert message["type"] == "snapshot"
    assert message["session"]["session_id"] == body["session_id"]
    assert item_of(message["session"], "Salad")["remaining"] == 1


def test_a_claim_reaches_every_open_socket(client, ready):
    body, ana = ready
    url = f"/ws/sessions/{body['session_id']}"

    with client.websocket_connect(url) as guest_ws, client.websocket_connect(url) as host_ws:
        receive(guest_ws)
        receive(host_ws)
        claim(client, body, salad_id(client, body), 1, ana)

        assert receive_until(guest_ws, has_claim_on("Salad"))["session"]["session_id"] == body["session_id"]
        assert receive_until(host_ws, has_claim_on("Salad"))


def test_reading_the_split_sends_no_snapshot(client, ready):
    body, ana = ready

    with client.websocket_connect(f"/ws/sessions/{body['session_id']}") as ws:
        receive(ws)
        client.get(f"/sessions/{body['session_id']}")
        claim(client, body, salad_id(client, body), 1, ana)

        # The first snapshot after the GET must already show the claim.
        assert item_of(receive(ws)["session"], "Salad")["remaining"] == 0


def test_a_closed_socket_releases_its_listener(client, ready):
    body, _ = ready
    before = listener_count()

    with client.websocket_connect(f"/ws/sessions/{body['session_id']}") as ws:
        receive(ws)
        assert listener_count() == before + 1

    deadline = time.monotonic() + 5
    while listener_count() > before and time.monotonic() < deadline:
        time.sleep(0.1)
    assert listener_count() == before


def test_an_unknown_split_closes_the_socket(client, clean_db):
    with client.websocket_connect("/ws/sessions/doesnotexist") as ws:
        assert receive(ws) == {"type": "gone"}
        with pytest.raises(WebSocketDisconnect) as closed:
            receive(ws)

    assert closed.value.code == 4404


def test_an_expired_split_closes_the_socket(client, ready):
    body, _ = ready
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(
            "update sessions set last_active_at = now() - interval '8 days' where id = %s",
            (body["session_id"],),
        )

    with client.websocket_connect(f"/ws/sessions/{body['session_id']}") as ws:
        assert receive(ws) == {"type": "gone"}
        with pytest.raises(WebSocketDisconnect) as closed:
            receive(ws)

    assert closed.value.code == 4404


# What the database announces

def notifications_during(listener, action):
    action()
    return [n.payload for n in listener.notifies(timeout=0.5)]


def test_each_kind_of_change_notifies_its_split(client, ready):
    body, ana = ready
    sid = body["session_id"]
    steak = item_of(get_view(client, body), "Steak")["id"]

    with psycopg.connect(TEST_URL, autocommit=True) as listener:
        listener.execute("LISTEN session_changes")
        rename = notifications_during(
            listener,
            lambda: client.patch(
                f"/sessions/{sid}/items/{steak}", json={"name": "Beef"}, headers=host(body)
            ),
        )
        bill = notifications_during(
            listener,
            lambda: client.patch(f"/sessions/{sid}", json={"tip_minor": 0}, headers=host(body)),
        )
        new_member = notifications_during(
            listener,
            lambda: client.post(f"/sessions/{sid}/members", json={"name": "Ben"}, headers=host(body)),
        )
        claimed = notifications_during(
            listener, lambda: claim(client, body, salad_id(client, body), 1, ana)
        )

    assert rename == [sid]
    assert bill == [sid]
    assert new_member == [sid]
    assert claimed == [sid]


def test_reading_the_split_notifies_nobody(client, ready):
    body, _ = ready

    with psycopg.connect(TEST_URL, autocommit=True) as listener:
        listener.execute("LISTEN session_changes")
        read = notifications_during(listener, lambda: client.get(f"/sessions/{body['session_id']}"))

    assert read == []
