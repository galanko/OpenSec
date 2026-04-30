/**
 * MigrationBanner — Phase 1 (PRD-0006) component.
 *
 * Announces the new pinned Review section above the Issues page. Dismiss
 * persists per session in `sessionStorage` (key
 * `opensec.issues.migrationBannerDismissed`); a fresh tab brings the banner
 * back so first-day users still see the change.
 *
 * Mirrors P1MigrationBanner in
 * `frontend/mockups/claude-design/PRD-0006/issues-page/phase1.jsx`.
 */
import { useState, type ReactElement } from 'react'

const STORAGE_KEY = 'opensec.issues.migrationBannerDismissed'
const ROADMAP_URL =
  'https://github.com/galanko/OpenSec/blob/main/docs/product/prds/PRD-0006-issues-page-and-dashboard.md'

export function MigrationBanner(): ReactElement | null {
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem(STORAGE_KEY) === '1',
  )

  if (dismissed) return null

  const dismiss = (): void => {
    sessionStorage.setItem(STORAGE_KEY, '1')
    setDismissed(true)
  }

  return (
    <div
      className="mx-8 mt-2 mb-4 rounded-xl px-4 py-3 flex items-start gap-3 bg-primary-container text-on-primary-container"
    >
      <span
        aria-hidden="true"
        className="material-symbols-outlined"
        style={{ fontSize: 18, fontVariationSettings: "'FILL' 1" }}
      >
        auto_awesome
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[12.5px] font-bold mb-0.5">
          New: Review section pinned to the top
        </div>
        <p className="text-[11.5px] leading-relaxed">
          Plans and PRs that need your call now live in one block above the rest of
          the queue. The full Issues redesign lands after the alpha.{' '}
          <a
            href={ROADMAP_URL}
            target="_blank"
            rel="noreferrer"
            className="underline font-semibold"
          >
            See what&apos;s coming &rarr;
          </a>
        </p>
      </div>
      <button
        type="button"
        onClick={dismiss}
        aria-label="Dismiss"
        className="rounded-md p-1 hover:bg-black/5"
      >
        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
          close
        </span>
      </button>
    </div>
  )
}
