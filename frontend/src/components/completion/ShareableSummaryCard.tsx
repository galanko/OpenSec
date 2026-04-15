/**
 * ShareableSummaryCard — placeholder component (EXEC-0002 Session 0).
 *
 * IMPL-0002 Milestone H3 ships the full 1200x630 gradient card that the PNG
 * exporter grabs via ref. Placeholder renders props so Session F can swap in
 * the real implementation without any wiring changes upstream.
 */
import { forwardRef } from 'react'

export interface ShareableSummaryCardProps {
  repoName: string
  completedAt: string
  vulnsFixed: number
  postureChecksPassing: number
  prsMerged: number
  grade: 'A' | 'B' | 'C' | 'D' | 'F'
}

const ShareableSummaryCard = forwardRef<HTMLDivElement, ShareableSummaryCardProps>(
  function ShareableSummaryCard(props, ref) {
    return (
      <div ref={ref} data-testid="ShareableSummaryCard">
        <dl>
          <dt>repoName</dt>
          <dd>{props.repoName}</dd>
          <dt>completedAt</dt>
          <dd>{props.completedAt}</dd>
          <dt>vulnsFixed</dt>
          <dd>{props.vulnsFixed}</dd>
          <dt>postureChecksPassing</dt>
          <dd>{props.postureChecksPassing}</dd>
          <dt>prsMerged</dt>
          <dd>{props.prsMerged}</dd>
          <dt>grade</dt>
          <dd>{props.grade}</dd>
        </dl>
      </div>
    )
  },
)

export default ShareableSummaryCard
