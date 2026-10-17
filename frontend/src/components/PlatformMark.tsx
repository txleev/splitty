import type { PaymentPlatform } from '../api/types'
import { PLATFORM_LABEL } from '../lib/paymentLinks'

/**
 * A letter badge in the app's colour. It stands in for the app's logo until official artwork is
 * added. It is hidden from screen readers, because the label next to it already names the app.
 */
export function PlatformMark({ platform }: { platform: PaymentPlatform }) {
  return (
    <span className={`platform-mark platform-${platform}`} aria-hidden="true">
      {PLATFORM_LABEL[platform].charAt(0)}
    </span>
  )
}
