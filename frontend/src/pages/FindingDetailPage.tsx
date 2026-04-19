/**
 * FindingDetailPage — plain-language detail view for a single finding
 * (frame 3.2).
 *
 * IMPL-0002 Milestone G4. Reuses the existing useFinding hook from
 * @/api/hooks. The technical metadata lives in the collapsible
 * TechnicalDetailsPanel so the primary read stays human-friendly.
 */

import { Link, useNavigate, useParams } from 'react-router'
import { useFinding } from '@/api/hooks'
import ErrorBoundary from '@/components/ErrorBoundary'
import ErrorState from '@/components/ErrorState'
import PageShell from '@/components/PageShell'
import PageSpinner from '@/components/PageSpinner'
import SeverityBadge from '@/components/SeverityBadge'
import TechnicalDetailsPanel from '@/components/TechnicalDetailsPanel'

export default function FindingDetailPage() {
  return (
    <ErrorBoundary
      fallbackTitle="Finding error"
      fallbackSubtitle="Something went wrong loading this finding."
    >
      <FindingDetailContent />
    </ErrorBoundary>
  )
}

function FindingDetailContent() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: finding, isLoading, isError, refetch } = useFinding(id)

  if (isError) {
    return (
      <PageShell title="Finding">
        <ErrorState
          title="Couldn't load this finding"
          subtitle="Please try again or go back to the findings queue."
          onRetry={() => refetch()}
        />
      </PageShell>
    )
  }

  if (isLoading || !finding) {
    return (
      <PageShell title="Finding">
        <PageSpinner />
      </PageShell>
    )
  }

  const body = finding.plain_description ?? finding.description ?? ''

  return (
    <PageShell
      title={finding.title}
      subtitle={finding.asset_label ?? undefined}
      actions={
        <Link
          to="/findings"
          className="inline-flex items-center gap-1.5 rounded-full bg-surface-container px-4 py-2 text-sm font-medium text-on-surface hover:bg-surface-container-high"
        >
          <span className="material-symbols-outlined text-sm" aria-hidden>
            arrow_back
          </span>
          Back to findings
        </Link>
      }
    >
      <div className="max-w-3xl">
        <SeverityBadge severity={finding.raw_severity} />
        {body && (
          <p className="mt-5 whitespace-pre-wrap text-base leading-relaxed text-on-surface">
            {body}
          </p>
        )}

        <TechnicalDetailsPanel
          sourceId={finding.source_id}
          rawPayload={finding.raw_payload}
        />

        <div className="mt-8 flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(`/findings`)}
            className="rounded-full bg-surface-container px-5 py-2.5 text-sm font-medium text-on-surface hover:bg-surface-container-high"
          >
            Cancel
          </button>
        </div>
      </div>
    </PageShell>
  )
}
