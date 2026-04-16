/**
 * AssessmentProgressList — step-by-step progress card shown while an
 * assessment is running (frame 2.1).
 *
 * IMPL-0002 Milestone G1. Polls /api/assessment/status/{id} via the
 * useAssessmentStatus hook (Session B upgrades to SSE later). Renders five
 * fixed steps keyed off the backend `step` string.
 */

import { useAssessmentStatus } from '@/api/dashboard'

interface Step {
  key: string
  label: string
}

const STEPS: Step[] = [
  { key: 'clone', label: 'Clone repository' },
  { key: 'parse_lockfiles', label: 'Parse lockfiles' },
  { key: 'cve_lookup', label: 'Cross-reference CVEs' },
  { key: 'posture_check', label: 'Run posture check' },
  { key: 'plain_language', label: 'Write plain-language descriptions' },
]

type StepState = 'done' | 'running' | 'pending'

function stateFor(step: Step, activeIdx: number, status?: string): StepState {
  if (status === 'complete') return 'done'
  // activeIdx === -1 signals "step unknown" — keep every row pending rather
  // than falsely highlighting the first step.
  if (activeIdx < 0) return 'pending'
  const idx = STEPS.findIndex((s) => s.key === step.key)
  if (idx < activeIdx) return 'done'
  if (idx === activeIdx) return 'running'
  return 'pending'
}

export interface AssessmentProgressListProps {
  assessmentId: string | null | undefined
}

export default function AssessmentProgressList({
  assessmentId,
}: AssessmentProgressListProps) {
  const { data } = useAssessmentStatus(assessmentId)
  const activeIdx = STEPS.findIndex((s) => s.key === data?.step)

  return (
    <section
      className="flex flex-col items-center gap-6 rounded-3xl bg-surface-container-low px-10 py-14 text-center"
      aria-label="Assessment in progress"
    >
      <div className="grid h-14 w-14 place-items-center rounded-full bg-primary-container">
        <span
          className="material-symbols-outlined animate-spin text-primary"
          style={{ fontSize: '28px' }}
          aria-hidden
        >
          radar
        </span>
      </div>
      <div>
        <h2 className="font-headline text-2xl font-bold text-on-surface">
          Assessing your repository
        </h2>
        <p className="mt-1 text-sm text-on-surface-variant">
          This usually takes under a minute. You can stay here or come back —
          the progress is saved.
        </p>
      </div>

      <ul
        role="list"
        aria-label="Assessment progress"
        className="w-full max-w-md space-y-3 text-left"
      >
        {STEPS.map((step) => {
          const state = stateFor(step, activeIdx, data?.status)
          return (
            <li
              key={step.key}
              data-testid="assessment-step"
              data-state={state}
              className="flex items-center gap-3"
            >
              <StepIcon state={state} />
              <span
                className={
                  state === 'pending'
                    ? 'text-sm text-on-surface-variant/70'
                    : 'text-sm font-medium text-on-surface'
                }
              >
                {step.label}
              </span>
              {state === 'running' && data?.progress_pct != null && (
                <span className="ml-auto text-xs font-medium text-primary">
                  {data.progress_pct}%
                </span>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}

function StepIcon({ state }: { state: StepState }) {
  if (state === 'done') {
    return (
      <span
        className="material-symbols-outlined text-tertiary"
        style={{ fontSize: '20px' }}
        aria-hidden
      >
        check_circle
      </span>
    )
  }
  if (state === 'running') {
    return (
      <span
        className="h-4 w-4 flex-none animate-spin rounded-full border-2 border-primary border-t-transparent"
        aria-hidden
      />
    )
  }
  return (
    <span
      className="h-2 w-2 flex-none rounded-full bg-outline-variant"
      aria-hidden
    />
  )
}
