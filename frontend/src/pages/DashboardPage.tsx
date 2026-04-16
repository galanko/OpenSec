/**
 * DashboardPage — the report-card home (frame 2.2).
 *
 * IMPL-0002 Milestone G4. Switches between assessment-running and
 * report-card states based on the /api/dashboard payload. Imports
 * CompletionStatusCard as a Session-F-owned stub (renders its props;
 * internals land in Session F).
 */

import type React from 'react'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { useDashboard, useFixPostureCheck } from '@/api/dashboard'
import type { DashboardPayload, PostureFixableCheck } from '@/api/dashboard'
import { onboardingApi } from '@/api/onboarding'
import AssessmentProgressList from '@/components/dashboard/AssessmentProgressList'
import CompletionProgressCard from '@/components/dashboard/CompletionProgressCard'
import GradeRing from '@/components/dashboard/GradeRing'
import PostureCheckItem from '@/components/dashboard/PostureCheckItem'
import ScorecardInfoLine from '@/components/dashboard/ScorecardInfoLine'
import CompletionCelebration from '@/components/completion/CompletionCelebration'
import CompletionStatusCard from '@/components/completion/CompletionStatusCard'
import SummaryActionPanel from '@/components/completion/SummaryActionPanel'
import InlineErrorCallout from '@/components/onboarding/InlineErrorCallout'
import ErrorBoundary from '@/components/ErrorBoundary'
import ErrorState from '@/components/ErrorState'
import PageShell from '@/components/PageShell'
import PageSpinner from '@/components/PageSpinner'

const CRITERIA_TOTAL = 5

const SEVERITY_ORDER: Array<{
  key: 'critical' | 'high' | 'medium' | 'low'
  label: string
  tone: string
}> = [
  { key: 'critical', label: 'Critical', tone: 'text-error' },
  { key: 'high', label: 'High', tone: 'text-error' },
  { key: 'medium', label: 'Medium', tone: 'text-tertiary' },
  { key: 'low', label: 'Low', tone: 'text-on-surface-variant' },
]

export default function DashboardPage() {
  return (
    <ErrorBoundary
      fallbackTitle="Dashboard error"
      fallbackSubtitle="Something went wrong loading the dashboard."
    >
      <DashboardContent />
    </ErrorBoundary>
  )
}

function DashboardContent() {
  const { data, isLoading, isError, refetch } = useDashboard()
  useAckOnboardingOnce(data)

  if (isError) {
    return (
      <PageShell title="Overview">
        <ErrorState
          title="Couldn't load the dashboard"
          subtitle="Please try again."
          onRetry={() => refetch()}
        />
      </PageShell>
    )
  }

  if (isLoading || !data) {
    return (
      <PageShell title="Overview">
        <PageSpinner />
      </PageShell>
    )
  }

  if (data.assessment?.status === 'running') {
    return (
      <PageShell title="Overview">
        <AssessmentProgressList assessmentId={data.assessment.id} />
      </PageShell>
    )
  }

  if (data.assessment == null) {
    return <EmptyDashboard />
  }

  return <ReportCard data={data} />
}

function EmptyDashboard() {
  const navigate = useNavigate()
  return (
    <PageShell title="Overview">
      <section
        data-testid="dashboard-empty"
        className="flex flex-col items-center gap-5 rounded-3xl bg-surface-container-low px-10 py-20 text-center"
      >
        <span
          className="material-symbols-outlined text-primary"
          style={{ fontSize: '44px' }}
          aria-hidden
        >
          radar
        </span>
        <div>
          <h2 className="font-headline text-2xl font-bold text-on-surface">
            No assessment yet
          </h2>
          <p className="mt-2 max-w-md text-sm text-on-surface-variant">
            Connect a repository to get your first security grade. It takes
            under a minute.
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate('/onboarding/welcome')}
          className="inline-flex items-center gap-1.5 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-on-primary shadow-sm hover:bg-primary/90"
        >
          <span className="material-symbols-outlined text-sm" aria-hidden>
            play_arrow
          </span>
          Start your first assessment
        </button>
      </section>
    </PageShell>
  )
}

