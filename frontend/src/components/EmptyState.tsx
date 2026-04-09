interface EmptyStateProps {
  icon: string
  title: string
  subtitle: string
  action?: {
    label: string
    href?: string
    onClick?: () => void
  }
  footer?: string
}

export default function EmptyState({ icon, title, subtitle, action, footer }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <div className="w-16 h-16 rounded-full bg-surface-container-low flex items-center justify-center mb-6">
        <span className="material-symbols-outlined text-3xl text-on-surface-variant">
          {icon}
        </span>
      </div>
      <h2 className="text-xl font-bold text-on-surface mb-2">{title}</h2>
      <p className="text-on-surface-variant text-sm text-center max-w-md mb-8">
        {subtitle}
      </p>
      {action && (
        action.href ? (
          <a
            href={action.href}
            className="bg-primary hover:bg-primary-dim text-white px-6 py-2.5 rounded-lg font-semibold text-sm transition-all shadow-lg shadow-primary/20 active:scale-95"
          >
            {action.label}
          </a>
        ) : (
          <button
            onClick={action.onClick}
            className="bg-primary hover:bg-primary-dim text-white px-6 py-2.5 rounded-lg font-semibold text-sm transition-all shadow-lg shadow-primary/20 active:scale-95"
          >
            {action.label}
          </button>
        )
      )}
      {footer && (
        <p className="text-xs text-on-surface-variant mt-4">{footer}</p>
      )}
    </div>
  )
}
