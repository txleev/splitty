import { useState, type ChangeEvent, type FormEvent } from 'react'
import { addItem, deleteItem, updateItem } from '../api/sessions'
import type { Item, ItemInput, ItemPatch, Session } from '../api/types'
import { ErrorNotice, Notice, Pill } from '../components/ui'
import { formatQuantity } from '../lib/format'
import { formatAmount, formatMoney, toInputValue } from '../lib/money'
import { useAction } from '../lib/useAction'
import { EMPTY_ITEM_FORM, readItemForm, type ItemFormValues } from './itemForm'

const MISSING_LABELS: Record<string, string> = {
  qty: 'quantity',
  unit_price: 'unit price',
  total_price: 'line total',
}

interface Props {
  session: Session
  hostToken: string
  applySession: (session: Session) => void
}

export function ItemEditor({ session, hostToken, applySession }: Props) {
  const action = useAction(applySession)
  const sessionId = session.session_id

  const remove = (item: Item) => {
    if (window.confirm(`Delete "${item.name}"? Its claims are removed too.`)) {
      void action.run(() => deleteItem(sessionId, hostToken, item.id))
    }
  }

  return (
    <section className="card stack">
      <h2>Items</h2>
      <ErrorNotice error={action.error} />
      {session.items.length === 0 && <p className="muted">No items yet. Add them below.</p>}

      <ul className="plain-list">
        {session.items.map((item) => (
          <ItemRow
            key={item.id}
            item={item}
            currency={session.currency}
            busy={action.busy}
            onSave={(patch) => action.run(() => updateItem(sessionId, hostToken, item.id, patch))}
            onDelete={() => remove(item)}
          />
        ))}
      </ul>

      <div className="stack">
        <h3 className="item-subtitle">Add an item</h3>
        <ItemForm
          initial={EMPTY_ITEM_FORM}
          submitLabel="Add item"
          busy={action.busy}
          resetOnSuccess
          onSubmit={(input) => action.run(() => addItem(sessionId, hostToken, input))}
        />
      </div>
    </section>
  )
}

interface RowProps {
  item: Item
  currency: string | null
  busy: boolean
  onSave: (patch: ItemPatch) => Promise<boolean>
  onDelete: () => void
}

function ItemRow({ item, currency, busy, onSave, onDelete }: RowProps) {
  const [editing, setEditing] = useState(false)

  // Only the fields that changed are sent. Setting a field clears its "missing" flag on the server.
  const save = async (input: ItemInput): Promise<boolean> => {
    const patch: ItemPatch = {}
    if (input.name !== item.name) patch.name = input.name
    if (input.quantity !== item.quantity) patch.quantity = input.quantity
    if (input.unit_price_minor !== item.unit_price_minor) {
      patch.unit_price_minor = input.unit_price_minor
    }
    if (input.total_minor !== item.total_minor) patch.total_minor = input.total_minor

    const saved = Object.keys(patch).length === 0 || (await onSave(patch))
    if (saved) {
      setEditing(false)
    }
    return saved
  }

  if (editing) {
    return (
      <li className="item">
        <ItemForm
          initial={{
            name: item.name,
            quantity: formatQuantity(item.quantity),
            unitPrice: toInputValue(item.unit_price_minor),
            total: toInputValue(item.total_minor),
          }}
          submitLabel="Save"
          busy={busy}
          onSubmit={save}
          onCancel={() => setEditing(false)}
        />
      </li>
    )
  }

  return (
    <li className="item">
      <div className="item-head">
        <span>{item.name}</span>
        <span className="num">{formatMoney(item.total_minor, currency)}</span>
      </div>
      <p className="muted small">
        {[
          `Quantity ${formatQuantity(item.quantity)}`,
          item.unit_price_minor !== null ? `${formatAmount(item.unit_price_minor)} each` : null,
        ]
          .filter(Boolean)
          .join(' · ')}
      </p>
      {item.missing.length > 0 && (
        <Notice tone="warn">
          Missing {item.missing.map((field) => MISSING_LABELS[field] ?? field).join(', ')}. Fill it in
          from the receipt.
        </Notice>
      )}
      {item.preassigned_names.length > 0 && (
        <p className="small">Note says: {item.preassigned_names.join(', ')}</p>
      )}
      <ClaimSummary item={item} />
      <div className="row">
        <button type="button" className="btn btn-small" onClick={() => setEditing(true)} disabled={busy}>
          Edit
        </button>
        <button type="button" className="btn btn-small btn-danger" onClick={onDelete} disabled={busy}>
          Delete
        </button>
      </div>
    </li>
  )
}

function ClaimSummary({ item }: { item: Item }) {
  const who = item.claims.map((claim) => `${claim.name} ${formatQuantity(claim.quantity)}`).join(', ')
  return (
    <div className="row small">
      <span className="muted">{who || 'Nobody has claimed it yet.'}</span>
      {item.remaining > 0 && <Pill tone="warn">{formatQuantity(item.remaining)} unclaimed</Pill>}
      {item.remaining < 0 && (
        <Pill tone="error">Over-claimed by {formatQuantity(-item.remaining)}</Pill>
      )}
      {item.remaining === 0 && <Pill tone="ok">All claimed</Pill>}
    </div>
  )
}

interface FormProps {
  initial: ItemFormValues
  submitLabel: string
  busy: boolean
  resetOnSuccess?: boolean
  onSubmit: (input: ItemInput) => Promise<boolean>
  onCancel?: () => void
}

function ItemForm({ initial, submitLabel, busy, resetOnSuccess = false, onSubmit, onCancel }: FormProps) {
  const [values, setValues] = useState<ItemFormValues>(initial)
  const [error, setError] = useState<string | null>(null)

  const field = (key: keyof ItemFormValues) => (event: ChangeEvent<HTMLInputElement>) => {
    const next = event.target.value
    setValues((current) => ({ ...current, [key]: next }))
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const result = readItemForm(values)
    if ('error' in result) {
      setError(result.error)
      return
    }
    setError(null)
    const saved = await onSubmit(result.input)
    if (saved && resetOnSuccess) {
      setValues(initial)
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <label className="field">
        <span>Name</span>
        <input value={values.name} onChange={field('name')} maxLength={120} disabled={busy} />
      </label>
      <div className="grid-2">
        <label className="field">
          <span>Quantity</span>
          <input inputMode="decimal" value={values.quantity} onChange={field('quantity')} disabled={busy} />
        </label>
        <label className="field">
          <span>Unit price</span>
          <input
            inputMode="decimal"
            value={values.unitPrice}
            onChange={field('unitPrice')}
            placeholder="optional"
            disabled={busy}
          />
        </label>
      </div>
      <label className="field">
        <span>Line total</span>
        <input inputMode="decimal" value={values.total} onChange={field('total')} disabled={busy} />
      </label>
      {error && <Notice tone="error">{error}</Notice>}
      <div className="row">
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {submitLabel}
        </button>
        {onCancel && (
          <button type="button" className="btn" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
