import { useEffect, useRef, useState } from 'react'
import ActionButton from './ActionButton'

interface PermissionApprovalCardProps {
  tool: string
  patterns: string[]
  onApprove: () => void
  onDeny: () => void
  loading?: boolean
  error?: string | null
  timeoutSeconds?: number
}

export default function PermissionApprovalCard({
  tool,
  patterns,
  onApprove,
  onDeny,
  loading = false,
  error = null,
  timeoutSeconds = 120,
}: PermissionApprovalCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const [remaining, setRemaining] = useState(timeoutSeconds)
  const timedOut = remaining <= 0

  // Auto-focus when the card appears
  useEffect(() => {
    cardRef.current?.focus()
  }, [])

  // Countdown timer
  useEffect(() => {
    if (timedOut || loading) return
    const interval = setInterval(() => {
      setRemaining((prev) => Math.max(0, prev - 1))
    }, 1000)
    return () => clearInterval(interval)
  }, [timedOut, loading])

  const minutes = Math.floor(remaining / 60)
  const seconds = remaining % 60
  const timeDisplay = `${minutes}:${String(seconds).padStart(2, '0')}`

  // Update aria-live text less frequently to avoid spamming screen readers
  const ariaTimeText = timedOut
    ? 'Timed out'
    : remaining % 30 === 0 || remaining <= 10
      ? `${timeDisplay} remaining`
      : undefined

  return (
    <div className="max-w-3xl self-start">
      <div
        ref={cardRef}
        tabIndex={-1}
        role="alert"
        className="bg-tertiary-container/40 rounded-xl p-5 border border-outline-variant/15 shadow-sm outline-none"
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <span className="material-symbols-outlined text-tertiary text-xl">
            shield
          </span>
          <h3 className="text-sm font-bold text-on-surface tracking-tight">
            Tool approval required
          </h3>
        </div>

        {/* Tool info */}
        <div className="mb-3">
          <p className="text-sm text-on-surface-variant">
            Agent wants to use: <span className="font-semibold text-on-surface">{tool}</span>
          </p>
        </div>

        {/* Command patterns */}
        {patterns.length > 0 && (
          <div className="bg-surface-container-lowest/80 rounded-lg p-3 mb-4 border border-outline-variant/10">
            <div className="space-y-1">
              {patterns.map((pattern, i) => (
                <code key={i} className="block text-xs font-mono text-on-surface-variant">
                  {pattern}
                </code>
              ))}
            </div>
          </div>
        )}

        {/* Countdown timer */}
        <div className="mb-4" aria-live="polite">
          {timedOut ? (
            <p className="text-xs text-error font-medium">Timed out</p>
          ) : (
            <p className="text-xs text-on-surface-variant">
              {ariaTimeText ?? `${timeDisplay} remaining`}
            </p>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-error-container/20 rounded-lg p-3 mb-4">
            <p className="text-xs text-error">{error}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3">
          <ActionButton
            label="Deny"
            icon="close"
            variant="outline"
            onClick={onDeny}
            disabled={loading || timedOut}
          />
          <ActionButton
            label="Approve"
            icon="check"
            variant="primary"
            onClick={onApprove}
            disabled={loading || timedOut}
          />
        </div>
      </div>
    </div>
  )
}
