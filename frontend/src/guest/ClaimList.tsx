import type { Item } from '../api/types'
import { Pill } from '../components/ui'
import { maxClaim, myClaim } from '../lib/claims'
import { formatQuantity } from '../lib/format'
import { formatMoney } from '../lib/money'

interface Props {
  items: Item[]
  currency: string | null
  // Null shows the bill without the claim buttons, for viewers who have not joined.
  memberId: number | null
  busy: boolean
  onClaim: (itemId: number, quantity: number) => void
}

export function ClaimList({ items, currency, memberId, busy, onClaim }: Props) {
  if (items.length === 0) {
    return <p className="muted">The host has not added any items yet.</p>
  }
  return (
    <ul className="plain-list">
      {items.map((item) => (
        <ClaimRow
          key={item.id}
          item={item}
          currency={currency}
          memberId={memberId}
          busy={busy}
          onClaim={onClaim}
        />
      ))}
    </ul>
  )
}

function ClaimRow({ item, currency, memberId, busy, onClaim }: Omit<Props, 'items'> & { item: Item }) {
  const own = memberId === null ? 0 : myClaim(item, memberId)
  const limit = memberId === null ? 0 : maxClaim(item, memberId)
  const others = item.claims
    .filter((claim) => claim.member_id !== memberId)
    .map((claim) => `${claim.name} ${formatQuantity(claim.quantity)}`)

  return (
    <li className="claim-row">
      <div className="claim-info">
        <span className="claim-name">
          {item.name}
          {item.quantity !== 1 && <span className="muted"> × {formatQuantity(item.quantity)}</span>}
        </span>
        <span className="muted small">{formatMoney(item.total_minor, currency)}</span>
        <ClaimStatus item={item} />
        {others.length > 0 && <span className="muted small">With {others.join(', ')}</span>}
      </div>

      {memberId !== null && (
        <div className="stepper">
          <button
            type="button"
            className="btn"
            aria-label={`Take one less ${item.name}`}
            disabled={busy || own === 0}
            onClick={() => onClaim(item.id, own - 1)}
          >
            −
          </button>
          <output aria-label={`Your ${item.name}`}>{own}</output>
          <button
            type="button"
            className="btn"
            aria-label={`Take one more ${item.name}`}
            disabled={busy || own >= limit}
            onClick={() => onClaim(item.id, own + 1)}
          >
            +
          </button>
        </div>
      )}
    </li>
  )
}

function ClaimStatus({ item }: { item: Item }) {
  if (item.remaining > 0) {
    return <Pill tone="warn">{formatQuantity(item.remaining)} unclaimed</Pill>
  }
  if (item.remaining < 0) {
    return <Pill tone="error">Over-claimed</Pill>
  }
  return <Pill tone="ok">All claimed</Pill>
}
