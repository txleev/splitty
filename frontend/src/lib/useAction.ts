import { useCallback, useState } from 'react'
import { ApiError } from '../api/client'
import type { Session } from '../api/types'

/**
 * Runs one request that changes a split. While it runs, the caller's buttons stay disabled. On
 * success the returned split is applied. On failure the error is kept for the panel to show.
 */
export function useAction(applySession: (session: Session) => void) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const run = useCallback(
    async (action: () => Promise<Session>): Promise<boolean> => {
      setBusy(true)
      setError(null)
      try {
        applySession(await action())
        return true
      } catch (caught) {
        setError(
          caught instanceof ApiError
            ? caught
            : new ApiError(0, 'Something went wrong. Try again.'),
        )
        return false
      } finally {
        setBusy(false)
      }
    },
    [applySession],
  )

  return { busy, error, run }
}
