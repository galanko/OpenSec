/**
 * IssuesPage — Phase 1 (PRD-0006).
 *
 * Replaces FindingsPage. Four sections in this order:
 *
 *   1. Needs your review — pinned at the top, primary-container framing.
 *   2. In progress       — collapsed by default with a stage-breakdown
 *                          summary; persists in sessionStorage.
 *   3. Todo              — flat, primary "Start" action per row.
 *   4. Done              — flat, dim, max 4 visible (rest behind "Show all").
 *
 * Click anywhere on a row (or on its action button) navigates to the existing
 * Workspace page — Phase 1 keeps `/workspace/:id` reachable. The side panel
 * lands in Phase 2.
 *
 * Reuses `useFindings({ scope: 'current' })` (no new query), the existing
 * Solve flow (createWorkspace + repo guard), and `useDashboard()` for the
 * grade letter shown in the IssuesHeader caption.
 */
import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import type { Finding } from '../api/client'
import { api } from '../api/client'
import { useDashboard } from '../api/dashboard'
import { useFindings, useIntegrations, useAllIntegrationsHealth } from '../api/hooks'
import EmptyState from '../components/EmptyState'
import ErrorBoundary from '../components/ErrorBoundary'
import ErrorState from '../components/ErrorState'
import ImportDialog from '../components/ImportDialog'
import { IssueCountBadge } from '../components/issues/IssueCountBadge'
import { IssueRow } from '../components/issues/IssueRow'
import { IssuesHeader, type SeverityFilter } from '../components/issues/IssuesHeader'
import { MigrationBanner } from '../components/issues/MigrationBanner'

const IN_PROGRESS_OPEN_KEY = 'opensec.issues.inProgressOpen'
const DONE_VISIBLE_LIMIT = 4

export default function IssuesPage() {
  return (
    <ErrorBoundary
      fallbackTitle="Issues error"
      fallbackSubtitle="Something went wrong loading issues."
    >
      <IssuesPageContent />
    </ErrorBoundary>
  )
}

