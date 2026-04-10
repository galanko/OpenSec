import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router'
import { api, type Finding } from '@/api/client'
import { useFindings, useIntegrations, useAllIntegrationsHealth } from '@/api/hooks'
import ActionButton from '@/components/ActionButton'
import EmptyState from '@/components/EmptyState'
import FindingRow from '@/components/FindingRow'
import ImportDialog from '@/components/ImportDialog'
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
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('updated')
  const [solving, setSolving] = useState<string | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [showRepoGuard, setShowRepoGuard] = useState(false)
  const [pendingFinding, setPendingFinding] = useState<Finding | null>(null)
  const navigate = useNavigate()
  const { data: integrations } = useIntegrations()
  const { data: healthStatuses } = useAllIntegrationsHealth((integrations?.length ?? 0) > 0)
  const githubInt = integrations?.find(i => i.provider_name === 'GitHub')
  const githubHealth = healthStatuses?.find(h => h.integration_id === githubInt?.id)
  const repoConfigured = !!githubInt?.config?.repo_url && githubHealth?.credential_status === 'ok'

  const params: { status?: string; has_workspace: boolean } = { has_workspace: false }
  if (statusFilter) params.status = statusFilter

  const { data: findings, isLoading, refetch } = useFindings(params)

  const sorted = [...(findings ?? [])].sort((a, b) => {
    if (sortBy === 'severity') {
      const sa = SEVERITY_ORDER[a.raw_severity?.toLowerCase() ?? 'low'] ?? 9
      const sb = SEVERITY_ORDER[b.raw_severity?.toLowerCase() ?? 'low'] ?? 9
      return sa - sb
    }
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  })

  const doSolve = useCallback(async (finding: Finding) => {
    setSolving(finding.id)
    try {
      const workspace = await api.createWorkspace({ finding_id: finding.id })
      navigate(`/workspace/${workspace.id}`)
    } catch (err) {
      console.error('Failed to create workspace:', err)
      setSolving(null)
    }
  }, [navigate])

  const handleSolve = useCallback((finding: Finding) => {
    if (!repoConfigured) {
      setPendingFinding(finding)
      setShowRepoGuard(true)
      return
    }
    doSolve(finding)
  }, [repoConfigured, doSolve])

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
        variant="primary"
        onClick={() => setImportOpen(true)}
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
        <ImportDialog
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
          title="No findings yet"
          subtitle="Import findings from your scanner to get started."
          action={{ label: 'Import', icon: 'upload_file', onClick: () => setImportOpen(true) }}
          footer="Supports Snyk, Wiz, and other JSON exports"
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
      {/* Repo guard dialog */}
      {showRepoGuard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[2px]">
          <div
            className="bg-surface-container-lowest rounded-xl shadow-xl w-full max-w-md mx-4 p-8"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-center mb-4">
              <span className="material-symbols-outlined text-4xl text-on-surface-variant">
                link_off
              </span>
            </div>
            <h3 className="text-lg font-bold text-on-surface text-center mb-2">
              GitHub integration not configured
            </h3>
            <p className="text-sm text-on-surface-variant text-center mb-6 leading-relaxed">
              A GitHub integration with repository URL and access token is needed for the
              agent to clone code and create pull requests. You can still explore findings
              without it.
            </p>
            <div className="flex flex-col gap-3">
              <button
                onClick={() => {
                  setShowRepoGuard(false)
                  navigate('/settings#integrations')
                }}
                className="w-full bg-primary text-on-primary py-2.5 rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors"
              >
                Configure integration
              </button>
              <button
                onClick={() => {
                  setShowRepoGuard(false)
                  if (pendingFinding) doSolve(pendingFinding)
                  setPendingFinding(null)
                }}
                className="w-full text-on-surface-variant py-2.5 rounded-lg text-sm font-medium hover:bg-surface-container transition-colors"
              >
                Continue without repo
              </button>
            </div>
          </div>
        </div>
      )}
    </PageShell>
  )
}
