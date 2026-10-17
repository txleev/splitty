import type { PaymentPlatform } from '../api/types'
import { toInputValue } from './money'

export const PLATFORM_LABEL: Record<PaymentPlatform, string> = {
  revolut: 'Revolut',
  wise: 'Wise',
}

// Payment links are offered only in these currencies.
const LINK_CURRENCIES = new Set(['EUR', 'GBP', 'USD'])

// Where each app takes a payment request. The amount and currency parameters still need checking
// against live accounts, so the page also shows the amount for the guest to paste.
const PAYMENT_BASE: Record<PaymentPlatform, string> = {
  revolut: 'https://revolut.me/',
  wise: 'https://wise.com/pay/me/',
}

interface LinkInput {
  platform: PaymentPlatform | null
  handle: string | null
  currency: string | null
  amountMinor: number | null
}

/**
 * The link a guest taps to pay the host. Null when the split has no handle, the currency has no
 * link, or the amount is not final. The handle is encoded, so host text cannot change where the
 * link goes.
 */
export function paymentLink({ platform, handle, currency, amountMinor }: LinkInput): string | null {
  const code = currency?.trim().toUpperCase() ?? ''
  if (!platform || !handle || amountMinor === null || !LINK_CURRENCIES.has(code)) {
    return null
  }
  const url = new URL(PAYMENT_BASE[platform] + encodeURIComponent(handle))
  url.searchParams.set('amount', toInputValue(amountMinor))
  url.searchParams.set('currency', code)
  return url.toString()
}
