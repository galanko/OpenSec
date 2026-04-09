import { useCallback, useMemo, useState } from 'react'
import { api, type Workspace } from '@/api/client'
import { useFinding, useWorkspaces } from '@/api/hooks'
import EmptyState from '@/components/EmptyState'
import HistoryCard from '@/components/HistoryCard'
import { generateExportMarkdown } from '@/lib/export-markdown'
import PageShell from '@/components/PageShell'

const STATE_TABS = [
  { value: 'closed', label: 'Closed' },
  { value: 'ready_to_close', label: 'Ready to close' },
]

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest first' },
  { value: 'oldest', label: 'Oldest first' },
]

export default function HistoryPage() {
  const [stateFilter, setStateFilter] = useState('closed')
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('newest')

  const { data: workspaces, isLoading } = useWorkspaces(
    { state: stateFilter },
  )

  const sorted = useMemo(() => {
    const list = [...(workspaces ?? [])]
    list.sort((a, b) => {
      const ta = new Date(a.updated_at).getTime()
      const tb = new Date(b.updated_at).getTime()
      return sortBy === 'newest' ? tb - ta : ta - tb
    })
    return list
  }, [workspaces, sortBy])

  const filterActions = (
    <>
      <div className="relative flex-1 max-w-md">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">
          search
        </span>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by finding, asset, or owner..."
          className="w-full bg-surface-container-lowest border border-outline-variant/10 rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-2 focus:ring-primary/20 transition-all"
        />
      </div>
      <div className="flex items-center gap-1 bg-surface-container-low rounded-lg p-1">
        {STATE_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setStateFilter(tab.value)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
              stateFilter === tab.value
                ? 'bg-white text-primary shadow-sm'
                : 'text-on-surface-variant hover:text-on-surface'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="relative">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">
          sort
        </span>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="bg-surface-container-lowest border border-outline-variant/10 rounded-lg pl-10 pr-4 py-2 text-sm font-medium appearance-none cursor-pointer hover:bg-surface-container transition-colors"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
    </>
  )

  return (
    <PageShell
      title="Operational memory"
      subtitle="Browse remediation work. Search past decisions, reopen workspaces, and export summaries."
      actions={filterActions}
    >
      {isLoading ? (
        <div className="flex justify-center py-24">
          <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      ) : sorted.length === 0 ? (
        <HistoryEmptyState hasSearch={!!search} />
      ) : (
        <div className="space-y-3">
          {sorted.map((ws) => (
            <FilterableRow key={ws.id} workspace={ws} search={search} />
          ))}
        </div>
      )}
    </PageShell>
  )
}

function FilterableRow({ workspace, search }: { workspace: Workspace; search: string }) {
  const { data: finding } = useFinding(workspace.finding_id)

  const handleExport = useCallback(async () => {
    let messages: { role: string; content: string }[] = []
    const sessionId = workspace.current_focus
    if (sessionId) {
      try {
        const detail = await api.getSession(sessionId)
        messages = detail.messages
          .filter((m) => m.content.trim())
          .map((m) => ({ role: m.role, content: m.content }))
      } catch { /* session gone */ }
    }

    let agentRuns: { agent_type: string; status: string; summary_markdown: string | null; confidence: number | null }[] = []
    try {
      agentRuns = await api.listAgentRuns(workspace.id)
    } catch { /* ignore */ }

    const md = generateExportMarkdown(workspace, finding ?? undefined, messages, agentRuns)

    const blob = new Blob([md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `remediation-${finding?.title?.slice(0, 40).replace(/\s+/g, '-') ?? workspace.id}.md`
    a.click()
    URL.revokeObjectURL(url)
  }, [workspace, finding])

  // Client-side search filter (after all hooks).
  if (search) {
    const q = search.toLowerCase()
    const haystack = [
      finding?.title,
      finding?.asset_label,
      finding?.likely_owner,
      finding?.source_type,
      finding?.source_id,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    if (!haystack.includes(q)) return null
  }

  return <HistoryCard workspace={workspace} onExport={handleExport} />
}

function HistoryEmptyState({ hasSearch }: { hasSearch: boolean }) {
  if (hasSearch) {
    return (
      <EmptyState
        icon="search_off"
        title="No matching workspaces"
        subtitle="Try adjusting your search or filters."
      />
    )
  }
  return (
    <EmptyState
      icon="history"
      title="No remediation history yet"
      subtitle="Start solving findings to build your operational memory."
      action={{ label: 'Go to findings', href: '/findings' }}
    />
  )
}

