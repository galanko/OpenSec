import { useMemo, useState } from 'react'
import { useProviders } from '@/api/hooks'

export interface ModelPickerDialogProps {
  open: boolean
  onClose: () => void
  onSelect: (provider: string, model: string) => void
}

/**
 * Searchable "any model" picker for the onboarding wizard's `Other` provider
 * path. Matches the affordance on the settings page without rewiring that
 * component's API-key management — this one is read-only over the provider
 * catalog.
 */
export default function ModelPickerDialog({
  open,
  onClose,
  onSelect,
}: ModelPickerDialogProps) {
  const { data: providers, isLoading } = useProviders()
  const [query, setQuery] = useState('')

  const results = useMemo(() => {
    if (!providers) return []
    const q = query.trim().toLowerCase()
    return providers
      .map((p) => {
        const entries = Object.entries(p.models)
        const matches = q
          ? entries.filter(
              ([modelId, m]) =>
                p.id.toLowerCase().includes(q) ||
                p.name.toLowerCase().includes(q) ||
                modelId.toLowerCase().includes(q) ||
                m.name?.toLowerCase().includes(q),
            )
          : entries
        return { provider: p, matches }
      })
      .filter((r) => r.matches.length > 0)
  }, [providers, query])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-scrim/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Pick any model"
    >
      <div className="w-full max-w-lg rounded-2xl bg-surface shadow-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-headline text-xl font-extrabold text-on-surface">
            Pick any model
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-on-surface-variant hover:text-on-surface px-2 py-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
            aria-label="Close"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="relative mb-4">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant/60 text-lg">
            search
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            placeholder="Search providers or models"
            className="w-full bg-surface-container-low rounded-lg pl-10 pr-4 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>

        <div className="max-h-80 overflow-y-auto pr-1 space-y-3">
          {isLoading && (
            <p className="text-sm text-on-surface-variant">Loading catalog…</p>
          )}
          {!isLoading && results.length === 0 && (
            <p className="text-sm text-on-surface-variant">
              No providers or models match "{query}".
            </p>
          )}
          {results.map(({ provider, matches }) => (
            <div
              key={provider.id}
              className="bg-surface-container-low rounded-lg p-3"
            >
              <p className="text-xs font-semibold uppercase tracking-wider text-on-surface-variant mb-2">
                {provider.name}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {matches.map(([modelId, model]) => (
                  <button
                    key={modelId}
                    type="button"
                    onClick={() => onSelect(provider.id, modelId)}
                    className="px-3 py-1.5 rounded-md text-xs font-mono bg-surface-container-lowest text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
                  >
                    {model.name || modelId}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
