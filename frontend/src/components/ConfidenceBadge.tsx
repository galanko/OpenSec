interface ConfidenceBadgeProps {
  confidence: number | null | undefined
}

type Tier = 'high' | 'medium' | 'low'

const tiers: Record<Tier, { dots: string; label: string; classes: string }> = {
  high: { dots: '\u25CF\u25CF\u25CF\u25CF', label: 'High', classes: 'text-tertiary' },
  medium: { dots: '\u25CF\u25CF\u25CB\u25CB', label: 'Medium', classes: 'text-secondary' },
  low: { dots: '\u25CF\u25CB\u25CB\u25CB', label: 'Low', classes: 'text-error' },
}

function getTier(confidence: number): Tier {
  if (confidence >= 0.7) return 'high'
  if (confidence >= 0.4) return 'medium'
  return 'low'
}

export default function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (confidence == null) return null

  const tier = getTier(confidence)
  const config = tiers[tier]

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${config.classes}`}>
      <span className="tracking-wider" aria-hidden="true">{config.dots}</span>
      <span>{config.label}</span>
    </span>
  )
}
