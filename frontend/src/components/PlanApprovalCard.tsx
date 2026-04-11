import { useState } from 'react'
import type { PlanOutput } from '@/api/client'

interface PlanApprovalCardProps {
  plan: PlanOutput
  branchName?: string
  onApprove: () => void
  onModify: () => void
}

export default function PlanApprovalCard({
  plan,
  branchName,
  onApprove,
  onModify,
}: PlanApprovalCardProps) {
  const [isStarting, setIsStarting] = useState(false)

  function handleApprove() {
    setIsStarting(true)
    onApprove()
  }

  return (
    <div className="bg-surface-container-lowest rounded-2xl rounded-bl-md shadow-sm overflow-hidden">
      <div className="px-6 pt-4 pb-2 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary text-sm">task_alt</span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
          Plan approval
        </span>
      </div>

      <div className="px-6 pb-5 space-y-4">
        {plan.plan_steps.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-on-surface mb-2">Fix steps</p>
            <ol className="space-y-1.5">
              {plan.plan_steps.map((step, i) => (
                <li key={i} className="flex gap-2 text-sm text-on-surface-variant">
                  <span className="text-on-surface font-semibold tabular-nums flex-shrink-0">{i + 1}.</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {branchName && (
          <div>
            <p className="text-xs font-semibold text-on-surface mb-1">Branch</p>
            <p className="text-sm text-on-surface-variant font-mono bg-surface-container-low px-2 py-1 rounded-lg inline-block">
              {branchName}
            </p>
          </div>
        )}

        {plan.definition_of_done.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-on-surface mb-2">Definition of done</p>
            <ul className="space-y-1">
              {plan.definition_of_done.map((item, i) => (
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

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleApprove}
            disabled={isStarting}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-xl text-sm font-semibold hover:bg-primary-dim transition-colors disabled:opacity-50"
          >
            {isStarting ? (
              <>
                <span className="material-symbols-outlined text-base animate-spin">progress_activity</span>
                Starting...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-base">play_arrow</span>
                Approve and start
              </>
            )}
          </button>
          <button
            onClick={onModify}
            disabled={isStarting}
            className="inline-flex items-center gap-2 px-4 py-2 text-on-surface-variant rounded-xl text-sm font-semibold hover:bg-surface-container-low transition-colors disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-base">edit</span>
            Modify plan
          </button>
        </div>
      </div>
    </div>
  )
}
