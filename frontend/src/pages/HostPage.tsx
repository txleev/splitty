import { useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'
import { SessionGone } from '../components/SessionGone'
import { Notice } from '../components/ui'
import { BillForm } from '../host/BillForm'
import { FinishCard } from '../host/FinishCard'
import { GuestsPanel } from '../host/GuestsPanel'
import { ItemEditor } from '../host/ItemEditor'
import { PaymentsPanel } from '../host/PaymentsPanel'
import { ShareCard } from '../host/ShareCard'
import type { Session } from '../api/types'
import { formatMoney } from '../lib/money'
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
      <header className="hero">
        <p className="eyebrow">Check &amp; share</p>
        <h1 className="display">Your receipt, decoded.</h1>
        <p className="lead">
          {session.items.length} {session.items.length === 1 ? 'item' : 'items'}
          {session.total_minor !== null && ` · ${formatMoney(session.total_minor, session.currency)}`}
        </p>
      </header>

      <ShareCard guestUrl={guestUrl} ready={session.status === 'ready'} />

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

      <ItemEditor session={session} hostToken={hostToken} applySession={applySession} />
      <BillForm
        key={billKey(session)}
        session={session}
        hostToken={hostToken}
        applySession={applySession}
      />
      <GuestsPanel session={session} hostToken={hostToken} applySession={applySession} />
      <FinishCard session={session} hostToken={hostToken} applySession={applySession} />
      {session.shares && session.shares.length > 0 && (
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
