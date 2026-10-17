import { useEffect, useState } from 'react'
import { GuestQrCode } from '../components/GuestQrCode'

interface Props {
  guestUrl: string
  // Guests can only join once the host has marked the split ready.
  ready: boolean
}

/** The invite: a QR code to scan and the link to copy, side by side. */
export function ShareCard({ guestUrl, ready }: Props) {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) {
      return
    }
    const timer = window.setTimeout(() => setCopied(false), 2000)
    return () => window.clearTimeout(timer)
  }, [copied])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(guestUrl)
      setCopied(true)
    } catch {
      // Clipboard access is blocked on some plain-http pages. The link can still be opened or held.
      setCopied(false)
    }
  }

  return (
    <section className="share" aria-label="Invite guests">
      <GuestQrCode value={guestUrl} />
      <div className="share-text">
        <h2>Let friends pick their items</h2>
        <p>Scan to join in a browser. No account or app needed.</p>
        <span className={`share-state ${ready ? '' : 'share-state-draft'}`}>
          <span className="share-dot" aria-hidden="true" />
          {ready ? 'Open for guests' : 'Guests can join once you mark it ready'}
        </span>
      </div>
      <div className="share-link">
        <a
          className="share-url"
          href={guestUrl}
          target="_blank"
          rel="noopener noreferrer"
          title="Open the guest page"
        >
          {guestUrl.replace(/^https?:\/\//, '')}
        </a>
        <button
          type="button"
          className={`btn btn-primary btn-small share-copy ${copied ? 'is-copied' : ''}`}
          onClick={() => void copy()}
        >
          {copied ? 'Copied ✓' : 'Copy link'}
        </button>
      </div>
    </section>
  )
}
