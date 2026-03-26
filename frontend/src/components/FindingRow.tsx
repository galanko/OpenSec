import type { Finding, Workspace } from '@/api/client'
import SeverityBadge, { SeverityIcon } from './SeverityBadge'

const statusDisplay: Record<string, { label: string; dot: string }> = {
  new: { label: 'Needs attention', dot: 'bg-primary' },
  triaged: { label: 'Investigating', dot: 'bg-secondary' },
  in_progress: { label: 'In progress', dot: 'bg-primary' },
  remediated: { label: 'Remediated', dot: 'bg-tertiary' },
  validated: { label: 'Validated', dot: 'bg-tertiary' },
  closed: { label: 'Closed', dot: 'bg-outline-variant' },
  exception: { label: 'Exception', dot: 'bg-outline-variant' },
}

interface FindingRowProps {
  finding: Finding
  onSolve: (finding: Finding) => void
  existingWorkspace?: Workspace
  disabled?: boolean
}

export default function FindingRow({ finding, onSolve, existingWorkspace, disabled }: FindingRowProps) {
  const status = statusDisplay[finding.status] ?? statusDisplay.new
  const isBlocked = finding.status === 'closed' || finding.status === 'exception'

  function timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime()
    const hours = Math.floor(diff / 3_600_000)
    if (hours < 1) return 'Just now'
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return days === 1 ? 'Yesterday' : `${days}d ago`
  }

  return (
    <div
      className={`group relative bg-surface-container-lowest rounded-xl p-6 transition-all duration-300 hover:shadow-xl hover:shadow-slate-200/40 border border-transparent hover:border-primary/5 flex flex-col md:flex-row md:items-center gap-6 ${
        isBlocked ? 'opacity-75 grayscale-[0.5]' : ''
      }`}
    >
      <div className="flex-shrink-0">
        <SeverityIcon severity={finding.raw_severity} />
      </div>

      <div className="flex-grow min-w-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mb-1">
          <SeverityBadge severity={finding.raw_severity} />
          <span className="text-xs font-medium text-on-surface-variant">
            {finding.source_id}
          </span>
          <span className="text-xs text-outline-variant">&bull;</span>
          <span className="text-xs font-medium text-on-surface-variant">
            {timeAgo(finding.updated_at)}
          </span>
        </div>
        <h3 className="text-lg font-bold text-on-surface truncate mb-1">
          {finding.title}
        </h3>
        <div className="flex flex-wrap items-center gap-x-4 text-sm text-on-surface-variant">
          {finding.asset_label && (
            <span className="flex items-center gap-x-1">
              <span className="material-symbols-outlined text-xs">dns</span>
              {finding.asset_label}
            </span>
          )}
          {finding.source_type && (
            <span className="flex items-center gap-x-1">
              <span className="material-symbols-outlined text-xs">hub</span>
              {finding.source_type}
            </span>
          )}
          {finding.likely_owner && (
            <span className="flex items-center gap-x-1">
              <span className="material-symbols-outlined text-xs">groups</span>
              {finding.likely_owner}
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-x-6 flex-shrink-0">
        <div className="text-right hidden lg:block">
          <span className="block text-xs font-medium text-outline-variant mb-1">
            Status
          </span>
          <span className="inline-flex items-center gap-x-1.5 text-sm font-semibold text-on-surface-variant">
            <span className={`w-2 h-2 rounded-full ${status.dot}`} />
            {status.label}
          </span>
        </div>
        {isBlocked ? (
          <button
            disabled
            className="bg-surface-container-highest text-on-surface-variant px-8 py-2.5 rounded-lg font-bold cursor-not-allowed"
          >
            Solved
          </button>
        ) : existingWorkspace ? (
          <button
            onClick={() => onSolve(finding)}
            disabled={disabled}
            className="flex items-center gap-2 bg-secondary-container text-on-secondary-container px-6 py-2.5 rounded-lg font-bold transition-all shadow-sm hover:shadow-md active:scale-95 disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-sm">login</span>
            Continue
          </button>
        ) : (
          <button
            onClick={() => onSolve(finding)}
            disabled={disabled}
            className="bg-primary hover:bg-primary-dim text-white px-8 py-2.5 rounded-lg font-bold transition-all shadow-lg shadow-primary/20 active:scale-95 disabled:opacity-50"
          >
            Solve
          </button>
        )}
      </div>
    </div>
  )
}
