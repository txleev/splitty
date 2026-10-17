import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Payment, Session, Share } from '../api/types'
import { PayPanel } from './PayPanel'

afterEach(cleanup)

const share: Share = {
  member_id: 2,
  name: 'Ben',
  subtotal_minor: 3200,
  tax_minor: 243,
  tip_minor: 0,
  total_minor: 3443,
  payment: 'unpaid',
}

function sessionWith(overrides: Partial<Session> = {}): Session {
  return {
    session_id: 'abc',
    status: 'ready',
    expires_at: '2026-10-24T00:00:00Z',
    currency: 'EUR',
    subtotal_minor: 3200,
    tax_minor: 243,
    tip_minor: 0,
    total_minor: 3443,
    warnings: [],
    host_payment_handle: 'ana.k',
    host_payment_platform: 'revolut',
    items: [],
    members: [],
    problems: [],
    locked: true,
    blockers: [],
    shares: [share],
    ...overrides,
  }
}

function renderPanel(session: Session, payment: Payment, markPaid = vi.fn()) {
  markPaid.mockResolvedValue(session)
  render(
    <PayPanel
      session={session}
      share={{ ...share, payment }}
      applySession={vi.fn()}
      markPaid={markPaid}
    />,
  )
  return markPaid
}

describe('PayPanel', () => {
  it('links to the host on the chosen app with the exact amount', () => {
    renderPanel(sessionWith(), 'unpaid')

    const link = screen.getByRole('link', { name: 'Pay 34.43 EUR with Revolut' })
    expect(link.getAttribute('href')).toBe('https://revolut.me/ana.k?amount=34.43&currency=EUR')
  })

  it('records the payment when the guest says they have paid', async () => {
    const markPaid = renderPanel(sessionWith(), 'unpaid')

    await userEvent.click(screen.getByRole('button', { name: "I've paid" }))

    expect(markPaid).toHaveBeenCalledWith(true)
  })

  it('lets a guest take back a payment they marked', async () => {
    const markPaid = renderPanel(sessionWith(), 'paid')

    expect(screen.getByText('You marked this paid. The host can see it.')).toBeTruthy()
    await userEvent.click(screen.getByRole('button', { name: 'Undo, I have not paid' }))

    expect(markPaid).toHaveBeenCalledWith(false)
  })

  it('warns when the share moved after the guest marked it paid', () => {
    renderPanel(sessionWith(), 'changed')

    expect(screen.getByText(/changed after you marked it paid/)).toBeTruthy()
  })

  it('explains how to pay when the host has no handle', () => {
    renderPanel(sessionWith({ host_payment_handle: null, host_payment_platform: null }), 'unpaid')

    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText(/has not added a payment handle/)).toBeTruthy()
  })

  it('offers no app link outside EUR, GBP and USD', () => {
    renderPanel(sessionWith({ currency: 'KGS' }), 'unpaid')

    expect(screen.queryByRole('link')).toBeNull()
    expect(screen.getByText(/Payment links work in EUR, GBP and USD/)).toBeTruthy()
  })
})