/**
 * Fire ``POST /api/onboarding/complete`` exactly once, the first time the
 * dashboard sees the current assessment flip to ``complete``. This moves the
 * completion ack off the wizard (which used to block on a 409 → complete
 * transition, defeating the progress-list UX).
 */
function useAckOnboardingOnce(data: DashboardPayload | undefined): void {
  const ackedRef = useRef<Set<string>>(new Set())
  useEffect(() => {
    const assessment = data?.assessment
    if (!assessment || assessment.status !== 'complete') return
    if (ackedRef.current.has(assessment.id)) return
    ackedRef.current.add(assessment.id)
    onboardingApi
      .complete({ assessment_id: assessment.id })
      .catch(() => {
        // Already-complete onboarding is expected (idempotent); swallow.
      })
  }, [data?.assessment])
}

interface PostureFeedback {
  kind: 'success' | 'error'
  checkName: PostureFixableCheck
  message: string
}

function ReportCard({ data }: { data: DashboardPayload }) {
  const navigate = useNavigate()
  const fixMutation = useFixPostureCheck()
  const [postureFeedback, setPostureFeedback] = useState<PostureFeedback | null>(
    null,
  )

  const repoName = repoNameFromUrl(data.assessment?.repo_url)
  const criteria = data.criteria
  const criteriaMet = countCriteriaMet(criteria)
  const remaining = Math.max(0, CRITERIA_TOTAL - criteriaMet)

  const heroCopy = buildHeroCopy(data.grade, remaining)

  const handleGenerate = (checkName: PostureFixableCheck) => {
    setPostureFeedback(null)
    fixMutation.mutate(checkName, {
      onSuccess: (resp) => {
        setPostureFeedback({
          kind: 'success',
          checkName,
          message:
            `We spawned a workspace (${resp.workspace_id}). The agent is drafting ` +
            'the pull request — check your GitHub notifications in a minute.',
        })
      },
      onError: (err) => {
        const msg = err instanceof Error ? err.message : 'Unknown error'
        setPostureFeedback({
          kind: 'error',
          checkName,
          message: msg.includes('No repo registered')
            ? 'Run an assessment first — we need a repo to open the PR against.'
            : msg.includes('vault') || msg.includes('token')
              ? 'GitHub integration not configured. Open Settings to add a PAT.'
              : msg,
        })
      },
    })
  }

  // Only celebrate at grade A with a live completion row. The backend already
  // suppresses stale completion_ids when the current snapshot no longer meets
  // every criterion; this guard is defence in depth against a stale payload.
  const completionBlock =
    data.completion_id && data.grade === 'A'
      ? renderCompletionBlock(data, repoName, 'A')
      : null

  const totalFindings = Object.values(data.findings_count_by_priority ?? {}).reduce(
    (a, b) => a + b,
    0,
  )
  const postureFails =
    (data.posture_total_count ?? 0) - (data.posture_pass_count ?? 0)
  const showGradeExplainer =
    data.grade !== 'A' && (totalFindings > 0 || postureFails > 0)

  return (
    <PageShell title="Overview" subtitle={repoName}>
      {completionBlock}
      {showGradeExplainer && (
        <GradeExplainer
          grade={data.grade}
          findingsCount={totalFindings}
          posturePassing={data.posture_pass_count ?? 0}
          postureTotal={data.posture_total_count ?? 0}
          onStartFixing={() => navigate('/findings')}
        />
      )}
      <div className="flex flex-col gap-6">
        <section className="flex flex-col items-start gap-6 rounded-3xl bg-surface-container-low p-8 md:flex-row md:items-center">
          <GradeRing
            grade={data.grade}
            criteriaMet={criteriaMet}
            criteriaTotal={CRITERIA_TOTAL}
          />
          <div className="flex-1">
            <p className="text-xs font-medium uppercase tracking-wide text-on-surface-variant">
              Security grade
            </p>
            <h2 className="mt-1 font-headline text-3xl font-bold text-on-surface">
              {heroCopy.headline}
            </h2>
            <p className="mt-2 text-base text-on-surface-variant">
              {heroCopy.body}
            </p>
          </div>
          <div className="w-full md:w-auto md:max-w-xs md:flex-shrink-0">
            <CompletionStatusCard
              completionId={data.completion_id ?? null}
              completedAt={data.assessment?.completed_at ?? null}
            />
          </div>
        </section>

        <CompletionProgressCard
          criteriaMet={criteriaMet}
          criteriaTotal={CRITERIA_TOTAL}
          repoName={repoName}
        />

        <VulnerabilitiesCard
          data={data}
          onStartFixing={() => navigate('/findings')}
        />
        <PostureCard
          data={data}
          onGenerate={handleGenerate}
          pending={fixMutation.isPending}
          feedback={postureFeedback}
        />

        <ScorecardInfoLine />
      </div>
    </PageShell>
  )
}

