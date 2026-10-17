import { markReady } from '../api/sessions'
import type { Session } from '../api/types'
import { Collapsible } from '../components/Collapsible'
import { SharesTable } from '../components/SharesTable'
import { ErrorNotice, Notice } from '../components/ui'
import { useAction } from '../lib/useAction'

interface Props {
  session: Session
  hostToken: string
  applySession: (session: Session) => void
}

export function FinishCard({ session, hostToken, applySession }: Props) {
  const action = useAction(applySession)
  const ready = session.status === 'ready'
  const blocked = session.problems.length > 0

  return (
    <>
      <section className="card stack">
        <ErrorNotice error={action.error} />

        {blocked ? (
          <Notice tone="error">
            <p>Fix these before guests can join:</p>
            <ul>
              {session.problems.map((problem) => (
                <li key={problem}>{problem}</li>
              ))}
            </ul>
          </Notice>
        ) : ready ? (
          <Notice tone="ok">
            Guests can join. Editing the bill pauses joining until you mark it ready again.
          </Notice>
        ) : (
          <Notice>Everything adds up. Mark the split ready so guests can join.</Notice>
        )}

        <button
          type="button"
          className="btn btn-primary btn-block"
          disabled={action.busy || blocked || ready}
          onClick={() => void action.run(() => markReady(session.session_id, hostToken))}
        >
          {ready ? 'Ready for guests' : 'Mark as ready'}
        </button>
      </section>

      {/* Keyed by state, so the section reopens when the split locks and the shares appear. */}
      <Collapsible
        key={session.locked ? 'shares' : 'open'}
        title={session.locked ? 'Who pays what' : 'Still open'}
        defaultOpen={session.locked}
        summary={session.locked ? undefined : `${session.blockers.length} left`}
      >
        {session.locked && session.shares ? (
          <SharesTable shares={session.shares} currency={session.currency} />
        ) : session.blockers.length > 0 ? (
          <ul>
            {session.blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        ) : (
          <p className="muted">Nothing is missing.</p>
        )}
      </Collapsible>
    </>
  )
}
