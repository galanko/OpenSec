import type { Finding } from '@/api/client'
import { resolveFindingDescription } from '@/lib/findingDescription'
import ActionButton from './ActionButton'
import DescriptionFallbackNote from './findings/DescriptionFallbackNote'
import ListCard from './ListCard'
import SeverityBadge, { SeverityIcon } from './SeverityBadge'

/**
 * FindingRow — plain-language row used on FindingsPage (frame 3.1).
 *
 * IMPL-0002 Milestone G3. Lead with the natural-language title, follow with
 * a practical description sentence, and keep technical metadata in a
 * monospace tech line below. The right rail keeps severity + status + Solve.
 */

const statusDisplay: Record<
  string,
  { label: string; dot: string; icon?: string }
> = {
  new: { label: 'Needs attention', dot: 'bg-error' },
  triaged: { label: 'Investigating', dot: 'bg-secondary' },
  in_progress: { label: 'In progress', dot: 'bg-primary' },
  remediated: { label: 'Remediated', dot: 'bg-tertiary', icon: 'code' },
  validated: { label: 'Validated', dot: 'bg-tertiary', icon: 'verified' },
  closed: { label: 'Closed', dot: 'bg-outline-variant' },
  exception: { label: 'Exception', dot: 'bg-outline-variant' },
}

interface FindingRowProps {
  finding: Finding
  onSolve: (finding: Finding) => void
  disabled?: boolean
}

function buildTechLine(finding: Finding): string {
  const parts: string[] = [finding.source_id]
  const raw = finding.raw_payload ?? null
  const cvss =
    raw && typeof raw === 'object' && 'cvss_score' in raw
      ? (raw as { cvss_score?: number | string | null }).cvss_score
      : null
  if (cvss != null && cvss !== '') {
    parts.push(`CVSS ${cvss}`)
  }
  if (finding.raw_severity) parts.push(finding.raw_severity.toLowerCase())
  const attack =
    raw && typeof raw === 'object' && 'attack_vector' in raw
      ? (raw as { attack_vector?: string | null }).attack_vector
      : null
  if (attack) parts.push(String(attack))
  return parts.join(' · ')
}

export default function FindingRow({
  finding,
  onSolve,
  disabled,
}: FindingRowProps) {
  const status = statusDisplay[finding.status] ?? statusDisplay.new
  const resolved = resolveFindingDescription(
    finding.plain_description,
    finding.description,
  )
  const techLine = buildTechLine(finding)

  return (
    <ListCard>
      <div className="flex-shrink-0">
        <SeverityIcon severity={finding.raw_severity} />
      </div>

      <div className="flex-grow min-w-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-1">
          <SeverityBadge severity={finding.raw_severity} />
          {finding.asset_label && (
            <span className="text-xs font-medium text-on-surface-variant">
              {finding.asset_label}
            </span>
          )}
        </div>
        <h3 className="text-base font-bold text-on-surface mb-1">
          {finding.title}
        </h3>
        {resolved.kind !== 'empty' && (
          <p
            data-testid="finding-description"
            className="text-sm text-on-surface-variant mb-2 leading-relaxed line-clamp-2"
          >
            {resolved.text}
          </p>
        )}
        {resolved.kind === 'fallback' && <DescriptionFallbackNote />}
        {resolved.kind === 'empty' && (
          <p
            data-testid="finding-description-empty"
            className="text-sm text-on-surface-variant mb-2"
          >
            <span
              className="material-symbols-outlined text-sm align-middle mr-1"
              aria-hidden
            >
              help_outline
            </span>
            No description available.
          </p>
        )}
        <p
          data-testid="finding-tech-line"
          className="font-mono text-xs text-on-surface-variant/80"
        >
          {techLine}
        </p>
      </div>

      <div className="flex items-center gap-x-4 flex-shrink-0">
        <div className="text-right hidden lg:block">
          <span className="block text-xs font-medium text-outline-variant mb-1">
            Status
          </span>
          <span className="inline-flex items-center gap-x-1.5 text-sm font-semibold text-on-surface-variant">
            <span className={`w-2 h-2 rounded-full ${status.dot}`} />
            {status.label}
            {status.icon && (
              <span
                className="material-symbols-outlined text-xs text-outline-variant"
                title={status.label}
              >
                {status.icon}
              </span>
            )}
          </span>
        </div>
        <ActionButton
          label="Solve"
          icon="play_arrow"
          onClick={() => onSolve(finding)}
          disabled={disabled}
        />
      </div>
    </ListCard>
  )
}
