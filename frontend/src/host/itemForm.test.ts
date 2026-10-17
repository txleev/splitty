import { describe, expect, it } from 'vitest'
import { readItemForm, type ItemFormValues } from './itemForm'

const valid: ItemFormValues = { name: ' Tea ', quantity: '2', unitPrice: '3.50', total: '7', splitEqually: false, splitCount: '' }

describe('readItemForm', () => {
  it('builds the request body with amounts in minor units', () => {
    expect(readItemForm(valid)).toEqual({
      input: { name: 'Tea', quantity: 2, unit_price_minor: 350, total_minor: 700, split_equally: false, split_count: null },
    })
  })

  it('passes the equal split flag through', () => {
    expect(readItemForm({ ...valid, splitEqually: true })).toEqual({
      input: { name: 'Tea', quantity: 2, unit_price_minor: 350, total_minor: 700, split_equally: true, split_count: null },
    })
  })

  it('allows an empty unit price', () => {
    expect(readItemForm({ ...valid, unitPrice: '' })).toEqual({
      input: { name: 'Tea', quantity: 2, unit_price_minor: null, total_minor: 700, split_equally: false, split_count: null },
    })
  })

  it('reads the number of people for an equal split', () => {
    const result = readItemForm({ ...valid, splitEqually: true, splitCount: ' 4 ' })
    expect(result).toEqual({ input: expect.objectContaining({ split_equally: true, split_count: 4 }) })
  })

  it('ignores a leftover head count when the equal split is off', () => {
    const result = readItemForm({ ...valid, splitEqually: false, splitCount: '4' })
    expect(result).toEqual({ input: expect.objectContaining({ split_equally: false, split_count: null }) })
  })

  it('refuses a head count that is not a whole number from 2 to 100', () => {
    for (const bad of ['1', '0', '101', '2.5', 'x', '-3']) {
      expect(readItemForm({ ...valid, splitEqually: true, splitCount: bad })).toEqual({
        error: expect.stringContaining('Number of people'),
      })
    }
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
