from datetime import timedelta

import psycopg
from psycopg import sql
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from errors import ApiError
from ids import hash_token, new_session_id, new_token
from money import format_minor, to_minor
from schemas import (
    ItemIn,
    ItemOut,
    JoinOut,
    MemberOut,
    ParsedReceipt,
    SessionCreated,
    SessionView,
)

# A session is removed after this much time without activity. Phase 8 adds the cleanup job.
SESSION_IDLE_TTL = timedelta(hours=24)

NOT_FOUND = "This split does not exist or has expired."
NOT_READY = "The split is not ready yet. Ask the host to finish it."
NAME_TAKEN = "That name has already joined. Pick a different name."

# Changing one of these can break the totals check, so the split goes back to draft.
BILL_FIELDS = {"currency", "subtotal_minor", "tax_minor", "tip_minor", "total_minor"}
SESSION_FIELDS = BILL_FIELDS | {"host_payment_handle"}
NON_EMPTY_ITEM_FIELDS = {"name", "quantity", "total_minor"}
# Editing an item field clears the parser's "missing" flag for it. The keys match structure.py.
MISSING_KEY = {"quantity": "qty", "unit_price_minor": "unit_price", "total_minor": "total_price"}


def clean_text(value: str) -> str:
    return " ".join(value.split())


def _required_name(raw: str) -> str:
    name = clean_text(raw)
    if not name:
        raise ApiError(422, "Name cannot be empty")
    return name


def _row(conn: psycopg.Connection, query: str, params=()):
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(query, params).fetchone()


def _rows(conn: psycopg.Connection, query: str, params=()):
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(query, params).fetchall()


def find_problems(
    *,
    items: list[ItemOut],
    currency: str | None,
    subtotal_minor: int | None,
    tax_minor: int | None,
    tip_minor: int | None,
    total_minor: int | None,
) -> list[str]:
    """What stops the host from marking the split ready. An empty list means it can be shared."""
    problems = []
    if not items:
        problems.append("The receipt has no items.")
    for item in items:
        if item.missing:
            problems.append(f"'{item.name}' is missing: {', '.join(item.missing)}.")
    if not currency:
        problems.append("Currency is not set.")
    if subtotal_minor is None:
        problems.append("Subtotal is not set.")
    if total_minor is None:
        problems.append("Total is not set.")
    if subtotal_minor is not None:
        items_sum = sum(item.total_minor for item in items)
        if items_sum != subtotal_minor:
            problems.append(
                f"Items add up to {format_minor(items_sum)} "
                f"but the subtotal is {format_minor(subtotal_minor)}."
            )
    if subtotal_minor is not None and total_minor is not None:
        expected = subtotal_minor + (tax_minor or 0) + (tip_minor or 0)
        if expected != total_minor:
            problems.append(
                f"Subtotal, tax and tip add up to {format_minor(expected)} "
                f"but the total is {format_minor(total_minor)}."
            )
    return problems


def _read_view(conn: psycopg.Connection, session_id: str) -> SessionView:
    head = _row(
        conn,
        """
        select status, last_active_at, currency, subtotal_minor, tax_minor, tip_minor,
               total_minor, warnings, host_payment_handle
        from sessions where id = %s
        """,
        (session_id,),
    )
    items = [
        ItemOut(
            id=r["id"],
            position=r["position"],
            name=r["name"],
            quantity=float(r["quantity"]),
            unit_price_minor=r["unit_price_minor"],
            total_minor=r["total_minor"],
            missing=r["missing"],
            preassigned_names=r["preassigned_names"],
        )
        for r in _rows(
            conn,
            """
            select id, position, name, quantity, unit_price_minor, total_minor,
                   missing, preassigned_names
            from session_items where session_id = %s order by position
            """,
            (session_id,),
        )
    ]
    members = [
        MemberOut(id=r["id"], name=r["name"], joined=r["joined"])
        for r in _rows(
            conn,
            "select id, name, token_hash is not null as joined "
            "from members where session_id = %s order by id",
            (session_id,),
        )
    ]
    return SessionView(
        session_id=session_id,
        status=head["status"],
        expires_at=head["last_active_at"] + SESSION_IDLE_TTL,
        currency=head["currency"],
        subtotal_minor=head["subtotal_minor"],
        tax_minor=head["tax_minor"],
        tip_minor=head["tip_minor"],
        total_minor=head["total_minor"],
        warnings=head["warnings"],
        host_payment_handle=head["host_payment_handle"],
        items=items,
        members=members,
        problems=find_problems(
            items=items,
            currency=head["currency"],
            subtotal_minor=head["subtotal_minor"],
            tax_minor=head["tax_minor"],
            tip_minor=head["tip_minor"],
            total_minor=head["total_minor"],
        ),
    )


