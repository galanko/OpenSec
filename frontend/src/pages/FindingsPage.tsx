import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { api, type Finding } from '@/api/client'
import { useFindings } from '@/api/hooks'
import ActionButton from '@/components/ActionButton'
import EmptyState from '@/components/EmptyState'
import ErrorBoundary from '@/components/ErrorBoundary'
import ErrorState from '@/components/ErrorState'
import FindingRow from '@/components/FindingRow'
import IngestProgress from '@/components/IngestProgress'
import PageShell from '@/components/PageShell'

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'new', label: 'New' },
  { value: 'triaged', label: 'Triaged' },
  { value: 'in_progress', label: 'In progress' },
]

const SORT_OPTIONS = [
  { value: 'updated', label: 'Latest' },
  { value: 'severity', label: 'Severity' },
]

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0, high: 1, medium: 2, low: 3,
}

export default function FindingsPage() {
  return (
    <ErrorBoundary fallbackTitle="Findings error" fallbackSubtitle="Something went wrong loading findings.">
      <FindingsPageContent />
    </ErrorBoundary>
  )
}

function FindingsPageContent() {
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('updated')
  const [solving, setSolving] = useState<string | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const navigate = useNavigate()

  const params: { status?: string; has_workspace: boolean } = { has_workspace: false }
  if (statusFilter) params.status = statusFilter

  const { data: findings, isLoading, isError, refetch } = useFindings(params)

  const seededRef = useRef(false)
  useEffect(() => {
    if (!isLoading && findings && findings.length === 0 && !seededRef.current) {
      seededRef.current = true
      api.seed().then(() => refetch())
    }
  }, [isLoading, findings, refetch])

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
      const workspace = await api.createWorkspace({ finding_id: finding.id })
      navigate(`/workspace/${workspace.id}`)
    } catch (err) {
      console.error('Failed to create workspace:', err)
      setSolving(null)
    }
  }, [navigate])

  if (isError) {
    return (
      <PageShell title="Findings" subtitle="Your vulnerability queue.">
        <ErrorState
          title="Couldn't load findings"
          subtitle="There was a problem fetching your findings. Please try again."
          onRetry={() => refetch()}
        />
      </PageShell>
    )
  }

  const filterActions = (
    <>
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
            <option key={opt.value} value={opt.value}>{opt.label}</option>
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
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
      <ActionButton
        label="Import"
        icon="upload_file"
        variant="secondary"
        onClick={() => setImportOpen(!importOpen)}
      />
    </>
  )

  return (
    <PageShell
      title="Findings"
      subtitle="Security findings awaiting remediation. Pick one to start a workspace."
      actions={filterActions}
    >
      {importOpen && (
        <IngestProgress
          onComplete={() => {
            refetch()
            setImportOpen(false)
          }}
          onClose={() => setImportOpen(false)}
        />
      )}

      {isLoading ? (
        <div className="flex justify-center py-24">
          <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      ) : sorted.length === 0 ? (
        <EmptyState
          icon="assignment_late"
          title="No open findings"
          subtitle="All findings are being worked on. Check Workspaces for active remediations or History for completed ones."
        />
      ) : (
        <div className="space-y-3">
          {sorted.map((finding) => (
            <FindingRow
              key={finding.id}
              finding={finding}
              onSolve={handleSolve}
              disabled={solving === finding.id}
            />
          ))}
        </div>
      )}
    </PageShell>
  )
}
