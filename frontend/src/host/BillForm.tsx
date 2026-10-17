import { useState, type FormEvent } from 'react'
import { updateBill } from '../api/sessions'
import type { BillPatch, PaymentPlatform, Session } from '../api/types'
import { ErrorNotice, Notice } from '../components/ui'
import { parseAmount, toInputValue } from '../lib/money'
import { useAction } from '../lib/useAction'
import { PaymentHandleField } from './PaymentHandleField'

interface Props {
  session: Session
  hostToken: string
  applySession: (session: Session) => void
}

export function BillForm({ session, hostToken, applySession }: Props) {
  const [currency, setCurrency] = useState(session.currency ?? '')
  const [subtotal, setSubtotal] = useState(toInputValue(session.subtotal_minor))
  const [tax, setTax] = useState(toInputValue(session.tax_minor))
  const [tip, setTip] = useState(toInputValue(session.tip_minor))
  const [total, setTotal] = useState(toInputValue(session.total_minor))
  const [handle, setHandle] = useState(session.host_payment_handle ?? '')
  const [platform, setPlatform] = useState<PaymentPlatform | null>(session.host_payment_platform)
  const [inputError, setInputError] = useState<string | null>(null)
  const action = useAction(applySession)

  const save = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const subtotalAmount = parseAmount(subtotal)
    const taxAmount = parseAmount(tax)
    const tipAmount = parseAmount(tip)
    const totalAmount = parseAmount(total)
    if (!subtotalAmount.ok || !taxAmount.ok || !tipAmount.ok || !totalAmount.ok) {
      setInputError('Amounts look like 14.50. Leave tax or tip empty if the receipt has none.')
      return
    }
    if (handle.trim() && !platform) {
      setInputError('Choose Revolut or Wise for the payment handle.')
      return
    }
    setInputError(null)

    const cleanHandle = handle.trim()
    const patch: BillPatch = {
      currency: currency.trim() || null,
      subtotal_minor: subtotalAmount.minor,
      tax_minor: taxAmount.minor,
      tip_minor: tipAmount.minor,
      total_minor: totalAmount.minor,
      host_payment_handle: cleanHandle || null,
      host_payment_platform: cleanHandle ? platform : null,
    }
    void action.run(() => updateBill(session.session_id, hostToken, patch))
  }

  return (
    <form className="card stack" onSubmit={save}>
      <div className="row between">
        <h2>Bill</h2>
        <span className="muted small">Saving a change makes the split a draft again.</span>
      </div>

      <div className="grid-2">
        <label className="field">
          <span>Currency</span>
          <input
            value={currency}
            onChange={(event) => setCurrency(event.target.value)}
            placeholder="EUR"
            maxLength={8}
            disabled={action.busy}
          />
        </label>
        <label className="field">
          <span>Subtotal</span>
          <input
            inputMode="decimal"
            value={subtotal}
            onChange={(event) => setSubtotal(event.target.value)}
            disabled={action.busy}
          />
        </label>
      </div>

      <div className="grid-2">
        <label className="field">
          <span>Tax</span>
          <input
            inputMode="decimal"
            value={tax}
            onChange={(event) => setTax(event.target.value)}
            disabled={action.busy}
          />
        </label>
        <label className="field">
          <span>Tip</span>
          <input
            inputMode="decimal"
            value={tip}
            onChange={(event) => setTip(event.target.value)}
            disabled={action.busy}
          />
        </label>
      </div>

      <label className="field">
        <span>Total</span>
        <input
          inputMode="decimal"
          value={total}
          onChange={(event) => setTotal(event.target.value)}
          disabled={action.busy}
        />
      </label>

      <PaymentHandleField
        handle={handle}
        platform={platform}
        disabled={action.busy}
        onHandleChange={setHandle}
        onPlatformChange={setPlatform}
      />

      {inputError && <Notice tone="error">{inputError}</Notice>}
      <ErrorNotice error={action.error} />
      <button type="submit" className="btn btn-primary" disabled={action.busy}>
        Save bill
      </button>
    </form>
  )
}
