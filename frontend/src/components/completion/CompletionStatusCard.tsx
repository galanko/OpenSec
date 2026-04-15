/**
 * CompletionStatusCard — placeholder component (EXEC-0002 Session 0).
 *
 * Dashboard aside that replaces the old FreshnessCard (IMPL-0002 Milestone H4).
 * Shield acts as a button that re-opens the shareable summary panel. Full
 * behavior ships in Session F.
 */
export interface CompletionStatusCardProps {
  completionId: string | null
  completedAt: string | null
  onReopenSummary?: () => void
}

export default function CompletionStatusCard(props: CompletionStatusCardProps) {
  return (
    <dl data-testid="CompletionStatusCard">
      <dt>completionId</dt>
      <dd>{props.completionId ?? 'null'}</dd>
      <dt>completedAt</dt>
      <dd>{props.completedAt ?? 'null'}</dd>
      <dt>onReopenSummary</dt>
      <dd>{props.onReopenSummary ? 'function' : 'undefined'}</dd>
    </dl>
  )
}
