// Surface 4 — Onboarding step 3

function OnboardingStep3Page() {
  return (
    <div className="bg-surface min-h-full flex items-center justify-center px-8 py-12" style={{minHeight: 880}}>
      <div className="w-full max-w-2xl">
        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-9">
          {[
            { n: 1, label: 'Connect repo', done: true },
            { n: 2, label: 'Configure AI', done: true },
            { n: 3, label: 'Start assessment', active: true },
          ].map((s, i) => (
            <React.Fragment key={s.n}>
              {i > 0 && <div className={cx('h-px w-8', s.done || s.active ? 'bg-primary' : 'bg-surface-container-high')} />}
              <div className="flex items-center gap-2">
                <div className={cx(
                  'w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold',
                  s.active ? 'bg-primary text-on-primary' : s.done ? 'bg-primary-container text-on-primary-container' : 'bg-surface-container-high text-on-surface-variant'
                )}>
                  {s.done ? <span className="material-symbols-outlined" style={{fontSize: 14}} aria-hidden>check</span> : s.n}
                </div>
                <span className={cx('text-xs font-semibold', s.active ? 'text-primary' : 'text-on-surface-variant')}>{s.label}</span>
              </div>
            </React.Fragment>
          ))}
        </div>

        {/* Card */}
        <div className="rounded-3xl bg-surface-container-lowest p-9">
          <p className="text-[11px] font-bold uppercase tracking-wider text-primary">Step 3 of 3</p>
          <h1 className="mt-1.5 font-headline text-[32px] font-extrabold text-on-surface tracking-tight leading-tight">Start security assessment</h1>
          <p className="mt-3 text-[15px] text-on-surface-variant leading-relaxed">
            We'll scan your repository using industry-standard security tools and run 15 posture checks on your repo's security configuration. This usually takes 2–5 minutes.
          </p>

          {/* Powered-by row */}
          <div className="mt-6 flex items-center gap-3 flex-wrap py-4 px-4 rounded-2xl bg-surface-container-low">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-on-surface-variant">Powered by</span>
            <ToolPillBar size="sm" tools={[
              { label: 'Trivy 0.52', icon: 'bug_report', state: 'pending' },
              { label: 'Semgrep 1.70', icon: 'code', state: 'pending' },
              { label: '15 posture checks', icon: 'rule', state: 'pending' },
            ]} />
          </div>

          {/* Step previews */}
          <ol className="mt-7 space-y-3">
            {[
              { n: 1, title: 'Detect your project type', body: 'We scan for lockfiles, config files, and language markers to pick the right tools automatically.', time: '~10 s' },
              { n: 2, title: 'Scan with Trivy', body: 'Industry-standard vulnerability scanner. Checks dependencies, secrets, and misconfigurations across all ecosystems.', time: '~60 s' },
              { n: 3, title: 'Check repo posture', body: '15 security checks covering CI supply chain, collaborator hygiene, and code integrity.', time: '~30 s' },
              { n: 4, title: 'Write plain-language descriptions', body: 'Our AI translates scan results into clear, actionable summaries.', time: '~60 s' },
            ].map(s => (
              <li key={s.n} className="flex gap-4 rounded-2xl bg-surface-container-low p-4">
                <div className="w-7 h-7 rounded-full bg-surface-container-lowest flex items-center justify-center flex-shrink-0">
                  <span className="font-headline text-xs font-bold text-on-surface-variant tabular-nums">{s.n}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="text-sm font-semibold text-on-surface">{s.title}</p>
                    <span className="text-[11px] font-medium text-on-surface-variant tabular-nums">{s.time}</span>
                  </div>
                  <p className="mt-1 text-[13px] text-on-surface-variant leading-relaxed">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>

          {/* CTA */}
          <div className="mt-7 flex items-center justify-between gap-3">
            <a href="#" className="text-sm font-semibold text-on-surface-variant hover:text-on-surface">← Back</a>
            <button className="inline-flex items-center gap-2 rounded-full bg-primary text-on-primary px-6 py-3 text-sm font-bold shadow-md hover:bg-primary-dim active:scale-[0.97] transition-all">
              Start assessment
              <span className="material-symbols-outlined" style={{fontSize: 18}} aria-hidden>play_arrow</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { OnboardingStep3Page });
