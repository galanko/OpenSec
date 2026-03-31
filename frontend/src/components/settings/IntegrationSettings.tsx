import { useState } from 'react'
import {
  useIntegrations,
  useCreateIntegration,
  useDeleteIntegration,
  useRegistry,
  useCredentials,
  useStoreCredential,
  useTestIntegration,
} from '@/api/hooks'
import type { RegistryEntry, CredentialField, IntegrationConfigItem } from '@/api/client'

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  if (status === 'available') {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
        Available
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-on-surface-variant bg-surface-container-low px-2 py-0.5 rounded-full">
      Coming soon
    </span>
  )
}

// ---------------------------------------------------------------------------
// Credential form (dynamic from credentials_schema)
// ---------------------------------------------------------------------------

function CredentialForm({
  entry,
  integrationId,
  onDone,
}: {
  entry: RegistryEntry
  integrationId: string
  onDone: () => void
}) {
  const storeCredential = useStoreCredential()
  const testIntegration = useTestIntegration()
  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleSaveAndTest = async () => {
    setSaving(true)
    setTestResult(null)
    try {
      // Store each credential
      for (const field of entry.credentials_schema) {
        const val = values[field.key_name]
        if (val && val.trim()) {
          await storeCredential.mutateAsync({
            integrationId,
            keyName: field.key_name,
            value: val.trim(),
          })
        }
      }
      // Test connection
      const result = await testIntegration.mutateAsync(integrationId)
      setTestResult(result)
    } catch (err) {
      setTestResult({ success: false, message: String(err) })
    } finally {
      setSaving(false)
    }
  }

  const allRequiredFilled = entry.credentials_schema
    .filter((f) => f.required)
    .every((f) => values[f.key_name]?.trim())

  return (
    <div className="space-y-4">
      {entry.credentials_schema.map((field: CredentialField) => (
        <div key={field.key_name}>
          <label className="text-xs font-semibold text-on-surface-variant block mb-1">
            {field.label}
            {field.required && <span className="text-error ml-0.5">*</span>}
          </label>
          <input
            type={field.type === 'password' ? 'password' : 'text'}
            value={values[field.key_name] || ''}
            onChange={(e) => setValues({ ...values, [field.key_name]: e.target.value })}
            placeholder={field.placeholder || ''}
            className="w-full bg-surface-container-lowest rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20"
          />
          {field.help_text && (
            <p className="text-xs text-on-surface-variant mt-1">{field.help_text}</p>
          )}
        </div>
      ))}

      {testResult && (
        <div
          className={`rounded-lg px-4 py-3 text-sm ${
            testResult.success
              ? 'bg-green-50 text-green-800'
              : 'bg-red-50 text-red-800'
          }`}
        >
          <span className="material-symbols-outlined text-base align-text-bottom mr-1">
            {testResult.success ? 'check_circle' : 'error'}
          </span>
          {testResult.message}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleSaveAndTest}
          disabled={!allRequiredFilled || saving}
          className="px-4 py-2 bg-primary text-on-primary rounded-md text-sm font-semibold disabled:opacity-40 transition-colors hover:bg-primary/90"
        >
          {saving ? 'Saving...' : 'Save & test'}
        </button>
        <button
          onClick={onDone}
          className="px-4 py-2 text-on-surface-variant hover:text-on-surface rounded-md text-sm transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Setup panel (slide-in for a single registry entry)
// ---------------------------------------------------------------------------

function SetupPanel({
  entry,
  integrationId,
  onClose,
}: {
  entry: RegistryEntry
  integrationId: string | null
  onClose: () => void
}) {
  const createIntegration = useCreateIntegration()
  const [createdId, setCreatedId] = useState<string | null>(integrationId)

  const handleCreate = async () => {
    const result = await createIntegration.mutateAsync({
      adapter_type: entry.adapter_type,
      provider_name: entry.name,
    })
    setCreatedId(result.id)
  }

  return (
    <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm shadow-slate-200/50 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-surface-container-low flex items-center justify-center">
            <span className="material-symbols-outlined text-xl text-on-surface-variant">
              {entry.icon}
            </span>
          </div>
          <div>
            <h3 className="text-lg font-bold text-on-surface">{entry.name}</h3>
            <p className="text-xs text-on-surface-variant">{entry.adapter_type.replace('_', ' ')}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-on-surface-variant hover:text-on-surface rounded-md transition-colors"
        >
          <span className="material-symbols-outlined text-xl">close</span>
        </button>
      </div>

      {/* Setup guide */}
      {entry.setup_guide_md && (
        <div className="prose prose-sm max-w-none text-on-surface-variant mb-6 whitespace-pre-line text-sm leading-relaxed">
          {entry.setup_guide_md}
        </div>
      )}

      {/* Credential form */}
      {entry.credentials_schema.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-on-surface mb-3">Credentials</h4>
          {createdId ? (
            <CredentialForm entry={entry} integrationId={createdId} onDone={onClose} />
          ) : (
            <button
              onClick={handleCreate}
              disabled={createIntegration.isPending}
              className="px-4 py-2 bg-primary text-on-primary rounded-md text-sm font-semibold disabled:opacity-40 transition-colors hover:bg-primary/90"
            >
              {createIntegration.isPending ? 'Setting up...' : 'Start setup'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Configured integration card
// ---------------------------------------------------------------------------

function ConfiguredCard({
  integration,
  registryEntry,
}: {
  integration: IntegrationConfigItem
  registryEntry: RegistryEntry | undefined
}) {
  const deleteIntegration = useDeleteIntegration()
  const testIntegration = useTestIntegration()
  const { data: credentials } = useCredentials(integration.id)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [testing, setTesting] = useState(false)

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await testIntegration.mutateAsync(integration.id)
      setTestResult(result)
    } catch (err) {
      setTestResult({ success: false, message: String(err) })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="bg-surface-container-low rounded-lg px-4 py-3">
      <div className="flex items-center gap-4">
        <div className="w-9 h-9 rounded-lg bg-surface-container-lowest flex items-center justify-center flex-shrink-0">
          <span className="material-symbols-outlined text-lg text-on-surface-variant">
            {registryEntry?.icon || 'extension'}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-on-surface">
            {integration.provider_name}
          </div>
          <div className="text-xs text-on-surface-variant flex items-center gap-2">
            <span>{integration.adapter_type.replace('_', ' ')}</span>
            {credentials && credentials.length > 0 && (
              <span className="text-green-600">
                {credentials.length} credential{credentials.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={handleTest}
          disabled={testing}
          className="p-1.5 text-on-surface-variant hover:text-primary rounded-md transition-colors"
          title="Test connection"
        >
          <span className="material-symbols-outlined text-base">
            {testing ? 'hourglass_top' : 'sync'}
          </span>
        </button>
        <button
          onClick={() => deleteIntegration.mutate(integration.id)}
          className="p-1.5 text-on-surface-variant hover:text-error rounded-md transition-colors"
          title="Remove integration"
        >
          <span className="material-symbols-outlined text-base">delete</span>
        </button>
      </div>
      {testResult && (
        <div
          className={`mt-2 rounded-md px-3 py-2 text-xs ${
            testResult.success
              ? 'bg-green-50 text-green-700'
              : 'bg-red-50 text-red-700'
          }`}
        >
          {testResult.message}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function IntegrationSettings() {
  const { data: integrations, isLoading: loadingIntegrations } = useIntegrations()
  const { data: registry, isLoading: loadingRegistry } = useRegistry()
  const [setupEntry, setSetupEntry] = useState<RegistryEntry | null>(null)

  const configuredIds = new Set(
    (integrations || []).map((i) => i.provider_name.toLowerCase()),
  )

  const getRegistryForIntegration = (integration: IntegrationConfigItem) =>
    registry?.find(
      (r) => r.name.toLowerCase() === integration.provider_name.toLowerCase(),
    )

  const isConfigured = (entry: RegistryEntry) =>
    configuredIds.has(entry.name.toLowerCase())

  const getIntegrationId = (entry: RegistryEntry) =>
    integrations?.find(
      (i) => i.provider_name.toLowerCase() === entry.name.toLowerCase(),
    )?.id || null

  return (
    <section id="integrations">
      <div className="mb-8">
        <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">
          Integrations
        </h2>
        <p className="text-on-surface-variant text-sm max-w-xl">
          Connect vulnerability scanners, ticketing systems, and validation tools to
          power the remediation pipeline.
        </p>
      </div>

      {/* Setup panel */}
      {setupEntry && (
        <SetupPanel
          entry={setupEntry}
          integrationId={getIntegrationId(setupEntry)}
          onClose={() => setSetupEntry(null)}
        />
      )}

      {/* Configured integrations */}
      {(integrations || []).length > 0 && (
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm shadow-slate-200/50 mb-6">
          <h3 className="text-sm font-semibold text-on-surface mb-3">
            Connected
          </h3>
          <div className="space-y-2">
            {(integrations || []).map((integration) => (
              <ConfiguredCard
                key={integration.id}
                integration={integration}
                registryEntry={getRegistryForIntegration(integration)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Registry catalog */}
      <div className="bg-surface-container-lowest rounded-xl p-6 shadow-sm shadow-slate-200/50">
        <h3 className="text-sm font-semibold text-on-surface mb-4">
          Available integrations
        </h3>
        {loadingRegistry || loadingIntegrations ? (
          <p className="text-sm text-on-surface-variant">Loading catalog...</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {(registry || []).map((entry) => {
              const configured = isConfigured(entry)
              return (
                <div
                  key={entry.id}
                  className={`rounded-lg p-4 transition-colors ${
                    entry.status === 'coming_soon'
                      ? 'bg-surface-container-low opacity-60'
                      : 'bg-surface-container-low hover:bg-surface-container'
                  }`}
                >
                  <div className="flex items-start gap-3 mb-2">
                    <div className="w-9 h-9 rounded-lg bg-surface-container-lowest flex items-center justify-center flex-shrink-0">
                      <span className="material-symbols-outlined text-lg text-on-surface-variant">
                        {entry.icon}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-on-surface">
                          {entry.name}
                        </span>
                        <StatusBadge status={entry.status} />
                      </div>
                      <p className="text-xs text-on-surface-variant mt-0.5 line-clamp-2">
                        {entry.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <div className="flex gap-1">
                      {entry.capabilities.map((cap) => (
                        <span
                          key={cap}
                          className="text-[10px] text-on-surface-variant bg-surface-container-lowest px-1.5 py-0.5 rounded"
                        >
                          {cap}
                        </span>
                      ))}
                    </div>
                    {entry.status === 'available' && !configured && (
                      <button
                        onClick={() => setSetupEntry(entry)}
                        className="text-xs font-semibold text-primary hover:text-primary/80 transition-colors"
                      >
                        Set up
                      </button>
                    )}
                    {configured && (
                      <span className="text-xs text-green-600 font-medium flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm">check_circle</span>
                        Connected
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </section>
  )
}
