import type { Share } from '../api/types'
import { formatAmount } from '../lib/money'

interface Props {
  shares: Share[]
  currency: string | null
  // The viewer's own member id, so their row can be highlighted.
  mineId?: number
}

export function SharesTable({ shares, currency, mineId }: Props) {
  const sum = (pick: (share: Share) => number) => shares.reduce((acc, share) => acc + pick(share), 0)

  return (
    <div className="table-wrap">
      <table className="shares">
        <thead>
          <tr>
            <th>Guest</th>
            <th className="num">Subtotal</th>
            <th className="num">Tax</th>
            <th className="num">Tip</th>
            <th className="num">Total</th>
          </tr>
        </thead>
        <tbody>
          {shares.map((share) => (
            <tr key={share.member_id} className={share.member_id === mineId ? 'mine' : undefined}>
              <td>
                {share.name}
                {share.member_id === mineId && <span className="muted"> (you)</span>}
              </td>
              <td className="num">{formatAmount(share.subtotal_minor)}</td>
              <td className="num">{formatAmount(share.tax_minor)}</td>
              <td className="num">{formatAmount(share.tip_minor)}</td>
              <td className="num">{formatAmount(share.total_minor)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th>All guests{currency ? ` (${currency})` : ''}</th>
            <td className="num">{formatAmount(sum((s) => s.subtotal_minor))}</td>
            <td className="num">{formatAmount(sum((s) => s.tax_minor))}</td>
            <td className="num">{formatAmount(sum((s) => s.tip_minor))}</td>
            <td className="num">{formatAmount(sum((s) => s.total_minor))}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