function VulnerabilitiesCard({
  data,
  onStartFixing,
}: {
  data: DashboardPayload
  onStartFixing: () => void
}) {
  const counts = data.findings_count_by_priority ?? {}
  const total = SEVERITY_ORDER.reduce(
    (sum, s) => sum + (counts[s.key] ?? 0),
    0,
  )
  const hasIssues = total > 0

  return (
    <section className="flex flex-col gap-4 rounded-3xl bg-surface-container-low p-6">
      <header>
        <h3 className="font-headline text-lg font-bold text-on-surface">
          Vulnerabilities
        </h3>
        <p className="text-sm text-on-surface-variant">
          Findings waiting to be solved.
        </p>
      </header>

      <div className="grid grid-cols-4 gap-3">
        {SEVERITY_ORDER.map((sev) => {
          const value = counts[sev.key] ?? 0
          return (
            <div
              key={sev.key}
              className="rounded-2xl bg-surface-container p-3"
            >
              <p className={`text-2xl font-bold leading-none ${sev.tone}`}>
                {value}
              </p>
              <p className="mt-1 text-xs font-medium text-on-surface-variant">
                {sev.label}
              </p>
            </div>
          )
        })}
      </div>

      {hasIssues ? (
        <button
          type="button"
          onClick={onStartFixing}
          className="inline-flex w-max items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-on-primary shadow-sm hover:bg-primary/90"
        >
          <span className="material-symbols-outlined text-sm" aria-hidden>
            play_arrow
          </span>
          Start fixing
        </button>
      ) : (
        <p className="text-sm text-tertiary">No open vulnerabilities. Nice.</p>
      )}
    </section>
  )
}

