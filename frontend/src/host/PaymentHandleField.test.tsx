import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PaymentHandleField } from './PaymentHandleField'

afterEach(cleanup)

describe('PaymentHandleField', () => {
  it('offers Revolut and Wise in the dropdown and reports the choice', async () => {
    const onPlatformChange = vi.fn()
    render(
      <PaymentHandleField
        handle="ana"
        platform={null}
        disabled={false}
        onHandleChange={vi.fn()}
        onPlatformChange={onPlatformChange}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Platform' }))
    expect(screen.getByRole('option', { name: 'Revolut' })).toBeTruthy()
    expect(screen.getByRole('option', { name: 'Wise' })).toBeTruthy()

    await userEvent.click(screen.getByRole('option', { name: 'Wise' }))

    expect(onPlatformChange).toHaveBeenCalledWith('wise')
    expect(screen.queryByRole('listbox')).toBeNull()
  })

  it('marks the saved platform as selected', async () => {
    render(
      <PaymentHandleField
        handle="ana"
        platform="revolut"
        disabled={false}
        onHandleChange={vi.fn()}
        onPlatformChange={vi.fn()}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Revolut' }))

    expect(screen.getByRole('option', { name: 'Revolut' }).getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('option', { name: 'Wise' }).getAttribute('aria-selected')).toBe('false')
  })

  it('passes typing in the handle to the parent', async () => {
    const onHandleChange = vi.fn()
    render(
      <PaymentHandleField
        handle=""
        platform={null}
        disabled={false}
        onHandleChange={onHandleChange}
        onPlatformChange={vi.fn()}
      />,
    )

    await userEvent.type(screen.getByLabelText('Payment handle'), 'a')

    expect(onHandleChange).toHaveBeenCalledWith('a')
  })
})
