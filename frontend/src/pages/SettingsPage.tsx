import { useHealth } from '@/api/hooks'

export default function SettingsPage() {
  const { data: health } = useHealth()

  return (
    <div className="p-8 lg:p-12">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row gap-12">
        {/* Settings Navigation */}
        <nav className="w-full md:w-64 flex-shrink-0 space-y-1">
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg bg-surface-container-lowest text-primary font-semibold shadow-sm shadow-slate-200/50" href="#model">
            <span className="material-symbols-outlined text-[20px]">neurology</span>
            <span className="text-sm">Model settings</span>
          </a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors" href="#about">
            <span className="material-symbols-outlined text-[20px]">info</span>
            <span className="text-sm">About</span>
          </a>
        </nav>

        {/* Settings Content */}
        <div className="flex-1 space-y-16 pb-24">
          {/* Model Settings */}
          <section className="scroll-mt-24" id="model">
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">Model settings</h2>
              <p className="text-on-surface-variant text-sm max-w-xl">
                The AI model is configured via the OpenCode engine. Edit <code className="text-xs bg-surface-container-low px-1.5 py-0.5 rounded font-mono">opencode.json</code> to change provider and model.
              </p>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm shadow-slate-200/50 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant block mb-2">Model</label>
                  <div className="bg-surface-container-low rounded-lg px-4 py-3 text-sm font-mono text-on-surface">
                    {health?.model || 'Not connected'}
                  </div>
                </div>
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant block mb-2">Engine status</label>
                  <div className="bg-surface-container-low rounded-lg px-4 py-3 text-sm flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${health?.opencode === 'running' ? 'bg-green-500' : 'bg-outline-variant'}`} />
                    {health?.opencode || 'Not connected'}
                  </div>
                </div>
              </div>
              {health && (
                <div>
                  <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant block mb-2">OpenCode version</label>
                  <div className="bg-surface-container-low rounded-lg px-4 py-3 text-sm font-mono text-on-surface">
                    {health.opencode_version}
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* About */}
          <section className="scroll-mt-24" id="about">
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">About</h2>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm shadow-slate-200/50">
              <p className="text-sm text-on-surface-variant leading-relaxed">
                <span className="font-bold text-on-surface">OpenSec</span> is a self-hosted cybersecurity remediation copilot.
                It ingests vulnerability findings, enriches them with AI agents, and guides you through planning, ticketing,
                validating, and closing remediations.
              </p>
              <div className="mt-6 flex items-center gap-2 text-xs text-on-surface-variant">
                <span className="material-symbols-outlined text-sm">code</span>
                Single-user community edition &middot; MIT licensed
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
