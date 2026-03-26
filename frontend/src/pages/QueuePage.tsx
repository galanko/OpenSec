export default function QueuePage() {
  return (
    <div className="p-8 lg:p-12">
      <div className="max-w-6xl mx-auto">
        {/* Page Header */}
        <div className="mb-10 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight text-on-surface mb-2">Work queue</h1>
            <p className="text-on-surface-variant max-w-lg">
              Prioritized security findings requiring immediate attention or verification. Review and resolve to
              maintain infrastructure integrity.
            </p>
          </div>
          <div className="flex items-center gap-x-3">
            <button className="flex items-center gap-x-2 px-4 py-2 bg-surface-container-lowest border border-outline-variant/10 rounded-lg text-sm font-medium hover:bg-surface-container transition-colors shadow-sm">
              <span className="material-symbols-outlined text-sm">filter_list</span>
              Filter
            </button>
            <button className="flex items-center gap-x-2 px-4 py-2 bg-surface-container-lowest border border-outline-variant/10 rounded-lg text-sm font-medium hover:bg-surface-container transition-colors shadow-sm">
              <span className="material-symbols-outlined text-sm">sort</span>
              Latest
            </button>
          </div>
        </div>

        {/* Finding Cards */}
        <div className="space-y-4">
          {/* Critical Finding */}
          <FindingCard
            severity="critical"
            findingId="#8421"
            timeAgo="2h ago"
            title="Apache Tomcat vulnerable version on web-prod-17"
            asset="web-prod-17"
            source="Tenable"
            team="Web Platform Team"
            status="Needs attention"
            statusColor="primary"
            icon="warning"
            iconBg="bg-error-container/20"
            iconColor="text-error"
          />

          {/* Medium Finding */}
          <FindingCard
            severity="medium"
            findingId="#8419"
            timeAgo="5h ago"
            title="Publicly exposed S3 bucket with permissive policy"
            asset="data-archive-01"
            source="CloudWatch"
            team="Data Engineering"
            status="Investigating"
            statusColor="secondary"
            icon="cloud"
            iconBg="bg-tertiary-container/20"
            iconColor="text-tertiary"
          />

          {/* Low Finding (blocked) */}
          <div className="group relative bg-surface-container-lowest opacity-75 grayscale-[0.5] rounded-xl p-6 transition-all duration-300 hover:shadow-xl hover:shadow-slate-200/40 border border-transparent flex flex-col md:flex-row md:items-center gap-6">
            <div className="flex-shrink-0">
              <div className="w-12 h-12 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
                <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>block</span>
              </div>
            </div>
            <div className="flex-grow min-w-0">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mb-1">
                <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant bg-surface-container-high px-2 py-0.5 rounded-full">Low</span>
                <span className="text-xs font-medium text-on-surface-variant">Finding #8405</span>
                <span className="text-xs text-outline-variant">&middot;</span>
                <span className="text-xs font-medium text-on-surface-variant">Yesterday</span>
              </div>
              <h3 className="text-lg font-bold text-on-surface truncate mb-1">Outdated SSH keys detected on jump-host-04</h3>
              <div className="flex flex-wrap items-center gap-x-4 text-sm text-on-surface-variant">
                <span className="flex items-center gap-x-1"><span className="material-symbols-outlined text-xs">vpn_key</span> jump-host-04</span>
                <span className="flex items-center gap-x-1"><span className="material-symbols-outlined text-xs">sync</span> Internal Scan</span>
                <span className="flex items-center gap-x-1"><span className="material-symbols-outlined text-xs">groups</span> IT Security</span>
              </div>
            </div>
            <div className="flex items-center gap-x-6 flex-shrink-0">
              <div className="text-right hidden lg:block">
                <span className="block text-xs font-medium text-outline-variant mb-1">Status</span>
                <span className="inline-flex items-center gap-x-1.5 text-sm font-semibold text-on-surface-variant">
                  <span className="w-2 h-2 rounded-full bg-outline-variant" />
                  Blocked (Pending approval)
                </span>
              </div>
              <button className="bg-surface-container-highest text-on-surface-variant px-8 py-2.5 rounded-lg font-bold transition-all cursor-not-allowed">
                Solve
              </button>
            </div>
          </div>
        </div>

        {/* AI Insight Banner */}
        <div className="mt-16 flex justify-center">
          <div className="bg-primary/5 rounded-2xl p-8 max-w-2xl text-center border border-primary/10">
            <span className="material-symbols-outlined text-primary text-4xl mb-4">auto_awesome</span>
            <h2 className="text-xl font-bold text-on-surface mb-2">Automated remediation is learning</h2>
            <p className="text-on-surface-variant text-sm leading-relaxed mb-6">
              Our Sentinel AI has observed your resolution patterns for Apache vulnerabilities. In 4 out of 5 cases,
              the fix involves an automated patch cycle. Would you like to enable auto-remediation for non-critical
              assets?
            </p>
            <div className="flex justify-center gap-x-4">
              <button className="text-sm font-bold text-primary hover:text-primary-dim transition-colors">
                Review automation rules
              </button>
              <button className="text-sm font-bold text-on-surface-variant hover:text-on-surface transition-colors">
                Dismiss
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar */}
      <div className="fixed right-0 top-16 bottom-0 w-80 bg-surface-container-low/30 backdrop-blur-sm border-l border-outline-variant/10 hidden xl:flex flex-col p-8 overflow-y-auto">
        <h4 className="text-xs font-bold uppercase tracking-widest text-outline-variant mb-6">Sentinel Insights</h4>
        <div className="space-y-8">
          <section>
            <div className="bg-surface-container-lowest rounded-xl p-5 shadow-sm border border-outline-variant/5 mb-4">
              <p className="text-sm font-semibold text-on-surface mb-3">Priority summary</p>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-on-surface-variant">Critical findings</span>
                  <span className="text-xs font-bold text-error">1 active</span>
                </div>
                <div className="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                  <div className="bg-error w-1/4 h-full" />
                </div>
              </div>
            </div>
            <p className="text-[13px] text-on-surface-variant leading-relaxed italic">
              &ldquo;The Apache Tomcat vulnerability on web-prod-17 represents the highest immediate risk due to its
              internet-facing status and known exploit availability.&rdquo;
            </p>
          </section>

          <section>
            <h5 className="text-sm font-bold text-on-surface mb-4">Active owners</h5>
            <div className="space-y-3">
              <div className="flex items-center gap-x-3">
                <div className="w-6 h-6 rounded-full bg-surface-container-high flex items-center justify-center text-[10px] font-bold text-on-surface-variant">DC</div>
                <span className="text-xs font-medium">David Chen</span>
                <span className="ml-auto w-2 h-2 rounded-full bg-primary/40" />
              </div>
              <div className="flex items-center gap-x-3">
                <div className="w-6 h-6 rounded-full bg-surface-container-high flex items-center justify-center text-[10px] font-bold text-on-surface-variant">SM</div>
                <span className="text-xs font-medium">Sarah Miller</span>
                <span className="ml-auto w-2 h-2 rounded-full bg-primary" />
              </div>
            </div>
          </section>

          <div className="mt-auto pt-8">
            <div className="p-4 bg-primary rounded-xl text-white">
              <p className="text-xs font-bold mb-2">Efficiency rating</p>
              <p className="text-2xl font-black mb-1">94%</p>
              <p className="text-[10px] opacity-80 uppercase tracking-widest font-bold">MTTR optimal range</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function FindingCard({
  severity,
  findingId,
  timeAgo,
  title,
  asset,
  source,
  team,
  status,
  statusColor,
  icon,
  iconBg,
  iconColor,
}: {
  severity: string
  findingId: string
  timeAgo: string
  title: string
  asset: string
  source: string
  team: string
  status: string
  statusColor: string
  icon: string
  iconBg: string
  iconColor: string
}) {
  const severityClasses =
    severity === 'critical'
      ? 'text-error bg-error-container/30'
      : severity === 'medium'
        ? 'text-tertiary bg-tertiary-container/30'
        : 'text-on-surface-variant bg-surface-container-high'

  return (
    <div className="group relative bg-surface-container-lowest rounded-xl p-6 transition-all duration-300 hover:shadow-xl hover:shadow-slate-200/40 border border-transparent hover:border-primary/5 flex flex-col md:flex-row md:items-center gap-6">
      <div className="flex-shrink-0">
        <div className={`w-12 h-12 rounded-full ${iconBg} flex items-center justify-center ${iconColor}`}>
          <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>{icon}</span>
        </div>
      </div>
      <div className="flex-grow min-w-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 mb-1">
          <span className={`text-xs font-bold uppercase tracking-wider ${severityClasses} px-2 py-0.5 rounded-full`}>
            {severity}
          </span>
          <span className="text-xs font-medium text-on-surface-variant">Finding {findingId}</span>
          <span className="text-xs text-outline-variant">&middot;</span>
          <span className="text-xs font-medium text-on-surface-variant">{timeAgo}</span>
        </div>
        <h3 className="text-lg font-bold text-on-surface truncate mb-1">{title}</h3>
        <div className="flex flex-wrap items-center gap-x-4 text-sm text-on-surface-variant">
          <span className="flex items-center gap-x-1"><span className="material-symbols-outlined text-xs">dns</span> {asset}</span>
          <span className="flex items-center gap-x-1"><span className="material-symbols-outlined text-xs">hub</span> {source}</span>
          <span className="flex items-center gap-x-1"><span className="material-symbols-outlined text-xs">groups</span> {team}</span>
        </div>
      </div>
      <div className="flex items-center gap-x-6 flex-shrink-0">
        <div className="text-right hidden lg:block">
          <span className="block text-xs font-medium text-outline-variant mb-1">Status</span>
          <span className={`inline-flex items-center gap-x-1.5 text-sm font-semibold text-${statusColor}`}>
            <span className={`w-2 h-2 rounded-full bg-${statusColor}`} />
            {status}
          </span>
        </div>
        <button className="bg-primary hover:bg-primary-dim text-white px-8 py-2.5 rounded-lg font-bold transition-all shadow-lg shadow-primary/20 active:scale-95">
          Solve
        </button>
      </div>
    </div>
  )
}
