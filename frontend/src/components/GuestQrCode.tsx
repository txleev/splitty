import { QRCodeSVG } from 'qrcode.react'

interface Props {
  value: string
}

/**
 * A scannable code for the guest link, so people at the table can open the split on their phones
 * without typing the address. The code keeps its own white tile and dark ink, because scanners
 * need the contrast whatever the page theme is.
 */
export function GuestQrCode({ value }: Props) {
  return (
    <div className="qr-tile">
      <QRCodeSVG
        value={value}
        size={168}
        level="M"
        marginSize={3}
        fgColor="#2a1b24"
        bgColor="#ffffff"
        title={`QR code for ${value}`}
      />
    </div>
  )
}
