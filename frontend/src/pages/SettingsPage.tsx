export default function SettingsPage() {
  return (
    <div className="p-8 lg:p-12">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row gap-12">
        {/* Settings Navigation */}
        <nav className="w-full md:w-64 flex-shrink-0 space-y-1">
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg bg-surface-container-lowest text-primary font-semibold shadow-sm shadow-slate-200/50" href="#model">
            <span className="material-symbols-outlined text-[20px]">neurology</span>
            <span className="text-sm">Model settings</span>
          </a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors" href="#agents">
            <span className="material-symbols-outlined text-[20px]">smart_toy</span>
            <span className="text-sm">Agent settings</span>
          </a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors" href="#workspace">
            <span className="material-symbols-outlined text-[20px]">workspaces</span>
            <span className="text-sm">Workspace defaults</span>
          </a>
          <a className="flex items-center gap-3 px-4 py-3 rounded-lg text-on-surface-variant hover:bg-surface-container-low transition-colors" href="#preferences">
            <span className="material-symbols-outlined text-[20px]">tune</span>
            <span className="text-sm">App preferences</span>
          </a>
        </nav>

        {/* Settings Content */}
        <div className="flex-1 space-y-16 pb-24">
          {/* Model Settings */}
          <section className="scroll-mt-24" id="model">
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">Model settings</h2>
              <p className="text-on-surface-variant text-sm max-w-xl">
                Configure the underlying intelligence engine that powers the sentinel&rsquo;s reasoning and detection logic.
              </p>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm shadow-slate-200/50 space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Provider</label>
                  <div className="relative">
                    <select className="w-full appearance-none bg-surface-container-low border-none rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-primary/20 transition-all outline-none cursor-pointer">
                      <option>OpenAI (Cloud)</option>
                      <option>Anthropic (Cloud)</option>
                      <option>Llama 3 (Local Runtime)</option>
                      <option>Mistral (Enterprise)</option>
                    </select>
                    <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant text-[20px]">expand_more</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Model name</label>
                  <input className="w-full bg-surface-container-low border-none rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-primary/20 transition-all outline-none font-mono" type="text" defaultValue="gpt-4-turbo-preview" />
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Temperature</label>
                  <span className="text-sm font-medium text-primary bg-primary-container px-2 py-0.5 rounded-full">0.7</span>
                </div>
                <input className="w-full h-1.5 bg-surface-container-high rounded-full appearance-none cursor-pointer accent-primary" max={1} min={0} step={0.1} type="range" defaultValue={0.7} />
                <div className="flex justify-between text-[10px] text-on-surface-variant font-medium uppercase tracking-widest">
                  <span>Precise</span>
                  <span>Balanced</span>
                  <span>Creative</span>
                </div>
              </div>
            </div>
          </section>

          {/* Agent Settings */}
          <section className="scroll-mt-24" id="agents">
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">Agent settings</h2>
              <p className="text-on-surface-variant text-sm max-w-xl">
                Enable specialized sub-routines and control how the sidebar reflects background activity.
              </p>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm shadow-slate-200/50 space-y-6">
              <ToggleRow icon="security" iconBg="bg-indigo-50" iconColor="text-indigo-600" label="Active threat hunting" description="Real-time scan for anomalous network patterns." enabled />
              <ToggleRow icon="auto_awesome" iconBg="bg-slate-100" iconColor="text-slate-500" label="Auto-remediation" description="Allow AI to patch known vulnerabilities automatically." enabled={false} />
              <div className="pt-6 border-t border-slate-100">
                <ToggleRow icon="" iconBg="" iconColor="" label="Auto-update sidebar" description="Dynamically refresh agent status in the main navigation." enabled />
              </div>
            </div>
          </section>

          {/* Workspace Defaults */}
          <section className="scroll-mt-24" id="workspace">
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">Workspace defaults</h2>
              <p className="text-on-surface-variant text-sm max-w-xl">
                Global behaviors for incident handling and session management.
              </p>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm shadow-slate-200/50 space-y-8">
              <div className="space-y-3">
                <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Default actions</label>
                <div className="flex flex-wrap gap-2">
                  <span className="px-3 py-1.5 rounded-full bg-primary text-white text-xs font-medium cursor-pointer">Quarantine</span>
                  <span className="px-3 py-1.5 rounded-full bg-surface-container-high text-on-surface-variant text-xs font-medium hover:bg-slate-200 transition-colors cursor-pointer">Notify admin</span>
                  <span className="px-3 py-1.5 rounded-full bg-surface-container-high text-on-surface-variant text-xs font-medium hover:bg-slate-200 transition-colors cursor-pointer">Ignore low-risk</span>
                  <span className="px-3 py-1.5 rounded-full bg-surface-container-high text-on-surface-variant text-xs font-medium hover:bg-slate-200 transition-colors cursor-pointer">Log only</span>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-primary text-[20px]">history_toggle_off</span>
                  <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">History behavior</label>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg border-2 border-primary bg-primary/5 cursor-pointer">
                    <p className="text-sm font-semibold text-primary">Persistence</p>
                    <p className="text-xs text-on-primary-fixed-variant mt-1">Keep all interaction history across sessions.</p>
                  </div>
                  <div className="p-4 rounded-lg border border-slate-100 hover:border-slate-200 transition-all cursor-pointer">
                    <p className="text-sm font-semibold">Ephemeral</p>
                    <p className="text-xs text-on-surface-variant mt-1">Clear history every time the workspace closes.</p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* App Preferences */}
          <section className="scroll-mt-24" id="preferences">
            <div className="mb-8">
              <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">App preferences</h2>
              <p className="text-on-surface-variant text-sm max-w-xl">
                Customize the interface language and notification delivery systems.
              </p>
            </div>
            <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm shadow-slate-200/50">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                <div className="space-y-6">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Display language</label>
                    <div className="relative">
                      <select className="w-full appearance-none bg-surface-container-low border-none rounded-lg px-4 py-3 text-sm focus:ring-2 focus:ring-primary/20 transition-all outline-none cursor-pointer">
                        <option>English (US)</option>
                        <option>Deutsch</option>
                        <option>Fran&ccedil;ais</option>
                      </select>
                      <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant text-[20px]">language</span>
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <label className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Notification channels</label>
                  <div className="space-y-3">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input defaultChecked className="w-4 h-4 rounded text-primary focus:ring-primary border-slate-300" type="checkbox" />
                      <span className="text-sm">In-app banners</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input defaultChecked className="w-4 h-4 rounded text-primary focus:ring-primary border-slate-300" type="checkbox" />
                      <span className="text-sm">Email digests</span>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input className="w-4 h-4 rounded text-primary focus:ring-primary border-slate-300" type="checkbox" />
                      <span className="text-sm">Desktop push</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-4 pt-8 border-t border-slate-200/50">
            <button className="px-6 py-2.5 text-sm font-semibold text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors">
              Discard changes
            </button>
            <button className="px-8 py-2.5 text-sm font-semibold text-white bg-gradient-to-tr from-primary to-primary-dim rounded-lg shadow-md shadow-indigo-200/50 active:scale-95 transition-transform">
              Save settings
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ToggleRow({ icon, iconBg, iconColor, label, description, enabled }: {
  icon: string; iconBg: string; iconColor: string; label: string; description: string; enabled: boolean
}) {
  return (
    <div className="flex items-center justify-between p-4 rounded-lg hover:bg-surface-container-low transition-colors cursor-pointer group">
      <div className="flex items-center gap-4">
        {icon && (
          <div className={`w-10 h-10 rounded-lg ${iconBg} flex items-center justify-center ${iconColor}`}>
            <span className="material-symbols-outlined">{icon}</span>
          </div>
        )}
        <div>
          <p className="text-sm font-semibold">{label}</p>
          <p className="text-xs text-on-surface-variant">{description}</p>
        </div>
      </div>
      <div className={`w-11 h-6 ${enabled ? 'bg-primary' : 'bg-surface-container-high'} rounded-full relative transition-colors cursor-pointer`}>
        <div className={`absolute ${enabled ? 'right-1' : 'left-1'} top-1 w-4 h-4 bg-white rounded-full shadow-sm`} />
      </div>
    </div>
  )
}
