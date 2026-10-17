// Mirrors backend/schemas.py. Amounts are integers in minor units (1450 = 14.50). Quantities are decimals.

export type Confirmation = 'none' | 'confirmed' | 'needs_reconfirm'

export type SessionStatus = 'draft' | 'ready'

export type PaymentPlatform = 'revolut' | 'wise'

// "changed": the guest marked an earlier amount, and their share has moved since.
export type Payment = 'unpaid' | 'paid' | 'changed'

export interface Claim {
  member_id: number
  name: string
  quantity: number
}

export interface Item {
  id: number
  position: number
  name: string
  quantity: number
  unit_price_minor: number | null
  total_minor: number
  missing: string[]
  preassigned_names: string[]
  // Quantity minus all claims. Below zero means the item is over-claimed.
  remaining: number
  claims: Claim[]
}

export interface Member {
  id: number
  name: string
  joined: boolean
  confirmation: Confirmation
}

export interface Share {
  member_id: number
  name: string
  subtotal_minor: number
  tax_minor: number
  tip_minor: number
  total_minor: number
  payment: Payment
}

export interface Session {
  session_id: string
  status: SessionStatus
  expires_at: string
  currency: string | null
  subtotal_minor: number | null
  tax_minor: number | null
  tip_minor: number | null
  total_minor: number | null
  warnings: string[]
  host_payment_handle: string | null
  host_payment_platform: PaymentPlatform | null
  items: Item[]
  members: Member[]
  problems: string[]
  locked: boolean
  blockers: string[]
  shares: Share[] | null
}

export interface CreatedSession extends Session {
  host_token: string
}

export interface JoinResult {
  member_id: number
  name: string
  member_token: string
}

export interface BillPatch {
  currency?: string | null
  subtotal_minor?: number | null
  tax_minor?: number | null
  tip_minor?: number | null
  total_minor?: number | null
  host_payment_handle?: string | null
  host_payment_platform?: PaymentPlatform | null
}

export interface ItemInput {
  name: string
  quantity: number
  unit_price_minor: number | null
  total_minor: number
}

export interface ItemPatch {
  name?: string
  quantity?: number
  unit_price_minor?: number | null
  total_minor?: number
}
