export default function HistoryPage() {
  return (
    <div className="p-8 lg:p-12 max-w-7xl mx-auto">
      {/* Header */}
      <section className="mb-12">
        <h1 className="text-4xl font-headline font-extrabold tracking-tight text-on-surface mb-2">Operational Memory</h1>
        <p className="text-on-surface-variant text-lg max-w-2xl leading-relaxed">
          A historical repository of solved findings, agent logic, and validated outcomes. Use this library to audit
          past actions or reuse successful remediation plans.
        </p>
      </section>

      {/* Stats Bento Row */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border border-outline-variant/10">
          <span className="text-sm font-label text-on-surface-variant uppercase tracking-wider">Total resolved</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-3xl font-headline font-bold">1,284</span>
            <span className="text-primary text-xs font-semibold">+12% this month</span>
          </div>
        </div>
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm border border-outline-variant/10">
          <span className="text-sm font-label text-on-surface-variant uppercase tracking-wider">Avg. time to fix</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-3xl font-headline font-bold">4.2h</span>
            <span className="text-on-surface-variant text-xs">-15m vs last week</span>
          </div>
        </div>
        <div className="bg-primary text-on-primary p-6 rounded-xl shadow-md flex justify-between items-center relative overflow-hidden">
          <div className="relative z-10">
            <span className="text-sm font-label opacity-80 uppercase tracking-wider">Success rate</span>
            <div className="text-3xl font-headline font-bold mt-2">99.2%</div>
          </div>
          <span className="material-symbols-outlined text-6xl opacity-20 absolute -right-2 -bottom-2">verified</span>
        </div>
      </section>

      {/* Filters */}
      <section className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-surface-container-lowest border border-outline-variant/15 rounded-lg text-sm font-medium text-on-surface-variant hover:bg-surface-container-low transition-colors">
            <span className="material-symbols-outlined text-sm">filter_list</span>
            Filter
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-surface-container-lowest border border-outline-variant/15 rounded-lg text-sm font-medium text-on-surface-variant hover:bg-surface-container-low transition-colors">
            <span className="material-symbols-outlined text-sm">calendar_month</span>
            Last 30 days
          </button>
        </div>
        <div className="text-sm text-on-surface-variant font-medium">
          Showing <span className="text-on-surface">48</span> of 1,284 findings
        </div>
      </section>

      {/* Findings List */}
      <div className="space-y-4">
        <HistoryEntry icon="security" iconColor="text-primary" title="Tomcat vulnerability on web-prod-17" team="Web Platform Team" ticket="PLAT-5571" time="2 days ago" />
        <HistoryEntry icon="leak_add" iconColor="text-error" title="AWS S3 Public Bucket Exposure" team="Cloud Ops" ticket="SEC-9021" time="5 days ago" />
        <HistoryEntry icon="key" iconColor="text-amber-500" title="Hardcoded API Key in frontend-repo" team="UI Team" ticket="DEV-1294" time="1 week ago" />

        {/* AI Insight Card */}
        <div className="relative bg-gradient-to-br from-primary to-indigo-700 rounded-2xl p-8 text-white shadow-xl overflow-hidden mt-12 mb-12">
          <div className="relative z-10 grid md:grid-cols-2 gap-8 items-center">
            <div>
              <h2 className="text-2xl font-headline font-bold mb-4">Historical pattern detected</h2>
              <p className="text-indigo-100 leading-relaxed mb-6">
                I&rsquo;ve noticed a 30% increase in Tomcat-related vulnerabilities across different subnets. Your past
                remediation plan for PLAT-5571 was 40% faster than manual resolution. I recommend standardizing this plan
                for future instances.
              </p>
              <button className="bg-white text-primary px-6 py-2.5 rounded-lg font-bold text-sm hover:bg-indigo-50 transition-colors shadow-lg">
                Standardize remediation
              </button>
            </div>
            <div className="hidden md:block">
              <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
                <div className="text-xs uppercase tracking-widest opacity-60 mb-4">Efficiency map</div>
                <div className="space-y-3">
                  <div className="h-2 w-full bg-white/10 rounded-full"><div className="h-full bg-white rounded-full" style={{ width: '85%' }} /></div>
                  <div className="h-2 w-full bg-white/10 rounded-full"><div className="h-full bg-white rounded-full" style={{ width: '45%' }} /></div>
                  <div className="h-2 w-full bg-white/10 rounded-full"><div className="h-full bg-white rounded-full" style={{ width: '65%' }} /></div>
                </div>
              </div>
            </div>
          </div>
          <div className="absolute -right-10 -top-10 w-64 h-64 bg-white/5 rounded-full blur-3xl" />
        </div>

        <HistoryEntry icon="database" iconColor="text-slate-400" title="Unencrypted Redis Cache" team="DB Admin" ticket="DB-112" time="10 days ago" />
      </div>

      {/* Pagination */}
      <footer className="mt-12 flex justify-center items-center gap-4">
        <button className="p-2 rounded-full border border-outline-variant/20 text-on-surface-variant hover:bg-surface-container-low transition-colors">
          <span className="material-symbols-outlined">chevron_left</span>
        </button>
        <div className="flex items-center gap-1">
          <span className="w-8 h-8 flex items-center justify-center rounded-lg bg-primary text-white text-sm font-bold">1</span>
          <span className="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container-low cursor-pointer transition-colors">2</span>
          <span className="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container-low cursor-pointer transition-colors">3</span>
          <span className="px-2 text-on-surface-variant">...</span>
          <span className="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container-low cursor-pointer transition-colors">24</span>
        </div>
        <button className="p-2 rounded-full border border-outline-variant/20 text-on-surface-variant hover:bg-surface-container-low transition-colors">
          <span className="material-symbols-outlined">chevron_right</span>
        </button>
      </footer>
    </div>
  )
}

function HistoryEntry({ icon, iconColor, title, team, ticket, time }: {
  icon: string; iconColor: string; title: string; team: string; ticket: string; time: string
}) {
  return (
    <div className="group bg-surface-container-lowest p-6 rounded-xl shadow-sm hover:shadow-md transition-all duration-300 border border-transparent hover:border-primary/10 flex flex-col lg:flex-row lg:items-center gap-6">
      <div className="flex-1">
        <div className="flex items-center gap-3 mb-1">
          <span className={`material-symbols-outlined ${iconColor}`} style={{ fontVariationSettings: "'FILL' 1" }}>{icon}</span>
          <h3 className="text-lg font-headline font-bold text-on-surface">{title}</h3>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-on-surface-variant">
          <span className="flex items-center gap-1.5"><span className="material-symbols-outlined text-xs">person</span> {team}</span>
          <span className="flex items-center gap-1.5"><span className="material-symbols-outlined text-xs">confirmation_number</span> {ticket}</span>
          <span className="flex items-center gap-1.5"><span className="material-symbols-outlined text-xs">schedule</span> {time}</span>
        </div>
      </div>
      <div className="flex items-center gap-4 lg:ml-auto">
        <span className="px-3 py-1 bg-primary-container text-on-primary-container text-xs font-bold rounded-full uppercase tracking-tighter">Fixed</span>
        <div className="h-8 w-px bg-outline-variant/20 hidden lg:block" />
        <div className="flex items-center gap-2">
          <button className="px-4 py-2 text-sm font-semibold text-primary hover:bg-primary/5 rounded-lg transition-colors">Open workspace</button>
          <button className="px-4 py-2 text-sm font-semibold text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors">View summary</button>
          <button className="p-2 text-on-surface-variant hover:text-primary transition-colors" title="Reuse Plan">
            <span className="material-symbols-outlined">rebase_edit</span>
          </button>
        </div>
      </div>
    </div>
  )
}
