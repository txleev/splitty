# Splitty backend

Room API. Receipts become sessions. Hosts review the bill, then guests join and claim.

## Endpoints

Base URL in the compose stack: `http://127.0.0.1:8001`.

| Method | Path                                   | Who       | Body                              | Notes                                          |
|--------|----------------------------------------|-----------|-----------------------------------|------------------------------------------------|
| GET    | `/health`                              | anyone    | —                                 |                                                |
| POST   | `/sessions`                            | anyone    | multipart `file` (image), `note`  | Creates a draft. Returns `host_token` once.    |
| GET    | `/sessions/{id}`                       | anyone    | —                                 | Current state. Also refreshes the 24-hour timer. |
| PATCH  | `/sessions/{id}`                       | host      | `currency`, `subtotal_minor`, `tax_minor`, `tip_minor`, `total_minor`, `host_payment_handle` | Editing the bill makes it a draft again. |
| POST   | `/sessions/{id}/items`                 | host      | `name`, `quantity`, `unit_price_minor`, `total_minor` |                                    |
| PATCH  | `/sessions/{id}/items/{item_id}`       | host      | any item field                    | Setting a field clears its `missing` flag.     |
| DELETE | `/sessions/{id}/items/{item_id}`       | host      | —                                 |                                                |
| POST   | `/sessions/{id}/members`               | host      | `name`                            | Adds a slot guests can claim.                  |
| DELETE | `/sessions/{id}/members/{member_id}`   | host      | —                                 | Only for slots nobody has joined.              |
| POST   | `/sessions/{id}/ready`                 | host      | —                                 | `409` with `problems` if the bill doesn't check out. |
| POST   | `/sessions/{id}/join`                  | guest     | `name`                            | Needs a ready split. Returns `member_token` once. |

- Host actions send the token in the `X-Host-Token` header.
- Amounts are integers in minor units (`1450` = 14.50).
- Unknown and expired sessions both return `404` with the same message.
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
- `money.py`, `ids.py`, `errors.py`: minor units, IDs and token hashing, and the error type.
- `db.py`, `migrations/`: connection and SQL migrations, applied in order at startup.
