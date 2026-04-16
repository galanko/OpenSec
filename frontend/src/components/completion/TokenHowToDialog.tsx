import { useCallback, useEffect, useRef } from 'react'

export interface TokenHowToDialogProps {
  open: boolean
  onClose: () => void
}

/**
 * "How to create a token" modal (UX frame 1.1a).
 *
 * Scrim + backdrop blur overlay per the mockup. Five-step walkthrough with
 * a deep-link to github.com/settings/tokens. The modal owns focus while
 * open, Escape closes it, and `prefers-reduced-motion` suppresses the
 * fade-in. Lives under `components/completion/` because the completion
 * ceremony re-opens it for PAT rotation.
 */
export default function TokenHowToDialog({ open, onClose }: TokenHowToDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const previouslyFocusedRef = useRef<HTMLElement | null>(null)

  // Lock body scroll while open, restore focus on close.
  useEffect(() => {
    if (!open) return
    previouslyFocusedRef.current = document.activeElement as HTMLElement | null
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    queueMicrotask(() => closeButtonRef.current?.focus())

    return () => {
      document.body.style.overflow = prevOverflow
      previouslyFocusedRef.current?.focus?.()
    }
  }, [open])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
        return
      }
      if (e.key !== 'Tab' || !dialogRef.current) return
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )
      if (focusable.length === 0) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    },
    [onClose],
  )

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
      onKeyDown={handleKeyDown}
    >
      {/* Scrim + backdrop blur. Click closes the dialog. */}
      <button
        type="button"
        aria-label="Close dialog"
        onClick={onClose}
        className="absolute inset-0 bg-on-surface/50 backdrop-blur-sm motion-safe:transition-opacity"
      />

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="token-howto-title"
        aria-describedby="token-howto-subtitle"
        className="relative w-full max-w-xl bg-surface-container-lowest rounded-2xl shadow-2xl overflow-hidden motion-safe:animate-in motion-safe:fade-in"
      >
        {/* Header */}
        <div className="flex items-start gap-4 px-7 pt-7 pb-5">
          <div className="w-11 h-11 rounded-xl bg-primary-container/60 flex items-center justify-center flex-shrink-0">
            <span className="material-symbols-outlined text-primary" aria-hidden="true">
              vpn_key
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <h3
              id="token-howto-title"
              className="font-headline text-xl font-extrabold text-on-surface"
            >
              Create a GitHub personal access token
            </h3>
            <p
              id="token-howto-subtitle"
              className="text-sm text-on-surface-variant mt-1"
            >
              A 90-second walkthrough. The token lets OpenSec clone, push, and
              open pull requests — nothing else.
            </p>
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="p-1 rounded-lg hover:bg-surface-container-low flex-shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-container-lowest"
          >
            <span className="material-symbols-outlined text-on-surface-variant">
              close
            </span>
          </button>
        </div>

        {/* Steps */}
        <ol className="px-7 pb-6 space-y-4">
          <Step n={1}>
            <p className="text-sm text-on-surface leading-relaxed">
              Open your GitHub token settings.
            </p>
            <a
              href="https://github.com/settings/tokens"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-1.5 text-sm font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-container-lowest rounded"
            >
              github.com/settings/tokens
              <span className="material-symbols-outlined text-sm" aria-hidden="true">
                open_in_new
              </span>
            </a>
          </Step>

          <Step n={2}>
            <p className="text-sm text-on-surface leading-relaxed">
              Click <span className="font-semibold">Generate new token</span> →{' '}
              <span className="font-semibold">Classic</span>. Give it a name
              like{' '}
              <span className="font-mono bg-surface-container-low px-1.5 py-0.5 rounded text-xs">
                OpenSec · your-project
              </span>
              .
            </p>
          </Step>

          <Step n={3}>
            <p className="text-sm text-on-surface leading-relaxed mb-2">
              Under <span className="font-semibold">Select scopes</span>, check
              just one box:
            </p>
            <div className="rounded-lg bg-surface-container-low px-4 py-3 flex items-start gap-3">
              <span
                className="material-symbols-outlined text-tertiary mt-0.5"
                style={{ fontVariationSettings: "'FILL' 1" }}
                aria-hidden="true"
              >
                check_box
              </span>
              <div className="min-w-0">
                <p className="font-mono text-sm font-semibold text-on-surface">
                  repo
                </p>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  Full control of private repositories — required to clone,
                  push, and open pull requests.
                </p>
              </div>
            </div>
          </Step>

          <Step n={4}>
            <p className="text-sm text-on-surface leading-relaxed">
              Set the expiration to whatever you're comfortable with — 90 days
              is a reasonable default.
            </p>
          </Step>

          <Step n={5}>
            <p className="text-sm text-on-surface leading-relaxed">
              Click <span className="font-semibold">Generate token</span>, copy
              the value that starts with{' '}
              <span className="font-mono">ghp_</span>, and paste it back into
              OpenSec.
            </p>
          </Step>
        </ol>

        {/* Footer */}
        <div className="px-7 py-4 bg-surface-container-low flex items-start gap-3">
          <span
            className="material-symbols-outlined text-tertiary text-sm mt-0.5"
            aria-hidden="true"
          >
            lock
          </span>
          <p className="text-xs text-on-surface-variant leading-relaxed">
            Tokens are stored locally in your OpenSec vault. They never leave
            this machine and are never logged.
          </p>
        </div>
      </div>
    </div>
  )
}

function Step({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-4">
      <span
        className="w-7 h-7 rounded-full bg-primary text-white font-bold text-sm flex items-center justify-center flex-shrink-0"
        aria-hidden="true"
      >
        {n}
      </span>
      <div className="flex-1 min-w-0">{children}</div>
    </li>
  )
}
