import { useState, type FormEvent } from 'react'
import { updateBill } from '../api/sessions'
import type { BillPatch, Session } from '../api/types'
import { ErrorNotice, Notice } from '../components/ui'
import { parseAmount, toInputValue } from '../lib/money'
import { useAction } from '../lib/useAction'

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
    setInputError(null)

    const patch: BillPatch = {
      currency: currency.trim() || null,
      subtotal_minor: subtotalAmount.minor,
      tax_minor: taxAmount.minor,
      tip_minor: tipAmount.minor,
      total_minor: totalAmount.minor,
      host_payment_handle: handle.trim() || null,
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
            placeholder="KGS"
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

      <label className="field">
        <span>Payment handle (optional)</span>
        <input
          value={handle}
          onChange={(event) => setHandle(event.target.value)}
          placeholder="e.g. your Revolut tag"
          maxLength={64}
          disabled={action.busy}
        />
      </label>

      {inputError && <Notice tone="error">{inputError}</Notice>}
      <ErrorNotice error={action.error} />
      <button type="submit" className="btn btn-primary" disabled={action.busy}>
        Save bill
      </button>
    </form>
  )
}
