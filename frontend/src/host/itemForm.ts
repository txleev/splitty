import type { ItemInput } from '../api/types'
import { parseQuantity } from '../lib/format'
import { parseAmount } from '../lib/money'

export interface ItemFormValues {
  name: string
  quantity: string
  unitPrice: string
  total: string
  splitEqually: boolean
}

export const EMPTY_ITEM_FORM: ItemFormValues = { name: '', quantity: '1', unitPrice: '', total: '', splitEqually: false }

/** Checks the item form and builds the request body. Returns the first problem as a sentence. */
export function readItemForm(values: ItemFormValues): { input: ItemInput } | { error: string } {
  const name = values.name.trim()
  const quantity = parseQuantity(values.quantity)
  const unit = parseAmount(values.unitPrice)
  const total = parseAmount(values.total)

  if (!name) {
    return { error: 'Give the item a name.' }
  }
  if (quantity === null) {
    return { error: 'Quantity must be a positive number.' }
  }
  if (!unit.ok) {
    return { error: 'Unit price looks like 3.50. Leave it empty if the receipt has none.' }
  }
  if (!total.ok || total.minor === null) {
    return { error: 'Enter the line total, like 7.00.' }
  }
  return {
    input: {
      name,
      quantity,
      unit_price_minor: unit.minor,
      total_minor: total.minor,
      split_equally: values.splitEqually,
    },
  }
}
