import ProviderSettings from '@/components/settings/ProviderSettings'
import IntegrationSettings from '@/components/settings/IntegrationSettings'
import PageShell from '@/components/PageShell'

const navSections = [
  { id: 'providers', icon: 'dns', label: 'Providers' },
  { id: 'integrations', icon: 'extension', label: 'Integrations' },
  { id: 'about', icon: 'info', label: 'About' },
]

export default function SettingsPage() {
  return (
    <PageShell title="Settings" subtitle="Configure providers, integrations, and preferences.">
      <div className="flex flex-col md:flex-row gap-12">
        {/* Settings navigation — sticky */}
        <nav className="w-full md:w-64 flex-shrink-0 space-y-1 md:sticky md:top-24 md:self-start">
          {navSections.map((section) => (
            <a
              key={section.id}
              href={`#${section.id}`}
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors"
            >
              <span className="material-symbols-outlined text-[20px]">{section.icon}</span>
              <span className="text-sm">{section.label}</span>
            </a>
          ))}
        </nav>

        {/* Settings content */}
        <div className="flex-1 space-y-16 pb-24">
          <ProviderSettings />
          <IntegrationSettings />

          {/* About */}
          <section className="scroll-mt-24" id="about">
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">About</h2>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm shadow-slate-200/50">
              <p className="text-sm text-on-surface-variant leading-relaxed">
                <span className="font-bold text-on-surface">OpenSec</span> is a self-hosted
                cybersecurity remediation copilot. It ingests vulnerability findings, enriches
                them with AI agents, and guides you through planning, ticketing, validating, and
                closing remediations.
              </p>
              <div className="mt-6 flex items-center gap-2 text-xs text-on-surface-variant">
                <span className="material-symbols-outlined text-sm">code</span>
                Single-user community edition &middot; AGPL-3.0 licensed
              </div>
            </div>
          </section>
        </div>
      </div>
    </PageShell>
  )
}
