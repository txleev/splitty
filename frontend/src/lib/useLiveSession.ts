import { useCallback, useEffect, useState } from 'react'
import type { Session } from '../api/types'

// Close code the server uses when a split is unknown or expired.
const GONE_CODE = 4404
const MAX_RETRY_MS = 10_000

export type LiveState = 'connecting' | 'live' | 'reconnecting' | 'gone'

type ServerMessage =
  | { type: 'snapshot'; session: Session }
  | { type: 'gone' }
  | { type: 'ping' }

function socketUrl(sessionId: string): string {
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${scheme}://${window.location.host}/api/ws/sessions/${encodeURIComponent(sessionId)}`
}

function parseMessage(data: unknown): ServerMessage | null {
  if (typeof data !== 'string') {
    return null
  }
  try {
    return JSON.parse(data) as ServerMessage
  } catch {
    return null
  }
}

/**
 * Keeps a split up to date. The server sends a full snapshot on connect and after every change,
 * so each snapshot replaces the last one. A dropped connection is retried with a growing delay.
 */
export function useLiveSession(sessionId: string) {
  const [session, setSession] = useState<Session | null>(null)
  const [state, setState] = useState<LiveState>('connecting')

  useEffect(() => {
    let socket: WebSocket | null = null
    let retryTimer: number | undefined
    let attempts = 0
    let stopped = false

    const connect = () => {
      socket = new WebSocket(socketUrl(sessionId))

      socket.onopen = () => {
        attempts = 0
      }
      socket.onmessage = (event) => {
        const message = parseMessage(event.data)
        if (message?.type === 'snapshot') {
          setSession(message.session)
          setState('live')
        } else if (message?.type === 'gone') {
          setState('gone')
        }
      }
      socket.onclose = (event) => {
        if (stopped) {
          return
        }
        if (event.code === GONE_CODE) {
          setState('gone')
          return
        }
        setState('reconnecting')
        retryTimer = window.setTimeout(connect, Math.min(1000 * 2 ** attempts, MAX_RETRY_MS))
        attempts += 1
      }
    }

    connect()
    return () => {
      stopped = true
      window.clearTimeout(retryTimer)
      socket?.close()
    }
  }, [sessionId])

  // A reply to one of this page's own requests is a fresh copy of the split, so it can be shown
  // straight away. The socket's next snapshot brings everyone else's changes.
  const applySession = useCallback((next: Session) => setSession(next), [])

  return { session, state, applySession }
}
