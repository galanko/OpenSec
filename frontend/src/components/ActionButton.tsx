interface ActionButtonProps {
  label: string
  icon?: string
  variant?: 'primary' | 'outline'
  onClick: () => void
  disabled?: boolean
}

export default function ActionButton({
  label,
  icon,
  variant = 'primary',
  onClick,
  disabled,
}: ActionButtonProps) {
  const base = 'flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed'

  const variants = {
    primary: 'bg-primary hover:bg-primary-dim text-white shadow-sm hover:shadow-md',
    outline: 'border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container',
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variants[variant]}`}
    >
      {icon && <span className="material-symbols-outlined text-sm">{icon}</span>}
      {label}
    </button>
  )
}
