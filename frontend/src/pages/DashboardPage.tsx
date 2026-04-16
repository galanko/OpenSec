/**
 * DashboardPage — the report-card home (frame 2.2).
 *
 * IMPL-0002 Milestone G4. Switches between assessment-running and
 * report-card states based on the /api/dashboard payload. Imports
 * CompletionStatusCard as a Session-F-owned stub (renders its props;
 * internals land in Session F).
 */

import { useNavigate } from 'react-router'
import { useDashboard, useFixPostureCheck } from '@/api/dashboard'
import type { DashboardPayload, PostureFixableCheck } from '@/api/dashboard'
import AssessmentProgressList from '@/components/dashboard/AssessmentProgressList'
import CompletionProgressCard from '@/components/dashboard/CompletionProgressCard'
import GradeRing from '@/components/dashboard/GradeRing'
import PostureCheckItem from '@/components/dashboard/PostureCheckItem'
import ScorecardInfoLine from '@/components/dashboard/ScorecardInfoLine'
import CompletionStatusCard from '@/components/completion/CompletionStatusCard'
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

  return <ReportCard data={data} />
}

function ReportCard({ data }: { data: DashboardPayload }) {
  const navigate = useNavigate()
  const fixMutation = useFixPostureCheck()

  const repoName = repoNameFromUrl(data.assessment?.repo_url)
  const criteria = data.criteria
  const criteriaMet = countCriteriaMet(criteria)
  const remaining = Math.max(0, CRITERIA_TOTAL - criteriaMet)

  const heroCopy = buildHeroCopy(data.grade, remaining)

  const handleGenerate = (checkName: PostureFixableCheck) => {
    fixMutation.mutate(checkName, {
      onSuccess: (resp) => navigate(`/workspace/${resp.workspace_id}`),
    })
  }

  return (
    <PageShell title="Overview" subtitle={repoName}>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_340px]">
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
          </section>

          <CompletionProgressCard
            criteriaMet={criteriaMet}
            criteriaTotal={CRITERIA_TOTAL}
            repoName={repoName}
          />

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <VulnerabilitiesCard data={data} onStartFixing={() => navigate('/findings')} />
            <PostureCard
              data={data}
              onGenerate={handleGenerate}
              pending={fixMutation.isPending}
            />
          </div>

          <ScorecardInfoLine />
        </div>

        <aside>
          <CompletionStatusCard
            completionId={data.completion_id ?? null}
            completedAt={data.assessment?.completed_at ?? null}
          />
        </aside>
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
}: {
  data: DashboardPayload
  onGenerate: (checkName: PostureFixableCheck) => void
  pending: boolean
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
