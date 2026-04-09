import { useState } from 'react'
import type { ExposureOutput } from '@/api/client'
import ConfidenceBadge from './ConfidenceBadge'
import Markdown from './Markdown'

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
  const [expanded, setExpanded] = useState(false)
  const urgency = urgencyLevels[data.recommended_urgency.toLowerCase()] ?? urgencyLevels.moderate

  return (
    <div className="bg-surface-container-lowest rounded-2xl rounded-bl-md shadow-sm overflow-hidden">
      {/* Agent label */}
      <div className="px-6 pt-4 pb-2 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
          Exposure analysis
        </span>
      </div>

      <div className="px-6 pb-5 space-y-4">
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

        {/* Confidence */}
        <div className="flex items-center justify-between">
          <ConfidenceBadge confidence={confidence} />
        </div>

        {/* Expandable details */}
        {(data.blast_radius || data.reachability_evidence || markdown) && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs font-semibold text-primary hover:text-primary-dim transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-sm" style={{ transition: 'transform 0.2s', transform: expanded ? 'rotate(90deg)' : 'none' }}>
              arrow_right
            </span>
            {expanded ? 'Hide analysis' : 'View full analysis'}
          </button>
        )}

        {expanded && (
          <div className="space-y-3 bg-surface-container-low rounded-xl p-4">
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
            {markdown && (
              <div>
                <p className="text-xs font-semibold text-on-surface mb-1">Full analysis</p>
                <Markdown content={markdown} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
