/**
 * SummaryActionPanel — placeholder component (EXEC-0002 Session 0).
 *
 * IMPL-0002 Milestone H4: three tiles (Download, Copy text, Copy markdown) +
 * footer info card. Placeholder renders its props; Session F ships the real
 * tiles and calls POST /api/completion/:id/share-action on each click.
 */
export interface SummaryActionPanelProps {
  completionId: string
  summaryText: string
  summaryMarkdown: string
  filename: string
  onAction?: (action: 'download' | 'copy_text' | 'copy_markdown') => void
}

export default function SummaryActionPanel(props: SummaryActionPanelProps) {
  return (
    <dl data-testid="SummaryActionPanel">
      <dt>completionId</dt>
      <dd>{props.completionId}</dd>
      <dt>filename</dt>
      <dd>{props.filename}</dd>
      <dt>summaryText</dt>
      <dd>{props.summaryText}</dd>
      <dt>summaryMarkdown</dt>
      <dd>{props.summaryMarkdown}</dd>
      <dt>onAction</dt>
      <dd>{props.onAction ? 'function' : 'undefined'}</dd>
    </dl>
  )
}
