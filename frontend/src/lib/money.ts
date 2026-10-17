// Amounts are integers in minor units (1450 = 14.50). These helpers turn typed text into minor units
// and minor units back into text.

export type ParsedAmount = { ok: true; minor: number | null } | { ok: false }

const AMOUNT = /^\d+(?:[.,]\d{1,2})?$/

/** Reads "14.5", "14,50" or "1 799.00". Blank means the amount is not set. */
export function parseAmount(text: string): ParsedAmount {
  const cleaned = text.replace(/\s/g, '')
  if (cleaned === '') {
    return { ok: true, minor: null }
  }
  if (!AMOUNT.test(cleaned)) {
    return { ok: false }
  }
  const [whole, cents = ''] = cleaned.replace(',', '.').split('.')
  return { ok: true, minor: Number(whole) * 100 + Number(cents.padEnd(2, '0')) }
}

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** 1450 becomes "1,450.00". */
export function formatAmount(minor: number): string {
  return formatter.format(minor / 100)
}

/** 1450 with KGS becomes "1,450.00 KGS". Unset amounts show a dash. */
export function formatMoney(minor: number | null | undefined, currency: string | null): string {
  if (minor === null || minor === undefined) {
    return '—'
  }
  return currency ? `${formatAmount(minor)} ${currency}` : formatAmount(minor)
}

/** The text an amount field shows for a stored value. */
export function toInputValue(minor: number | null | undefined): string {
  return minor === null || minor === undefined ? '' : (minor / 100).toFixed(2)
}
