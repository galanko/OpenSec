import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import OnboardingShell from '@/components/onboarding/OnboardingShell'
import InlineErrorCallout from '@/components/onboarding/InlineErrorCallout'
import ConnectionResultCard from '@/components/onboarding/ConnectionResultCard'
import WizardNav from '@/components/onboarding/WizardNav'
import TokenHowToDialog from '@/components/completion/TokenHowToDialog'
import {
  onboardingApi,
  OnboardingApiError,
  type OnboardingRepoResponse,
} from '@/api/onboarding'
import { onboardingStorage } from './storage'

const MISSING_REPO_SCOPE_CODE = 'missing_repo_scope'

// How long the verified card stays on screen before we auto-advance to
// step 2. UX Spec Rev 2 calls for "a small spinner + 'Loading Step 2'
// inline hint" after verification — the delay lets the celebratory
// moment register so users see which repo got verified, while still
// owning the auto-advance. Long enough to read the repo name, short
// enough that users don't start hunting for a button.
const AUTO_ADVANCE_DELAY_MS = 1_400

type ConnectState =
  | { kind: 'idle' }
  | { kind: 'submitting' }
  | { kind: 'error'; error: OnboardingApiError }
  | { kind: 'verified'; response: OnboardingRepoResponse }

/**
 * Onboarding frames 1.1 / 1.2 / 1.3 — "Connect your project".
 *
 * On success the verified card renders for ~1.4s and then the wizard
 * auto-advances to `/onboarding/ai`. UX Spec Rev 2 asked for this —
 * a manual "Continue to AI config" click is a dead-end interaction
 * once verification has succeeded, and users kept pausing there
 * trying to figure out whether something was wrong.
 */
export default function ConnectRepo() {
  const navigate = useNavigate()
  const [repoUrl, setRepoUrl] = useState('')
  const [token, setToken] = useState('')
  const [state, setState] = useState<ConnectState>({ kind: 'idle' })
  const [dialogOpen, setDialogOpen] = useState(false)

  // Auto-advance to AI config once the verified card has registered.
  // A dependency on ``state.kind`` is enough — ``setTimeout`` cleanup
  // kicks in if the user hits "Change" during the window.
  useEffect(() => {
    if (state.kind !== 'verified') return
    const timer = window.setTimeout(() => {
      navigate('/onboarding/ai')
    }, AUTO_ADVANCE_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [state.kind, navigate])

  const missingScope =
    state.kind === 'error' && state.error.code === MISSING_REPO_SCOPE_CODE

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!repoUrl.trim() || !token.trim()) return

    setState({ kind: 'submitting' })
    try {
      const response = await onboardingApi.connectRepo({
        repo_url: repoUrl.trim(),
        github_token: token,
      })
      onboardingStorage.set('assessmentId', response.assessment_id)
      onboardingStorage.set('repoUrl', response.repo_url)
      setState({ kind: 'verified', response })
    } catch (err) {
      setState({
        kind: 'error',
        error:
          err instanceof OnboardingApiError
            ? err
            : new OnboardingApiError(
                err instanceof Error ? err.message : 'Unknown error',
                0,
              ),
      })
    }
  }

  return (
    <OnboardingShell step={1}>
      <h1 className="font-headline text-3xl font-extrabold text-on-surface mb-2">
        Connect your project
      </h1>
      <p className="text-on-surface-variant mb-8">
        Point OpenSec at the repository you'd like to secure. We use a personal
        access token so every change lands as a draft pull request you review.
      </p>

      {state.kind === 'verified' ? (
        <div
          className="motion-safe:animate-[fadeIn_220ms_ease-out]"
          data-testid="connected-confirmation"
        >
          {state.response.verified ? (
            <ConnectionResultCard
              verified={state.response.verified}
              onChange={() => setState({ kind: 'idle' })}
            />
          ) : (
            <div className="w-full rounded-2xl bg-surface-container-lowest shadow-sm px-6 py-6">
              <div className="flex items-start gap-3">
                <span
                  className="material-symbols-outlined text-tertiary mt-0.5"
                  aria-hidden="true"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  check_circle
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-sm font-semibold text-on-surface truncate">
                    {state.response.repo_url}
                  </p>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    Connected — ready to continue
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setState({ kind: 'idle' })}
                  className="text-xs font-semibold text-on-surface-variant hover:text-on-surface px-2 py-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
                >
                  Change
                </button>
              </div>
            </div>
          )}
          {/*
            * UX Spec Rev 2: after verification, replace the "Continue to
            * AI config" button with a small spinner + "Loading step 2…"
            * hint so the user sees the wizard is doing the next thing for
            * them instead of waiting on a click.
            */}
          <div
            role="status"
            aria-live="polite"
            className="mt-8 flex items-center gap-3 text-sm text-on-surface-variant"
          >
            <div
              className="h-4 w-4 animate-spin rounded-full border-[2px] border-primary/30 border-t-primary"
              aria-hidden="true"
            />
            <span>Loading step 2…</span>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate>
          <label className="block mb-5">
            <span className="block text-sm font-semibold text-on-surface mb-2">
              Repository URL
            </span>
            <input
              type="text"
              autoComplete="off"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/your-handle/your-project"
              className="w-full px-4 py-3 rounded-lg bg-surface-container-lowest shadow-sm border-0 ring-0 focus:ring-2 focus:ring-primary/30 focus:outline-none text-sm font-mono"
            />
          </label>

          <div className="mb-3">
            <div className="flex items-center justify-between mb-2">
              <label
                htmlFor="onboarding-pat"
                className="text-sm font-semibold text-on-surface"
              >
                GitHub personal access token
              </label>
              <button
                type="button"
                onClick={() => setDialogOpen(true)}
                className="text-xs font-medium text-primary hover:underline flex items-center gap-1 rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface px-1 py-0.5"
              >
                <span
                  className="material-symbols-outlined text-sm"
                  aria-hidden="true"
                >
                  help_outline
                </span>
                How to create a token
              </button>
            </div>
            <input
              id="onboarding-pat"
              type="password"
              autoComplete="off"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              aria-invalid={missingScope || undefined}
              placeholder="ghp_••••••••••••••••••••••••••••"
              className={`w-full px-4 py-3 rounded-lg bg-surface-container-lowest shadow-sm border-0 ring-0 focus:ring-2 focus:outline-none text-sm font-mono ${
                missingScope
                  ? 'ring-2 ring-error/40 focus:ring-error/60'
                  : 'focus:ring-primary/30'
              }`}
            />
          </div>

          {state.kind === 'error' && (
            <InlineErrorCallout
              title={
                missingScope
                  ? "Your token is missing the 'repo' scope"
                  : "We couldn't verify that repository"
              }
              body={
                missingScope ? (
                  <>
                    Regenerate the token with the{' '}
                    <span className="font-mono">repo</span> box checked, then
                    paste it back here. Your repo URL is kept.
                  </>
                ) : (
                  <>{state.error.message}</>
                )
              }
              action={
                missingScope
                  ? {
                      label: 'How to create a token',
                      href: 'https://github.com/settings/tokens',
                    }
                  : undefined
              }
            />
          )}

          <WizardNav
            onBack={() => navigate('/onboarding/welcome')}
            onNext={() => {
              /* handled by form submit */
            }}
            nextLabel={
              state.kind === 'submitting' ? 'Verifying…' : 'Verify and continue'
            }
            nextDisabled={
              !repoUrl.trim() || !token.trim() || state.kind === 'submitting'
            }
            nextType="submit"
          />
        </form>
      )}

      <TokenHowToDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
      />
    </OnboardingShell>
  )
}
