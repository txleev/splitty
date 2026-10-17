import { useState } from 'react'
import { useParams } from 'react-router'
import { ApiError } from '../api/client'
import { claimItem, confirmClaims } from '../api/sessions'
import { BillTotals } from '../components/BillTotals'
import { SessionGone } from '../components/SessionGone'
import { SharesTable } from '../components/SharesTable'
import { ErrorNotice, LiveBadge, Notice } from '../components/ui'
import { ClaimList } from '../guest/ClaimList'
import { ConfirmPanel } from '../guest/ConfirmPanel'
import { JoinForm } from '../guest/JoinForm'
import { estimateSubtotal } from '../lib/claims'
import { formatMoney } from '../lib/money'
import { clearSeat, loadSeat, saveSeat, type Seat } from '../lib/storage'
import { useAction } from '../lib/useAction'
import { useLiveSession } from '../lib/useLiveSession'

export function GuestPage() {
  const { sessionId = '' } = useParams()
  // Keyed by id so a different split never reuses this one's seat or socket.
  return <GuestView key={sessionId} sessionId={sessionId} />
}

function GuestView({ sessionId }: { sessionId: string }) {
  const { session, state, applySession } = useLiveSession(sessionId)
  const [seat, setSeat] = useState<Seat | null>(() => loadSeat(sessionId))
  const [notice, setNotice] = useState<string | null>(null)
  const action = useAction(applySession)

  if (state === 'gone') {
    return <SessionGone />
  }
  if (!session) {
    return <Notice>Loading the split…</Notice>
  }

  const myMember = seat ? session.members.find((m) => m.id === seat.memberId && m.joined) : undefined
  const draft = session.status !== 'ready'
  const openSlots = session.members.filter((m) => !m.joined)

  // The server answers 403 "Unknown member token" once the host has released this name.
  const forgetIfReleased = (caught: unknown): never => {
    if (caught instanceof ApiError && caught.status === 403) {
      clearSeat(sessionId)
      setSeat(null)
      setNotice('The host released your name. Join again to take it back.')
    }
    throw caught
  }

  const claim = (itemId: number, quantity: number) => {
    if (!seat) {
      return
    }
    void action.run(() => claimItem(sessionId, seat.token, itemId, quantity).catch(forgetIfReleased))
  }

  const confirm = () => {
    if (!seat) {
      return
    }
    void action.run(() => confirmClaims(sessionId, seat.token).catch(forgetIfReleased))
  }

  const joined = (next: Seat) => {
    saveSeat(sessionId, next)
    setSeat(next)
    setNotice(null)
  }

  return (
    <>
      <section className="card stack">
        <div className="row between">
          <h1>Bill split</h1>
          <LiveBadge state={state} />
        </div>
        <BillTotals session={session} />
        {session.host_payment_handle && (
          <p>
            Pay the host: <strong>{session.host_payment_handle}</strong>
          </p>
        )}
      </section>

      {draft && !myMember && (
        <Notice tone="warn">
          The host is still checking the bill. You can join once it is ready.
        </Notice>
      )}
      {draft && myMember && (
        <Notice tone="warn">
          The host is changing the bill. Check your items again once it is ready.
        </Notice>
      )}

      {myMember ? (
        <>
          <section className="card stack">
            <div className="row between">
              <h2>Your items</h2>
              <span className="muted">{myMember.name}</span>
            </div>
            <ErrorNotice error={action.error} />
            <ClaimList
              items={session.items}
              currency={session.currency}
              memberId={myMember.id}
              busy={action.busy}
              onClaim={claim}
            />
            <p className="muted small">
              About {formatMoney(estimateSubtotal(session.items, myMember.id), session.currency)}{' '}
              before tax and tip. The final amounts appear once everyone has confirmed.
            </p>
          </section>
          <ConfirmPanel
            confirmation={myMember.confirmation}
            busy={action.busy}
            onConfirm={confirm}
          />
        </>
      ) : (
        <>
          <section className="card stack">
            <h2>Items</h2>
            <ClaimList
              items={session.items}
              currency={session.currency}
              memberId={null}
              busy={false}
              onClaim={() => undefined}
            />
          </section>
          <JoinForm
            sessionId={sessionId}
            openSlots={openSlots}
            disabled={draft}
            notice={notice}
            onJoined={joined}
          />
        </>
      )}

      {session.locked && session.shares ? (
        <section className="card stack">
          <h2>Who pays what</h2>
          <SharesTable shares={session.shares} currency={session.currency} mineId={myMember?.id} />
        </section>
      ) : (
        <section className="card stack">
          <h2>Still open</h2>
          {session.blockers.length > 0 ? (
            <ul>
              {session.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">Nothing is missing.</p>
          )}
        </section>
      )}
    </>
  )
}
