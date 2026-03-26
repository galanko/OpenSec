export default function WorkspacePage() {
  return (
    <div className="flex flex-col">
      {/* Remediation Header Bar */}
      <section className="bg-surface-container-lowest px-8 py-4 flex items-center justify-between border-b border-surface-container">
        <div className="flex items-center gap-4">
          <div className="p-2 bg-error-container/20 rounded-lg">
            <span className="material-symbols-outlined text-error">warning</span>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Apache Tomcat vulnerable version...</h1>
            <div className="flex gap-3 mt-1 items-center">
              <span className="px-2 py-0.5 rounded-full bg-error-container text-on-error-container text-[10px] font-bold uppercase tracking-wider">
                Critical
              </span>
              <span className="text-xs text-on-surface-variant">
                Asset: <span className="text-on-surface font-medium">web-prod-17</span>
              </span>
              <span className="text-xs text-on-surface-variant">
                Likely owner: <span className="text-on-surface font-medium">Web Platform Team</span>
              </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-outline-variant/30 text-sm hover:bg-surface-container transition-colors">
            <span className="material-symbols-outlined text-sm">share</span>
            Share
          </button>
          <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-outline-variant/30 text-sm hover:bg-surface-container transition-colors">
            <span className="material-symbols-outlined text-sm">more_vert</span>
          </button>
        </div>
      </section>

      <div className="flex flex-1 overflow-hidden">
        {/* Chat Thread */}
        <section className="flex-1 overflow-y-auto px-8 py-10 bg-surface-container-low flex flex-col gap-8 scroll-smooth">
          {/* Finding Summary Bubble */}
          <div className="max-w-3xl">
            <div className="bg-white rounded-2xl p-6 shadow-md border border-surface-container/80">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center flex-shrink-0">
                  <span className="material-symbols-outlined text-primary">auto_awesome</span>
                </div>
                <div>
                  <h3 className="text-lg font-bold mb-2">Finding summary</h3>
                  <p className="text-on-surface-variant text-sm leading-relaxed mb-4">
                    CVE-2023-46589 identified on <span className="font-mono text-primary">web-prod-17</span>. The
                    version of Apache Tomcat (9.0.82) is vulnerable to request smuggling. This allows attackers to
                    bypass security constraints and access unauthorized internal resources.
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-surface-container-low rounded-lg">
                      <p className="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest mb-1">Impact</p>
                      <p className="text-sm font-semibold">Remote Code Execution (RCE)</p>
                    </div>
                    <div className="p-3 bg-surface-container-low rounded-lg">
                      <p className="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest mb-1">Exposure</p>
                      <p className="text-sm font-semibold">Publicly accessible</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Suggested Action Chips */}
          <div className="flex flex-wrap gap-2 max-w-3xl">
            {['Explain why this matters', 'Find owner', 'Enrich issue', 'Check exposure', 'Build remediation plan', 'Draft ticket', 'Validate closure'].map((action) => (
              <button key={action} className="px-4 py-2 rounded-full border border-primary/10 bg-white text-xs font-medium text-primary hover:bg-primary-container/30 shadow-sm transition-all">
                {action}
              </button>
            ))}
          </div>

          {/* Agent Running State */}
          <div className="max-w-3xl">
            <div className="bg-indigo-50/80 border border-indigo-100 rounded-xl p-4 flex items-center gap-4 animate-pulse shadow-sm">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-primary/40" />
                <div className="w-1.5 h-1.5 rounded-full bg-primary/60" />
                <div className="w-1.5 h-1.5 rounded-full bg-primary/80" />
              </div>
              <p className="text-sm text-on-primary-fixed-variant font-medium">Looking for owner... Comparing prior tickets...</p>
            </div>
          </div>

          {/* Agent Result Card */}
          <div className="max-w-3xl self-start">
            <div className="bg-white rounded-2xl shadow-md overflow-hidden border border-surface-container/80">
              <div className="bg-primary/5 px-6 py-3 border-b border-surface-container/50 flex items-center justify-between">
                <h3 className="text-sm font-bold text-primary tracking-tight">Owner Resolver Result</h3>
                <span className="text-[10px] font-bold text-on-surface-variant uppercase bg-surface-container-high px-2 py-0.5 rounded">Result 012</span>
              </div>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <p className="text-lg font-bold text-on-surface">Best match: Web Platform Team</p>
                  <div className="flex items-center gap-1.5 text-primary-dim">
                    <span className="text-sm font-bold">92% confidence</span>
                    <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>verified</span>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <span className="material-symbols-outlined text-on-surface-variant mt-0.5">fact_check</span>
                    <div>
                      <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-1">Evidence</p>
                      <p className="text-sm text-on-surface leading-relaxed">
                        CMDB records link <span className="font-mono">web-prod-17</span> to &lsquo;Platform
                        Services&rsquo; namespace. 8 out of 10 prior Tomcat vulnerabilities on this subnet were
                        resolved by @mark_dev (Lead, Web Platform Team).
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <span className="material-symbols-outlined text-on-surface-variant mt-0.5">lightbulb</span>
                    <div>
                      <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-1">Recommendation</p>
                      <p className="text-sm text-on-surface">
                        Assign to Web Platform Team and draft a Jira ticket with the pre-approved remediation script
                        for Tomcat 9.x.
                      </p>
                    </div>
                  </div>
                </div>
                <div className="mt-6 flex gap-3">
                  <button className="bg-primary text-white text-xs font-bold px-4 py-2 rounded-lg hover:shadow-lg hover:shadow-primary/20 transition-all">
                    Assign &amp; Draft Ticket
                  </button>
                  <button className="text-on-surface-variant text-xs font-bold px-4 py-2 rounded-lg border border-outline-variant/30 hover:bg-surface-container-low transition-all">
                    Ignore result
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="h-24" />
        </section>

        {/* Right Sidebar */}
        <aside className="w-80 bg-surface-container-low border-l border-surface-container overflow-y-auto hidden lg:block">
          <div className="p-6 flex flex-col gap-8">
            <SidebarSection title="Summary">
              <div className="bg-surface-container-lowest p-4 rounded-xl shadow-sm border border-surface-container/50">
                <p className="text-xs font-semibold mb-1">What</p>
                <p className="text-xs text-on-surface-variant leading-relaxed mb-3">
                  Vulnerable Apache Tomcat 9.0.82 allows HTTP request smuggling.
                </p>
                <p className="text-xs font-semibold mb-1">Why</p>
                <p className="text-xs text-on-surface-variant leading-relaxed">
                  Critical for compliance and prevents unauthorized admin access to the production cluster.
                </p>
              </div>
            </SidebarSection>

            <SidebarSection title="Evidence">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs bg-surface-container-lowest p-2 rounded-lg border border-surface-container/30">
                  <span className="text-on-surface-variant">Version scan</span>
                  <span className="font-mono text-error">9.0.82</span>
                </div>
                <div className="flex items-center justify-between text-xs bg-surface-container-lowest p-2 rounded-lg border border-surface-container/30">
                  <span className="text-on-surface-variant">Public exposure</span>
                  <span className="text-error font-medium">True</span>
                </div>
              </div>
            </SidebarSection>

            <SidebarSection title="Owner">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-primary font-bold text-xs">WP</div>
                <div>
                  <p className="text-xs font-bold">Web Platform Team</p>
                  <p className="text-[10px] text-primary font-medium">92% match</p>
                </div>
              </div>
            </SidebarSection>

            <SidebarSection title="Plan">
              <div className="bg-surface-container-lowest p-4 rounded-xl border border-surface-container/50">
                <ul className="text-xs space-y-3">
                  <li className="flex gap-2">
                    <span className="w-4 h-4 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold">1</span>
                    <span>Upgrade to Tomcat 10.1.16+</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="w-4 h-4 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold">2</span>
                    <span>Rotate cluster secrets</span>
                  </li>
                </ul>
                <div className="mt-4 pt-4 border-t border-surface-container flex justify-between items-center">
                  <span className="text-[10px] text-on-surface-variant">Target due date</span>
                  <span className="text-xs font-bold text-error">Oct 24, 2023</span>
                </div>
              </div>
            </SidebarSection>

            <SidebarSection title="Definition of done">
              <div className="space-y-2">
                <div className="flex items-start gap-2 text-xs">
                  <span className="material-symbols-outlined text-sm text-on-surface-variant">check_box_outline_blank</span>
                  <span>Tomcat process reports v10.1.16</span>
                </div>
                <div className="flex items-start gap-2 text-xs">
                  <span className="material-symbols-outlined text-sm text-on-surface-variant">check_box_outline_blank</span>
                  <span>WAF rules updated to block smuggling patterns</span>
                </div>
              </div>
            </SidebarSection>

            <SidebarSection title="References">
              <div className="space-y-2">
                <div className="flex items-center justify-between p-2 bg-white rounded-lg border border-surface-container text-xs">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-sm text-primary">confirmation_number</span>
                    <span className="font-bold">SEC-1428</span>
                  </div>
                  <span className="text-[10px] text-on-surface-variant bg-surface-container px-1.5 py-0.5 rounded">Linked</span>
                </div>
                <div className="flex items-center justify-between p-2 bg-white rounded-lg border border-surface-container text-xs">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-sm text-on-surface-variant">history</span>
                    <span className="font-medium text-on-surface-variant">PLAT-5571</span>
                  </div>
                  <span className="text-[10px] text-on-surface-variant">Similar case</span>
                </div>
              </div>
            </SidebarSection>

            <SidebarSection title="Validation">
              <div className="flex items-center gap-2 text-xs font-bold text-on-surface-variant">
                <div className="w-2 h-2 rounded-full bg-outline-variant" />
                <span>Status: Not started</span>
              </div>
            </SidebarSection>
          </div>
        </aside>
      </div>

      {/* Floating Chat Input */}
      <div className="fixed bottom-8 left-[calc(5rem+2rem)] right-[calc(20rem+2rem)] flex justify-center z-30">
        <div className="w-full max-w-3xl bg-white rounded-2xl shadow-2xl shadow-slate-900/10 border border-slate-200 p-2 flex items-center gap-2">
          <button className="p-2 hover:bg-surface-container rounded-lg transition-colors text-on-surface-variant">
            <span className="material-symbols-outlined">add_circle</span>
          </button>
          <input
            className="flex-1 bg-transparent border-none focus:ring-0 text-sm py-3 px-2"
            placeholder="Type a message or use @ to mention agents..."
            type="text"
          />
          <button className="bg-primary text-white p-2 rounded-xl hover:scale-105 active:scale-95 transition-all shadow-lg shadow-primary/20">
            <span className="material-symbols-outlined">send</span>
          </button>
        </div>
      </div>
    </div>
  )
}

function SidebarSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h4 className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant mb-3">{title}</h4>
      {children}
    </section>
  )
}
