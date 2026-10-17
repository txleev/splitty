import { useState } from 'react'
import type { Payment, Session, Share } from '../api/types'
import { PlatformMark } from '../components/PlatformMark'
import { ErrorNotice, Notice, type Tone } from '../components/ui'
import { formatMoney, toInputValue } from '../lib/money'
import { PLATFORM_LABEL, paymentLink } from '../lib/paymentLinks'
import { useAction } from '../lib/useAction'

interface Props {
  session: Session
  share: Share
  applySession: (session: Session) => void
  // Records this guest's payment on the server and returns the updated split.
  markPaid: (paid: boolean) => Promise<Session>
}

const PAYMENT_NOTICE: Record<Payment, { tone: Tone; text: string }> = {
  unpaid: { tone: 'info', text: 'Pay the host, then mark it paid here.' },
  paid: { tone: 'ok', text: 'You marked this paid. The host can see it.' },
  changed: {
    tone: 'warn',
    text: 'Your share changed after you marked it paid. Check the new amount, pay it, then mark it paid again.',
  },
}

function noLinkText(session: Session, amount: string): string {
  if (!session.host_payment_handle || !session.host_payment_platform) {
    return `The host has not added a payment handle. Pay ${amount} directly, then mark it paid here.`
  }
  return `Payment links work in EUR, GBP and USD. Pay ${amount} directly, then mark it paid here.`
}

/** What one guest owes, the way to pay it, and their own paid mark. */
export function PayPanel({ session, share, applySession, markPaid }: Props) {
  const action = useAction(applySession)
  const [copied, setCopied] = useState(false)
  const amount = formatMoney(share.total_minor, session.currency)
  const plainAmount = toInputValue(share.total_minor)
  const platform = session.host_payment_platform
  const link = paymentLink({
    platform,
    handle: session.host_payment_handle,
    currency: session.currency,
    amountMinor: share.total_minor,
  })
  const notice = PAYMENT_NOTICE[share.payment]

  const copyAmount = async () => {
    try {
      await navigator.clipboard.writeText(plainAmount)
      setCopied(true)
    } catch {
      // Clipboard access is blocked on some plain-http pages. The amount is shown on screen.
      setCopied(false)
    }
  }

  return (
    <section className="card stack">
      <div className="row between">
        <h2>Your payment</h2>
        <strong className="pay-amount">{amount}</strong>
      </div>
      <Notice tone={notice.tone}>{notice.text}</Notice>
      <ErrorNotice error={action.error} />

      {link && platform ? (
        <a className="btn btn-primary btn-block" href={link} target="_blank" rel="noopener noreferrer">
          <PlatformMark platform={platform} /> Pay {amount} with {PLATFORM_LABEL[platform]}
        </a>
      ) : (
        <Notice>{noLinkText(session, amount)}</Notice>
      )}

      <div className="row">
        <button type="button" className="btn btn-small" onClick={() => void copyAmount()}>
          {copied ? 'Amount copied' : 'Copy amount'}
        </button>
        <span className="muted small">Paste it in the app if the amount is not filled in.</span>
      </div>

      {share.payment === 'paid' ? (
        <button
          type="button"
          className="btn btn-block"
          disabled={action.busy}
          onClick={() => void action.run(() => markPaid(false))}
        >
          Undo, I have not paid
        </button>
      ) : (
        <button
          type="button"
          className="btn btn-block"
          disabled={action.busy}
          onClick={() => void action.run(() => markPaid(true))}
        >
          I&apos;ve paid
        </button>
      )}
    </section>
  )
}
