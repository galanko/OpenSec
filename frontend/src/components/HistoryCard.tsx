import type { Workspace } from '@/api/client'
import { useAgentRuns, useFinding } from '@/api/hooks'
import SeverityBadge from './SeverityBadge'

const stateStyles: Record<string, { label: string; classes: string }> = {
  open: { label: 'Open', classes: 'text-primary bg-primary-container/40' },
  waiting: { label: 'Waiting', classes: 'text-secondary bg-secondary-container/40' },
  ready_to_close: { label: 'Ready to close', classes: 'text-tertiary bg-tertiary-container/40' },
  closed: { label: 'Closed', classes: 'text-on-surface-variant bg-surface-container-high' },
  reopened: { label: 'Reopened', classes: 'text-primary bg-primary-container/40' },
}

const agentLabels: Record<string, string> = {
  finding_enricher: 'Enricher',
  owner_resolver: 'Owner',
  exposure_analyzer: 'Exposure',
  remediation_planner: 'Planner',
  validation_checker: 'Validator',
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const hours = Math.floor(diff / 3_600_000)
  if (hours < 1) return 'Just now'
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return days === 1 ? 'Yesterday' : `${days}d ago`
}

interface HistoryCardProps {
  workspace: Workspace
  isSelected: boolean
  onSelect: () => void
  onReopen: () => void
  onExport: () => void
}

export default function HistoryCard({
  workspace,
  isSelected,
  onSelect,
  onReopen,
  onExport,
}: HistoryCardProps) {
  const { data: finding } = useFinding(workspace.finding_id)
  const { data: agentRuns } = useAgentRuns(workspace.id)

  const state = stateStyles[workspace.state] ?? stateStyles.open
  const completedRuns = (agentRuns ?? []).filter((r) => r.status === 'completed')
  const agentTypes = [...new Set(completedRuns.map((r) => r.agent_type))]

  return (
    <div
      className={`bg-surface-container-lowest rounded-xl transition-all duration-200 border ${
        isSelected
          ? 'border-primary/20 shadow-lg shadow-primary/5'
          : 'border-transparent hover:shadow-md hover:border-primary/5'
      }`}
    >
      {/* Summary row */}
      <button
        onClick={onSelect}
        className="w-full text-left p-5 flex flex-col md:flex-row md:items-center gap-4"
      >
        {/* Finding context */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            {finding?.raw_severity && <SeverityBadge severity={finding.raw_severity} />}
            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${state.classes}`}>
              {state.label}
            </span>
            <span className="text-xs text-outline-variant">
              {timeAgo(workspace.updated_at)}
            </span>
          </div>
          <h3 className="text-base font-bold text-on-surface truncate">
            {finding?.title ?? 'Loading...'}
          </h3>
          <div className="flex flex-wrap items-center gap-x-4 mt-1 text-xs text-on-surface-variant">
            {finding?.asset_label && (
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">dns</span>
                {finding.asset_label}
              </span>
            )}
            {finding?.likely_owner && (
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">groups</span>
                {finding.likely_owner}
              </span>
            )}
            {finding?.source_type && (
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">hub</span>
                {finding.source_type}
              </span>
            )}
          </div>
        </div>

        {/* Agent summary */}
        <div className="flex items-center gap-4 flex-shrink-0">
          {agentTypes.length > 0 && (
            <div className="hidden md:flex items-center gap-1">
              {agentTypes.map((type) => (
                <span
                  key={type}
                  className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-primary-container/30 text-primary"
                >
                  {agentLabels[type] ?? type}
                </span>
              ))}
            </div>
          )}
          <span className="material-symbols-outlined text-on-surface-variant text-sm">
            {isSelected ? 'expand_less' : 'expand_more'}
          </span>
        </div>
      </button>

      {/* Action bar (always visible) */}
      {isSelected && (
        <div className="px-5 pb-4 flex items-center gap-2 border-t border-surface-container/50 pt-3">
          <button
            onClick={onReopen}
            className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-dim text-white text-xs font-bold rounded-lg transition-all shadow-sm"
          >
            <span className="material-symbols-outlined text-sm">login</span>
            {workspace.state === 'closed' ? 'Reopen' : 'Continue'}
          </button>
          <button
            onClick={onExport}
            className="flex items-center gap-1.5 px-4 py-2 border border-outline-variant/30 text-xs font-bold rounded-lg hover:bg-surface-container transition-colors"
          >
            <span className="material-symbols-outlined text-sm">download</span>
            Export
          </button>
        </div>
      )}
    </div>
  )
}
