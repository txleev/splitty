import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { joinSession } from '../api/sessions'
import type { Member } from '../api/types'
import { JoinForm } from './JoinForm'

vi.mock('../api/sessions', () => ({ joinSession: vi.fn() }))

const openSlots: Member[] = [{ id: 3, name: 'Ben', joined: false, confirmation: 'none' }]

afterEach(cleanup)

describe('JoinForm', () => {
  it('joins with a name from the list and hands back the seat', async () => {
    vi.mocked(joinSession).mockResolvedValue({ member_id: 3, name: 'Ben', member_token: 'tok' })
    const onJoined = vi.fn()
    render(
      <JoinForm sessionId="abc" openSlots={openSlots} disabled={false} notice={null} onJoined={onJoined} />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Ben' }))

    expect(joinSession).toHaveBeenCalledWith('abc', 'Ben')
    expect(onJoined).toHaveBeenCalledWith({ memberId: 3, name: 'Ben', token: 'tok' })
  })

  it('explains a taken name and says how to get it back', async () => {
    vi.mocked(joinSession).mockRejectedValue(
      new ApiError(409, 'That name has already joined. Pick a different name.'),
    )
    render(
      <JoinForm sessionId="abc" openSlots={[]} disabled={false} notice={null} onJoined={vi.fn()} />,
    )

    await userEvent.type(screen.getByLabelText('Your name'), 'Ana')
    await userEvent.click(screen.getByRole('button', { name: 'Join' }))

    expect(await screen.findByText('That name has already joined. Pick a different name.')).toBeTruthy()
    expect(screen.getByText(/ask the host to release your name/)).toBeTruthy()
  })

  it('does not allow joining while the split is still a draft', () => {
    render(
      <JoinForm sessionId="abc" openSlots={openSlots} disabled notice={null} onJoined={vi.fn()} />,
    )
    expect((screen.getByRole('button', { name: 'Ben' }) as HTMLButtonElement).disabled).toBe(true)
  })
})
