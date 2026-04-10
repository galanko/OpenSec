import ActionButton from '@/components/ActionButton'

interface EmptyStateProps {
  icon: string
  title: string
  subtitle: string
  action?: {
    label: string
    icon?: string
    variant?: 'primary' | 'outline' | 'secondary'
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
            className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold transition-all active:scale-95 bg-primary hover:bg-primary-dim text-white shadow-sm hover:shadow-md"
          >
            {action.icon && <span className="material-symbols-outlined text-sm">{action.icon}</span>}
            {action.label}
          </a>
        ) : (
          <ActionButton
            label={action.label}
            icon={action.icon}
            variant={action.variant ?? 'primary'}
            onClick={action.onClick ?? (() => {})}
          />
        )
      )}
      {footer && (
        <p className="text-xs text-on-surface-variant mt-4">{footer}</p>
      )}
    </div>
  )
}