function PostureCard({
  data,
  onGenerate,
  pending,
  feedback,
}: {
  data: DashboardPayload
  onGenerate: (checkName: PostureFixableCheck) => void
  pending: boolean
  feedback: PostureFeedback | null
}) {
  const { posture_pass_count, posture_total_count, criteria } = data
  const failures: Array<{
    name: 'security_md' | 'dependabot_config'
    label: string
    description: string
  }> = []
  if (!criteria.security_md_present) {
    failures.push({
      name: 'security_md',
      label: 'SECURITY.md is missing',
      description:
        'We can generate a starter file and open a PR you can review.',
    })
  }
  if (!criteria.dependabot_present) {
    failures.push({
      name: 'dependabot_config',
      label: 'Dependabot is not configured',
      description:
        'We can open a PR with a weekly update schedule and alerts.',
    })
  }

  return (
    <section className="flex flex-col gap-4 rounded-3xl bg-surface-container-low p-6">
      <header>
        <h3 className="font-headline text-lg font-bold text-on-surface">
          Repo posture
        </h3>
        <p className="text-sm text-on-surface-variant">
          {posture_pass_count} of {posture_total_count} checks pass
        </p>
      </header>

      {feedback && feedback.kind === 'error' && (
        <InlineErrorCallout
          title={`Couldn't open the PR for ${feedback.checkName === 'security_md' ? 'SECURITY.md' : 'Dependabot'}`}
          body={<>{feedback.message}</>}
          action={
            feedback.message.toLowerCase().includes('github integration')
              ? { label: 'Open Settings', href: '/settings' }
              : undefined
          }
        />
      )}
      {feedback && feedback.kind === 'success' && (
        <div
          role="status"
          className="rounded-lg bg-tertiary-container/30 px-4 py-3 flex items-start gap-3"
        >
          <span
            className="material-symbols-outlined text-tertiary flex-shrink-0"
            aria-hidden
          >
            check_circle
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-on-surface">
              Workspace spawned
            </p>
            <p className="text-sm text-on-surface-variant mt-1 leading-relaxed">
              {feedback.message}
            </p>
          </div>
        </div>
      )}

      <ul role="list" className="flex flex-col gap-3">
        {failures.map((f) => (
          <PostureCheckItem
            key={f.name}
            checkName={f.name}
            status="fail"
            label={f.label}
            description={f.description}
            onGenerate={onGenerate}
            pending={pending}
          />
        ))}
        <li className="pt-1 text-sm text-on-surface-variant">
          <span className="material-symbols-outlined align-middle text-tertiary">
            check_circle
          </span>{' '}
          {posture_pass_count} other checks passing
        </li>
      </ul>
    </section>
  )
}

/**
 * Counts how many of the five completion criteria are met.
 *
 * The five criteria, in order of the pill meter:
 *   1. SECURITY.md is committed
 *   2. Dependabot is configured
 *   3. No critical vulnerabilities remain open
 *   4. At least 80% of posture checks pass (health threshold)
 *   5. 100% of posture checks pass (completion threshold)
 *
 * Criteria 4 and 5 are intentionally overlapping: hitting 100% implies 80%,
 * so perfect posture counts for both. A repo at 80–99% earns only criterion 4.
 */
function countCriteriaMet(c: DashboardPayload['criteria']): number {
  return [
    c.security_md_present,
    c.dependabot_present,
    c.no_critical_vulns,
    c.posture_checks_total > 0 &&
      c.posture_checks_passing >= Math.ceil(c.posture_checks_total * 0.8),
    c.posture_checks_total > 0 &&
      c.posture_checks_passing === c.posture_checks_total,
  ].filter(Boolean).length
}

function GradeExplainer({
  grade,
  findingsCount,
  posturePassing,
  postureTotal,
  onStartFixing,
}: {
  grade: DashboardPayload['grade']
  findingsCount: number
  posturePassing: number
  postureTotal: number
  onStartFixing: () => void
}) {
  const postureFails = Math.max(0, postureTotal - posturePassing)
  const parts: string[] = []
  if (findingsCount > 0) {
    parts.push(
      `${findingsCount} ${findingsCount === 1 ? 'vulnerability' : 'vulnerabilities'}`,
    )
  }
  if (postureFails > 0) {
    parts.push(
      `${postureFails} of ${postureTotal} posture check${postureTotal === 1 ? '' : 's'} failing`,
    )
  }
  const summary = parts.join(' and ')

  return (
    <section
      data-testid="grade-explainer"
      className="mb-6 rounded-3xl bg-surface-container-low p-6"
    >
      <div className="flex items-start gap-4">
        <span
          className="material-symbols-outlined text-tertiary mt-0.5"
          aria-hidden
        >
          info
        </span>
        <div className="flex-1">
          <h3 className="font-headline text-lg font-bold text-on-surface">
            {grade === 'F'
              ? 'Your project starts at grade F'
              : `Your project is at grade ${grade}`}
          </h3>
          <p className="mt-1 text-sm text-on-surface-variant">
            {summary
              ? `We found ${summary}. Each fix moves the grade up — start anywhere below.`
              : 'Keep fixing findings to raise the grade.'}
          </p>
          {findingsCount > 0 && (
            <button
              type="button"
              onClick={onStartFixing}
              className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-on-primary shadow-sm hover:bg-primary/90"
            >
              <span className="material-symbols-outlined text-sm" aria-hidden>
                play_arrow
              </span>
              Start fixing
            </button>
          )}
        </div>
      </div>
    </section>
  )
}

