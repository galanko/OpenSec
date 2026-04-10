import type { PlanOutput } from '@/api/client'
import ResultCardShell from './ResultCardShell'

interface PlannerResultCardProps {
  data: PlanOutput
  confidence?: number | null
  markdown?: string
}

export default function PlannerResultCard({ data, confidence, markdown }: PlannerResultCardProps) {
  const expandContent = (
    <>
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
    </>
  )

  const hasExpandable = !!(data.dependencies.length > 0 || data.validation_method)

  return (
    <ResultCardShell
      title="Remediation plan"
      confidence={confidence}
      markdown={markdown}
      expandContent={hasExpandable ? expandContent : undefined}
    >
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
    </ResultCardShell>
  )
}