function IssuesPageContent() {
  const navigate = useNavigate()
  const [solving, setSolving] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [importOpen, setImportOpen] = useState(false)
  const [showRepoGuard, setShowRepoGuard] = useState(false)
  const [pendingFinding, setPendingFinding] = useState<Finding | null>(null)
  const [doneExpanded, setDoneExpanded] = useState(false)
  const [inProgressOpen, setInProgressOpen] = useState(
    () => sessionStorage.getItem(IN_PROGRESS_OPEN_KEY) === '1',
  )

  const { data: integrations } = useIntegrations()
  const { data: healthStatuses } = useAllIntegrationsHealth(
    (integrations?.length ?? 0) > 0,
  )
  const githubInt = integrations?.find((i) => i.provider_name === 'GitHub')
  const githubHealth = healthStatuses?.find((h) => h.integration_id === githubInt?.id)
  const repoConfigured =
    !!githubInt?.config?.repo_url && githubHealth?.credential_status === 'ok'

  const { data: dashboard } = useDashboard()
  const grade = dashboard?.grade ?? null

  // ``has_workspace: false`` is intentionally NOT passed (unlike the legacy
  // FindingsPage). Issues page needs findings WITH workspaces too — they're
  // what populate Review, In progress, and Done. ``scope: 'current'`` keeps
  // posture rows out of the response (Phase 1 is vulnerability-only).
  // ``refetchIntervalMs: 5000`` polls every 5s so rows visibly transition
  // between sections as agents progress — no manual refresh needed.
  const {
    data: findings,
    isLoading,
    isError,
    refetch,
  } = useFindings({ scope: 'current', refetchIntervalMs: 5000 })

  const { sections, inProgressBreakdown, totalIssues } = useMemo(() => {
    const review: Finding[] = []
    const inProgress: Finding[] = []
    const todo: Finding[] = []
    const done: Finding[] = []
    const breakdown = { planning: 0, generating: 0, opening_pr: 0, validating: 0 }
    let total = 0
    for (const f of findings ?? []) {
      if (
        severityFilter !== 'all' &&
        (f.raw_severity ?? '').toLowerCase() !== severityFilter
      ) {
        continue
      }
      total += 1
      const section = f.derived?.section ?? 'todo'
      if (section === 'review') review.push(f)
      else if (section === 'in_progress') {
        inProgress.push(f)
        const stage = f.derived?.stage
        if (stage && stage in breakdown) {
          breakdown[stage as keyof typeof breakdown] += 1
        }
      } else if (section === 'done') done.push(f)
      else todo.push(f)
    }
    return {
      sections: { review, inProgress, todo, done },
      inProgressBreakdown: breakdown,
      totalIssues: total,
    }
  }, [findings, severityFilter])

  const startWorkspace = useCallback(
    async (finding: Finding) => {
      // Existing workspace? Just navigate.
      const existing = finding.derived?.workspace_id
      if (existing) {
        navigate(`/workspace/${existing}`)
        return
      }
      setSolving(finding.id)
      try {
        const workspace = await api.createWorkspace({ finding_id: finding.id })
        navigate(`/workspace/${workspace.id}`)
      } catch (err) {
        console.error('Failed to create workspace:', err)
        setSolving(null)
      }
    },
    [navigate],
  )

  const handleActivate = useCallback(
    (finding: Finding) => {
      // If a workspace already exists, skip the GitHub-integration guard —
      // the agent has run before so the user has already moved past it.
      if (finding.derived?.workspace_id) {
        navigate(`/workspace/${finding.derived.workspace_id}`)
        return
      }
      if (!repoConfigured) {
        setPendingFinding(finding)
        setShowRepoGuard(true)
        return
      }
      void startWorkspace(finding)
    },
    [navigate, repoConfigured, startWorkspace],
  )

  const toggleInProgress = useCallback(() => {
    setInProgressOpen((prev) => {
      const next = !prev
      sessionStorage.setItem(IN_PROGRESS_OPEN_KEY, next ? '1' : '0')
      return next
    })
  }, [])

  if (isError) {
    return (
      <div className="bg-background min-h-screen">
        <ErrorState
          title="Couldn't load issues"
          subtitle="There was a problem fetching your issues. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const allFindings = findings ?? []
  const showEmptyReviewCard =
    sections.review.length === 0 &&
    sections.inProgress.length + sections.todo.length + sections.done.length > 0
  const allRepoEmpty = !isLoading && allFindings.length === 0

  return (
    <div className="bg-background min-h-screen">
      <MigrationBanner />
      <IssuesHeader
        findings={allFindings}
        grade={grade}
        severityFilter={severityFilter}
        onSeverityFilterChange={setSeverityFilter}
      />

      {importOpen && (
        <ImportDialog
          onComplete={() => {
            void refetch()
            setImportOpen(false)
          }}
          onClose={() => setImportOpen(false)}
        />
      )}

      {isLoading ? (
        <div className="flex justify-center py-24">
          <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      ) : allRepoEmpty ? (
        <EmptyState
          icon="assignment_late"
          title="No issues yet"
          subtitle="Import findings from your scanner to get started."
          action={{
            label: 'Import',
            icon: 'upload_file',
            onClick: () => setImportOpen(true),
          }}
          footer="Supports Snyk, Wiz, and other JSON exports"
        />
      ) : (
        <div className="px-8 pb-12">
          {/* ── REVIEW ──────────────────────────────────────────────── */}
          {sections.review.length > 0 ? (
            <section
              aria-label="Review section"
              className="rounded-2xl mb-8 bg-primary-container/30"
              style={{ padding: '16px 8px 12px' }}
            >
              <div className="flex items-center gap-3 px-4 mb-3">
                <span
                  aria-hidden="true"
                  className="rounded-full bg-primary"
                  style={{ width: 3, height: 18 }}
                />
                <span
                  className="material-symbols-outlined text-primary"
                  style={{ fontSize: 17, fontVariationSettings: "'FILL' 1" }}
                  aria-hidden="true"
                >
                  rate_review
                </span>
                <h2 className="font-headline font-extrabold text-[16px] text-on-surface">
                  Needs your review
                </h2>
                <IssueCountBadge count={sections.review.length} tone="primary" />
                <span className="text-[12px] text-on-surface-variant ml-1">
                  Approve, refine, or reject before the agent ships.
                </span>
              </div>
              <div className="space-y-px">
                {sections.review.map((f) => (
                  <IssueRow key={f.id} finding={f} onActivate={handleActivate} />
                ))}
              </div>
            </section>
          ) : (
            showEmptyReviewCard && (
              <section
                aria-label="Review section"
                className="rounded-2xl mb-8 px-12 py-10 bg-tertiary-container text-on-tertiary-container"
              >
                <h2 className="font-headline font-extrabold text-[24px] mb-2 leading-tight">
                  Review is clear.
                </h2>
                <p className="text-[13.5px] leading-relaxed max-w-2xl">
                  All open issues are either in progress or in the Todo queue. The
                  next thing that needs you will land here.
                </p>
              </section>
            )
          )}

          {/* ── IN PROGRESS ─────────────────────────────────────────── */}
          {/* Render the In progress section unless we're already showing the
              "Review is clear" empty card AND there's nothing in progress to
              report — keeps the page from displaying two consecutive
              empty-state messages. */}
          {(sections.inProgress.length > 0 || !showEmptyReviewCard) && (
            <section aria-label="In progress section" className="mb-8">
              <button
                type="button"
                onClick={toggleInProgress}
                aria-expanded={inProgressOpen}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors bg-surface-container-lowest border border-outline-variant hover:bg-surface-container"
              >
                <span
                  className="material-symbols-outlined text-on-surface-variant"
                  style={{ fontSize: 18 }}
                  aria-hidden="true"
                >
                  {inProgressOpen ? 'expand_more' : 'chevron_right'}
                </span>
                <span className="flex items-center gap-1.5">
                  <span
                    className="opensec-pulse-dot rounded-full bg-primary"
                    style={{ width: 6, height: 6 }}
                    aria-hidden="true"
                  />
                  <span
                    className="material-symbols-outlined text-on-surface-variant"
                    style={{ fontSize: 15 }}
                    aria-hidden="true"
                  >
                    autorenew
                  </span>
                </span>
                <h2 className="font-headline font-bold text-[14px] text-on-surface">
                  In progress
                </h2>
                <IssueCountBadge
                  count={sections.inProgress.length}
                  tone="muted"
                />
                <span className="flex items-center gap-1 text-[11px] text-on-surface-variant ml-1">
                  <span>{inProgressBreakdown.planning} planning</span>
                  <span className="text-outline">·</span>
                  <span>{inProgressBreakdown.generating} generating</span>
                  <span className="text-outline">·</span>
                  <span>{inProgressBreakdown.opening_pr} opening PR</span>
                  <span className="text-outline">·</span>
                  <span>{inProgressBreakdown.validating} validating</span>
                </span>
                <span className="ml-auto text-[11.5px] text-on-surface-variant font-medium">
                  {inProgressOpen
                    ? 'Hide'
                    : 'Agents working — no action needed'}
                </span>
              </button>
              {inProgressOpen && (
                <div className="space-y-px mt-3">
                  {sections.inProgress.map((f) => (
                    <IssueRow key={f.id} finding={f} onActivate={handleActivate} />
                  ))}
                </div>
              )}
            </section>
          )}

          {/* ── TODO ────────────────────────────────────────────────── */}
          <section aria-label="Todo section" className="mb-8">
            <div className="flex items-center gap-3 px-2 mb-2">
              <span
                className="material-symbols-outlined text-on-surface-variant"
                style={{ fontSize: 16 }}
                aria-hidden="true"
              >
                inbox
              </span>
              <h2 className="font-headline font-bold text-[15px] text-on-surface">
                Todo
              </h2>
              <IssueCountBadge count={sections.todo.length} tone="muted" />
              <span className="text-[12px] text-on-surface-variant ml-2">
                Triaged but not yet picked up. Start one, or let the agent batch
                them tonight.
              </span>
            </div>
            <div className="space-y-px">
              {sections.todo.map((f) => (
                <IssueRow
                  key={f.id}
                  finding={f}
                  onActivate={handleActivate}
                />
              ))}
              {sections.todo.length === 0 && (
                <p className="text-[12px] text-on-surface-variant px-3 py-2">
                  Inbox clean.
                </p>
              )}
            </div>
            {solving && (
              <p className="text-[11.5px] text-on-surface-variant mt-2 px-3">
                Starting workspace&hellip;
              </p>
            )}
          </section>

          {/* ── DONE ────────────────────────────────────────────────── */}
          <section aria-label="Done section">
            <div className="flex items-center gap-3 px-2 mb-2">
              <span
                className="material-symbols-outlined text-on-surface-variant"
                style={{ fontSize: 16 }}
                aria-hidden="true"
              >
                check_circle
              </span>
              <h2 className="font-headline font-bold text-[15px] text-on-surface">
                Done
              </h2>
              <IssueCountBadge count={sections.done.length} tone="muted" />
              <span className="text-[12px] text-on-surface-variant ml-2">
                Closed in the last 7 days.
              </span>
              {sections.done.length > DONE_VISIBLE_LIMIT && (
                <button
                  type="button"
                  onClick={() => setDoneExpanded((p) => !p)}
                  className="ml-auto text-[12px] text-primary font-semibold hover:underline"
                >
                  {doneExpanded
                    ? 'Show less'
                    : `Show all (${sections.done.length})`}
                </button>
              )}
            </div>
            <div className="space-y-px">
              {(doneExpanded
                ? sections.done
                : sections.done.slice(0, DONE_VISIBLE_LIMIT)
              ).map((f) => (
                <IssueRow
                  key={f.id}
                  finding={f}
                  onActivate={handleActivate}
                  dim
                />
              ))}
              {sections.done.length === 0 && (
                <p className="text-[12px] text-on-surface-variant px-3 py-2">
                  Nothing closed yet.
                </p>
              )}
            </div>
          </section>

          {totalIssues === 0 && (
            <p className="text-[12px] text-on-surface-variant mt-6 px-2 text-center">
              No matching issues at this severity.
            </p>
          )}
        </div>
      )}

      {/* Repo guard dialog (carried over from FindingsPage). */}
      {showRepoGuard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[2px]">
          <div className="bg-surface-container-lowest rounded-xl shadow-xl w-full max-w-md mx-4 p-8">
            <div className="flex justify-center mb-4">
              <span className="material-symbols-outlined text-4xl text-on-surface-variant">
                link_off
              </span>
            </div>
            <h3 className="text-lg font-bold text-on-surface text-center mb-2">
              GitHub integration not configured
            </h3>
            <p className="text-sm text-on-surface-variant text-center mb-6 leading-relaxed">
              A GitHub integration with repository URL and access token is needed
              for the agent to clone code and create pull requests. You can still
              explore findings without it.
            </p>
            <div className="flex flex-col gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowRepoGuard(false)
                  navigate('/settings#integrations')
                }}
                className="w-full bg-primary text-on-primary py-2.5 rounded-lg text-sm font-semibold hover:bg-primary-dim transition-colors"
              >
                Configure integration
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowRepoGuard(false)
                  if (pendingFinding) void startWorkspace(pendingFinding)
                  setPendingFinding(null)
                }}
                className="w-full text-on-surface-variant py-2.5 rounded-lg text-sm font-medium hover:bg-surface-container transition-colors"
              >
                Continue without repo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
