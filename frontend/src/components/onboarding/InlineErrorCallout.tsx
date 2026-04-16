import { type ReactNode } from 'react'

export interface InlineErrorCalloutProps {
  title: string
  body: ReactNode
  /** Optional deep-link shown as a small "Learn more" action. */
  action?: {
    label: string
    href: string
  }
}

/**
 * Rounded `error-container/20` alert used on UX frame 1.2 (missing `repo`
 * scope) and as a generic inline callout. Announced via `aria-live="polite"`.
 */
export default function InlineErrorCallout({
  title,
  body,
  action,
}: InlineErrorCalloutProps) {
  return (
    <div
      role="alert"
      aria-live="polite"
      className="mt-4 rounded-lg bg-error-container/20 px-4 py-3 flex items-start gap-3"
    >
      <span
        className="material-symbols-outlined text-error flex-shrink-0"
        aria-hidden="true"
      >
        error
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-on-surface">{title}</p>
        <div className="text-sm text-on-surface-variant mt-1 leading-relaxed">
          {body}
        </div>
        {action && (
          <a
            href={action.href}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-2 text-sm font-semibold text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface rounded"
          >
            {action.label}
            <span className="material-symbols-outlined text-sm" aria-hidden="true">
              open_in_new
            </span>
          </a>
        )}
      </div>
    </div>
  )
}
