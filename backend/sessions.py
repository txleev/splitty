from datetime import timedelta

import psycopg
from psycopg import sql
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from errors import ApiError
from ids import hash_token, new_session_id, new_token
from money import format_minor, to_minor
from schemas import (
    ClaimOut,
    Confirmation,
    ItemIn,
    ItemOut,
    JoinOut,
    MeOut,
    MemberOut,
    ParsedReceipt,
    SessionCreated,
    SessionView,
    ShareOut,
)
from shares import compute_shares

# A session is removed after this much time without activity. Phase 8 adds the cleanup job.
SESSION_IDLE_TTL = timedelta(days=7)

NOT_FOUND = "This split does not exist or has expired."
NOT_READY = "The split is not ready yet. Ask the host to finish it."
NAME_TAKEN = "That name has already joined. Pick a different name."

# Changing one of these can break the totals check, so the split goes back to draft.
BILL_FIELDS = {"currency", "subtotal_minor", "tax_minor", "tip_minor", "total_minor"}
SESSION_FIELDS = BILL_FIELDS | {"host_payment_handle"}
NON_EMPTY_ITEM_FIELDS = {"name", "quantity", "total_minor"}
# Renaming an item does not change what anyone owes. Every other item field does.
NAME_ONLY = {"name"}
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
        if item.quantity <= 0:
            # Such a line could never be claimed, so its amount would be lost from the shares.
            problems.append(f"'{item.name}' has no quantity. Set it to 1 or more.")
        elif not item.quantity.is_integer():
            problems.append(
                f"'{item.name}' has quantity {item.quantity:g}. Claims need whole numbers: "
                "set the quantity to 1 and enter the line total."
            )
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


def _confirmation(confirmed_version: int | None, bill_version: int) -> Confirmation:
    if confirmed_version is None:
        return "none"
    return "confirmed" if confirmed_version == bill_version else "needs_reconfirm"


def find_blockers(
    *,
    status: str,
    problems: list[str],
    items: list[ItemOut],
    members: list[MemberOut],
) -> list[str]:
    """What stops the split from locking. An empty list means every share is final."""
    if problems:
        return ["The bill does not add up yet. Fix the problems above."]
    if status != "ready":
        return ["The host needs to mark the split ready again."]

    blockers = []
    joined = [m for m in members if m.joined]
    if not joined:
        blockers.append("No guests have joined yet.")
    for item in items:
        if item.remaining > 0:
            blockers.append(f"{item.name} has {item.remaining:g} unclaimed.")
        elif item.remaining < 0:
            blockers.append(f"{item.name} is over-claimed.")

    # A released name keeps its claims. Until someone rejoins it, its share has no payer.
    claimant_ids = {claim.member_id for item in items for claim in item.claims}
    for member in members:
        if not member.joined and member.id in claimant_ids:
            blockers.append(f"{member.name} has claims but has not rejoined.")
    for member in joined:
        if member.confirmation != "confirmed":
            blockers.append(f"{member.name} has not confirmed.")
    return blockers


def _shares_out(
    items: list[ItemOut],
    members: list[MemberOut],
    tax_minor: int | None,
    tip_minor: int | None,
) -> list[ShareOut]:
    joined = [m for m in members if m.joined]
    shares = compute_shares(
        items=[(item.total_minor, {c.member_id: c.quantity for c in item.claims}) for item in items],
        member_ids=[m.id for m in joined],
        tax_minor=tax_minor or 0,
        tip_minor=tip_minor or 0,
    )
    return [
        ShareOut(
            member_id=m.id,
            name=m.name,
            subtotal_minor=shares[m.id].subtotal,
            tax_minor=shares[m.id].tax,
            tip_minor=shares[m.id].tip,
            total_minor=shares[m.id].total,
        )
        for m in joined
    ]


