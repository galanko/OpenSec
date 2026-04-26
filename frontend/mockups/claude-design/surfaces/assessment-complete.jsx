// Surface 3 — Assessment-complete summary interstitial (2 variations)

// ─── Variation A — three side-by-side cards (matches brief) ───
function AssessmentCompletePageA() {
  return (
    <div className="bg-surface flex" style={{minHeight: 880}}>
      <SideNav active="dashboard" />
      <main className="flex-1 px-8 py-10 flex flex-col items-center">
        <div className="w-full max-w-3xl">
          {/* Hero */}
          <div className="flex flex-col items-center text-center gap-4 mb-8">
            <div className="grid h-16 w-16 place-items-center rounded-full bg-tertiary-container/60">
              <span className="material-symbols-outlined msym-filled text-tertiary" style={{fontSize: 30}} aria-hidden>check</span>
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-tertiary">Assessment complete</p>
              <h1 className="mt-1.5 font-headline text-[36px] font-extrabold text-on-surface tracking-tight leading-tight">Here's what we found.</h1>
              <p className="mt-2 text-[15px] text-on-surface-variant max-w-md mx-auto">
                We scanned 312 dependencies and ran 15 posture checks. Take a look before heading to your report card.
              </p>
            </div>
            <div className="mt-2">
              <ToolPillBar tools={[
                { label: 'Trivy 0.52', icon: 'bug_report', state: 'done' },
                { label: 'Semgrep 1.70', icon: 'code', state: 'done' },
                { label: '15 posture checks', icon: 'rule', state: 'done' },
              ]} />
            </div>
          </div>

          {/* Three cards */}
          <div className="grid grid-cols-3 gap-3 mb-7">
            <div className="rounded-3xl bg-surface-container-lowest p-5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">Vulnerabilities</p>
              <p className="font-headline text-[36px] font-extrabold text-on-surface mt-1 leading-none tabular-nums">10</p>
              <p className="text-[11px] text-on-surface-variant mt-1">findings total</p>
              <div className="mt-4 flex flex-wrap gap-1.5">
                <SeverityChip kind="high" count={2} />
                <SeverityChip kind="medium" count={5} />
                <SeverityChip kind="low" count={3} />
              </div>
              <p className="mt-3 text-[10px] text-on-surface-variant">Trivy · Semgrep</p>
            </div>

            <div className="rounded-3xl bg-surface-container-lowest p-5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">Posture</p>
              <p className="font-headline text-[36px] font-extrabold text-on-surface mt-1 leading-none tabular-nums">12<span className="text-on-surface-variant text-2xl">/15</span></p>
              <p className="text-[11px] text-on-surface-variant mt-1">checks pass</p>
              <ul className="mt-4 space-y-1 text-[11px] text-on-surface-variant">
                <li>· CI supply chain</li>
                <li>· Collaborator hygiene</li>
                <li>· Code integrity</li>
                <li>· Repo configuration</li>
              </ul>
            </div>

            <div className="rounded-3xl bg-primary-container/40 p-5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-on-primary-container">Quick wins</p>
              <p className="font-headline text-[36px] font-extrabold text-on-primary-container mt-1 leading-none tabular-nums">3</p>
              <p className="text-[11px] text-on-primary-container/80 mt-1">we can fix automatically</p>
              <ul className="mt-4 space-y-1 text-[11px] text-on-primary-container">
                <li>· Pin actions to SHA</li>
                <li>· Generate code owners</li>
                <li>· Configure Dependabot</li>
              </ul>
            </div>
          </div>

          {/* Grade preview */}
          <div className="rounded-3xl bg-surface-container-low p-6 flex items-center gap-5 mb-6">
            <GradeRing grade="B" percent={80} size={72} sub="8/10" />
            <div className="flex-1">
              <p className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">Your grade</p>
              <p className="font-headline text-[22px] font-extrabold text-on-surface mt-0.5 leading-tight">8 of 10 criteria met — Grade B</p>
              <p className="text-sm text-on-surface-variant mt-1">Two criteria away from A. Both fixable with one click.</p>
            </div>
          </div>

          {/* CTA */}
          <div className="flex justify-center">
            <button className="inline-flex items-center gap-2 rounded-full bg-primary text-on-primary px-6 py-3 text-sm font-bold shadow-md hover:bg-primary-dim active:scale-[0.97] transition-all">
              View your report card
              <span className="material-symbols-outlined" style={{fontSize: 18}} aria-hidden>arrow_forward</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

// ─── Variation B — editorial vertical with the grade as the hero ───
function AssessmentCompletePageB() {
  return (
    <div className="bg-surface flex" style={{minHeight: 880}}>
      <SideNav active="dashboard" />
      <main className="flex-1 px-8 py-12 flex flex-col items-center">
        <div className="w-full max-w-2xl">
          {/* Eyebrow + huge type lockup */}
          <div className="flex flex-col items-center text-center mb-10">
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-tertiary">Assessment complete</p>
            <div className="my-6 flex items-center justify-center gap-6">
              <GradeRing grade="B" percent={80} size={140} sub="8 of 10" />
              <div className="text-left">
                <p className="font-headline text-[64px] font-extrabold text-on-surface leading-none tracking-tight">Grade B.</p>
                <p className="font-headline text-[20px] font-bold text-on-surface-variant mt-2 leading-snug">Two checks from an A.</p>
              </div>
            </div>
            <p className="text-[15px] text-on-surface-variant max-w-md leading-relaxed">
              We scanned 312 dependencies and ran 15 posture checks. Three are quick wins our agents can resolve with one click.
            </p>
          </div>

          {/* Inline summary strip */}
          <div className="rounded-3xl bg-surface-container-lowest p-6 mb-5">
            <div className="grid grid-cols-3 divide-x divide-surface-container-high">
              <div className="px-4 first:pl-0">
                <p className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">Findings</p>
                <p className="font-headline text-[28px] font-extrabold text-on-surface mt-1 leading-none tabular-nums">10</p>
                <p className="text-[11px] text-on-surface-variant mt-0.5">2 high · 5 med · 3 low</p>
              </div>
              <div className="px-4">
                <p className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">Posture</p>
                <p className="font-headline text-[28px] font-extrabold text-on-surface mt-1 leading-none tabular-nums">12<span className="text-base text-on-surface-variant">/15</span></p>
                <p className="text-[11px] text-on-surface-variant mt-0.5">across 4 categories</p>
              </div>
              <div className="px-4">
                <p className="text-[11px] font-bold uppercase tracking-wider text-on-primary-container">Quick wins</p>
                <p className="font-headline text-[28px] font-extrabold text-primary mt-1 leading-none tabular-nums">3</p>
                <p className="text-[11px] text-on-surface-variant mt-0.5">one-click fixes</p>
              </div>
            </div>
          </div>

          {/* Tool credit */}
          <div className="flex items-center justify-center gap-3 mb-8">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">Scanned by</span>
            <ToolPillBar size="sm" tools={[
              { label: 'Trivy 0.52', icon: 'bug_report', state: 'done' },
              { label: 'Semgrep 1.70', icon: 'code', state: 'done' },
              { label: '15 posture checks', icon: 'rule', state: 'done' },
            ]} />
          </div>

          <div className="flex justify-center">
            <button className="inline-flex items-center gap-2 rounded-full bg-primary text-on-primary px-7 py-3.5 text-sm font-bold shadow-md hover:bg-primary-dim active:scale-[0.97] transition-all">
              View your report card
              <span className="material-symbols-outlined" style={{fontSize: 18}} aria-hidden>arrow_forward</span>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

Object.assign(window, { AssessmentCompletePageA, AssessmentCompletePageB });
