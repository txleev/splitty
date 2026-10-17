import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { createSession } from '../api/sessions'
import { messageOf } from '../api/client'
import { Notice } from '../components/ui'
import { saveHostToken } from '../lib/storage'

export function HomePage() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file) {
      setError('Choose a receipt photo first.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const created = await createSession(file, note)
      saveHostToken(created.session_id, created.host_token)
      // The token also travels in the navigation state, in case the browser blocks storage.
      navigate(`/s/${created.session_id}/host`, { state: { hostToken: created.host_token } })
    } catch (caught) {
      setError(messageOf(caught))
      setBusy(false)
    }
  }

  return (
    <>
      <section className="card">
        <h1>Split a receipt</h1>
        <p className="muted">
          Take a photo of the receipt. We read the items, you check them, then you share a link with
          everyone at the table.
        </p>
      </section>

      <form className="card stack" onSubmit={submit}>
        <label className="field">
          <span>Receipt photo</span>
          <input
            type="file"
            accept="image/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            disabled={busy}
            required
          />
        </label>

        <label className="field">
          <span>Notes (optional)</span>
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Who ordered what, e.g. Ana had the soup, Ben the steak"
            maxLength={2000}
            disabled={busy}
          />
        </label>

        {error && <Notice tone="error">{error}</Notice>}
        {busy && (
          <Notice>Reading the receipt. This can take up to a minute. Keep this page open.</Notice>
        )}

        <button className="btn btn-primary btn-block" type="submit" disabled={busy || !file}>
          {busy ? 'Reading…' : 'Read receipt'}
        </button>
      </form>
    </>
  )
}
