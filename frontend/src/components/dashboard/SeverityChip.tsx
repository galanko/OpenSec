import { cn } from '@/lib/utils'

/**
 * SeverityChip — compact severity counter for the report-card vulnerability tile.
 *
 * Five kinds map to the Serene Sentinel tonal palette:
 *
 *   critical → error family
 *   high     → error-container
 *   medium   → warning family (ADR-0029) — NOT tertiary, despite the
 *              Claude design's reference JSX defaulting medium to tertiary.
 *              The architect's regression test
 *              `test_severity_chip_medium_uses_warning_token` guards this.
 *   low      → on-surface-variant on a neutral surface
 *   code     → primary container — denotes Semgrep code-issue findings, which
 *              read distinct from dependency vulns.
 */

export type SeverityChipKind = 'critical' | 'high' | 'medium' | 'low' | 'code'

export interface SeverityChipProps {
  kind: SeverityChipKind
  count: number
  className?: string
}

const KIND_CLASSES: Record<SeverityChipKind, string> = {
  critical: 'bg-error/15 text-error',
  high: 'bg-error-container/30 text-error',
  // ADR-0029: medium severity uses the warning token family — not tertiary.
  // This pairing yields 7.6:1 contrast (AAA) on the light-mode surface.
  medium: 'bg-warning-container/40 text-on-warning-container',
  low: 'bg-surface-container-high text-on-surface-variant',
  code: 'bg-primary-container/45 text-on-primary-container',
}

const KIND_LABELS: Record<SeverityChipKind, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  code: 'Code',
}

export function SeverityChip({ kind, count, className }: SeverityChipProps) {
  return (
    <span
      data-testid={`severity-chip-${kind}`}
      data-severity={kind}
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold tabular-nums',
        KIND_CLASSES[kind],
        className,
      )}
    >
      <span>{KIND_LABELS[kind]}</span>
      <span aria-hidden="true">·</span>
      <span aria-label={`${count} ${KIND_LABELS[kind].toLowerCase()}`}>{count}</span>
    </span>
  )
}
