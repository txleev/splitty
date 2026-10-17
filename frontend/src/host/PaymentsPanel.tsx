import { setMemberPaid } from '../api/sessions'
import type { Payment, Session, Share } from '../api/types'
import { Collapsible } from '../components/Collapsible'
import { ErrorNotice, Pill, type Tone } from '../components/ui'
import { formatMoney } from '../lib/money'
import { useAction } from '../lib/useAction'

interface Props {
  sessionId: string
  currency: string | null
  shares: Share[]
  hostToken: string
  applySession: (session: Session) => void
}

const STATUS: Record<Payment, { label: string; tone: Tone }> = {
  unpaid: { label: 'Unpaid', tone: 'warn' },
  paid: { label: 'Paid', tone: 'ok' },
  changed: { label: 'Amount changed', tone: 'warn' },
}

/** Who has paid their share. Guests mark their own, and the host can mark cash payments. */
export function PaymentsPanel({ sessionId, currency, shares, hostToken, applySession }: Props) {
  const action = useAction(applySession)

  const toggle = (share: Share) => {
    void action.run(() => setMemberPaid(sessionId, hostToken, share.member_id, share.payment !== 'paid'))
  }

  return (
    <Collapsible
      title="Payments"
      defaultOpen
      summary={`${shares.filter((share) => share.payment === 'paid').length} of ${shares.length} paid`}
    >
      <p className="muted small">
        Guests mark their own share paid. You can mark a cash payment here as well.
      </p>
      <ErrorNotice error={action.error} />

      <ul className="plain-list">
        {shares.map((share) => {
          const status = STATUS[share.payment]
          return (
            <li key={share.member_id} className="member-row">
              <div className="member-main">
                <span className="avatar" aria-hidden="true">
                  {share.name.charAt(0)}
                </span>
                <div>
                  <strong>{share.name}</strong>
                  <div className="muted small">{formatMoney(share.total_minor, currency)}</div>
                </div>
              </div>
              <div className="row">
                <Pill tone={status.tone}>{status.label}</Pill>
                <button
                  type="button"
                  className="btn btn-small"
                  disabled={action.busy}
                  onClick={() => toggle(share)}
                >
                  {share.payment === 'paid' ? 'Undo' : 'Mark paid'}
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </Collapsible>
  )
}