def _select_active(conn: psycopg.Connection, session_id: str, lock: bool = False) -> dict:
    """Return the session's host token hash and status. A session idle too long counts as gone."""
    query = (
        "select host_token_hash, status from sessions "
        "where id = %s and last_active_at > now() - %s"
    )
    if lock:
        query += " for update"
    row = _row(conn, query, (session_id, SESSION_IDLE_TTL))
    if row is None:
        raise ApiError(404, NOT_FOUND)
    return row


def _touch(conn: psycopg.Connection, session_id: str) -> None:
    conn.execute("update sessions set last_active_at = now() where id = %s", (session_id,))


def _require_host(conn: psycopg.Connection, session_id: str, host_token: str | None) -> None:
    # Locking the row also serializes host edits with joins and with marking the split ready.
    session = _select_active(conn, session_id, lock=True)
    if not host_token:
        raise ApiError(401, "Host token is required")
    if hash_token(host_token) != session["host_token_hash"]:
        raise ApiError(403, "Wrong host token")
    _touch(conn, session_id)


def _reset_draft(conn: psycopg.Connection, session_id: str) -> None:
    conn.execute("update sessions set status = 'draft' where id = %s", (session_id,))


def _unique_names(raw_names) -> list[str]:
    seen = {}
    for raw in raw_names:
        name = clean_text(raw)
        if name and name.casefold() not in seen:
            seen[name.casefold()] = name
    return list(seen.values())


def create_session(conn: psycopg.Connection, receipt: ParsedReceipt) -> SessionCreated:
    session_id = new_session_id()
    host_token = new_token()

    with conn.transaction():
        conn.execute(
            """
            insert into sessions (
                id, host_token_hash, currency,
                subtotal_minor, tax_minor, tip_minor, total_minor, warnings
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session_id,
                hash_token(host_token),
                receipt.currency,
                to_minor(receipt.subtotal),
                to_minor(receipt.tax),
                to_minor(receipt.tip),
                to_minor(receipt.total),
                receipt.warnings,
            ),
        )
        for position, item in enumerate(receipt.items, start=1):
            conn.execute(
                """
                insert into session_items (
                    session_id, position, name, quantity, unit_price_minor, total_minor,
                    missing, preassigned_names
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session_id,
                    position,
                    item.name,
                    item.qty,
                    to_minor(item.unit_price),
                    to_minor(item.total_price),
                    item.missing,
                    item.assigned_to,
                ),
            )
        # Names the note assigned become member slots that guests can claim.
        for name in _unique_names(n for item in receipt.items for n in item.assigned_to):
            conn.execute(
                "insert into members (session_id, name) values (%s, %s)", (session_id, name)
            )
        view = _read_view(conn, session_id)

    return SessionCreated(**view.model_dump(), host_token=host_token)


def get_view(conn: psycopg.Connection, session_id: str) -> SessionView:
    with conn.transaction():
        _select_active(conn, session_id)
        _touch(conn, session_id)
        return _read_view(conn, session_id)


def update_session(
    conn: psycopg.Connection, session_id: str, host_token: str | None, changes: dict
) -> SessionView:
    changes = dict(changes)
    for field in ("currency", "host_payment_handle"):
        if field in changes:
            changes[field] = clean_text(changes[field] or "") or None

    with conn.transaction():
        _require_host(conn, session_id, host_token)
        if changes:
            assert set(changes) <= SESSION_FIELDS
            assignments = sql.SQL(", ").join(
                sql.SQL("{} = %s").format(sql.Identifier(field)) for field in changes
            )
            conn.execute(
                sql.SQL("update sessions set {} where id = %s").format(assignments),
                [*changes.values(), session_id],
            )
            if BILL_FIELDS & changes.keys():
                _reset_draft(conn, session_id)
        return _read_view(conn, session_id)


def add_item(
    conn: psycopg.Connection, session_id: str, host_token: str | None, item: ItemIn
) -> SessionView:
    with conn.transaction():
        _require_host(conn, session_id, host_token)
        position = _row(
            conn,
            "select coalesce(max(position), 0) + 1 as next_position "
            "from session_items where session_id = %s",
            (session_id,),
        )["next_position"]
        conn.execute(
            """
            insert into session_items (session_id, position, name, quantity, unit_price_minor, total_minor)
            values (%s, %s, %s, %s, %s, %s)
            """,
            (
                session_id,
                position,
                _required_name(item.name),
                item.quantity,
                item.unit_price_minor,
                item.total_minor,
            ),
        )
        _reset_draft(conn, session_id)
        return _read_view(conn, session_id)


