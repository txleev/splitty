import { useState, type FormEvent } from 'react'
import { ApiError, messageOf } from '../api/client'
import { joinSession } from '../api/sessions'
import type { Member } from '../api/types'
import { ErrorNotice, Notice } from '../components/ui'
import type { Seat } from '../lib/storage'

interface Props {
  sessionId: string
  // Names the host has set aside that nobody has taken yet.
  openSlots: Member[]
  disabled: boolean
  notice: string | null
  onJoined: (seat: Seat) => void
}

export function JoinForm({ sessionId, openSlots, disabled, notice, onJoined }: Props) {
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const joinAs = async (rawName: string) => {
    const cleaned = rawName.trim()
    if (!cleaned || busy || disabled) {
      return
    }
    setBusy(true)
    setError(null)
    try {
      const result = await joinSession(sessionId, cleaned)
      onJoined({ memberId: result.member_id, name: result.name, token: result.member_token })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught : new ApiError(0, messageOf(caught)))
      setBusy(false)
    }
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void joinAs(name)
  }

  return (
    <section className="card stack">
      <h2>Join this split</h2>
      <p className="muted">Tap a name from the list, or type your own.</p>
      {notice && <Notice tone="warn">{notice}</Notice>}

      {openSlots.length > 0 && (
        <div className="chips">
          {openSlots.map((slot) => (
            <button
              key={slot.id}
              type="button"
              className="btn"
              disabled={busy || disabled}
              onClick={() => void joinAs(slot.name)}
            >
              {slot.name}
            </button>
          ))}
        </div>
      )}

      <form className="stack" onSubmit={submit}>
        <label className="field">
          <span>Your name</span>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={40}
            autoComplete="off"
            disabled={busy || disabled}
          />
        </label>
        <button
          className="btn btn-primary btn-block"
          type="submit"
          disabled={busy || disabled || !name.trim()}
        >
          Join
        </button>
      </form>

      <ErrorNotice error={error} />
      {error?.status === 409 && (
        <Notice tone="info">
          If this is you on another device, ask the host to release your name. Then join again.
        </Notice>
      )}
    </section>
  )
}
