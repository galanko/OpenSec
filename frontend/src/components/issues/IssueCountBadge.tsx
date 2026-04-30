/**
 * IssueCountBadge — Phase 1 atom (PRD-0006).
 *
 * Mono-font count pill in three tones. Used by section headers, the Review
 * block heading, and filter chips' trailing count. Mirrors IPCountBadge in
 * `frontend/mockups/claude-design/PRD-0006/issues-page/atoms.jsx`.
 */
import type { ReactElement } from 'react'

type CountTone = 'primary' | 'tertiary' | 'muted'

const TONE_CLASSES: Record<CountTone, string> = {
  primary: 'bg-primary-container text-on-primary-container',
  tertiary: 'bg-tertiary-container text-on-tertiary-container',
  muted: 'bg-surface-container-high text-on-surface-variant',
}

interface IssueCountBadgeProps {
  count: number
  tone?: CountTone
}

export function IssueCountBadge({
  count,
  tone = 'muted',
}: IssueCountBadgeProps): ReactElement {
  return (
    <span
      data-testid={`count-badge-${tone}`}
      className={`inline-flex items-center justify-center font-semibold font-mono rounded-full ${TONE_CLASSES[tone]}`}
      style={{
        minWidth: 22,
        height: 20,
        padding: '0 7px',
        fontSize: 11,
        lineHeight: 1,
      }}
    >
      {count}
    </span>
  )
}
