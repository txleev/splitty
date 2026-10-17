import type { Session } from '../api/types'
import { formatMoney } from '../lib/money'

export function BillTotals({ session }: { session: Session }) {
  const rows: { label: string; minor: number | null; total?: boolean }[] = [
    { label: 'Subtotal', minor: session.subtotal_minor },
    { label: 'Tax', minor: session.tax_minor },
    { label: 'Tip', minor: session.tip_minor },
    { label: 'Total', minor: session.total_minor, total: true },
  ]

  return (
    <dl className="totals">
      {rows.map((row) => (
        <div key={row.label} className={row.total ? 'totals-total' : undefined}>
          <dt>{row.label}</dt>
          <dd>{formatMoney(row.minor, session.currency)}</dd>
        </div>
      ))}
    </dl>
  )
}
