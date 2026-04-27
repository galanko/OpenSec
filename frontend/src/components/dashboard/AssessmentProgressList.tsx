/**
 * AssessmentProgressList — step-by-step progress card shown while an
 * assessment is running (PRD-0003 v0.2 / surfaces/assessment-progress.jsx).
 *
 * Drives off ``data.steps[]`` directly — the backend route is the
 * single source of truth for the step taxonomy, the per-step state, and
 * the labels/hints. An earlier version hard-coded a frontend ``STEPS``
 * array which silently broke when PR-B widened the engine's step
 * vocabulary from 5 keys (``cloning``, ``parsing_lockfiles``, ...) to
 * 6 (``detect``, ``trivy_vuln``, ``trivy_secret``, ``semgrep``,
 * ``posture``, ``descriptions``); the running cursor never matched any
 * frontend key, so the row sat stuck on "Clone Repository" until the
 * assessment completed and the cursor jumped to the last entry.
 *
 * No artificial pacing — the backend drives the UI. If a run finishes
 * in a flash we'd rather show it in a flash than fake five seconds of
 * progress.
 */

import { useAssessmentStatus } from '@/api/dashboard'
import type { components } from '@/api/types'

type AssessmentStep = components['schemas']['AssessmentStep']

export interface AssessmentProgressListProps {
  assessmentId: string | null | undefined
  /**
   * When true, render only the bare step list — no surrounding card,
   * spinner hero, or headline. Used by ``AssessmentInProgressView`` which
   * already provides its own editorial chrome. Direct callers leave it
   * false to get the standalone card.
   */
  chromeless?: boolean
}

export default function AssessmentProgressList({
  assessmentId,
  chromeless = false,
}: AssessmentProgressListProps) {
  const { data } = useAssessmentStatus(assessmentId)
  const steps = data?.steps ?? []

  const stepList = (
    <ul
      role="list"
      aria-label="Assessment progress"
      className={
        chromeless
          ? 'w-full space-y-1.5 text-left'
          : 'w-full max-w-md space-y-3 text-left'
      }
    >
      {steps.length === 0 ? (
        <li
          data-testid="assessment-step"
          data-state="pending"
          className="flex items-center gap-3 px-3 py-1.5"
        >
          <PendingDot />
          <span className="text-sm text-on-surface-variant/70">
            Waiting for the engine to report progress…
          </span>
        </li>
      ) : (
        steps.map((step) => <StepRow key={step.key} step={step} />)
      )}
    </ul>
  )

  if (chromeless) return stepList

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

      {stepList}
    </section>
  )
}

// --------------------------------------------------------------------- row

function StepRow({ step }: { step: AssessmentStep }) {
  const state = (step.state ?? 'pending') as
    | 'pending'
    | 'running'
    | 'done'
    | 'skipped'
  if (state === 'running') {
    return (
      <li
        data-testid="assessment-step"
        data-state="running"
        data-step-key={step.key}
        className="flex flex-col gap-2 rounded-2xl bg-primary-container/30 px-3 py-2.5"
      >
        <div className="flex items-center gap-3">
          <RunningSpinner />
          <span className="text-sm font-semibold text-on-surface">
            {step.label}
          </span>
          {step.progress_pct != null && (
            <span className="ml-auto text-xs font-bold tabular-nums text-primary">
              {step.progress_pct}%
            </span>
          )}
        </div>
        {step.detail && (
          <p className="ml-7 text-xs text-on-surface-variant">{step.detail}</p>
        )}
        {step.progress_pct != null && (
          <div
            className="ml-7 h-1.5 overflow-hidden rounded-full bg-surface-container-high"
            aria-hidden
          >
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${step.progress_pct}%` }}
            />
          </div>
        )}
      </li>
    )
  }

  if (state === 'done') {
    return (
      <li
        data-testid="assessment-step"
        data-state="done"
        data-step-key={step.key}
        className="flex items-center gap-3 px-3 py-1.5"
      >
        <DoneIcon />
        <span className="text-sm font-medium text-on-surface">
          {step.label}
        </span>
        {step.result_summary && (
          <span className="ml-auto rounded-full bg-surface-container px-2 py-0.5 text-[10px] font-medium text-on-surface-variant">
            {step.result_summary}
          </span>
        )}
      </li>
    )
  }

  if (state === 'skipped') {
    return (
      <li
        data-testid="assessment-step"
        data-state="skipped"
        data-step-key={step.key}
        className="flex items-center gap-3 px-3 py-1.5"
      >
        <SkippedIcon />
        <span className="text-sm text-on-surface-variant/55 line-through">
          {step.label}
        </span>
        <span className="ml-auto text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant/55">
          Skipped
        </span>
      </li>
    )
  }

  // pending
  return (
    <li
      data-testid="assessment-step"
      data-state="pending"
      data-step-key={step.key}
      className="flex items-center gap-3 px-3 py-1.5"
    >
      <PendingDot />
      <span className="text-sm text-on-surface-variant/70">{step.label}</span>
      {step.hint && (
        <span className="ml-auto text-[10px] text-on-surface-variant/55">
          {step.hint}
        </span>
      )}
    </li>
  )
}

// --------------------------------------------------------------------- icons

function DoneIcon() {
  return (
    <span
      className="material-symbols-outlined text-tertiary"
      style={{
        fontSize: 18,
        fontVariationSettings: "'FILL' 1",
      }}
      aria-hidden
    >
      check_circle
    </span>
  )
}

function RunningSpinner() {
  return (
    <span
      className="h-4 w-4 flex-none animate-spin rounded-full border-2 border-primary border-t-transparent"
      aria-hidden
    />
  )
}

function SkippedIcon() {
  return (
    <span
      className="material-symbols-outlined text-on-surface-variant/55"
      style={{ fontSize: 16 }}
      aria-hidden
    >
      remove_circle
    </span>
  )
}

function PendingDot() {
  return (
    <span
      className="h-2 w-2 flex-none rounded-full bg-outline-variant"
      aria-hidden
    />
  )
}
