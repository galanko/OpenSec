/**
 * AssessmentProgressList — step-by-step progress card shown while an
 * assessment is running (frame 2.1).
 *
 * Polls /api/assessment/status/{id} via the useAssessmentStatus hook. The
 * backend emits the current phase in the ``step`` field; this component
 * renders the five fixed rows and highlights whichever one is active.
 *
 * Client-side pacing: tiny repos finish in under a second, which makes the
 * progress list feel like a flicker rather than a process. We guarantee each
 * step stays on screen for at least ``MIN_STEP_DWELL_MS`` so the five rows
 * take ~10 seconds total to walk through even when the backend is done
 * immediately. If the backend is slower than the pacer, the backend wins.
 */

import { useEffect, useState } from 'react'
import { useAssessmentStatus } from '@/api/dashboard'

interface Step {
  key: string
  label: string
}

const STEPS: Step[] = [
  { key: 'cloning', label: 'Clone repository' },
  { key: 'parsing_lockfiles', label: 'Parse lockfiles' },
  { key: 'looking_up_cves', label: 'Cross-reference CVEs' },
  { key: 'checking_posture', label: 'Run posture checks' },
  { key: 'grading', label: 'Compute grade' },
]

const MIN_STEP_DWELL_MS = 2_000

type StepState = 'done' | 'running' | 'pending'

function stateFor(step: Step, activeIdx: number, isComplete: boolean): StepState {
  if (isComplete) return 'done'
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
  const backendIdx = STEPS.findIndex((s) => s.key === data?.step)
  const displayedIdx = usePacedStep(backendIdx, data?.status === 'complete')
  const isCompleteForDisplay =
    data?.status === 'complete' && displayedIdx >= STEPS.length - 1

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
          const state = stateFor(step, displayedIdx, isCompleteForDisplay)
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

/**
 * Displayed step index = ``max(backendIdx, pacedIdx)`` where ``pacedIdx``
 * advances by one every ``MIN_STEP_DWELL_MS``. Stays on the last step until
 * the backend reports ``complete``; then allows the final row to flip to
 * "done". Never moves backward.
 */
function usePacedStep(backendIdx: number, backendComplete: boolean): number {
  const [pacedIdx, setPacedIdx] = useState(0)

  useEffect(() => {
    if (pacedIdx >= STEPS.length - 1) return
    const t = window.setTimeout(() => {
      setPacedIdx((i) => Math.min(i + 1, STEPS.length - 1))
    }, MIN_STEP_DWELL_MS)
    return () => window.clearTimeout(t)
  }, [pacedIdx])

  const effective = Math.max(pacedIdx, backendIdx)
  // Before the backend reports complete, never show "all done" — hold the
  // final step as "running" so the user can see why we're waiting.
  if (backendComplete) return STEPS.length - 1
  return Math.min(effective, STEPS.length - 1)
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
