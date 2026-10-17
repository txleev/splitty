# Splitty

Split a restaurant bill without the arithmetic. The host photographs a receipt, Splitty reads it, and everyone at the table claims what they ate from their own phone. Each person sees their exact share, tax and tip included, and pays the host through Revolut or Wise.

Built for the Wise hackathon.

## How it works

1. **Host uploads a receipt photo** (with an optional note such as "Jack and I had the salad"). OCR and an LLM turn it into line items, tax, tip and total.
2. **Host reviews the bill.** They fix anything the OCR got wrong, add a payment handle, and mark the split ready. The page shows a guest link and QR code.
3. **Guests open the link**, join under a name, claim items, and confirm. Shared dishes can be split equally, optionally among a fixed number of people.
4. **Everyone sees live updates.** Shares are calculated exactly: tax and tip follow each guest's subtotal, and rounding never loses a cent.
5. **Guests pay** with a deep link to the host's Revolut or Wise handle and mark their share as paid. The host can also mark cash payments.

Sessions need no accounts. Access is by random tokens kept in the browser, and a session expires after 7 days without activity.

## Architecture

```
 Browser (React) ──/api──▶ backend (FastAPI) ──▶ PostgreSQL
                              │   ▲                 │
                              │   └─ LISTEN/NOTIFY ─┘   live snapshots over WebSocket
                              ▼
                        ocr-mvp (FastAPI)
                        PaddleOCR + Groq LLM
```

| Directory                  | What it is                                                         | Docs                                |
|----------------------------|--------------------------------------------------------------------|-------------------------------------|
| [frontend/](frontend/)     | Mobile-first React 19 + Vite + TypeScript app (host and guest UI). | [frontend/README.md](frontend/README.md) |
| [backend/](backend/)       | Room API: sessions, claims, shares, payments, WebSocket live view. | [backend/README.md](backend/README.md)   |
| [ocr-mvp/](ocr-mvp/)       | Receipt OCR (PaddleOCR) and structuring (Groq). Also holds the Docker Compose stack. | [ocr-mvp/README.md](ocr-mvp/README.md) |

## Quick start

You need Docker, Node.js, and a [Groq](https://console.groq.com) API key.

**1. Configure and start the backend stack** (database, OCR service, Room API):

```bash
cd ocr-mvp
cp .env.example .env      # set UID, GID (`id -u`, `id -g`) and GROQ_API_KEY
docker compose up -d --build
```

The first start downloads the PaddleOCR models into `ocr-mvp/models/`, which can take a few minutes. The OCR service refuses to start without `GROQ_API_KEY`.

| Service  | URL                     |
|----------|-------------------------|
| OCR      | http://localhost:8000   |
| Room API | http://127.0.0.1:8001   |
| Postgres | `127.0.0.1:5432` (user, password and database all `splitty`) |

**2. Start the frontend:**

```bash
cd frontend
npm install
npm run dev               # http://127.0.0.1:5173
```

The dev server proxies `/api/*` (including the WebSocket) to the Room API. Set `SPLITTY_API` to point it elsewhere.

Open http://127.0.0.1:5173, upload a receipt, and share the guest link. On a phone, use the machine's LAN address instead of `127.0.0.1`.

## Payments and currencies

The host enters one payment handle and picks a platform, **Revolut** or **Wise**. Guests get a payment link when the split's currency is **EUR, GBP, USD or HUF**. Receipts that write forint as "Ft" are treated as HUF. For other currencies, guests see their amount to pay manually.

The link parameters (amount and currency) have not been verified against live Revolut and Wise accounts. The page therefore also shows the amount so guests can paste it.

## Testing

```bash
# backend: needs the db container; uses a separate splitty_test database
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q

# frontend
cd frontend
npm test            # Vitest
npm run lint        # oxlint
npm run build       # type-check and build

# OCR service 
cd ocr-mvp
python -m venv .venv && .venv/bin/pip install -r requirements.txt pytest httpx
.venv/bin/python -m pytest tests -q
```

## Known limitations

- **Not production-ready.** The Room API is bound to localhost only, with no auth or rate limiting beyond session tokens.
- **Live viewers are capped.** Each open WebSocket holds one Postgres connection (default limit 100). A shared listener is planned.
- **Tokens live in the browser.** A lost host token cannot be recovered. A guest who loses their browser needs the host to release their name.
- **Whole-unit claims only.** An item with a fractional quantity cannot be claimed, except with "Split equally".
- **Production build wiring is missing.** `/api` and WebSocket upgrades must be served from the same origin as the frontend. This is part of the deployment phase.

## Privacy

Receipts can contain personal data. Use synthetic or redacted receipts for testing, and never commit `.env` files or API keys. Both are covered by `.gitignore`.