function buildHeroCopy(
  grade: DashboardPayload['grade'],
  remaining: number,
): { headline: string; body: string } {
  if (grade == null) {
    return {
      headline: 'Working on it',
      body: 'We are still assessing your repository.',
    }
  }
  if (grade === 'A') {
    return {
      headline: 'Security completion reached',
      body: 'All five criteria are met. Keep it up.',
    }
  }
  if (remaining === 0) {
    return {
      headline: 'Almost there',
      body: 'Criteria look good. Address any remaining findings to earn grade A.',
    }
  }
  return {
    headline: 'Nearly there',
    body: `Fix ${remaining} more ${remaining === 1 ? 'item' : 'items'} to reach security completion.`,
  }
}

function repoNameFromUrl(url: string | null | undefined): string {
  if (!url) return 'your repository'
  try {
    const u = new URL(url)
    return u.pathname.replace(/^\//, '').replace(/\.git$/, '') || url
  } catch {
    return url
  }
}

type LetterGrade = 'A' | 'B' | 'C' | 'D' | 'F'

function renderCompletionBlock(
  data: DashboardPayload,
  repoName: string,
  grade: LetterGrade,
): React.ReactNode {
  const completionId = data.completion_id ?? ''
  const completedAtIso = data.assessment?.completed_at ?? null
  const completedDate = formatCompletedDate(completedAtIso)
  const vulnsFixed = Object.values(data.findings_count_by_priority ?? {}).reduce(
    (a, b) => a + b,
    0,
  )
  const posturePassing = data.posture_pass_count ?? 0
  const filename = buildSummaryFilename(repoName, completedAtIso)

  const summaryText = `I secured ${repoName} with OpenSec — ${vulnsFixed} vulnerabilities reviewed, ${posturePassing} posture checks passing, grade ${grade}. opensec.dev`
  const summaryMarkdown = `![Secured by OpenSec](opensec-summary.png)\n<!-- ${repoName} · completed ${completedDate} · grade ${grade} -->`

  const scrollToPanel = () => {
    document
      .getElementById('summary-panel')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="mb-8" data-testid="completion-block">
      <CompletionCelebration
        repoName={repoName}
        completedDate={completedDate}
        grade={grade}
        criteriaCount={CRITERIA_TOTAL}
        onDownloadClick={scrollToPanel}
        onCopyTextClick={() => {
          void navigator.clipboard?.writeText(summaryText)
        }}
        onCopyMarkdownClick={() => {
          void navigator.clipboard?.writeText(summaryMarkdown)
        }}
      />
      <div className="mt-10">
        <SummaryActionPanel
          completionId={completionId}
          summaryText={summaryText}
          summaryMarkdown={summaryMarkdown}
          filename={filename}
          cardProps={{
            repoName,
            completedAt: completedDate,
            vulnsFixed,
            postureChecksPassing: posturePassing,
            prsMerged: 0,
            grade,
          }}
        />
      </div>
    </div>
  )
}

function formatCompletedDate(iso: string | null): string {
  if (!iso) return 'today'
  // Defensive: backend emits full ISO; take the date part for display.
  return iso.slice(0, 10)
}

function buildSummaryFilename(repoName: string, iso: string | null): string {
  const safe = repoName.replace(/[^a-z0-9_-]+/gi, '-').toLowerCase()
  const date = (iso ?? new Date().toISOString()).slice(0, 10)
  return `${safe}_opensec-summary_${date}.png`
}
