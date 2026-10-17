import type { Item } from '../api/types'

// Quantities are floats, so a remainder such as 0.9999999999 should still count as one whole unit.
const EPSILON = 1e-9

export function myClaim(item: Item, memberId: number): number {
  return item.claims.find((claim) => claim.member_id === memberId)?.quantity ?? 0
}

/** The most this guest can set: their own claim plus whatever is still free. Whole units only. */
export function maxClaim(item: Item, memberId: number): number {
  const own = myClaim(item, memberId)
  return Math.max(own, own + Math.floor(item.remaining + EPSILON))
}

/**
 * This guest's subtotal before tax and tip, in minor units. It is an estimate for the guest to
 * look at. Once the split locks, the server's shares are the final amounts.
 */
export function estimateSubtotal(items: Item[], memberId: number): number {
  return items.reduce((sum, item) => {
    const own = myClaim(item, memberId)
    if (own === 0 || item.quantity <= 0) {
      return sum
    }
    return sum + Math.round((own / item.quantity) * item.total_minor)
  }, 0)
}
