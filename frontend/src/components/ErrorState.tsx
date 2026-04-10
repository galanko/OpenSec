interface ErrorStateProps {
  title: string
  subtitle?: string
  onRetry?: () => void
  retryLabel?: string
}

export default function ErrorState({ title, subtitle, onRetry, retryLabel = 'Try again' }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <div className="w-16 h-16 rounded-full bg-error-container/20 flex items-center justify-center mb-6">
        <span className="material-symbols-outlined text-3xl text-error">
          error_outline
        </span>
      </div>
      <h2 className="text-xl font-bold text-on-surface mb-2">{title}</h2>
      {subtitle && (
        <p className="text-on-surface-variant text-sm text-center max-w-md mb-8">
          {subtitle}
        </p>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-primary text-sm font-semibold px-6 py-2.5 rounded-lg border border-outline-variant/30 hover:bg-primary-container/20 transition-all active:scale-95"
        >
          {retryLabel}
        </button>
      )}
    </div>
  )
}
