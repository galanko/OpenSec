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

        <Section title="Owner">
          <JsonPanel data={sidebar?.owner ?? null} />
        </Section>

        <Section title="Plan">
          <JsonPanel data={sidebar?.plan ?? null} />
        </Section>

        <Section title="Definition of done">
          <JsonPanel data={sidebar?.definition_of_done ?? null} />
        </Section>

        <Section title="Ticket">
          <JsonPanel data={sidebar?.linked_ticket ?? null} />
        </Section>

        <Section title="Validation">
          <JsonPanel data={sidebar?.validation ?? null} />
        </Section>
      </div>
    </aside>
  )
}
