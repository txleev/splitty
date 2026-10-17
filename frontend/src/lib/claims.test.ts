import { describe, expect, it } from 'vitest'
import type { Item } from '../api/types'
import { estimateSubtotal, maxClaim, myClaim } from './claims'

function item(overrides: Partial<Item>): Item {
  return {
    id: 1,
    position: 0,
    name: 'Tea',
    quantity: 1,
    unit_price_minor: null,
    total_minor: 300,
    missing: [],
    preassigned_names: [],
    remaining: 1,
    claims: [],
    ...overrides,
  }
}

const ANA = 7
const BEN = 8

describe('myClaim', () => {
  it('returns this guest quantity, or zero when they have not claimed', () => {
    const tea = item({ claims: [{ member_id: ANA, name: 'Ana', quantity: 2 }] })
    expect(myClaim(tea, ANA)).toBe(2)
    expect(myClaim(tea, BEN)).toBe(0)
  })
})

describe('maxClaim', () => {
  it('allows the own claim plus whatever is still free', () => {
    const tea = item({
      quantity: 3,
      remaining: 1,
      claims: [
        { member_id: ANA, name: 'Ana', quantity: 1 },
        { member_id: BEN, name: 'Ben', quantity: 1 },
      ],
    })
    expect(maxClaim(tea, ANA)).toBe(2)
    expect(maxClaim(tea, 99)).toBe(1)
  })

  it('never drops below the own claim when the item is over-claimed', () => {
    const tea = item({
      quantity: 1,
      remaining: -1,
      claims: [
        { member_id: ANA, name: 'Ana', quantity: 1 },
        { member_id: BEN, name: 'Ben', quantity: 1 },
      ],
    })
    expect(maxClaim(tea, ANA)).toBe(1)
  })

  it('counts only whole units, so a half-unit cannot be claimed', () => {
    const halfPizza = item({ quantity: 0.5, remaining: 0.5 })
    expect(maxClaim(halfPizza, ANA)).toBe(0)
  })
})

describe('estimateSubtotal', () => {
  it('splits each line by the claimed quantity', () => {
    const items = [
      item({ quantity: 2, total_minor: 3000, claims: [{ member_id: ANA, name: 'Ana', quantity: 1 }] }),
      item({ id: 2, quantity: 1, total_minor: 1000, claims: [{ member_id: ANA, name: 'Ana', quantity: 1 }] }),
      item({ id: 3, quantity: 1, total_minor: 500 }),
    ]
    expect(estimateSubtotal(items, ANA)).toBe(1500 + 1000)
  })

  it('rounds each line to the nearest minor unit', () => {
    const items = [item({ quantity: 3, total_minor: 100, claims: [{ member_id: ANA, name: 'Ana', quantity: 1 }] })]
    expect(estimateSubtotal(items, ANA)).toBe(33)
  })
})
