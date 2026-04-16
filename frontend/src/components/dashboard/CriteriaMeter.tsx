/**
 * CriteriaMeter — horizontal pill meter (default 5 pills).
 *
 * IMPL-0002 Milestone G3. Fills left-to-right. Reusable across the dashboard
 * wherever we need a compact criteria indicator.
 */

export interface CriteriaMeterProps {
  met: number
  total: number
}

export default function CriteriaMeter({ met, total }: CriteriaMeterProps) {
  const safeTotal = Math.max(0, total)
  const filled = Math.min(safeTotal, Math.max(0, met))

  return (
    <div
      className="flex items-center gap-2"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={safeTotal}
      aria-valuenow={filled}
      aria-label={`${filled} of ${safeTotal} criteria met`}
    >
      {Array.from({ length: safeTotal }).map((_, idx) => {
        const state = idx < filled ? 'met' : 'empty'
        return (
          <span
            key={idx}
            data-testid="criteria-meter-pill"
            data-state={state}
            className={
              state === 'met'
                ? 'h-2 flex-1 rounded-full bg-primary'
                : 'h-2 flex-1 rounded-full bg-surface-container-high'
            }
          />
        )
      })}
    </div>
  )
}
