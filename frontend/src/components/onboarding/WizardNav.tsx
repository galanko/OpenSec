export interface WizardNavProps {
  onBack: () => void
  onNext: () => void
  nextLabel: string
  nextIcon?: string
  nextDisabled?: boolean
  /** Hide the Back link when the wizard is on its first real step. */
  hideBack?: boolean
  /** Override the form-submit behavior; defaults to `button`. */
  nextType?: 'button' | 'submit'
}

/**
 * Shared Back/Next footer for every onboarding page (frames 1.1–1.5).
 * Keeps the button styling in one place so design tweaks land once.
 */
export default function WizardNav({
  onBack,
  onNext,
  nextLabel,
  nextIcon = 'arrow_forward',
  nextDisabled,
  hideBack,
  nextType = 'button',
}: WizardNavProps) {
  return (
    <div className="mt-10 flex items-center justify-between">
      {hideBack ? (
        <span />
      ) : (
        <button
          type="button"
          onClick={onBack}
          className="text-sm font-semibold text-on-surface-variant hover:text-on-surface px-2 py-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
        >
          ← Back
        </button>
      )}
      <button
        type={nextType}
        disabled={nextDisabled}
        onClick={nextType === 'button' ? onNext : undefined}
        className="px-5 py-2.5 rounded-lg bg-primary text-white font-bold text-sm hover:bg-primary-dim transition-colors active:scale-95 shadow-sm flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
      >
        {nextLabel}
        {nextIcon && (
          <span className="material-symbols-outlined text-sm" aria-hidden="true">
            {nextIcon}
          </span>
        )}
      </button>
    </div>
  )
}