def _read_view(conn: psycopg.Connection, session_id: str) -> SessionView:
    head = _row(
        conn,
        """
        select status, last_active_at, bill_version, currency, subtotal_minor, tax_minor,
               tip_minor, total_minor, warnings, host_payment_handle
        from sessions where id = %s
        """,
        (session_id,),
    )

    claims_by_item: dict[int, list[ClaimOut]] = {}
    for r in _rows(
        conn,
        """
        select c.item_id, c.member_id, m.name, c.quantity
        from claims c join members m on m.id = c.member_id
        where m.session_id = %s order by m.id
        """,
        (session_id,),
    ):
        claims_by_item.setdefault(r["item_id"], []).append(
            ClaimOut(member_id=r["member_id"], name=r["name"], quantity=r["quantity"])
        )

    items = []
    for r in _rows(
        conn,
        """
        select id, position, name, quantity, unit_price_minor, total_minor,
               missing, preassigned_names
        from session_items where session_id = %s order by position
        """,
        (session_id,),
    ):
        claims = claims_by_item.get(r["id"], [])
        quantity = float(r["quantity"])
        items.append(
            ItemOut(
                id=r["id"],
                position=r["position"],
                name=r["name"],
                quantity=quantity,
                unit_price_minor=r["unit_price_minor"],
                total_minor=r["total_minor"],
                missing=r["missing"],
                preassigned_names=r["preassigned_names"],
                remaining=quantity - sum(c.quantity for c in claims),
                claims=claims,
            )
        )

    members = [
        MemberOut(
            id=r["id"],
            name=r["name"],
            joined=r["joined"],
            confirmation=_confirmation(r["confirmed_bill_version"], head["bill_version"]),
        )
        for r in _rows(
            conn,
            "select id, name, token_hash is not null as joined, confirmed_bill_version "
            "from members where session_id = %s order by id",
            (session_id,),
        )
    ]

    problems = find_problems(
        items=items,
        currency=head["currency"],
        subtotal_minor=head["subtotal_minor"],
        tax_minor=head["tax_minor"],
        tip_minor=head["tip_minor"],
        total_minor=head["total_minor"],
    )
    blockers = find_blockers(
        status=head["status"], problems=problems, items=items, members=members
    )
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
        problems=problems,
        locked=not blockers,
        blockers=blockers,
        shares=(
            _shares_out(items, members, head["tax_minor"], head["tip_minor"])
            if not blockers
            else None
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


# Lock order everywhere: the session row first, then item rows. Taking them in the same
# order in every request is what prevents deadlocks.
def _require_host(conn: psycopg.Connection, session_id: str, host_token: str | None) -> None:
    session = _select_active(conn, session_id, lock=True)
    if not host_token:
        raise ApiError(401, "Host token is required")
    if hash_token(host_token) != session["host_token_hash"]:
        raise ApiError(403, "Wrong host token")
    _touch(conn, session_id)


def _require_member(conn: psycopg.Connection, session_id: str, member_token: str | None) -> dict:
    _select_active(conn, session_id, lock=True)
    if not member_token:
        raise ApiError(401, "Member token is required")
    member = _row(
        conn,
        "select id, name from members where session_id = %s and token_hash = %s",
        (session_id, hash_token(member_token)),
    )
    if member is None:
        raise ApiError(403, "Unknown member token")
    _touch(conn, session_id)
    return member


def _reset_draft(conn: psycopg.Connection, session_id: str) -> None:
    conn.execute("update sessions set status = 'draft' where id = %s", (session_id,))


def _bump_bill(conn: psycopg.Connection, session_id: str) -> None:
    conn.execute("update sessions set bill_version = bill_version + 1 where id = %s", (session_id,))


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


def read_snapshot(conn: psycopg.Connection, session_id: str) -> SessionView:
    """The current state without refreshing the idle timer. Live connections use this."""
    with conn.transaction():
        _select_active(conn, session_id)
        return _read_view(conn, session_id)


def check_alive(conn: psycopg.Connection, session_id: str) -> None:
    """Raise 404 if the split has expired. Does not refresh the idle timer."""
    with conn.transaction():
        _select_active(conn, session_id)


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
                _bump_bill(conn, session_id)
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
        _bump_bill(conn, session_id)
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
            # The item keeps its id, so its claims stay. Only the amounts change what people owe.
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
            if changes.keys() - NAME_ONLY:
                _bump_bill(conn, session_id)
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
        # Deleting the item also deletes its claims (cascade), so affected guests must confirm again.
        _reset_draft(conn, session_id)
        _bump_bill(conn, session_id)
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


def _host_member(conn: psycopg.Connection, session_id: str, member_id: int) -> dict:
    member = _row(
        conn,
        "select id, token_hash from members where id = %s and session_id = %s for update",
        (member_id, session_id),
    )
    if member is None:
        raise ApiError(404, "Member not found")
    return member


def release_member(
    conn: psycopg.Connection, session_id: str, host_token: str | None, member_id: int
) -> SessionView:
    """Free a joined guest's name so they can rejoin, for example after clearing their browser.

    Their claims stay on the name. Their old token stops working, and rejoining with the same
    name takes the same slot back.
    """
    with conn.transaction():
        _require_host(conn, session_id, host_token)
        member = _host_member(conn, session_id, member_id)
        if member["token_hash"] is None:
            raise ApiError(409, "This name has not joined, so there is nothing to release")
        conn.execute(
            "update members set token_hash = null, joined_at = null, "
            "confirmed_bill_version = null where id = %s",
            (member_id,),
        )
        return _read_view(conn, session_id)


def unlock_member(
    conn: psycopg.Connection, session_id: str, host_token: str | None, member_id: int
) -> SessionView:
    """Clear a guest's confirmation so they check their choices again. Their claims stay."""
    with conn.transaction():
        _require_host(conn, session_id, host_token)
        _host_member(conn, session_id, member_id)
        conn.execute(
            "update members set confirmed_bill_version = null where id = %s", (member_id,)
        )
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


def get_me(conn: psycopg.Connection, session_id: str, member_token: str | None) -> MeOut:
    """Lets a guest who comes back to the page find their own name and confirmation state."""
    with conn.transaction():
        member = _require_member(conn, session_id, member_token)
        state = _row(
            conn,
            """
            select m.confirmed_bill_version, s.bill_version
            from members m join sessions s on s.id = m.session_id
            where m.id = %s
            """,
            (member["id"],),
        )
        return MeOut(
            member_id=member["id"],
            name=member["name"],
            confirmation=_confirmation(state["confirmed_bill_version"], state["bill_version"]),
        )


def set_claim(
    conn: psycopg.Connection,
    session_id: str,
    member_token: str | None,
    item_id: int,
    quantity: int,
) -> SessionView:
    """Set this guest's claim on an item to `quantity`. Zero removes the claim."""
    with conn.transaction():
        member = _require_member(conn, session_id, member_token)
        # Lock the item so two guests can't both take the last portion.
        item = _row(
            conn,
            "select id, name, quantity from session_items "
            "where id = %s and session_id = %s for update",
            (item_id, session_id),
        )
        if item is None:
            raise ApiError(404, "Item not found")

        current = _row(
            conn,
            "select quantity from claims where member_id = %s and item_id = %s",
            (member["id"], item_id),
        )
        current_quantity = current["quantity"] if current else 0
        if current_quantity == quantity:
            return _read_view(conn, session_id)

        taken_by_others = _row(
            conn,
            "select coalesce(sum(quantity), 0) as taken from claims "
            "where item_id = %s and member_id <> %s",
            (item_id, member["id"]),
        )["taken"]
        left = item["quantity"] - taken_by_others
        if quantity > 0 and quantity > left:
            raise ApiError(409, f"Only {float(max(left, 0)):g} left of {item['name']}.")

        if quantity == 0:
            conn.execute(
                "delete from claims where member_id = %s and item_id = %s",
                (member["id"], item_id),
            )
        else:
            conn.execute(
                """
                insert into claims (member_id, item_id, quantity) values (%s, %s, %s)
                on conflict (member_id, item_id) do update set quantity = excluded.quantity
                """,
                (member["id"], item_id, quantity),
            )
        # A changed choice has to be confirmed again.
        conn.execute(
            "update members set confirmed_bill_version = null where id = %s", (member["id"],)
        )
        return _read_view(conn, session_id)


def confirm(conn: psycopg.Connection, session_id: str, member_token: str | None) -> SessionView:
    """Confirm this guest's claims against the current bill. Confirming again is always allowed."""
    with conn.transaction():
        member = _require_member(conn, session_id, member_token)
        view = _read_view(conn, session_id)

        if view.problems:
            raise ApiError(
                409,
                {
                    "message": "The host is still fixing the bill. Confirm once it adds up.",
                    "problems": view.problems,
                },
            )
        over_claimed = [
            item.name
            for item in view.items
            if item.remaining < 0 and any(c.member_id == member["id"] for c in item.claims)
        ]
        if over_claimed:
            raise ApiError(
                409,
                {
                    "message": "Some of your claims no longer fit the bill. "
                    "Lower them and confirm again.",
                    "items": over_claimed,
                },
            )

        bill_version = _row(
            conn, "select bill_version from sessions where id = %s", (session_id,)
        )["bill_version"]
        conn.execute(
            "update members set confirmed_bill_version = %s where id = %s",
            (bill_version, member["id"]),
        )
        return _read_view(conn, session_id)