def update_item(
    conn: psycopg.Connection,
    session_id: str,
    item_id: int,
    host_token: str | None,
    changes: dict,
) -> SessionView:
    changes = dict(changes)
    with conn.transaction():
        _require_host(conn, session_id, host_token)
        if _row(
            conn,
            "select id from session_items where id = %s and session_id = %s",
            (item_id, session_id),
        ) is None:
            raise ApiError(404, "Item not found")
        for field in NON_EMPTY_ITEM_FIELDS & changes.keys():
            if changes[field] is None:
                raise ApiError(422, f"{field} cannot be empty")
        if "name" in changes:
            changes["name"] = _required_name(changes["name"])
        if changes:
            cleared = [MISSING_KEY[f] for f in changes if f in MISSING_KEY]
            assignments = [sql.SQL("{} = %s").format(sql.Identifier(f)) for f in changes]
            assignments.append(
                sql.SQL(
                    "missing = array(select m from unnest(missing) as m "
                    "where m <> all(%s::text[]))"
                )
            )
            conn.execute(
                sql.SQL("update session_items set {} where id = %s and session_id = %s").format(
                    sql.SQL(", ").join(assignments)
                ),
                [*changes.values(), cleared, item_id, session_id],
            )
            _reset_draft(conn, session_id)
        return _read_view(conn, session_id)


def delete_item(
    conn: psycopg.Connection, session_id: str, item_id: int, host_token: str | None
) -> SessionView:
    with conn.transaction():
        _require_host(conn, session_id, host_token)
        deleted = conn.execute(
            "delete from session_items where id = %s and session_id = %s", (item_id, session_id)
        ).rowcount
        if deleted == 0:
            raise ApiError(404, "Item not found")
        _reset_draft(conn, session_id)
        return _read_view(conn, session_id)


def add_member(
    conn: psycopg.Connection, session_id: str, host_token: str | None, raw_name: str
) -> SessionView:
    with conn.transaction():
        _require_host(conn, session_id, host_token)
        name = _required_name(raw_name)
        try:
            # Nested transaction: a duplicate name rolls back only this insert.
            with conn.transaction():
                conn.execute(
                    "insert into members (session_id, name) values (%s, %s)", (session_id, name)
                )
        except UniqueViolation:
            raise ApiError(409, "A member with this name already exists")
        return _read_view(conn, session_id)


def remove_member(
    conn: psycopg.Connection, session_id: str, host_token: str | None, member_id: int
) -> SessionView:
    with conn.transaction():
        _require_host(conn, session_id, host_token)
        member = _row(
            conn,
            "select token_hash from members where id = %s and session_id = %s",
            (member_id, session_id),
        )
        if member is None:
            raise ApiError(404, "Member not found")
        if member["token_hash"] is not None:
            raise ApiError(409, "This guest has already joined and cannot be removed")
        conn.execute("delete from members where id = %s", (member_id,))
        return _read_view(conn, session_id)


def mark_ready(conn: psycopg.Connection, session_id: str, host_token: str | None) -> SessionView:
    with conn.transaction():
        _require_host(conn, session_id, host_token)
        view = _read_view(conn, session_id)
        if view.problems:
            raise ApiError(
                409,
                {"message": "The split cannot be shared yet.", "problems": view.problems},
            )
        conn.execute("update sessions set status = 'ready' where id = %s", (session_id,))
        return _read_view(conn, session_id)


def join(conn: psycopg.Connection, session_id: str, raw_name: str) -> JoinOut:
    name = _required_name(raw_name)
    member_token = new_token()
    try:
        with conn.transaction():
            session = _select_active(conn, session_id, lock=True)
            _touch(conn, session_id)
            if session["status"] != "ready":
                raise ApiError(409, NOT_READY)

            # Case-insensitive, so "jack" takes the "Jack" slot the note created.
            member = _row(
                conn,
                "select id, name, token_hash from members "
                "where session_id = %s and lower(name) = lower(%s) for update",
                (session_id, name),
            )
            if member is None:
                member = _row(
                    conn,
                    """
                    insert into members (session_id, name, token_hash, joined_at)
                    values (%s, %s, %s, now())
                    returning id, name
                    """,
                    (session_id, name, hash_token(member_token)),
                )
            elif member["token_hash"] is None:
                conn.execute(
                    "update members set token_hash = %s, joined_at = now() where id = %s",
                    (hash_token(member_token), member["id"]),
                )
            else:
                raise ApiError(409, NAME_TAKEN)
    except UniqueViolation:
        # Two guests typed the same new name at the same moment.
        raise ApiError(409, NAME_TAKEN)

    return JoinOut(member_id=member["id"], name=member["name"], member_token=member_token)
