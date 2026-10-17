import type { ReactNode } from 'react'
import type { ApiError } from '../api/client'
import type { LiveState } from '../lib/useLiveSession'

export type Tone = 'info' | 'ok' | 'warn' | 'error'

export function Notice({ tone = 'info', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div className={`notice notice-${tone}`} role={tone === 'error' ? 'alert' : undefined}>
      {children}
    </div>
  )
}

/** Shows a failed request: its message, then the lines that say what to fix. */
export function ErrorNotice({ error }: { error: ApiError | null }) {
  if (!error) {
    return null
  }
  return (
    <Notice tone="error">
      <p>{error.message}</p>
      {error.details.length > 0 && (
        <ul>
          {error.details.map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ul>
      )}
    </Notice>
  )
}

export function Pill({ tone = 'info', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}

const LIVE_LABELS: Record<LiveState, { text: string; tone: Tone }> = {
  connecting: { text: 'Connecting…', tone: 'info' },
  live: { text: 'Live', tone: 'ok' },
  reconnecting: { text: 'Reconnecting…', tone: 'warn' },
  gone: { text: 'Expired', tone: 'error' },
}

export function LiveBadge({ state }: { state: LiveState }) {
  const { text, tone } = LIVE_LABELS[state]
  return <Pill tone={tone}>{text}</Pill>
}
