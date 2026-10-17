import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { GuestQrCode } from './GuestQrCode'

afterEach(cleanup)

describe('GuestQrCode', () => {
  it('renders a code labelled with the guest link it encodes', () => {
    const url = 'https://splitty.example/s/abc123XYZ_-'
    const { container } = render(<GuestQrCode value={url} />)

    expect(container.querySelector('svg')).not.toBeNull()
    expect(container.querySelector('svg title')?.textContent).toBe(`QR code for ${url}`)
  })
})
