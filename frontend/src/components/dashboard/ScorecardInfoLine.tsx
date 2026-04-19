/**
 * ScorecardInfoLine — static footer info line on the dashboard pointing at
 * the OpenSSF Scorecard project. This is the ONE place in Session E where
 * the word "badge" may appear, because it references the external Scorecard
 * security badge generically. See UX-0002 vocabulary table.
 *
 * IMPL-0002 Milestone G2.
 */

export interface ScorecardInfoLineProps {
  scorecardUrl?: string
}

const DEFAULT_URL = 'https://github.com/ossf/scorecard'

export default function ScorecardInfoLine({
  scorecardUrl = DEFAULT_URL,
}: ScorecardInfoLineProps) {
  return (
    <aside
      data-testid="ScorecardInfoLine"
      className="flex items-start gap-3 rounded-2xl bg-primary-container/25 px-5 py-4"
    >
      <span
        className="material-symbols-outlined flex-none text-primary"
        aria-hidden
      >
        info
      </span>

      <p className="text-sm text-on-surface-variant">
        Want an independent second opinion? OpenSSF Scorecard grades open
        source projects against an industry-wide checklist and can issue a
        public security badge.{' '}
        <a
          href={scorecardUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 font-semibold text-primary hover:underline"
        >
          Learn more
          <span className="material-symbols-outlined text-sm" aria-hidden>
            open_in_new
          </span>
        </a>
      </p>
    </aside>
  )
}
