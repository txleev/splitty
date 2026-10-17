// Tokens stay in this browser. The server keeps only their hashes, so a lost host token cannot be
// recovered. Storage can be blocked (for example in private windows), so every access is guarded.

export interface Seat {
  memberId: number
  name: string
  token: string
}

const hostKey = (sessionId: string) => `splitty.host.${sessionId}`
const seatKey = (sessionId: string) => `splitty.seat.${sessionId}`

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) {
      window.localStorage.removeItem(key)
    } else {
      window.localStorage.setItem(key, value)
    }
  } catch {
    // Storage is unavailable. The page keeps working for this visit, but the token is not kept.
  }
}

export function saveHostToken(sessionId: string, token: string): void {
  write(hostKey(sessionId), token)
}

export function loadHostToken(sessionId: string): string | null {
  return read(hostKey(sessionId))
}

export function saveSeat(sessionId: string, seat: Seat): void {
  write(seatKey(sessionId), JSON.stringify(seat))
}

export function loadSeat(sessionId: string): Seat | null {
  const raw = read(seatKey(sessionId))
  if (!raw) {
    return null
  }
  try {
    const seat = JSON.parse(raw) as Partial<Seat>
    const valid =
      typeof seat.memberId === 'number' &&
      typeof seat.name === 'string' &&
      typeof seat.token === 'string'
    return valid ? (seat as Seat) : null
  } catch {
    return null
  }
}

export function clearSeat(sessionId: string): void {
  write(seatKey(sessionId), null)
}
