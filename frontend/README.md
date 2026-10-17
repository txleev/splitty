# Splitty frontend

Mobile-first React app (Vite, TypeScript). Hosts review a receipt and share a link. Guests join, claim items, and confirm. Everyone sees live updates.

## Run

The backend must be running. In the compose stack it is on `http://127.0.0.1:8001`.

```bash
npm install
npm run dev        # http://127.0.0.1:5173
```

The dev server forwards `/api/*` to the backend, including the WebSocket, with the `/api` prefix removed. Point it somewhere else with `SPLITTY_API`:

```bash
SPLITTY_API=http://127.0.0.1:8001 npm run dev
```

## Scripts

| Command           | What it does                                  |
|-------------------|-----------------------------------------------|
| `npm run dev`     | Dev server with hot reload and the API proxy. |
| `npm run build`   | Type-checks, then builds to `dist/`.          |
| `npm run preview` | Serves `dist/` locally.                       |
| `npm test`        | Unit and component tests (Vitest, jsdom).     |
| `npm run lint`    | oxlint.                                       |

## Pages

- `/`: upload a receipt photo with an optional note. Creates a split and opens the host page.
- `/s/:id/host`: host review. Edit the bill and items, add or release guests, mark the split ready. Shows the guest link.
- `/s/:id`: guest page. Join from the open names or type a new one. Set claims, confirm them, and pay as soon as they have confirmed. The full "who pays what" table appears once the split locks.

## Layout

- `src/api/`: request helper (`client.ts`), endpoint functions (`sessions.ts`), types that mirror `backend/schemas.py`.
- `src/lib/`: money and quantity parsing, claim maths, token storage, the live WebSocket hook (`useLiveSession.ts`), and the request state hook (`useAction.ts`).
- `src/pages/`: the three routes.
- `src/host/`, `src/guest/`: panels for each side.
- `src/components/`: shared pieces such as notices, the shares table, and the live badge.

## Things to know

- Tokens are kept in this browser's `localStorage`: the host token under `splitty.host.<id>`, a guest's seat under `splitty.seat.<id>`. The server keeps only hashes. A lost host token cannot be recovered, and a guest who loses their browser needs the host to release their name.
- Amounts are typed as decimals and sent as integers in minor units. `1 799,50` and `1799.5` both work.
- Guests' estimated subtotals are rounded per line, so they can differ from the final shares by a cent. The page labels them as estimates.
- A claim is a whole number of units. An item with a fractional quantity (such as 0.5) cannot be claimed, so the split cannot lock until it is changed.
- The host can tick "Split equally" on an item. Guests then tick "I'm in" instead of using the stepper, and everyone who joined pays the same share of the line. The host can also set the number of people, so each share is fixed up front and guests do not have to wait for each other. The quantity is ignored, so a fractional quantity is fine. Changing the tick clears that item's claims.
- The production build expects the same origin to serve `/api` and to pass WebSocket upgrades through to the backend. That wiring belongs to the deployment phase.
