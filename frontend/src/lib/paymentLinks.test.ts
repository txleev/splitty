import { describe, expect, it } from 'vitest'
import { paymentLink } from './paymentLinks'

describe('paymentLink', () => {
  it('builds a Revolut link with the exact amount and currency', () => {
    expect(
      paymentLink({ platform: 'revolut', handle: 'ana.k', currency: 'EUR', amountMinor: 1507 }),
    ).toBe('https://revolut.me/ana.k?amount=1507&currency=EUR')
  })

  it('sends Revolut the amount in minor units, so 182.91 USD is not shown as 1.82', () => {
    expect(
      paymentLink({
        platform: 'revolut',
        handle: 'metharasansilunid',
        currency: 'USD',
        amountMinor: 18291,
      }),
    ).toBe('https://revolut.me/metharasansilunid?amount=18291&currency=USD')
  })

  it('builds a Wise link', () => {
    expect(
      paymentLink({ platform: 'wise', handle: 'ben_b', currency: 'GBP', amountMinor: 3443 }),
    ).toBe('https://wise.com/pay/me/ben_b?amount=34.43&currency=GBP')
  })

  it('accepts USD written in lower case', () => {
    expect(
      paymentLink({ platform: 'revolut', handle: 'ana', currency: 'usd', amountMinor: 1000 }),
    ).toBe('https://revolut.me/ana?amount=1000&currency=USD')
  })

  it('reads "Ft" from a receipt as HUF', () => {
    expect(
      paymentLink({ platform: 'revolut', handle: 'txleev', currency: 'Ft', amountMinor: 167700 }),
    ).toBe('https://revolut.me/txleev?amount=167700&currency=HUF')
  })

  it('offers no link in any other currency', () => {
    expect(
      paymentLink({ platform: 'revolut', handle: 'ana', currency: 'KGS', amountMinor: 1000 }),
    ).toBeNull()
  })

  it('offers no link without a platform, handle, currency or final amount', () => {
    const full = { platform: 'wise' as const, handle: 'ana', currency: 'EUR', amountMinor: 1000 }

    expect(paymentLink({ ...full, platform: null })).toBeNull()
    expect(paymentLink({ ...full, handle: null })).toBeNull()
    expect(paymentLink({ ...full, currency: null })).toBeNull()
    expect(paymentLink({ ...full, amountMinor: null })).toBeNull()
  })

  it('encodes unexpected characters so they cannot change the destination', () => {
    const link = paymentLink({
      platform: 'revolut',
      handle: 'a/b?x=1#',
      currency: 'EUR',
      amountMinor: 500,
    })

    const url = new URL(link ?? '')
    expect(url.origin).toBe('https://revolut.me')
    expect(url.pathname).toBe('/a%2Fb%3Fx%3D1%23')
    expect(url.searchParams.get('amount')).toBe('500')
  })
})
