import { useState } from 'react'
import {
  useIntegrations,
  useCreateIntegration,
  useUpdateIntegration,
  useDeleteIntegration,
} from '@/api/hooks'

export default function IntegrationSettings() {
  const { data: integrations, isLoading } = useIntegrations()
  const createIntegration = useCreateIntegration()
  const updateIntegration = useUpdateIntegration()
  const deleteIntegration = useDeleteIntegration()

  const [showAdd, setShowAdd] = useState(false)
  const [newAdapterType, setNewAdapterType] = useState('')
  const [newProviderName, setNewProviderName] = useState('')

  const adapterTypes = [
    { value: 'finding_source', label: 'Vulnerability scanner' },
    { value: 'ownership_context', label: 'Ownership context' },
    { value: 'ticketing', label: 'Ticketing system' },
    { value: 'validation', label: 'Validation tool' },
  ]

  const handleAdd = () => {
    if (!newAdapterType || !newProviderName.trim()) return
    createIntegration.mutate(
      { adapter_type: newAdapterType, provider_name: newProviderName.trim() },
      {
        onSuccess: () => {
          setShowAdd(false)
          setNewAdapterType('')
          setNewProviderName('')
        },
      },
    )
  }

  const handleToggle = (id: string, currentEnabled: boolean) => {
    updateIntegration.mutate({ id, data: { enabled: !currentEnabled } })
  }

  const handleDelete = (id: string) => {
    deleteIntegration.mutate(id)
  }

  return (
    <section className="scroll-mt-24" id="integrations">
      <div className="mb-8">
        <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">
          Integrations
        </h2>
        <p className="text-on-surface-variant text-sm max-w-xl">
          Connect vulnerability scanners, ticketing systems, and validation tools to
          power the remediation pipeline.
        </p>
      </div>

      <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm shadow-slate-200/50">
        {isLoading ? (
          <p className="text-sm text-on-surface-variant">Loading integrations...</p>
        ) : (integrations || []).length === 0 && !showAdd ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="w-14 h-14 rounded-full bg-surface-container-low flex items-center justify-center mb-4">
              <span className="material-symbols-outlined text-2xl text-on-surface-variant">
                extension
              </span>
            </div>
            <h3 className="text-lg font-bold text-on-surface mb-1">
              No integrations configured
            </h3>
            <p className="text-on-surface-variant text-sm text-center max-w-md mb-6">
              Connect your security stack to enable automated remediation workflows.
            </p>
            <button
              onClick={() => setShowAdd(true)}
              className="px-5 py-2.5 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors"
            >
              Add integration
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Existing integrations */}
            {(integrations || []).map((integration) => (
              <div
                key={integration.id}
                className="flex items-center gap-4 bg-surface-container-low rounded-lg px-4 py-3"
              >
                <span
                  className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    integration.enabled ? 'bg-green-500' : 'bg-outline-variant'
                  }`}
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-on-surface">
                    {integration.provider_name}
                  </div>
                  <div className="text-xs text-on-surface-variant">
                    {adapterTypes.find((t) => t.value === integration.adapter_type)?.label ||
                      integration.adapter_type}
                  </div>
                </div>
                <button
                  onClick={() => handleToggle(integration.id, integration.enabled)}
                  className={`relative w-10 h-5 rounded-full transition-colors ${
                    integration.enabled ? 'bg-primary' : 'bg-outline-variant'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                      integration.enabled ? 'translate-x-5' : 'translate-x-0.5'
                    }`}
                  />
                </button>
                <button
                  onClick={() => handleDelete(integration.id)}
                  className="p-1.5 text-on-surface-variant hover:text-error rounded-md transition-colors"
                  title="Remove integration"
                >
                  <span className="material-symbols-outlined text-base">delete</span>
                </button>
              </div>
            ))}

            {/* Add form */}
            {showAdd ? (
              <div className="bg-surface-container-low rounded-lg p-4 space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold text-on-surface-variant block mb-1">
                      Type
                    </label>
                    <select
                      value={newAdapterType}
                      onChange={(e) => setNewAdapterType(e.target.value)}
                      className="w-full bg-surface-container-lowest rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20"
                    >
                      <option value="">Select type...</option>
                      {adapterTypes.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-on-surface-variant block mb-1">
                      Provider name
                    </label>
                    <input
                      type="text"
                      value={newProviderName}
                      onChange={(e) => setNewProviderName(e.target.value)}
                      placeholder="e.g. Snyk, Jira, SonarQube"
                      className="w-full bg-surface-container-lowest rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/20"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleAdd}
                    disabled={!newAdapterType || !newProviderName.trim() || createIntegration.isPending}
                    className="px-4 py-2 bg-primary text-on-primary rounded-md text-sm font-semibold disabled:opacity-40"
                  >
                    {createIntegration.isPending ? 'Adding...' : 'Add'}
                  </button>
                  <button
                    onClick={() => {
                      setShowAdd(false)
                      setNewAdapterType('')
                      setNewProviderName('')
                    }}
                    className="px-4 py-2 text-on-surface-variant hover:text-on-surface rounded-md text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowAdd(true)}
                className="flex items-center gap-2 text-sm text-primary hover:text-primary/80 font-medium mt-2"
              >
                <span className="material-symbols-outlined text-base">add</span>
                Add integration
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
