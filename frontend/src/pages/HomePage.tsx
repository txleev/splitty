import { useEffect, useId, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router'
import { createSession } from '../api/sessions'
import { messageOf } from '../api/client'
import { Collapsible } from '../components/Collapsible'
import { Notice } from '../components/ui'
import { saveHostToken } from '../lib/storage'

export function HomePage() {
  const navigate = useNavigate()
  const fileId = useId()
  const [file, setFile] = useState<File | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // A preview of the chosen photo. The address is released when the photo changes or the page closes.
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview)
      }
    }
  }, [preview])

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
      <header className="hero">
        <p className="eyebrow">Split a receipt</p>
        <h1 className="display">
          Good meal.
          <br />
          Easy split.
        </h1>
        <p className="lead">
          Take a photo of the receipt. We read the items, you check them, then everyone at the table
          picks theirs from a link.
        </p>
      </header>

      <form className="stack" onSubmit={submit}>
        <label className="dropzone" htmlFor={fileId}>
          <input
            id={fileId}
            className="visually-hidden"
            type="file"
            accept="image/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            disabled={busy}
          />
          <div className="stage">
            <span className="corner corner-tl" />
            <span className="corner corner-tr" />
            <span className="corner corner-bl" />
            <span className="corner corner-br" />
            {preview ? (
              <div className="paper paper-photo">
                <img src={preview} alt="The receipt you chose" />
                {busy && <span className="scan" />}
              </div>
            ) : (
              <ReceiptSketch />
            )}
            {file && <span className="stage-caption">{file.name}</span>}
          </div>
        </label>

        {!file && (
          <label htmlFor={fileId} className="btn btn-primary btn-block">
            <CameraIcon />
            Choose receipt photo
          </label>
        )}

        {file && (
          <Collapsible variant="inline" title="Add a note" summary="optional">
            <textarea
              aria-label="Notes"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Who ordered what, e.g. Ana had the soup, Ben the steak"
              maxLength={2000}
              disabled={busy}
            />
          </Collapsible>
        )}

        {error && <Notice tone="error">{error}</Notice>}
        {busy && (
          <p className="working" role="status">
            Reading the receipt. This can take up to a minute, so keep this page open.
          </p>
        )}

        {file && (
          <div className="stack">
            <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
              {busy ? 'Reading…' : 'Read receipt'}
            </button>
            {!busy && (
              <label htmlFor={fileId} className="btn btn-ghost btn-block">
                Choose a different photo
              </label>
            )}
          </div>
        )}
      </form>

      {!file && (
        <>
          <section className="card features">
            <Feature icon={<ScanIcon />} title="We read it for you">
              Items, tax and tip come straight off the photo.
            </Feature>
            <Feature icon={<QrIcon />} title="Share a link or QR">
              Friends pick their items in the browser, live.
            </Feature>
            <Feature icon={<ArrowIcon />} title="Pay back in one tap">
              Revolut or Wise, prefilled with the exact amount.
            </Feature>
          </section>
          <p className="fineprint">No account. No app install. Just a browser.</p>
        </>
      )}
    </>
  )
}

/** A made-up receipt, drawn with bars, so the empty stage has something to look at. */
function ReceiptSketch() {
  const widths = [
    ['58%', '16%'],
    ['44%', '14%'],
    ['66%', '16%'],
    ['50%', '14%'],
  ]
  return (
    <div className="paper" aria-hidden="true">
      <span className="paper-head" />
      {widths.map(([name, price], index) => (
        <div className="paper-line" key={index}>
          <span className="paper-bar" style={{ width: name }} />
          <span className="paper-bar" style={{ width: price }} />
        </div>
      ))}
      <div className="paper-rule" />
      <div className="paper-line paper-total">
        <span className="paper-bar" style={{ width: '30%' }} />
        <span className="paper-bar" style={{ width: '24%' }} />
      </div>
    </div>
  )
}

function Feature({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="feature">
      <span className="feature-icon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <strong>{title}</strong>
        <span className="muted small">{children}</span>
      </div>
    </div>
  )
}

const iconProps = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
} as const

function CameraIcon() {
  return (
    <svg {...iconProps}>
      <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
      <circle cx="12" cy="13" r="3.5" />
    </svg>
  )
}

function ScanIcon() {
  return (
    <svg {...iconProps}>
      <path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3" />
      <path d="M8 12h8" />
    </svg>
  )
}

function QrIcon() {
  return (
    <svg {...iconProps}>
      <rect x="4" y="4" width="6" height="6" rx="1" />
      <rect x="14" y="4" width="6" height="6" rx="1" />
      <rect x="4" y="14" width="6" height="6" rx="1" />
      <path d="M14 14h2v2h-2zM18 18h2M18 14v0M14 18v2" />
    </svg>
  )
}

function ArrowIcon() {
  return (
    <svg {...iconProps}>
      <path d="M7 17 17 7M9 7h8v8" />
    </svg>
  )
}
