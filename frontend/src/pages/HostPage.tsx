import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'
import { GuestQrCode } from '../components/GuestQrCode'
import { SessionGone } from '../components/SessionGone'
import { LiveBadge, Notice, Pill } from '../components/ui'
import { BillForm } from '../host/BillForm'
import { FinishCard } from '../host/FinishCard'
import { GuestsPanel } from '../host/GuestsPanel'
import { ItemEditor } from '../host/ItemEditor'
import { PaymentsPanel } from '../host/PaymentsPanel'
import type { Session } from '../api/types'
import { loadHostToken } from '../lib/storage'
import { useLiveSession } from '../lib/useLiveSession'

export function HostPage() {
  const { sessionId = '' } = useParams()
  // Keyed by id so a different split never reuses this one's token or socket.
  return <HostView key={sessionId} sessionId={sessionId} />
}

function HostView({ sessionId }: { sessionId: string }) {
  const location = useLocation()
  const { session, state, applySession } = useLiveSession(sessionId)
  const [hostToken] = useState<string | null>(() => {
    // Storage first. The navigation state covers a browser that blocks storage on this visit.
    const fromState = (location.state as { hostToken?: unknown } | null)?.hostToken
    return loadHostToken(sessionId) ?? (typeof fromState === 'string' ? fromState : null)
  })

  if (state === 'gone') {
    return <SessionGone />
  }
  if (!session) {
    return <Notice>Loading the split…</Notice>
  }
  if (!hostToken) {
    return (
      <section className="card stack">
        <h1>Host access needed</h1>
        <p className="muted">
          Only the browser that created this split can manage it. You can still open the guest page
          to join and claim items.
        </p>
        <Link to={`/s/${sessionId}`} className="btn btn-primary">
          Open the guest page
        </Link>
      </section>
    )
  }

  const guestUrl = `${window.location.origin}/s/${session.session_id}`

  return (
    <>
      <section className="card stack">
        <div className="row between">
          <h1>Review the bill</h1>
          <div className="row">
            <Pill tone={session.status === 'ready' ? 'ok' : 'warn'}>
              {session.status === 'ready' ? 'Ready' : 'Draft'}
            </Pill>
            <LiveBadge state={state} />
          </div>
        </div>
        <label className="field">
          <span>Guest link</span>
          <input readOnly value={guestUrl} onFocus={(event) => event.currentTarget.select()} />
        </label>
        <div className="row">
          <CopyButton text={guestUrl} />
          <Link to={`/s/${session.session_id}`}>Open the guest page</Link>
        </div>
        <GuestQrCode value={guestUrl} />
      </section>

      {session.warnings.length > 0 && (
        <Notice tone="warn">
          <strong>Check these against the receipt</strong>
          <ul>
            {session.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </Notice>
      )}

      <BillForm
        key={billKey(session)}
        session={session}
        hostToken={hostToken}
        applySession={applySession}
      />
      <ItemEditor session={session} hostToken={hostToken} applySession={applySession} />
      <GuestsPanel session={session} hostToken={hostToken} applySession={applySession} />
      <FinishCard session={session} hostToken={hostToken} applySession={applySession} />
      {session.locked && session.shares && (
        <PaymentsPanel
          sessionId={session.session_id}
          currency={session.currency}
          shares={session.shares}
          hostToken={hostToken}
          applySession={applySession}
        />
      )}
    </>
  )
}

// The bill form resets whenever the saved bill changes, so it never shows stale values.
function billKey(session: Session): string {
  return JSON.stringify([
    session.currency,
    session.subtotal_minor,
    session.tax_minor,
    session.tip_minor,
    session.total_minor,
    session.host_payment_handle,
    session.host_payment_platform,
  ])
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
    } catch {
      // Clipboard access is blocked on some plain-http pages. The link field can still be selected.
      setCopied(false)
    }
  }

  return (
    <button type="button" className="btn btn-small" onClick={() => void copy()}>
      {copied ? 'Copied' : 'Copy link'}
    </button>
  )
}
