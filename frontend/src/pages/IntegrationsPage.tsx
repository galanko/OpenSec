export default function IntegrationsPage() {
  return (
    <div className="p-8 lg:p-12 max-w-7xl mx-auto">
      {/* Header */}
      <header className="mb-12">
        <h1 className="font-headline text-4xl font-extrabold text-on-surface tracking-tight mb-3">Integrations</h1>
        <p className="text-on-surface-variant text-lg max-w-2xl leading-relaxed">
          Connect your security stack to enable automated remediation, centralized visibility, and
          intelligence-driven workflows.
        </p>
      </header>

      {/* Category Filter */}
      <div className="flex flex-wrap gap-3 mb-12">
        <button className="px-6 py-2.5 rounded-full bg-primary text-on-primary text-sm font-medium transition-all shadow-md shadow-primary/10">All apps</button>
        <button className="px-6 py-2.5 rounded-full bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-high transition-all text-sm font-medium">Finding sources</button>
        <button className="px-6 py-2.5 rounded-full bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-high transition-all text-sm font-medium">Context / ownership sources</button>
        <button className="px-6 py-2.5 rounded-full bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-high transition-all text-sm font-medium">Ticketing</button>
        <button className="px-6 py-2.5 rounded-full bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container-high transition-all text-sm font-medium">Validation</button>
      </div>

      {/* Integrations Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
        <IntegrationCard icon="security" iconColor="text-primary" name="Tenable" description="Vulnerability management and risk-based assessment for your entire attack surface." status="connected" />
        <IntegrationCard icon="task_alt" iconColor="text-secondary" name="Jira" description="Sync security findings directly into developer workflows with automated ticket creation." status="connected" />
        <IntegrationCard icon="hub" iconColor="text-tertiary" name="ServiceNow" description="Enterprise-grade IT service management for asset tracking and incident response." status="available" />
        <IntegrationCard icon="radar" iconColor="text-primary" name="CrowdStrike" description="Endpoint protection and threat intelligence integration for real-time asset context." status="connected" />

        {/* AI Recommendation Card */}
        <div className="md:col-span-2 xl:col-span-2 relative bg-gradient-to-br from-primary to-primary-dim rounded-xl p-10 flex flex-col md:flex-row gap-10 items-center overflow-hidden">
          <div className="absolute -right-20 -top-20 w-80 h-80 bg-white/10 rounded-full blur-3xl" />
          <div className="relative z-10 flex-1">
            <div className="flex items-center gap-2 mb-4">
              <span className="material-symbols-outlined text-white" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
              <span className="text-white/80 font-bold uppercase tracking-widest text-xs">AI insight</span>
            </div>
            <h2 className="font-headline text-3xl font-extrabold text-white mb-4 leading-tight">Recommended integrations</h2>
            <p className="text-white/90 text-lg leading-relaxed mb-6">
              Based on your recent security scans, connecting <span className="font-bold underline">Splunk</span> could
              reduce your incident MTTR by up to 24% through automated logging.
            </p>
            <button className="px-8 py-3 bg-white text-primary font-bold rounded-lg hover:bg-surface-container-lowest transition-all active:scale-95">
              Explore insights
            </button>
          </div>
          <div className="relative z-10 w-full md:w-64 aspect-square glass-card rounded-2xl p-6 border border-white/20 shadow-2xl flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-primary text-4xl">monitoring</span>
            </div>
            <div className="text-on-surface text-2xl font-bold mb-1">+24%</div>
            <div className="text-on-surface-variant text-sm">Potential efficiency</div>
          </div>
        </div>
      </div>

      {/* Pagination */}
      <footer className="mt-16 flex flex-col md:flex-row items-center justify-between gap-6 pb-20">
        <div className="flex items-center gap-4">
          <button className="flex items-center gap-2 text-on-surface-variant font-medium hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            Previous
          </button>
          <div className="flex items-center gap-1">
            <span className="w-8 h-8 flex items-center justify-center rounded-lg bg-primary text-on-primary font-bold text-sm">1</span>
            <span className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-surface-container-high text-on-surface-variant font-medium text-sm transition-all cursor-pointer">2</span>
            <span className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-surface-container-high text-on-surface-variant font-medium text-sm transition-all cursor-pointer">3</span>
          </div>
          <button className="flex items-center gap-2 text-on-surface-variant font-medium hover:text-on-surface transition-colors">
            Next
            <span className="material-symbols-outlined text-sm">arrow_forward</span>
          </button>
        </div>
        <div className="flex items-center gap-2 text-on-surface-variant text-sm">
          <span className="material-symbols-outlined text-sm">sync</span>
          Last updated 2 minutes ago
        </div>
      </footer>
    </div>
  )
}

function IntegrationCard({ icon, iconColor, name, description, status }: {
  icon: string; iconColor: string; name: string; description: string; status: 'connected' | 'available'
}) {
  const isConnected = status === 'connected'
  return (
    <div className="group relative flex flex-col bg-surface-container-lowest rounded-xl p-8 border border-transparent hover:shadow-2xl hover:shadow-slate-200/50 transition-all duration-300">
      <div className="flex justify-between items-start mb-6">
        <div className="w-14 h-14 rounded-lg bg-surface-container-low flex items-center justify-center">
          <span className={`material-symbols-outlined text-3xl ${iconColor}`}>{icon}</span>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold tracking-wide uppercase ${
          isConnected
            ? 'bg-primary-container text-on-primary-container'
            : 'bg-surface-container-high text-on-surface-variant'
        }`}>
          {isConnected ? 'Connected' : 'Available'}
        </span>
      </div>
      <h3 className="font-headline text-xl font-bold text-on-surface mb-2">{name}</h3>
      <p className="text-on-surface-variant text-sm mb-8 leading-relaxed">{description}</p>
      <div className="mt-auto flex items-center justify-between pt-6 border-t border-surface-container">
        <button className="text-primary text-sm font-semibold hover:underline decoration-2 underline-offset-4 transition-all">
          {isConnected ? 'Test connection' : 'Connect app'}
        </button>
        <button className="material-symbols-outlined text-on-surface-variant hover:text-on-surface transition-colors">
          {isConnected ? 'more_horiz' : 'info'}
        </button>
      </div>
    </div>
  )
}
