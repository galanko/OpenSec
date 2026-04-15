/**
 * ScorecardInfoLine — placeholder component (EXEC-0002 Session 0).
 *
 * IMPL-0002 Milestone G2: static info line pointing to OpenSSF Scorecard.
 * Placeholder renders props; Session E renders the real copy + external link.
 */
export interface ScorecardInfoLineProps {
  scorecardUrl?: string
}

export default function ScorecardInfoLine(props: ScorecardInfoLineProps) {
  return (
    <dl data-testid="ScorecardInfoLine">
      <dt>scorecardUrl</dt>
      <dd>{props.scorecardUrl ?? 'https://github.com/ossf/scorecard'}</dd>
    </dl>
  )
}
