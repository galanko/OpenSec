export default function IntegrationsPage() {
  return (
    <div className="p-8 lg:p-12 max-w-7xl mx-auto">
      <header className="mb-12">
        <h1 className="font-headline text-4xl font-extrabold text-on-surface tracking-tight mb-3">Integrations</h1>
        <p className="text-on-surface-variant text-lg max-w-2xl leading-relaxed">
          Connect your security stack to enable automated remediation, centralized visibility, and
          intelligence-driven workflows.
        </p>
      </header>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center py-24">
        <div className="w-16 h-16 rounded-full bg-surface-container-low flex items-center justify-center mb-6">
          <span className="material-symbols-outlined text-3xl text-on-surface-variant">extension</span>
        </div>
        <h2 className="text-xl font-bold text-on-surface mb-2">No integrations configured</h2>
        <p className="text-on-surface-variant text-sm text-center max-w-md">
          Connect vulnerability scanners, ticketing systems, and validation tools to power the remediation pipeline.
        </p>
      </div>
    </div>
  )
}
