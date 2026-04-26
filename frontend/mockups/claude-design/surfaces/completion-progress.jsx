// Surface 5 — Completion progress (10 criteria) — focused/standalone view

const CRITERIA = [
  { label: 'SECURITY.md present', met: true },
  { label: 'Dependabot configured', met: true },
  { label: 'No critical vulns', met: true },
  { label: 'No high vulns', met: false },
  { label: 'Branch protection enabled', met: true },
  { label: 'No committed secrets', met: true },
  { label: 'CI actions pinned to SHA', met: false },
  { label: 'No stale collaborators', met: true },
  { label: 'Code owners file exists', met: false },
  { label: 'Secret scanning enabled', met: true },
];

function CompletionProgressPage() {
  const met = CRITERIA.filter(c => c.met).length;
  const pct = (met / CRITERIA.length) * 100;
  return (
    <div className="bg-surface flex flex-col items-center justify-center px-8 py-10" style={{minHeight: 700}}>
      <div className="w-full max-w-2xl rounded-3xl bg-surface-container-lowest p-8">
        <header className="flex items-baseline justify-between mb-6">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-primary">Completion progress</p>
            <h2 className="mt-1.5 font-headline text-[24px] font-extrabold text-on-surface tracking-tight">{met} of {CRITERIA.length} criteria met</h2>
          </div>
          <span className="font-headline text-[32px] font-extrabold text-primary tabular-nums leading-none">{Math.round(pct)}%</span>
        </header>

        {/* Progress bar with 10 ticks */}
        <div className="relative h-3 mb-1">
          <div className="absolute inset-0 rounded-full bg-surface-container-high overflow-hidden">
            <div className="h-full rounded-full bg-primary transition-all" style={{width: pct + '%'}} />
          </div>
          {/* Ticks */}
          <div className="absolute inset-0 flex justify-between items-center px-[1.5px]">
            {Array.from({length: 11}).map((_, i) => (
              <span key={i} className="w-[1.5px] h-3 bg-surface-container-lowest/70" />
            ))}
          </div>
        </div>
        <div className="flex justify-between text-[10px] font-medium text-on-surface-variant tabular-nums mt-1.5 mb-7">
          {Array.from({length: 11}).map((_, i) => <span key={i}>{i}</span>)}
        </div>

        {/* Criteria list — 2-column desktop */}
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {CRITERIA.map((c, i) => (
            <li key={i} className={cx(
              'flex items-center gap-2.5 rounded-full px-3 py-2',
              c.met ? 'bg-tertiary-container/45' : 'bg-surface-container-high'
            )}>
              <span className={cx(
                'material-symbols-outlined flex-shrink-0',
                c.met ? 'msym-filled text-tertiary' : 'text-on-surface-variant/70'
              )} style={{fontSize: 16}} aria-hidden>
                {c.met ? 'check_circle' : 'radio_button_unchecked'}
              </span>
              <span className={cx(
                'text-[13px]',
                c.met ? 'font-medium text-on-tertiary-container' : 'text-on-surface-variant'
              )}>
                {c.label}
              </span>
            </li>
          ))}
        </ul>

        <p className="mt-5 text-[13px] text-on-surface-variant text-center">
          Reach <span className="font-semibold text-on-surface">10 of 10</span> to unlock Grade A and the shareable summary.
        </p>
      </div>
    </div>
  );
}

Object.assign(window, { CompletionProgressPage });
