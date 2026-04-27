/**
 * ScannedByLine — the report-card hero divider row
 * (PRD-0003 v0.2 / surfaces/report-card.jsx).
 *
 *   ┌───────────────────────────────────────────────────────┐
 *   │ Scanned by  [Trivy 0.52 · 7]  [Semgrep 1.70 · 3]  ... │
 *   └───────────────────────────────────────────────────────┘
 *
 * Wraps :class:`ToolPillBar` (size sm) with a small label so the brand-trust
 * signal sits clearly under the GradeRing.
 */

import type { components } from '@/api/types'

import ToolPillBar from './ToolPillBar'

type AssessmentTool = components['schemas']['AssessmentTool']

export interface ScannedByLineProps {
  tools: AssessmentTool[]
}

export default function ScannedByLine({ tools }: ScannedByLineProps) {
  return (
    <div
      data-testid="scanned-by-line"
      className="flex items-center gap-3 flex-wrap"
    >
      <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
        Scanned by
      </span>
      <ToolPillBar tools={tools} size="sm" />
    </div>
  )
}
