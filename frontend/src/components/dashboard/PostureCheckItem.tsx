/**
 * PostureCheckItem — a single row in the dashboard posture card.
 *
 * IMPL-0002 Milestone G5. Three visual states:
 *   - pass      → compact 1-line check
 *   - advisory  → muted informational row
 *   - fail      → expanded row with "Generate and open PR" CTA, but only
 *                 when checkName is a generator-supported check
 *                 (security_md or dependabot_config).
 */

export type PostureCheckStatus = 'pass' | 'advisory' | 'fail'
export type PostureCheckName =
  | 'security_md'
  | 'dependabot_config'
  | (string & {})

const GENERATOR_CHECKS = new Set<string>(['security_md', 'dependabot_config'])

export interface PostureCheckItemProps {
  checkName: PostureCheckName
  status: PostureCheckStatus
  label: string
  description?: string
  onGenerate?: (checkName: 'security_md' | 'dependabot_config') => void
  pending?: boolean
}

export default function PostureCheckItem({
  checkName,
  status,
  label,
  description,
  onGenerate,
  pending = false,
}: PostureCheckItemProps) {
  if (status === 'pass') {
    return (
      <li
        data-testid="posture-check-item"
        data-state="pass"
        className="flex items-center gap-2.5 py-1"
      >
        <span
          className="material-symbols-outlined text-tertiary"
          style={{ fontSize: '20px' }}
          aria-hidden
        >
          check_circle
        </span>
        <span className="text-sm font-medium text-on-surface">{label}</span>
      </li>
    )
  }

  if (status === 'advisory') {
    return (
      <li
        data-testid="posture-check-item"
        data-state="advisory"
        className="flex items-center gap-2.5 py-1"
      >
        <span
          className="material-symbols-outlined text-on-surface-variant"
          style={{ fontSize: '20px' }}
          aria-hidden
        >
          info
        </span>
        <span className="text-sm text-on-surface-variant">{label}</span>
      </li>
    )
  }

  // fail
  const canGenerate =
    GENERATOR_CHECKS.has(checkName) && typeof onGenerate === 'function'

  return (
    <li
      data-testid="posture-check-item"
      data-state="fail"
      className="flex flex-col gap-3 rounded-2xl bg-primary-container/25 p-4 lg:flex-row lg:items-start"
    >
      <span
        className="material-symbols-outlined text-error"
        style={{ fontSize: '20px' }}
        aria-hidden
      >
        error
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-on-surface">{label}</p>
        {description && (
          <p className="mt-1 text-sm text-on-surface-variant">{description}</p>
        )}
      </div>
      {canGenerate && (
        <button
          type="button"
          disabled={pending}
          onClick={() =>
            onGenerate?.(checkName as 'security_md' | 'dependabot_config')
          }
          className="inline-flex flex-shrink-0 self-start items-center gap-1.5 whitespace-nowrap rounded-full bg-primary px-4 py-2 text-sm font-semibold text-on-primary shadow-sm transition hover:bg-primary/90 disabled:opacity-60"
        >
          <span className="material-symbols-outlined text-sm" aria-hidden>
            play_arrow
          </span>
          {pending ? 'Opening…' : 'Generate and open PR'}
        </button>
      )}
    </li>
  )
}
