import { useCallback, useRef, useState } from 'react'
import { api } from '../../api/client'

export type ShareAction = 'download' | 'copy_text' | 'copy_markdown'

/**
 * Records share-actions to the backend fire-and-forget, and provides an
 * exclusive-run helper so the surrounding click handler can be de-duplicated
 * too.
 *
 * Invariants:
 *  - Exactly one POST per user intent. A second click on the same action
 *    while the first handler is still running is a deterministic no-op —
 *    the in-flight Set is held for the entire handler, not just the POST,
 *    so even instant-resolving network mocks (MSW) can't sneak a dupe past.
 *  - Buttons stay enabled (no `disabled` attribute) so screen readers keep
 *    them in the focus order; `isPending(action)` is exposed for optional
 *    spinner affordance.
 *  - Failures are swallowed with `console.warn` by design — fire-and-forget
 *    recording must never block the copy/download action the user is taking.
 */
export function useShareAction(completionId: string | null) {
  const inflight = useRef<Set<ShareAction>>(new Set())
  const [pending, setPending] = useState<Set<ShareAction>>(new Set())

  /**
   * Run `fn` exclusively for the given action. Second calls for the same
   * action while the first is still in-flight are no-ops.
   *
   * `record` is called as part of the exclusive window, BEFORE `fn`'s own
   * side-effects (clipboard write, download trigger) are tried, because the
   * dedupe only works if the whole handler body sits inside the window.
   */
  const runExclusive = useCallback(
    async (action: ShareAction, fn: () => Promise<void> | void): Promise<void> => {
      if (inflight.current.has(action)) return
      inflight.current.add(action)
      setPending(new Set(inflight.current))
      try {
        await fn()
      } finally {
        inflight.current.delete(action)
        setPending(new Set(inflight.current))
      }
    },
    [],
  )

  /** Plain fire-and-forget POST; used inside `runExclusive` by callers. */
  const record = useCallback(
    async (action: ShareAction): Promise<void> => {
      if (!completionId) return
      try {
        await api.recordShareAction(completionId, action)
      } catch (err) {
        console.warn('share-action recording failed:', err)
      }
    },
    [completionId],
  )

  const isPending = useCallback(
    (action: ShareAction) => pending.has(action),
    [pending],
  )

  return { runExclusive, record, isPending }
}
