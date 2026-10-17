# OCR MVP

Receipt OCR service. It runs PaddleOCR on a receipt image and, through Groq, turns the text into structured JSON.

## Endpoints

| Method | Path      | Input                                   | Output                                        |
|--------|-----------|-----------------------------------------|-----------------------------------------------|
| GET    | `/health` | —                                       | `{"status": "ok"}`                            |
| POST   | `/ocr`    | multipart `file` (image)                | per-line text, score, box, and grouped rows   |
| POST   | `/parse`  | multipart `file` (image), optional `note` | structured receipt (items, tax, tip, total) |

`/ocr` is Step 1 (OCR only). `/parse` runs Step 1 and Step 2 together.

## Setup

1. Copy `.env.example` to `.env` and fill in `UID`, `GID` and `GROQ_API_KEY`.
2. Start the service:

   ```bash
   docker compose up --build
   ```

   The first start downloads the PaddleOCR models into `./models`. This can take a few minutes.
   The service refuses to start if `GROQ_API_KEY` is empty.

## Database (PostgreSQL)

No configuration is needed. The defaults are user `splitty`, password `splitty`, database `splitty`, port `5432`.

```bash
docker compose up -d db                              # start only the database
docker compose exec db psql -U splitty -d splitty    # open a psql shell
```

Connection string for app code running on the host:

```
postgresql://splitty:splitty@localhost:5432/splitty
```

The port is bound to `127.0.0.1`, so other machines cannot connect. Data lives in the Docker volume `pgdata`
and survives `docker compose down` and restarts. To wipe it, run `docker compose down -v`. This also stops the OCR service.

## Examples

```bash
# Step 1: OCR only
curl -F "file=@receipt.jpeg" http://localhost:8000/ocr

# Steps 1 + 2: structured receipt, with an optional note about who ordered what
curl -F "file=@receipt.jpeg" -F "note=Jack and I had the salad" http://localhost:8000/parse
```

## Local development

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt pytest httpx
.venv/bin/python -m pytest tests -q
```

`run_ocr.py <image>` runs OCR on one file and writes the result to `output/`.

## Layout

- `server.py`: FastAPI app and endpoints.
- `ocr_core.py`: PaddleOCR setup and conversion of results to `{text, score, box}`.
- `lines.py`: groups OCR cells into visual rows (`"item | price"`).
- `structure.py`: Groq call, JSON schema validation, and total checks.
- `tests/`: unit tests for grouping and structuring. Groq is faked, so no key is needed.

## Notes

- Receipts can contain customers' personal data. Use synthetic or redacted samples when testing.
- Totals that don't add up produce `warnings` in the response, not an error.
