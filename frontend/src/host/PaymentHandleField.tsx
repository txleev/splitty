import { useEffect, useRef, useState } from 'react'
import type { PaymentPlatform } from '../api/types'
import { PlatformMark } from '../components/PlatformMark'
import { PLATFORM_LABEL } from '../lib/paymentLinks'

const PLATFORMS: PaymentPlatform[] = ['revolut', 'wise']

interface Props {
  handle: string
  platform: PaymentPlatform | null
  disabled: boolean
  onHandleChange: (handle: string) => void
  onPlatformChange: (platform: PaymentPlatform) => void
}

/** One field for the host's handle, with a dropdown beside it that says which app it belongs to. */
export function PaymentHandleField({
  handle,
  platform,
  disabled,
  onHandleChange,
  onPlatformChange,
}: Props) {
  return (
    <div className="field">
      <span>Payment handle (optional)</span>
      <div className="handle-row">
        <PlatformMenu value={platform} disabled={disabled} onChange={onPlatformChange} />
        <input
          className="grow"
          aria-label="Payment handle"
          value={handle}
          onChange={(event) => onHandleChange(event.target.value)}
          placeholder="Username or tag"
          maxLength={64}
          autoComplete="off"
          disabled={disabled}
        />
      </div>
    </div>
  )
}

function PlatformMenu({
  value,
  disabled,
  onChange,
}: {
  value: PaymentPlatform | null
  disabled: boolean
  onChange: (platform: PaymentPlatform) => void
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  // Close on a click outside the menu, or on Escape.
  useEffect(() => {
    if (!open) {
      return
    }
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }
    document.addEventListener('pointerdown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('pointerdown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const choose = (platform: PaymentPlatform) => {
    onChange(platform)
    setOpen(false)
  }

  return (
    <div className="platform-menu" ref={rootRef}>
      <button
        type="button"
        className="btn platform-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        {value ? (
          <span className="platform-choice">
            <PlatformMark platform={value} />
            {PLATFORM_LABEL[value]}
          </span>
        ) : (
          <span className="muted">Platform</span>
        )}
        <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div role="listbox" aria-label="Payment platform" className="platform-options">
          {PLATFORMS.map((option) => (
            <button
              key={option}
              type="button"
              role="option"
              aria-selected={option === value}
              className="platform-option"
              onClick={() => choose(option)}
            >
              <PlatformMark platform={option} />
              {PLATFORM_LABEL[option]}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
