export default function QueuePage() {
  return (
    <div className="p-8 lg:p-12">
      <div className="max-w-6xl mx-auto">
        <div className="mb-10">
          <h1 className="text-4xl font-extrabold tracking-tight text-on-surface mb-2">Work queue</h1>
          <p className="text-on-surface-variant max-w-lg">
            Prioritized security findings requiring immediate attention or verification. Review and resolve to
            maintain infrastructure integrity.
          </p>
        </div>

        {/* Empty state */}
        <div className="flex flex-col items-center justify-center py-24">
          <div className="w-16 h-16 rounded-full bg-surface-container-low flex items-center justify-center mb-6">
            <span className="material-symbols-outlined text-3xl text-on-surface-variant">assignment_late</span>
          </div>
          <h2 className="text-xl font-bold text-on-surface mb-2">No findings yet</h2>
          <p className="text-on-surface-variant text-sm text-center max-w-md mb-8">
            Connect a vulnerability scanner in Integrations to start importing findings, or wait for your first scan results.
          </p>
          <a
            href="/integrations"
            className="bg-primary hover:bg-primary-dim text-white px-6 py-2.5 rounded-lg font-semibold text-sm transition-all shadow-lg shadow-primary/20 active:scale-95"
          >
            Connect a scanner
          </a>
        </div>
      </div>
    </div>
  )
}
