import { useAgentChips } from '@/api/hooks'

interface ActionChipsProps {
  onAction: (agentType: string) => void
  disabled?: boolean
}

export default function ActionChips({ onAction, disabled }: ActionChipsProps) {
  const { data: chips, isLoading } = useAgentChips()

  if (isLoading || !chips) {
    return (
      <div className="flex gap-2 max-w-3xl">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-9 w-32 rounded-full bg-surface-container-high animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-wrap gap-2 max-w-3xl">
      {chips.map((chip) => (
        <button
          key={chip.agent_type}
          onClick={() => onAction(chip.agent_type)}
          disabled={disabled}
          className="px-4 py-2 rounded-full border border-primary/10 bg-white text-xs font-medium text-primary hover:bg-primary-container/30 shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {chip.label}
        </button>
      ))}
    </div>
  )
}
