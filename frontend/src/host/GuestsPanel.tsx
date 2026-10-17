import { useState, type FormEvent } from 'react'
import { addMember, releaseMember, removeMember, unlockMember } from '../api/sessions'
import type { Member, Session } from '../api/types'
import { ErrorNotice } from '../components/ui'
import { useAction } from '../lib/useAction'

interface Props {
  session: Session
  hostToken: string
  applySession: (session: Session) => void
}

function memberStatus(member: Member): string {
  if (!member.joined) return 'Not joined yet'
  if (member.confirmation === 'confirmed') return 'Confirmed'
  if (member.confirmation === 'needs_reconfirm') return 'Changed, needs to confirm again'
  return 'Joined, not confirmed'
}

export function GuestsPanel({ session, hostToken, applySession }: Props) {
  const action = useAction(applySession)
  const [name, setName] = useState('')
  const sessionId = session.session_id

  const add = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const cleaned = name.trim()
    if (!cleaned) {
      return
    }
    if (await action.run(() => addMember(sessionId, hostToken, cleaned))) {
      setName('')
    }
  }

  const remove = (member: Member) => {
    if (window.confirm(`Remove ${member.name}? Any claims they made are removed too.`)) {
      void action.run(() => removeMember(sessionId, hostToken, member.id))
    }
  }

  const release = (member: Member) => {
    const message = `Release ${member.name}? Their browser loses access. Their claims stay, and joining with the same name takes this slot back.`
    if (window.confirm(message)) {
      void action.run(() => releaseMember(sessionId, hostToken, member.id))
    }
  }

  return (
    <section className="card stack">
      <h2>Guests</h2>
      <p className="muted small">
        Add a name for each person at the table. Guests pick their name when they open the link.
      </p>
      <ErrorNotice error={action.error} />

      {session.members.length === 0 && <p className="muted">No guests yet.</p>}
      <ul className="plain-list">
        {session.members.map((member) => (
          <li key={member.id} className="member-row">
            <div>
              <strong>{member.name}</strong>
              <div className="muted small">{memberStatus(member)}</div>
            </div>
            <div className="row">
              {member.joined ? (
                <button
                  type="button"
                  className="btn btn-small btn-danger"
                  disabled={action.busy}
                  onClick={() => release(member)}
                >
                  Release
                </button>
              ) : (
                <button
                  type="button"
                  className="btn btn-small btn-danger"
                  disabled={action.busy}
                  onClick={() => remove(member)}
                >
                  Remove
                </button>
              )}
              {member.confirmation === 'confirmed' && (
                <button
                  type="button"
                  className="btn btn-small"
                  disabled={action.busy}
                  onClick={() => void action.run(() => unlockMember(sessionId, hostToken, member.id))}
                >
                  Ask to confirm again
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      <form className="row" onSubmit={add}>
        <input
          className="grow"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Guest name"
          maxLength={40}
          disabled={action.busy}
        />
        <button type="submit" className="btn" disabled={action.busy || !name.trim()}>
          Add guest
        </button>
      </form>
    </section>
  )
}
