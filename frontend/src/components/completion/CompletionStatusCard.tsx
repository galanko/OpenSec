/**
 * CompletionStatusCard — the persistent dashboard affordance.
 *
 * Dumb display: the frozen Session 0 contract (`completionId`, `completedAt`,
 * `onReopenSummary?`) deliberately excludes grade/criteria/re-assess props —
 * Session E's DashboardPage wraps this card and owns the richer chrome. The
 * card's job is just to show that security is held, and let the user re-open
 * the shareable summary by tapping the shield.
 *
 * The shield is a real `<button type="button">` with `aria-label="Re-open
 * shareable summary card"`. `hover:scale-105` is kept under reduced-motion
 * but its transition duration is zeroed by the global CSS rule, so the scale
 * snaps instead of animating — WCAG 2.3.3 compliant without removing the
 * affordance entirely.
 */
import ShieldSVG from './ShieldSVG'

export interface CompletionStatusCardProps {
  completionId: string | null
  completedAt: string | null
  onReopenSummary?: () => void
}

function formatDate(isoLike: string | null): string {
  if (!isoLike) return ''
  // Take just the yyyy-mm-dd prefix if this looks like an ISO timestamp.
  return isoLike.slice(0, 10)
}

export default function CompletionStatusCard({
  completionId,
  completedAt,
  onReopenSummary,
}: CompletionStatusCardProps) {
  const dateLabel = formatDate(completedAt)

  return (
    <aside
      data-testid="CompletionStatusCard"
      data-completion-id={completionId ?? ''}
      className="w-full md:w-72 bg-surface-container-lowest rounded-2xl shadow-sm p-6 text-center"
    >
      <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-tertiary">
        Security complete
      </span>

      <button
        type="button"
        aria-label="Re-open shareable summary card"
        onClick={() => onReopenSummary?.()}
        className="group mt-4 mx-auto block p-2 rounded-full transition-transform hover:scale-105 focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-container-lowest motion-safe-scale"
      >
        <ShieldSVG
          completedDate={dateLabel}
          width={80}
          height={96}
          ariaHidden
        />
        <span
          aria-hidden="true"
          className="mt-2 block text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity"
        >
          Tap for summary
        </span>
      </button>

      {dateLabel && (
        <p className="text-xs text-on-surface-variant font-medium mt-4">
          Completed on {dateLabel}
        </p>
      )}
    </aside>
  )
}
