import type { SidebarState } from '@/api/client'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3">
        {title}
      </h4>
      {children}
    </section>
  )
}

function EmptySection() {
  return (
    <p className="text-xs text-outline-variant italic">Not yet available</p>
  )
}

function JsonPanel({ data }: { data: Record<string, unknown> | null }) {
  if (!data || Object.keys(data).length === 0) return <EmptySection />

  // Render key-value pairs from the JSON object.
  return (
    <div className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container/50 space-y-2">
      {Object.entries(data).map(([key, value]) => (
        <div key={key}>
          <p className="text-xs font-semibold mb-0.5">{key.replace(/_/g, ' ')}</p>
          <p className="text-xs text-on-surface-variant leading-relaxed">
            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </p>
        </div>
      ))}
    </div>
  )
}

const PR_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pr_created: { label: 'Draft', color: 'text-tertiary' },
  draft: { label: 'Draft', color: 'text-tertiary' },
  open: { label: 'Open', color: 'text-primary' },
  merged: { label: 'Merged', color: 'text-secondary' },
  failed: { label: 'Failed', color: 'text-error' },
}

function PullRequestPanel({ data }: { data: Record<string, unknown> | null }) {
  if (!data || Object.keys(data).length === 0) return <EmptySection />

  const status = data.status as string | undefined
  const prUrl = data.pr_url as string | undefined
  const branchName = data.branch_name as string | undefined
  const changesSummary = data.changes_summary as string | undefined
  const testResults = data.test_results as string | undefined
  const statusConfig = status ? PR_STATUS_LABELS[status] : undefined

  return (
    <div className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container/50 space-y-2">
      {statusConfig && (
        <div className="flex items-center gap-1.5">
          <span className={`inline-block w-2 h-2 rounded-full ${statusConfig.color.replace('text-', 'bg-')}`} />
          <span className={`text-xs font-semibold ${statusConfig.color}`}>{statusConfig.label}</span>
        </div>
      )}
      {branchName && (
        <div>
          <p className="text-xs font-semibold mb-0.5">branch</p>
          <p className="text-xs text-on-surface-variant font-mono leading-relaxed">{branchName}</p>
        </div>
      )}
      {changesSummary && (
        <div>
          <p className="text-xs font-semibold mb-0.5">changes</p>
          <p className="text-xs text-on-surface-variant leading-relaxed">{changesSummary}</p>
        </div>
      )}
      {testResults && (
        <div>
          <p className="text-xs font-semibold mb-0.5">tests</p>
          <p className="text-xs text-on-surface-variant leading-relaxed">{testResults}</p>
        </div>
      )}
      {prUrl && (
        <a
          href={prUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:text-primary-dim transition-colors mt-1"
        >
          <span className="material-symbols-outlined text-sm">open_in_new</span>
          View on GitHub
        </a>
      )}
    </div>
  )
}

interface WorkspaceSidebarProps {
  sidebar: SidebarState | null | undefined
}

export default function WorkspaceSidebar({ sidebar }: WorkspaceSidebarProps) {
  return (
    <aside className="w-80 bg-surface-container-low border-l border-surface-container overflow-y-auto hidden lg:block">
      <div className="p-6 flex flex-col gap-8">
        <Section title="Summary">
          <JsonPanel data={sidebar?.summary ?? null} />
        </Section>

        <Section title="Evidence">
          <JsonPanel data={sidebar?.evidence ?? null} />
        </Section>

        <Section title="Plan">
          <JsonPanel data={sidebar?.plan ?? null} />
        </Section>

        <Section title="Definition of done">
          <JsonPanel data={sidebar?.definition_of_done ?? null} />
        </Section>

        <Section title="Pull request">
          <PullRequestPanel data={sidebar?.pull_request ?? null} />
        </Section>

        <Section title="Validation">
          <JsonPanel data={sidebar?.validation ?? null} />
        </Section>
      </div>
    </aside>
  )
}
