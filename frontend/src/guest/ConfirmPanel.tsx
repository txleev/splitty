import type { Confirmation } from '../api/types'
import { Notice } from '../components/ui'

interface Props {
  confirmation: Confirmation
  busy: boolean
  onConfirm: () => void
}

const TEXT: Record<Confirmation, string> = {
  none: 'Check your items, then confirm them. You can change them until everyone has confirmed.',
  confirmed: 'Confirmed. If you change an item, you will need to confirm again.',
  needs_reconfirm: 'The bill changed after you confirmed. Check your items, then confirm again.',
}

export function ConfirmPanel({ confirmation, busy, onConfirm }: Props) {
  return (
    <section className="card stack">
      <Notice tone={confirmation === 'needs_reconfirm' ? 'warn' : confirmation === 'confirmed' ? 'ok' : 'info'}>
        {TEXT[confirmation]}
      </Notice>
      <button
        type="button"
        className="btn btn-primary btn-block"
        disabled={busy || confirmation === 'confirmed'}
        onClick={onConfirm}
      >
        {confirmation === 'needs_reconfirm' ? 'Confirm again' : 'Confirm my items'}
      </button>
    </section>
  )
}
