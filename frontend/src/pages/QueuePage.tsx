import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { api, type Finding } from '@/api/client'
import { useFindings, useWorkspaces } from '@/api/hooks'
import FindingRow from '@/components/FindingRow'

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'new', label: 'New' },
  { value: 'triaged', label: 'Triaged' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'remediated', label: 'Remediated' },
  { value: 'validated', label: 'Validated' },
  { value: 'closed', label: 'Closed' },
]

const SORT_OPTIONS = [
  { value: 'updated', label: 'Latest' },
  { value: 'severity', label: 'Severity' },
]

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

export default function QueuePage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('updated')
  const [solving, setSolving] = useState<string | null>(null)
  const navigate = useNavigate()

  const { data: findings, isLoading, refetch } = useFindings(
    statusFilter ? { status: statusFilter } : undefined,
  )

  // Load all workspaces to check which findings already have one.
  const { data: workspaces } = useWorkspaces()

  // Build a map: finding_id -> workspace
  const workspaceByFinding = new Map(
    (workspaces ?? []).map((ws) => [ws.finding_id, ws]),
  )

  // Auto-seed on first load if no findings exist.
  const [seeded, setSeeded] = useState(false)
  useEffect(() => {
    if (!isLoading && findings && findings.length === 0 && !seeded) {
      setSeeded(true)
      api.seed().then(() => refetch())
    }
  }, [isLoading, findings, seeded, refetch])

  const sorted = [...(findings ?? [])].sort((a, b) => {
    if (sortBy === 'severity') {
      const sa = SEVERITY_ORDER[a.raw_severity?.toLowerCase() ?? 'low'] ?? 9
      const sb = SEVERITY_ORDER[b.raw_severity?.toLowerCase() ?? 'low'] ?? 9
      return sa - sb
    }
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  })

  const handleSolve = useCallback(async (finding: Finding) => {
    setSolving(finding.id)
    try {
      // Check if a workspace already exists for this finding.
      const existing = workspaceByFinding.get(finding.id)
      if (existing) {
        navigate(`/workspace/${existing.id}`)
        return
      }
      // Create a new workspace.
      const workspace = await api.createWorkspace({ finding_id: finding.id })
      navigate(`/workspace/${workspace.id}`)
    } catch (err) {
      console.error('Failed to create workspace:', err)
      setSolving(null)
    }
  }, [navigate, workspaceByFinding])

  return (
    <div className="p-8 lg:p-12">
      <div className="max-w-6xl mx-auto">
        {/* Page header */}
        <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight text-on-surface mb-2">
              Work queue
            </h1>
            <p className="text-on-surface-variant max-w-lg">
              Prioritized security findings requiring immediate attention or
              verification. Review and resolve to maintain infrastructure integrity.
            </p>
          </div>
          <div className="flex items-center gap-x-3">
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">
                filter_list
              </span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-surface-container-lowest border border-outline-variant/10 rounded-lg pl-10 pr-4 py-2 text-sm font-medium appearance-none cursor-pointer hover:bg-surface-container transition-colors shadow-sm"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">
                sort
              </span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-surface-container-lowest border border-outline-variant/10 rounded-lg pl-10 pr-4 py-2 text-sm font-medium appearance-none cursor-pointer hover:bg-surface-container transition-colors shadow-sm"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Finding list */}
        {isLoading ? (
          <div className="flex justify-center py-24">
            <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
          </div>
        ) : sorted.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="w-16 h-16 rounded-full bg-surface-container-low flex items-center justify-center mb-6">
              <span className="material-symbols-outlined text-3xl text-on-surface-variant">
                assignment_late
              </span>
            </div>
            <h2 className="text-xl font-bold text-on-surface mb-2">No findings yet</h2>
            <p className="text-on-surface-variant text-sm text-center max-w-md mb-8">
              Connect a vulnerability scanner in Integrations to start importing
              findings, or wait for your first scan results.
            </p>
            <a
              href="/integrations"
              className="bg-primary hover:bg-primary-dim text-white px-6 py-2.5 rounded-lg font-semibold text-sm transition-all shadow-lg shadow-primary/20 active:scale-95"
            >
              Connect a scanner
            </a>
          </div>
        ) : (
          <div className="space-y-4">
            {sorted.map((finding) => (
              <FindingRow
                key={finding.id}
                finding={finding}
                onSolve={handleSolve}
                existingWorkspace={workspaceByFinding.get(finding.id)}
                disabled={solving === finding.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
