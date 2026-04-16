import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router'
import OnboardingShell from '@/components/onboarding/OnboardingShell'
import ProviderCard from '@/components/onboarding/ProviderCard'
import WizardNav from '@/components/onboarding/WizardNav'
import InlineErrorCallout from '@/components/onboarding/InlineErrorCallout'
import ModelPickerDialog from '@/components/onboarding/ModelPickerDialog'
import { useProviders, useUpdateModel } from '@/api/hooks'
import { onboardingStorage } from './storage'

/**
 * The short list the wizard surfaces as cards. ``google`` is OpenCode's
 * provider id for Gemini — the user-facing label stays "Gemini". ``other``
 * is a meta-choice that opens the full searchable catalog.
 */
type ProviderChoice = 'openai' | 'anthropic' | 'google' | 'other'

const CARDS: {
  id: ProviderChoice
  name: string
  description: string
  icon: string
}[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    description: 'GPT-4 class models. Good default for most maintainers.',
    icon: 'auto_awesome',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    description: 'Claude models. Excellent at careful reasoning.',
    icon: 'psychology',
  },
  {
    id: 'google',
    name: 'Gemini',
    description: "Google's multimodal models with large context windows.",
    icon: 'hub',
  },
  {
    id: 'other',
    name: 'Other',
    description: 'Pick any model from the full catalog.',
    icon: 'more_horiz',
  },
]

interface Selection {
  provider: string
  model: string
}

export default function ConfigureAI() {
  const navigate = useNavigate()
  const { data: providers } = useProviders()
  const updateModel = useUpdateModel()

  const [providerId, setProviderId] = useState<ProviderChoice>('openai')
  const [selection, setSelection] = useState<Selection | null>(null)
  const [otherOpen, setOtherOpen] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // Models available for the short-list providers. "Other" always opens the
  // picker — we never need a local model list for it.
  const modelsForProvider = useMemo(() => {
    if (!providers || providerId === 'other') return []
    const p = providers.find((x) => x.id === providerId)
    if (!p) return []
    return Object.entries(p.models).map(([id, m]) => ({
      id,
      name: m.name || id,
    }))
  }, [providers, providerId])

  function handleCardSelect(id: ProviderChoice) {
    setProviderId(id)
    setSelection(null)
    if (id === 'other') setOtherOpen(true)
  }

  function handleOtherPick(provider: string, model: string) {
    setSelection({ provider, model })
    setProviderId('other')
    setOtherOpen(false)
  }

  function handleContinue() {
    if (!selection) return
    setErrorMsg(null)
    const fullId = `${selection.provider}/${selection.model}`
    updateModel.mutate(fullId, {
      onSuccess: () => {
        onboardingStorage.set('provider', selection.provider)
        onboardingStorage.set('model', selection.model)
        navigate('/onboarding/start')
      },
      onError: (err) => {
        setErrorMsg(
          err instanceof Error ? err.message : 'Could not save model choice',
        )
      },
    })
  }

  const canContinue = !!selection && !updateModel.isPending

  return (
    <OnboardingShell step={2}>
      <h1 className="font-headline text-3xl font-extrabold text-on-surface mb-2">
        Configure your AI model
      </h1>
      <p className="text-on-surface-variant mb-8">
        OpenSec uses your model to explain findings and draft fixes. Pick a
        provider, then pick a model. You can change this later in Settings.
      </p>

      <div
        role="radiogroup"
        aria-label="AI provider"
        className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8"
      >
        {CARDS.map((p) => (
          <ProviderCard
            key={p.id}
            provider={p}
            selected={providerId === p.id}
            onSelect={handleCardSelect}
          />
        ))}
      </div>

      {providerId !== 'other' && (
        <label className="block mb-5">
          <span className="block text-sm font-semibold text-on-surface mb-2">
            Model <span className="text-error">*</span>
          </span>
          <select
            value={selection?.provider === providerId ? selection.model : ''}
            onChange={(e) => {
              const modelId = e.target.value
              if (!modelId) {
                setSelection(null)
              } else {
                setSelection({ provider: providerId, model: modelId })
              }
            }}
            className="w-full px-4 py-3 rounded-lg bg-surface-container-lowest shadow-sm border-0 ring-0 focus:ring-2 focus:ring-primary/30 focus:outline-none text-sm"
          >
            <option value="">
              {modelsForProvider.length
                ? 'Pick a model…'
                : 'Loading model catalog…'}
            </option>
            {modelsForProvider.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {providerId === 'other' && (
        <div className="mb-5 rounded-lg bg-surface-container-lowest shadow-sm px-4 py-3 flex items-center gap-3">
          <span className="material-symbols-outlined text-on-surface-variant">
            more_horiz
          </span>
          <div className="flex-1 text-sm">
            {selection ? (
              <>
                <span className="text-on-surface-variant">Selected:</span>{' '}
                <span className="font-mono font-semibold text-on-surface">
                  {selection.provider}/{selection.model}
                </span>
              </>
            ) : (
              <span className="text-on-surface-variant">
                No model picked yet — open the catalog to choose one.
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => setOtherOpen(true)}
            className="text-xs font-semibold text-primary hover:underline px-2 py-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          >
            {selection ? 'Change' : 'Open catalog'}
          </button>
        </div>
      )}

      {errorMsg && (
        <InlineErrorCallout
          title="Could not save the model choice"
          body={<>{errorMsg}</>}
        />
      )}

      <div className="mt-6 flex items-start gap-3 rounded-lg bg-surface-container-low px-4 py-3">
        <span
          className="material-symbols-outlined text-tertiary text-sm mt-0.5"
          aria-hidden="true"
        >
          info
        </span>
        <p className="text-xs text-on-surface-variant leading-relaxed">
          Your selection becomes the default model OpenSec uses for every
          explanation and draft fix. Set API keys per-provider in Settings.
        </p>
      </div>

      <WizardNav
        onBack={() => navigate('/onboarding/connect')}
        onNext={handleContinue}
        nextLabel={updateModel.isPending ? 'Saving…' : 'Continue'}
        nextDisabled={!canContinue}
      />

      <ModelPickerDialog
        open={otherOpen}
        onClose={() => setOtherOpen(false)}
        onSelect={handleOtherPick}
      />
    </OnboardingShell>
  )
}
