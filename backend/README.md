# Splitty backend

Room API. Receipts become sessions. Hosts review the bill, then guests join and claim.

## Endpoints

Base URL in the compose stack: `http://127.0.0.1:8001`.

| Method | Path                                   | Who       | Body                              | Notes                                          |
|--------|----------------------------------------|-----------|-----------------------------------|------------------------------------------------|
| GET    | `/health`                              | anyone    | —                                 |                                                |
| POST   | `/sessions`                            | anyone    | multipart `file` (image), `note`  | Creates a draft. Returns `host_token` once.    |
| GET    | `/sessions/{id}`                       | anyone    | —                                 | Current state. Also refreshes the 7-day timer. |
| PATCH  | `/sessions/{id}`                       | host      | `currency`, `subtotal_minor`, `tax_minor`, `tip_minor`, `total_minor`, `host_payment_handle`, `host_payment_platform` | Editing the bill makes it a draft again. The handle and platform go together. |
| POST   | `/sessions/{id}/items`                 | host      | `name`, `quantity`, `unit_price_minor`, `total_minor` |                                    |
| PATCH  | `/sessions/{id}/items/{item_id}`       | host      | any item field                    | Setting a field clears its `missing` flag.     |
| DELETE | `/sessions/{id}/items/{item_id}`       | host      | —                                 |                                                |
| POST   | `/sessions/{id}/members`               | host      | `name`                            | Adds a slot guests can claim.                  |
| DELETE | `/sessions/{id}/members/{member_id}`   | host      | —                                 | Only for slots nobody has joined.              |
| POST   | `/sessions/{id}/members/{member_id}/release` | host | —                             | Frees a joined name so that guest can rejoin. Their claims stay. |
| POST   | `/sessions/{id}/members/{member_id}/unlock`  | host | —                             | Clears a guest's confirmation so they check again. |
| POST   | `/sessions/{id}/ready`                 | host      | —                                 | `409` with `problems` if the bill doesn't check out. |
| POST   | `/sessions/{id}/join`                  | guest     | `name`                            | Needs a ready split. Returns `member_token` once. |
| GET    | `/sessions/{id}/me`                    | guest     | —                                 | Who this token belongs to, and its confirmation state. |
| PUT    | `/sessions/{id}/items/{item_id}/claim` | guest     | `quantity` (whole number, 0 removes) | Sets this guest's total for the item. Safe to repeat. |
| POST   | `/sessions/{id}/confirm`               | guest     | —                                 | Confirms current claims. Always allowed to repeat. |
| PUT    | `/sessions/{id}/me/paid`               | guest     | `paid` (bool)                     | Marks this guest's share as paid, or unmarks it. Marking needs this guest to have confirmed. |
| PUT    | `/sessions/{id}/members/{member_id}/paid` | host   | `paid` (bool)                     | Same, for any joined guest, for example a cash payment. |
| WS     | `/ws/sessions/{id}`                    | anyone    | —                                 | Live view. Sends a snapshot on connect and after every change. |

### Live updates

- Each message is `{"type": "snapshot", "session": {...}}`, with the same shape as `GET /sessions/{id}`. Replace the whole state each time. There is no event replay, so a reconnecting client just takes the next snapshot.
- Every 25 seconds the server sends `{"type": "ping"}`. Clients can ignore it. It also checks that the split still exists.
- When the split is unknown or expired, the server sends `{"type": "gone"}` and closes with code `4404`.
- Changes reach the server through PostgreSQL `LISTEN/NOTIFY`. Triggers in migration `004` send the split id after each commit. Reading a split does not wake other viewers.
- Each open socket holds one database connection. PostgreSQL allows 100 by default, so this limits the number of live viewers. Phase 8 should add a shared listener.

- Host actions send the token in the `X-Host-Token` header. Guest actions send `X-Member-Token`.
- Claims stay attached to their item when the host edits it. If a quantity drops below what guests claimed, the item is over-claimed (`remaining` < 0). Affected guests can't confirm until they lower their claims.
- A confirmation becomes `needs_reconfirm` when the amounts change after the guest confirmed. Changing a claim clears the confirmation.
- An item with `split_equally: true` is claimed with `quantity` 1 (join) or 0 (leave). An optional `split_count` (2 to 100) fixes how many people share it: each pays total ÷ count even before all have joined, joining stops when every spot is taken, and the item locks only when all spots are filled. Without it, whoever joins splits the line. Everyone who joined pays an equal share of the line total, and it counts as claimed once one guest is in. Changing the flag deletes that item's claims.
- A split locks when every item is fully claimed, every joined guest has confirmed the current bill, and the bill adds up. `blockers` lists what is still missing.
- `shares` holds the exact amounts of each joined guest who has confirmed the current bill. A guest does not wait for the others: their share appears, and they can pay, as soon as they confirm. It is `null` while the bill is a draft or does not add up. `locked` still means everything is claimed and everyone has confirmed.
- A guest's part of a line is their claimed quantity over the line quantity, times the line total. Units nobody has claimed yet stay unclaimed instead of raising the other guests' parts. Tax and tip follow each guest's subtotal against the whole bill, so a guest's amount does not move while others choose (an equal split still moves as people join, and the guest sees "changed" if they had paid). Once everything is claimed the shares add up to the total. Rounding goes to the largest remainders, and ties go to the earlier joiner.
- Releasing a name is for guests who lost their browser. The old token stops working, the claims stay, and rejoining with the same name takes the same slot back.
- Payments: each share has a `payment` of `unpaid`, `paid` or `changed`. Marking a share paid stores the exact amount owed at that moment. If the share moves later, the status becomes `changed` until the guest pays and marks it again. Payments do not affect locking.
- The payment handle is a username or tag with no spaces, slashes or links. It is stored with its platform, `revolut` or `wise`.
- Amounts are integers in minor units (`1450` = 14.50).
- A session expires after 7 days without activity. Unknown and expired sessions both return `404` with the same message.
- A split can be shared only when every check passes: items have no missing fields, the currency and total are set, items add up to the subtotal, and subtotal + tax + tip = total.

## Run

The backend runs in the compose stack in `../ocr-mvp`. It needs the `db` and `ocr` services:

```bash
cd ../ocr-mvp && docker compose up -d --build backend
```

## Tests

The tests need the `db` container running. They use a separate database, `splitty_test`, which is created automatically. The OCR call is faked, so no API calls are made.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

## Layout

- `main.py`: routes, startup migrations, and error responses.
- `sessions.py`: all session logic (create, edit, ready check, join) and the expiry rule.
- `ocr_client.py`: calls `ocr-mvp /parse`.
- `schemas.py`: request and response models.
- `shares.py`: splits a bill into each guest's share, with exact rounding.
- `live.py`: the WebSocket endpoint, which listens for changes and pushes snapshots.
- `money.py`, `ids.py`, `errors.py`: minor units, IDs and token hashing, and the error type.
- `db.py`, `migrations/`: connection and SQL migrations, applied in order at startup.
