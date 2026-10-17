import { describe, expect, it } from 'vitest'
import { formatMoney, parseAmount, toInputValue } from './money'

describe('parseAmount', () => {
  it('reads dot and comma decimals into minor units', () => {
    expect(parseAmount('14.5')).toEqual({ ok: true, minor: 1450 })
    expect(parseAmount('14,50')).toEqual({ ok: true, minor: 1450 })
    expect(parseAmount('14')).toEqual({ ok: true, minor: 1400 })
    expect(parseAmount('0.05')).toEqual({ ok: true, minor: 5 })
  })

  it('ignores spaces used as thousands separators', () => {
    expect(parseAmount('1 799.00')).toEqual({ ok: true, minor: 179900 })
  })

  it('treats blank input as not set', () => {
    expect(parseAmount('   ')).toEqual({ ok: true, minor: null })
  })

  it('rejects anything that is not an amount', () => {
    for (const text of ['abc', '1.234', '-5', '1,000.00', '.5']) {
      expect(parseAmount(text), text).toEqual({ ok: false })
    }
  })
})

describe('formatting', () => {
  it('shows two decimals with thousands separators and the currency', () => {
    expect(formatMoney(145000, 'KGS')).toBe('1,450.00 KGS')
    expect(formatMoney(5, null)).toBe('0.05')
  })

  it('shows a dash when the amount is not set', () => {
    expect(formatMoney(null, 'KGS')).toBe('—')
  })

  it('turns stored amounts into input text and back', () => {
    expect(toInputValue(1450)).toBe('14.50')
    expect(toInputValue(null)).toBe('')
    expect(parseAmount(toInputValue(1450))).toEqual({ ok: true, minor: 1450 })
  })
})
