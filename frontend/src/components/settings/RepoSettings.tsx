import { useState, useEffect } from 'react'
import { useRepoSettings, useUpdateRepoSettings, useTestRepoConnection } from '@/api/hooks'

export default function RepoSettings() {
  const { data: repoSettings, isLoading } = useRepoSettings()
  const updateSettings = useUpdateRepoSettings()
  const testConnection = useTestRepoConnection()

  const [url, setUrl] = useState('')
  const [token, setToken] = useState('')
  const [tokenTouched, setTokenTouched] = useState(false)

  useEffect(() => {
    if (repoSettings?.url) setUrl(repoSettings.url)
  }, [repoSettings?.url])

  const isConfigured = repoSettings?.url && repoSettings?.has_token

  const handleSave = async () => {
    const data: { url?: string; token?: string } = {}
    if (url !== (repoSettings?.url ?? '')) data.url = url
    if (tokenTouched && token) data.token = token
    if (Object.keys(data).length === 0) return
    await updateSettings.mutateAsync(data)
    setToken('')
    setTokenTouched(false)
  }

  const handleTest = async () => {
    const testToken = tokenTouched && token ? token : '__saved__'
    // For testing with saved token, we need to actually use the saved token.
    // The backend test endpoint needs fresh token, so require user to enter one.
    if (!url) return
    if (!tokenTouched && !repoSettings?.has_token) return
    await testConnection.mutateAsync({
      url,
      token: tokenTouched && token ? token : '',
    })
  }

  if (isLoading) return null

  return (
    <section id="repo">
      <div className="mb-8">
        <h2 className="text-2xl font-bold tracking-tight text-on-surface mb-2">
          Repository
        </h2>
        <p className="text-sm text-on-surface-variant leading-relaxed">
          Connect a GitHub repository so agents can create pull requests with fixes.
        </p>
      </div>

      <div className="bg-surface-container-lowest rounded-xl p-8 shadow-sm shadow-outline-variant/10">
        {/* Status indicator */}
        <div className="flex items-center gap-2 mb-6">
          <span className={`w-2 h-2 rounded-full ${isConfigured ? 'bg-green-500' : 'bg-outline-variant/40'}`} />
          <span className="text-xs font-medium text-on-surface-variant">
            {isConfigured ? 'Connected' : 'Not configured'}
          </span>
        </div>

        {/* URL field */}
        <div className="mb-5">
          <label className="block text-xs font-semibold text-on-surface mb-1.5">
            Repository URL
          </label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/org/repo"
            className="w-full bg-surface-container rounded-lg px-4 py-2.5 text-sm text-on-surface placeholder:text-on-surface-variant/50 outline-none focus:ring-2 focus:ring-primary/30 transition-all"
          />
        </div>

        {/* Token field */}
        <div className="mb-6">
          <label className="block text-xs font-semibold text-on-surface mb-1.5">
            Personal access token
          </label>
          <input
            type="password"
            value={tokenTouched ? token : ''}
            onChange={(e) => { setToken(e.target.value); setTokenTouched(true) }}
            placeholder={repoSettings?.has_token ? 'Token saved — enter new to replace' : 'ghp_...'}
            className="w-full bg-surface-container rounded-lg px-4 py-2.5 text-sm text-on-surface placeholder:text-on-surface-variant/50 outline-none focus:ring-2 focus:ring-primary/30 transition-all"
          />
          <p className="mt-1 text-[11px] text-on-surface-variant/70">
            Needs <code className="text-[10px] bg-surface-container px-1 rounded">repo</code> scope for cloning and PR creation.
          </p>
        </div>

        {/* Test result banner */}
        {testConnection.data && (
          <div className={`mb-5 rounded-lg px-4 py-3 text-sm ${
            testConnection.data.success
              ? 'bg-green-500/10 text-green-700'
              : 'bg-error/10 text-error'
          }`}>
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-base">
                {testConnection.data.success ? 'check_circle' : 'error'}
              </span>
              {testConnection.data.message}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={updateSettings.isPending}
            className="bg-primary text-on-primary px-5 py-2 rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {updateSettings.isPending ? 'Saving...' : 'Save'}
          </button>

          <button
            onClick={handleTest}
            disabled={testConnection.isPending || !url || (!tokenTouched && !repoSettings?.has_token)}
            className="border border-outline-variant/20 text-on-surface px-5 py-2 rounded-lg text-sm font-medium hover:bg-surface-container transition-colors disabled:opacity-40"
          >
            {testConnection.isPending ? 'Testing...' : 'Test connection'}
          </button>
        </div>
      </div>
    </section>
  )
}
