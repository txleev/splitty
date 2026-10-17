import type { PaymentPlatform } from '../api/types'
import { toInputValue } from './money'

export const PLATFORM_LABEL: Record<PaymentPlatform, string> = {
  revolut: 'Revolut',
  wise: 'Wise',
}

// The codes a currency can be written as, mapped to the code payment links use. Receipts write
// forint as "Ft", so that maps to HUF.
const LINK_CURRENCIES = new Map<string, string>([
  ['EUR', 'EUR'],
  ['GBP', 'GBP'],
  ['USD', 'USD'],
  ['HUF', 'HUF'],
  ['FT', 'HUF'],
  ['€', 'EUR'],
  ['£', 'GBP'],
  ['$', 'USD'],
])

/** Shown to guests when a payment link is not possible in the split's currency. */
export const LINK_CURRENCY_TEXT = 'EUR, GBP, USD and HUF (Ft)'

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

/** The payment-link code for a currency as written on a receipt or in the bill, or null if none. */
export function linkCurrency(currency: string | null): string | null {
  return LINK_CURRENCIES.get(currency?.trim().toUpperCase() ?? '') ?? null
}

// Revolut reads the amount in minor units, so 182.91 USD is sent as 18291. A decimal "182.91" was
// shown in Revolut as 1.82. Wise is sent a decimal amount. Neither is confirmed on a live account.
function amountParam(platform: PaymentPlatform, amountMinor: number): string {
  return platform === 'revolut' ? String(amountMinor) : toInputValue(amountMinor)
}

/**
 * The link a guest taps to pay the host. Null when the split has no handle, the currency has no
 * link, or the amount is not final. The handle is encoded, so host text cannot change where the
 * link goes.
 */
export function paymentLink({ platform, handle, currency, amountMinor }: LinkInput): string | null {
  const code = linkCurrency(currency)
  if (!platform || !handle || amountMinor === null || !code) {
    return null
  }
  const url = new URL(PAYMENT_BASE[platform] + encodeURIComponent(handle))
  url.searchParams.set('amount', amountParam(platform, amountMinor))
  url.searchParams.set('currency', code)
  return url.toString()
}
