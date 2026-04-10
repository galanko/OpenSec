import { useAgentChips } from '@/api/hooks'

type ChipState = 'default' | 'suggested' | 'running' | 'completed' | 'disabled'

interface ActionChipsProps {
  onAction: (agentType: string) => void
  disabled?: boolean
  suggestedAgentType?: string | null
  runningAgentType?: string | null
  completedAgentTypes?: string[]
}

const chipStyles: Record<ChipState, string> = {
  default:
    'border-primary/10 bg-white text-primary hover:bg-primary-container/30',
  suggested:
    'border-primary/20 bg-primary-container/30 text-primary ring-2 ring-primary/20 animate-[pulse_3s_ease-in-out_infinite]',
  running:
    'border-primary/10 bg-white text-primary/70 cursor-wait',
  completed:
    'border-tertiary/10 bg-tertiary-container/30 text-tertiary',
  disabled:
    'border-primary/10 bg-white text-primary opacity-50 cursor-not-allowed',
}

function getChipState(
  agentType: string,
  props: Pick<ActionChipsProps, 'disabled' | 'suggestedAgentType' | 'runningAgentType' | 'completedAgentTypes'>,
): ChipState {
  if (props.runningAgentType === agentType) return 'running'
  if (props.completedAgentTypes?.includes(agentType)) return 'completed'
  if (props.disabled) return 'disabled'
  if (props.suggestedAgentType === agentType) return 'suggested'
  return 'default'
}

export default function ActionChips({
  onAction,
  disabled,
  suggestedAgentType,
  runningAgentType,
  completedAgentTypes,
}: ActionChipsProps) {
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
      {chips.map((chip) => {
        const state = getChipState(chip.agent_type, {
          disabled,
          suggestedAgentType,
          runningAgentType,
          completedAgentTypes,
        })
        const isClickable = state !== 'disabled' && state !== 'running'

        return (
          <button
            key={chip.agent_type}
            onClick={() => isClickable && onAction(chip.agent_type)}
            disabled={!isClickable}
            className={`px-4 py-2 rounded-full border text-xs font-medium shadow-sm transition-all flex items-center gap-1.5 ${chipStyles[state]}`}
          >
            {state === 'running' && (
              <span className="material-symbols-outlined text-sm animate-spin">progress_activity</span>
            )}
            {state === 'completed' && (
              <span className="material-symbols-outlined text-sm">check</span>
            )}
            {chip.label}
          </button>
        )
      })}
    </div>
  )
}
