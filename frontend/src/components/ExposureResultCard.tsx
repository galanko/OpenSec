import type { ExposureOutput } from '@/api/client'
import ResultCardShell from './ResultCardShell'

interface ExposureResultCardProps {
  data: ExposureOutput
  confidence?: number | null
  markdown?: string
}

const urgencyLevels: Record<string, { width: string; color: string; label: string }> = {
  critical: { width: '100%', color: 'bg-error', label: 'Critical' },
  high: { width: '80%', color: 'bg-error/80', label: 'High' },
  moderate: { width: '50%', color: 'bg-tertiary', label: 'Moderate' },
  medium: { width: '50%', color: 'bg-tertiary', label: 'Medium' },
  low: { width: '25%', color: 'bg-secondary', label: 'Low' },
}

export default function ExposureResultCard({ data, confidence, markdown }: ExposureResultCardProps) {
  const urgency = urgencyLevels[data.recommended_urgency.toLowerCase()] ?? urgencyLevels.moderate

  const expandContent = (
    <>
      {data.blast_radius && (
        <div>
          <p className="text-xs font-semibold text-on-surface mb-1">Blast radius</p>
          <p className="text-sm text-on-surface-variant leading-relaxed">{data.blast_radius}</p>
        </div>
      )}
      {data.reachability_evidence && (
        <div>
          <p className="text-xs font-semibold text-on-surface mb-1">Evidence</p>
          <p className="text-sm text-on-surface-variant leading-relaxed">{data.reachability_evidence}</p>
        </div>
      )}
    </>
  )

  const hasExpandable = !!(data.blast_radius || data.reachability_evidence)

  return (
    <ResultCardShell
      title="Exposure analysis"
      confidence={confidence}
      markdown={markdown}
      expandLabel="View full analysis"
      collapseLabel="Hide analysis"
      expandContent={hasExpandable ? expandContent : undefined}
    >
      {/* Key facts grid */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-2">
        {data.reachable != null && (
          <div>
            <p className="text-xs font-semibold text-on-surface">Reachability</p>
            <p className="text-sm text-on-surface-variant">{data.reachable}</p>
          </div>
        )}
        {data.environment != null && (
          <div>
            <p className="text-xs font-semibold text-on-surface">Environment</p>
            <p className="text-sm text-on-surface-variant">{data.environment}</p>
          </div>
        )}
        {data.internet_facing != null && (
          <div>
            <p className="text-xs font-semibold text-on-surface">Internet-facing</p>
            <p className="text-sm text-on-surface-variant">{data.internet_facing ? 'Yes' : 'No'}</p>
          </div>
        )}
        {data.business_criticality != null && (
          <div>
            <p className="text-xs font-semibold text-on-surface">Criticality</p>
            <p className="text-sm text-on-surface-variant">{data.business_criticality}</p>
          </div>
        )}
      </div>

      {/* Urgency bar */}
      <div>
        <p className="text-xs font-semibold text-on-surface mb-1">Urgency</p>
        <div className="flex items-center gap-3">
          <div className="flex-1 h-2 bg-surface-container-high rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${urgency.color}`}
              style={{ width: urgency.width }}
            />
          </div>
          <span className="text-xs text-on-surface-variant">{urgency.label}</span>
        </div>
      </div>
    </ResultCardShell>
  )
}
