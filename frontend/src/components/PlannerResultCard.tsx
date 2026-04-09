import { useState } from 'react'
import type { PlanOutput } from '@/api/client'
import ConfidenceBadge from './ConfidenceBadge'
import Markdown from './Markdown'

interface PlannerResultCardProps {
  data: PlanOutput
  confidence?: number | null
  markdown?: string
}

export default function PlannerResultCard({ data, confidence, markdown }: PlannerResultCardProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-surface-container-lowest rounded-2xl rounded-bl-md shadow-sm overflow-hidden">
      {/* Agent label */}
      <div className="px-6 pt-4 pb-2 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
          Remediation plan
        </span>
      </div>

      <div className="px-6 pb-5 space-y-4">
        {/* Fix steps */}
        {data.plan_steps.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-on-surface mb-2">Fix steps</p>
            <ol className="space-y-1.5">
              {data.plan_steps.map((step, i) => (
                <li key={i} className="flex gap-2 text-sm text-on-surface-variant">
                  <span className="text-on-surface font-semibold tabular-nums flex-shrink-0">{i + 1}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Interim mitigation */}
        {data.interim_mitigation && (
          <div>
            <p className="text-xs font-semibold text-on-surface mb-1">Interim mitigation</p>
            <p className="text-sm text-on-surface-variant">{data.interim_mitigation}</p>
          </div>
        )}

        {/* Effort */}
        {data.estimated_effort && (
          <div>
            <p className="text-xs font-semibold text-on-surface">Effort</p>
            <p className="text-sm text-on-surface-variant">{data.estimated_effort}</p>
          </div>
        )}

        {/* Definition of done */}
        {data.definition_of_done.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-on-surface mb-2">Definition of done</p>
            <ul className="space-y-1">
              {data.definition_of_done.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-on-surface-variant">
                  <span className="material-symbols-outlined text-base text-on-surface-variant/40 flex-shrink-0 mt-0.5">
                    check_box_outline_blank
                  </span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Confidence */}
        <div className="flex items-center justify-between">
          <ConfidenceBadge confidence={confidence} />
        </div>

        {/* Expandable details */}
        {(data.dependencies.length > 0 || data.validation_method || markdown) && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs font-semibold text-primary hover:text-primary-dim transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-sm" style={{ transition: 'transform 0.2s', transform: expanded ? 'rotate(90deg)' : 'none' }}>
              arrow_right
            </span>
            {expanded ? 'Hide details' : 'View details'}
          </button>
        )}

        {expanded && (
          <div className="space-y-3 bg-surface-container-low rounded-xl p-4">
            {data.dependencies.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-on-surface mb-1">Dependencies</p>
                <ul className="space-y-0.5">
                  {data.dependencies.map((dep, i) => (
                    <li key={i} className="text-sm text-on-surface-variant">{dep}</li>
                  ))}
                </ul>
              </div>
            )}
            {data.validation_method && (
              <div>
                <p className="text-xs font-semibold text-on-surface mb-1">Validation method</p>
                <p className="text-sm text-on-surface-variant">{data.validation_method}</p>
              </div>
            )}
            {markdown && (
              <div>
                <p className="text-xs font-semibold text-on-surface mb-1">Full plan</p>
                <Markdown content={markdown} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
