/**
 * CompletionProgressCard — placeholder component (EXEC-0002 Session 0).
 *
 * IMPL-0002 Milestone G2 will replace this stub with the real visual
 * (previously "BadgePreviewCard"). For now it renders its prop list so
 * downstream sessions can import, type-check, and wire it in.
 */
export interface CompletionProgressCardProps {
  criteriaMet: number
  criteriaTotal: number
  grade: 'A' | 'B' | 'C' | 'D' | 'F' | null
  repoName: string
}

export default function CompletionProgressCard(props: CompletionProgressCardProps) {
  return (
    <dl data-testid="CompletionProgressCard">
      <dt>repoName</dt>
      <dd>{props.repoName}</dd>
      <dt>criteriaMet</dt>
      <dd>{props.criteriaMet}</dd>
      <dt>criteriaTotal</dt>
      <dd>{props.criteriaTotal}</dd>
      <dt>grade</dt>
      <dd>{props.grade ?? 'null'}</dd>
    </dl>
  )
}
