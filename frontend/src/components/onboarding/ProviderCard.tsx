import { cn } from '@/lib/utils'

export interface ProviderCardData<Id extends string = string> {
  id: Id
  name: string
  description: string
  icon: string
}

export interface ProviderCardProps<Id extends string = string> {
  provider: ProviderCardData<Id>
  selected: boolean
  onSelect: (id: Id) => void
}

/**
 * Selectable provider tile in the ConfigureAI grid (UX frame 1.4).
 * Active state uses `ring-2 ring-primary`; inactive uses a tonal
 * background. No `1px solid` borders.
 */
export default function ProviderCard<Id extends string = string>({
  provider,
  selected,
  onSelect,
}: ProviderCardProps<Id>) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      onClick={() => onSelect(provider.id)}
      className={cn(
        'flex flex-col items-start gap-2 rounded-lg bg-surface-container-lowest shadow-sm px-4 py-4 text-left transition-all',
        'hover:shadow-md active:scale-[0.99]',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
        selected && 'ring-2 ring-primary',
      )}
    >
      <span
        className="material-symbols-outlined text-primary"
        aria-hidden="true"
      >
        {provider.icon}
      </span>
      <span className="font-headline text-sm font-bold text-on-surface">
        {provider.name}
      </span>
      <span className="text-xs text-on-surface-variant leading-relaxed">
        {provider.description}
      </span>
    </button>
  )
}
