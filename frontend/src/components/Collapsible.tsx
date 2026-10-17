import { useEffect, useId, useState, type ReactNode } from 'react'

interface Props {
  title: string
  // A short line beside the title, so a closed section still tells you what is inside.
  summary?: ReactNode
  defaultOpen?: boolean
  // "card" is a section of its own. "inline" is a quiet toggle inside another card.
  variant?: 'card' | 'inline'
  children: ReactNode
}

const ANIMATION_MS = 340

/**
 * A section that folds away. The content stays mounted while closed, so a half-filled form keeps
 * its values, and `inert` keeps it out of reach of the keyboard and screen readers.
 */
export function Collapsible({
  title,
  summary,
  defaultOpen = false,
  variant = 'card',
  children,
}: Props) {
  const [open, setOpen] = useState(defaultOpen)
  // The panel clips its content to animate its height. Once it has finished opening it stops
  // clipping, so a dropdown inside can extend past the edge.
  const [settled, setSettled] = useState(defaultOpen)
  const panelId = useId()

  useEffect(() => {
    if (!open) {
      return
    }
    const timer = window.setTimeout(() => setSettled(true), ANIMATION_MS)
    return () => window.clearTimeout(timer)
  }, [open])

  const toggle = () => {
    if (open) {
      setSettled(false)
    }
    setOpen(!open)
  }

  const Heading = variant === 'card' ? 'h2' : 'h3'
  const classes = [
    'collapsible',
    variant === 'card' ? 'card' : 'collapsible-inline',
    open ? 'is-open' : '',
    open && settled ? 'is-settled' : '',
  ]

  return (
    <section className={classes.filter(Boolean).join(' ')}>
      <Heading className="collapsible-title">
        <button
          type="button"
          className="collapsible-trigger"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={toggle}
        >
          <span className="collapsible-heading">{title}</span>
          {summary && <span className="collapsible-summary">{summary}</span>}
          <svg
            className="collapsible-chevron"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      </Heading>
      <div id={panelId} className="collapsible-panel" inert={!open}>
        <div className="collapsible-inner">
          <div className="stack collapsible-body">{children}</div>
        </div>
      </div>
    </section>
  )
}
