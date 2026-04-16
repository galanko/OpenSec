import { useCallback, useRef } from 'react'
import { api } from '../../api/client'

export type ShareAction = 'download' | 'copy_text' | 'copy_markdown'

/**
 * Runs a share-action handler exactly once per user intent.
 *
 * The in-flight Set is held for the entire handler — not just the POST —
 * so a double-click whose second event lands before the first handler
 * settles is a deterministic no-op, regardless of network speed. Failures
 * are swallowed with `console.warn` so a flaky POST never blocks the copy
 * or download the user is actually taking.
 */
export function useShareAction(completionId: string | null) {
  const inflight = useRef<Set<ShareAction>>(new Set())

  return useCallback(
    async (action: ShareAction, sideEffect: () => Promise<void> | void): Promise<void> => {
      if (inflight.current.has(action)) return
      inflight.current.add(action)
      try {
        await sideEffect()
        if (completionId) {
          try {
            await api.recordShareAction(completionId, action)
          } catch (err) {
            console.warn('share-action recording failed:', err)
          }
        }
      } finally {
        inflight.current.delete(action)
      }
    },
    [completionId],
  )
}
