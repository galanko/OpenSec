import { type VerifiedRepoSummary } from '@/api/onboarding'

export interface ConnectionResultCardProps {
  verified: VerifiedRepoSummary
  /** Called when the user clicks "Change" to re-open the form. */
  onChange: () => void
}

/**
 * Compact 3-column verified metadata card (UX frame 1.3). Tonal layering
 * only — no borders. Three cells separated by generous padding.
 */
export default function ConnectionResultCard({
  verified,
  onChange,
}: ConnectionResultCardProps) {
  return (
    <div className="w-full rounded-2xl bg-surface-container-lowest shadow-sm px-6 py-6">
      <div className="flex items-start gap-3">
        <span
          className="material-symbols-outlined text-tertiary mt-0.5"
          aria-hidden="true"
          style={{ fontVariationSettings: "'FILL' 1" }}
        >
          check_circle
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-mono text-sm font-semibold text-on-surface truncate">
            {verified.repo_name}
          </p>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Verified · we can clone and open pull requests
          </p>
        </div>
        <button
          type="button"
          onClick={onChange}
          className="text-xs font-semibold text-on-surface-variant hover:text-on-surface px-2 py-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
        >
          Change
        </button>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-4">
        <DetailCell label="Visibility" value={verified.visibility} />
        <DetailCell label="Default branch" value={verified.default_branch} />
        <DetailCell
          label="Permissions"
          value={verified.permissions?.join(', ') || '—'}
        />
      </div>
    </div>
  )
}

function DetailCell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">
        {label}
      </p>
      <p className="text-sm font-semibold text-on-surface mt-1 truncate">
        {value}
      </p>
    </div>
  )
}
