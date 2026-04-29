/**
 * IssueStageChip — Phase 1 atom (PRD-0006).
 *
 * Renders all 13 stage values across 5 tones per the design handoff:
 *   - in_flight (planning / generating / pushing / opening_pr / validating):
 *       primary-container bg with a pulsing dot.
 *   - ready (plan_ready / pr_ready): solid primary bg.
 *   - awaiting (pr_awaiting_val): primary-container bg with a pulsing dot.
 *   - positive (fixed / false_positive): tertiary-container with a check.
 *   - neutral (accepted / wont_fix / deferred / todo): surface-container-high
 *       with a verdict-specific icon (block / schedule).
 *
 * Verb form is the signal: -ing forms = passive (agent working), adjective
 * forms = action (you decide). The chip wrapper carries `aria-live="polite"`
 * so screen readers announce stage transitions.
 *
 * The pulse-dot keyframes live in `issues.css` and respect
 * `prefers-reduced-motion: reduce`.
 */
import type { ReactElement } from 'react'
import './issues.css'

export type IssueStage =
  | 'todo'
  | 'planning'
  | 'generating'
  | 'pushing'
  | 'opening_pr'
  | 'validating'
  | 'plan_ready'
  | 'pr_ready'
  | 'pr_awaiting_val'
  | 'fixed'
  | 'false_positive'
  | 'wont_fix'
  | 'accepted'
  | 'deferred'

type Tone = 'in_flight' | 'ready' | 'awaiting' | 'positive' | 'neutral'

interface StageVisual {
  label: string
  tone: Tone
  icon?: 'check' | 'block' | 'schedule'
}

const STAGE_VISUALS: Record<IssueStage, StageVisual> = {
  // active stages
  planning: { label: 'Planning', tone: 'in_flight' },
  generating: { label: 'Generating fix', tone: 'in_flight' },
  pushing: { label: 'Pushing branch', tone: 'in_flight' },
  opening_pr: { label: 'Opening PR', tone: 'in_flight' },
  validating: { label: 'Validating fix', tone: 'in_flight' },
  // ready (call to action)
  plan_ready: { label: 'Plan ready', tone: 'ready' },
  pr_ready: { label: 'PR ready', tone: 'ready' },
  pr_awaiting_val: { label: 'Awaiting validation', tone: 'awaiting' },
  // verdicts
  fixed: { label: 'Fixed', tone: 'positive', icon: 'check' },
  false_positive: { label: 'False positive', tone: 'positive', icon: 'check' },
  accepted: { label: 'Accepted', tone: 'neutral', icon: 'check' },
  wont_fix: { label: "Won't fix", tone: 'neutral', icon: 'block' },
  deferred: { label: 'Deferred', tone: 'neutral', icon: 'schedule' },
  todo: { label: 'Todo', tone: 'neutral' },
}

const TONE_CLASSES: Record<Tone, { wrapper: string; dot: string }> = {
  in_flight: {
    wrapper: 'bg-primary-container text-on-primary-container',
    dot: 'bg-primary',
  },
  ready: {
    wrapper: 'bg-primary text-on-primary',
    dot: 'bg-on-primary',
  },
  awaiting: {
    wrapper: 'bg-primary-container text-on-primary-container',
    dot: 'bg-primary',
  },
  positive: {
    wrapper: 'bg-tertiary-container text-on-tertiary-container',
    dot: '',
  },
  neutral: {
    wrapper: 'bg-surface-container-high text-on-surface-variant',
    dot: '',
  },
}

const HAS_PULSE_DOT: Record<Tone, boolean> = {
  in_flight: true,
  ready: false,
  awaiting: true,
  positive: false,
  neutral: false,
}

interface IssueStageChipProps {
  kind: IssueStage
  size?: 'sm' | 'md'
}

export function IssueStageChip({
  kind,
  size = 'md',
}: IssueStageChipProps): ReactElement {
  const v = STAGE_VISUALS[kind]
  const tone = TONE_CLASSES[v.tone]
  const padY = size === 'sm' ? 2 : 3
  const padX = size === 'sm' ? 7 : 9
  const fontSize = size === 'sm' ? '10.5px' : '11px'

  return (
    <span
      data-testid={`stage-chip-${kind}`}
      aria-live="polite"
      className={`inline-flex items-center gap-1 font-semibold rounded-full whitespace-nowrap ${tone.wrapper}`}
      style={{
        padding: `${padY}px ${padX}px`,
        fontSize,
        lineHeight: 1,
      }}
    >
      {HAS_PULSE_DOT[v.tone] && (
        <span
          aria-hidden="true"
          className={`opensec-pulse-dot inline-block rounded-full ${tone.dot}`}
          style={{ width: 6, height: 6 }}
        />
      )}
      {v.icon && (
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 12 }}
          aria-hidden="true"
        >
          {v.icon}
        </span>
      )}
      {v.label}
    </span>
  )
}
