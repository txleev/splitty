import { describe, expect, it } from 'vitest'
import { readItemForm, type ItemFormValues } from './itemForm'

const valid: ItemFormValues = { name: ' Tea ', quantity: '2', unitPrice: '3.50', total: '7', splitEqually: false }

describe('readItemForm', () => {
  it('builds the request body with amounts in minor units', () => {
    expect(readItemForm(valid)).toEqual({
      input: { name: 'Tea', quantity: 2, unit_price_minor: 350, total_minor: 700, split_equally: false },
    })
  })

  it('passes the equal split flag through', () => {
    expect(readItemForm({ ...valid, splitEqually: true })).toEqual({
      input: { name: 'Tea', quantity: 2, unit_price_minor: 350, total_minor: 700, split_equally: true },
    })
  })

  it('allows an empty unit price', () => {
    expect(readItemForm({ ...valid, unitPrice: '' })).toEqual({
      input: { name: 'Tea', quantity: 2, unit_price_minor: null, total_minor: 700, split_equally: false },
    })
  })

  it('says what to fix first', () => {
    expect(readItemForm({ ...valid, name: '  ' })).toEqual({ error: 'Give the item a name.' })
    expect(readItemForm({ ...valid, quantity: '0' })).toEqual({
      error: 'Quantity must be a positive number.',
    })
    expect(readItemForm({ ...valid, total: '' })).toEqual({ error: 'Enter the line total, like 7.00.' })
    expect(readItemForm({ ...valid, unitPrice: 'x' })).toEqual({
      error: expect.stringContaining('Unit price'),
    })
  })
})
