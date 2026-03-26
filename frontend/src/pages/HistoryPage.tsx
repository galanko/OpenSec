export default function HistoryPage() {
  return (
    <div className="p-8 lg:p-12 max-w-7xl mx-auto">
      <section className="mb-12">
        <h1 className="text-4xl font-headline font-extrabold tracking-tight text-on-surface mb-2">Operational Memory</h1>
        <p className="text-on-surface-variant text-lg max-w-2xl leading-relaxed">
          A historical repository of solved findings, agent logic, and validated outcomes. Use this library to audit
          past actions or reuse successful remediation plans.
        </p>
      </section>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center py-24">
        <div className="w-16 h-16 rounded-full bg-surface-container-low flex items-center justify-center mb-6">
          <span className="material-symbols-outlined text-3xl text-on-surface-variant">history</span>
        </div>
        <h2 className="text-xl font-bold text-on-surface mb-2">No completed remediations</h2>
        <p className="text-on-surface-variant text-sm text-center max-w-md">
          Completed workspaces will appear here. Start by solving a finding from the Queue.
        </p>
      </div>
    </div>
  )
}
