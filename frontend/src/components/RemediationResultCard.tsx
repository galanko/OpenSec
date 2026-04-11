import type { RemediationExecutorOutput } from '@/api/client'
import ResultCardShell from './ResultCardShell'

interface RemediationResultCardProps {
  data: RemediationExecutorOutput
  confidence?: number | null
  markdown?: string
}

const STATUS_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  pr_created: { label: 'PR created', icon: 'check_circle', color: 'text-tertiary' },
  changes_made: { label: 'Changes made', icon: 'code', color: 'text-primary' },
  failed: { label: 'Failed', icon: 'error', color: 'text-error' },
  needs_approval: { label: 'Needs approval', icon: 'pending', color: 'text-secondary' },
}

export default function RemediationResultCard({ data, confidence, markdown }: RemediationResultCardProps) {
  const statusConfig = STATUS_CONFIG[data.status] ?? {
    label: data.status,
    icon: 'info',
    color: 'text-on-surface-variant',
  }

  const expandContent = data.error_details ? (
    <div>
      <p className="text-xs font-semibold text-error mb-1">Error details</p>
      <p className="text-sm text-on-surface-variant">{data.error_details}</p>
    </div>
  ) : undefined

  return (
    <ResultCardShell
      title="Remediation result"
      confidence={confidence}
      markdown={markdown}
      expandContent={expandContent}
    >
      {/* Status */}
      <div className="flex items-center gap-2">
        <span className={`material-symbols-outlined text-base ${statusConfig.color}`}>
          {statusConfig.icon}
        </span>
        <span className={`text-sm font-semibold ${statusConfig.color}`}>
          {statusConfig.label}
        </span>
      </div>

      {/* Branch name */}
      {data.branch_name && (
        <div>
          <p className="text-xs font-semibold text-on-surface mb-1">Branch</p>
          <p className="text-sm text-on-surface-variant font-mono bg-surface-container-low px-2 py-1 rounded-lg inline-block">
            {data.branch_name}
          </p>
        </div>
      )}

      {/* Changes summary */}
      {data.changes_summary && (
        <div>
          <p className="text-xs font-semibold text-on-surface mb-1">Changes</p>
          <p className="text-sm text-on-surface-variant">{data.changes_summary}</p>
        </div>
      )}

      {/* Test results */}
      {data.test_results && (
        <div>
          <p className="text-xs font-semibold text-on-surface mb-1">Test results</p>
          <p className="text-sm text-on-surface-variant">{data.test_results}</p>
        </div>
      )}

      {/* PR link */}
      {data.pr_url && (
        <div>
          <a
            href={data.pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:text-primary-dim transition-colors"
          >
            <span className="material-symbols-outlined text-base">open_in_new</span>
            View pull request
          </a>
        </div>
      )}
    </ResultCardShell>
  )
}
