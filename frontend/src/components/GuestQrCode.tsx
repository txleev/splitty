import { QRCodeSVG } from 'qrcode.react'

interface Props {
  value: string
}

/**
 * A scannable code for the guest link, so people at the table can open the split on their phones
 * without typing the address. The code keeps its own white background, because scanners need the
 * contrast even when the page is in dark mode.
 */
export function GuestQrCode({ value }: Props) {
  return (
    <div className="qr-block">
      <div className="qr-frame">
        <QRCodeSVG value={value} size={176} level="M" marginSize={4} title={`QR code for ${value}`} />
      </div>
      <p className="muted small">Scan with a phone camera to open the split.</p>
    </div>
  )
}
