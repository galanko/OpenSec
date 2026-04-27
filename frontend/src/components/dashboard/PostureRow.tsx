/**
 * PostureRow — read-time four-state posture row for the dashboard
 * (PRD-0003 v0.2 / ADR-0032 §1.2).
 *
 * States (all sourced from the backend's read-time projection):
 *   pass     — filled check_circle in tertiary
 *   fail     — filled cancel in error, card-style row
 *   done     — filled check_circle + "Draft PR ↗" link to ``pr_url``
 *   advisory — outline info icon + right-aligned ``advisory`` chip
 *
 * Distinct from the in-flight :class:`PostureCheckItem` (PRD-0004 Story 3),
 * which renders the ``to_do | running | succeeded | failed`` machine. The
 * dashboard reads completed assessments and projects to the four-state
 * vocabulary; both components reinforce the same visual grammar.
 */

import type { ReactNode } from 'react'

export type PostureWireState = 'pass' | 'fail' | 'done' | 'advisory'
export type PostureGradeImpact = 'counts' | 'advisory'

export interface PostureRowProps {
  name: string
  displayName: string
  state: PostureWireState
  gradeImpact: PostureGradeImpact
  prUrl?: string | null
  detail?: string | null
  /** Generator CTA shown for ``fail`` rows when the check is fixable. */
  generatorSlot?: ReactNode
}

const cx = (...xs: (string | false | null | undefined)[]) =>
  xs.filter(Boolean).join(' ')

interface StateMeta {
  icon: string
  iconFilled: boolean
  iconColor: string
  rowTint: string
}

const STATE_META: Record<PostureWireState, StateMeta> = {
  pass: {
    icon: 'check_circle',
    iconFilled: true,
    iconColor: 'text-tertiary',
    rowTint: 'bg-surface-container-lowest',
  },
  fail: {
    icon: 'cancel',
    iconFilled: true,
    iconColor: 'text-error',
    rowTint: 'bg-primary-container/30',
  },
  done: {
    icon: 'check_circle',
    iconFilled: true,
    iconColor: 'text-tertiary',
    rowTint: 'bg-tertiary-container/20',
  },
  advisory: {
    icon: 'info',
    iconFilled: false,
    iconColor: 'text-on-surface-variant',
    rowTint: 'bg-surface-container-lowest',
  },
}

export default function PostureRow({
  name,
  displayName,
  state,
  gradeImpact,
  prUrl,
  detail,
  generatorSlot,
}: PostureRowProps) {
  const meta = STATE_META[state]
  return (
    <li
      data-testid="posture-row"
      data-check-name={name}
      data-state={state}
      data-grade-impact={gradeImpact}
      className={cx(
        'flex items-start gap-3 rounded-2xl px-4 py-3 transition-colors',
        meta.rowTint,
      )}
    >
      <span
        className={cx('material-symbols-outlined flex-shrink-0', meta.iconColor)}
        style={{
          fontSize: 22,
          ...(meta.iconFilled ? { fontVariationSettings: "'FILL' 1" } : undefined),
        }}
        aria-hidden
      >
        {meta.icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-on-surface">{displayName}</p>
        {detail && (
          <p className="mt-0.5 text-xs text-on-surface-variant">{detail}</p>
        )}
      </div>
      <div className="flex-shrink-0 self-center">
        {state === 'done' && prUrl && (
          <a
            data-testid="posture-row-pr-link"
            href={prUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-tertiary-container/40 px-3 py-1 text-[11px] font-semibold text-on-tertiary-container hover:bg-tertiary-container/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tertiary/60"
          >
            Draft PR
            <span className="material-symbols-outlined" style={{ fontSize: 12 }} aria-hidden>
              open_in_new
            </span>
          </a>
        )}
        {state === 'advisory' && (
          <span
            data-testid="posture-row-advisory-chip"
            className="inline-flex items-center rounded-full bg-surface-container-high px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant"
          >
            Advisory
          </span>
        )}
        {state === 'fail' && generatorSlot}
      </div>
    </li>
  )
}
