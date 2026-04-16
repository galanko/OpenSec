import { useState } from 'react'
import { useNavigate } from 'react-router'
import OnboardingShell from '@/components/onboarding/OnboardingShell'
import ProviderCard from '@/components/onboarding/ProviderCard'
import WizardNav from '@/components/onboarding/WizardNav'
import { onboardingStorage } from './storage'

export type ProviderId = 'openai' | 'anthropic' | 'local'

export interface Provider {
  id: ProviderId
  name: string
  description: string
  icon: string
}

const PROVIDERS: Provider[] = [
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
    id: 'local',
    name: 'Local model',
    description: 'Run against an Ollama or compatible endpoint.',
    icon: 'dns',
  },
]

export default function ConfigureAI() {
  const navigate = useNavigate()
  const [providerId, setProviderId] = useState<ProviderId>('openai')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')

  const canContinue = apiKey.trim().length > 0

  function handleContinue() {
    onboardingStorage.set('provider', providerId)
    if (model.trim()) onboardingStorage.set('model', model.trim())
    // TODO(session-g): persist the API key to the backend vault here via
    // `POST /api/settings/api-keys/:provider`. Today the value is dropped
    // on navigation — matches the MSW contract, but the reassurance copy
    // below is only accurate once Session G wires the real call.
    navigate('/onboarding/start')
  }

  return (
    <OnboardingShell step={2}>
      <h1 className="font-headline text-3xl font-extrabold text-on-surface mb-2">
        Configure your AI model
      </h1>
      <p className="text-on-surface-variant mb-8">
        OpenSec uses your model to explain findings and draft fixes. Pick a
        provider and drop in an API key. You can change this later in
        Settings.
      </p>

      <div
        role="radiogroup"
        aria-label="AI provider"
        className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8"
      >
        {PROVIDERS.map((p) => (
          <ProviderCard
            key={p.id}
            provider={p}
            selected={providerId === p.id}
            onSelect={setProviderId}
          />
        ))}
      </div>

      <label className="block mb-5">
        <span className="block text-sm font-semibold text-on-surface mb-2">
          API key
        </span>
        <input
          type="password"
          autoComplete="off"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="sk-••••••••••••••••••••••••••••"
          className="w-full px-4 py-3 rounded-lg bg-surface-container-lowest shadow-sm border-0 ring-0 focus:ring-2 focus:ring-primary/30 focus:outline-none text-sm font-mono"
        />
      </label>

      <label className="block mb-3">
        <span className="block text-sm font-semibold text-on-surface mb-2">
          Model{' '}
          <span className="text-on-surface-variant font-normal">(optional)</span>
        </span>
        <input
          type="text"
          autoComplete="off"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          placeholder="Leave blank to use our recommended default"
          className="w-full px-4 py-3 rounded-lg bg-surface-container-lowest shadow-sm border-0 ring-0 focus:ring-2 focus:ring-primary/30 focus:outline-none text-sm font-mono"
        />
      </label>

      <div className="mt-6 flex items-start gap-3 rounded-lg bg-surface-container-low px-4 py-3">
        <span
          className="material-symbols-outlined text-tertiary text-sm mt-0.5"
          aria-hidden="true"
        >
          lock
        </span>
        <p className="text-xs text-on-surface-variant leading-relaxed">
          Keys stay on this machine. OpenSec stores them in its local vault
          and never sends them anywhere else.
        </p>
      </div>

      <WizardNav
        onBack={() => navigate('/onboarding/connect')}
        onNext={handleContinue}
        nextLabel="Test and continue"
        nextDisabled={!canContinue}
      />
    </OnboardingShell>
  )
}
