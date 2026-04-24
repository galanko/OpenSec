const severityConfig: Record<string, { label: string; icon: string; classes: string }> = {
  critical: {
    label: 'Critical',
    icon: 'warning',
    classes: 'text-error bg-error-container/30',
  },
  high: {
    label: 'High',
    icon: 'error',
    classes: 'text-error bg-error-container/20',
  },
  // ADR-0029 / IMPL-0004 T14: medium severity moved from the tertiary
  // (success-green) family to the new warning family so it scans as
  // "attention needed but not blocking" rather than "fine".
  medium: {
    label: 'Medium',
    icon: 'info',
    classes: 'text-on-warning-container bg-warning-container/40',
  },
  low: {
    label: 'Low',
    icon: 'info',
    classes: 'text-on-surface-variant bg-surface-container-high',
  },
}

interface SeverityBadgeProps {
  severity: string | null | undefined
  size?: 'sm' | 'md'
}

export default function SeverityBadge({ severity, size = 'sm' }: SeverityBadgeProps) {
  const key = (severity ?? 'medium').toLowerCase()
  const config = severityConfig[key] ?? severityConfig.medium

  if (size === 'md') {
    return (
      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${config.classes}`}>
        {config.label}
      </span>
    )
  }

  return (
    <span className={`text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${config.classes}`}>
      {config.label}
    </span>
  )
}

export function SeverityIcon({ severity }: { severity: string | null | undefined }) {
  const key = (severity ?? 'medium').toLowerCase()
  const config = severityConfig[key] ?? severityConfig.medium

  const iconClasses: Record<string, string> = {
    critical: 'bg-error-container/20 text-error',
    high: 'bg-error-container/15 text-error',
    medium: 'bg-warning-container/40 text-on-warning-container',
    low: 'bg-surface-container-high text-on-surface-variant',
  }

  return (
    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${iconClasses[key] ?? iconClasses.medium}`}>
      <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>
        {config.icon}
      </span>
    </div>
  )
}
