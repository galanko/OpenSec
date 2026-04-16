import { useEffect } from 'react'
import { useNavigate } from 'react-router'
import { onboardingStorage } from './storage'

/**
 * Onboarding frame 1.0 — "Welcome · first launch".
 * Centered hero, single "Get started" CTA, no progress bar (wizard starts
 * on the next page). Soft gradient backdrop mirrors the mockup.
 */
export default function Welcome() {
  const navigate = useNavigate()

  // Landing on Welcome means the user is starting fresh. Wipe any stale
  // assessment id / repo url left over from an abandoned run so later
  // pages never pick up the wrong context.
  useEffect(() => {
    onboardingStorage.clear()
  }, [])

  return (
    <div className="min-h-screen bg-surface relative overflow-hidden flex flex-col items-center justify-center px-6 py-20">
      {/* soft backdrop */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-container/30 via-transparent to-tertiary-container/20 pointer-events-none" />

      <div className="relative text-center max-w-xl">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-surface-container-lowest mb-6 shadow-sm">
          <span className="font-headline text-3xl font-extrabold text-primary">
            O
          </span>
        </div>
        <h1 className="font-headline text-4xl font-extrabold tracking-tight text-on-surface mb-3">
          Welcome to OpenSec
        </h1>
        <p className="text-on-surface-variant text-lg leading-relaxed mb-10">
          In three short steps we'll connect your repository, set up your AI
          model, and run a security assessment. Most maintainers are done in
          under three minutes.
        </p>
        <div className="flex items-center justify-center">
          <button
            type="button"
            onClick={() => navigate('/onboarding/connect')}
            className="px-8 py-3 rounded-lg bg-primary hover:bg-primary-dim text-white font-bold text-sm transition-colors active:scale-95 shadow-sm inline-flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
          >
            Get started
            <span className="material-symbols-outlined text-sm" aria-hidden="true">
              arrow_forward
            </span>
          </button>
        </div>
        <p className="mt-8 text-xs text-on-surface-variant">
          Self-hosted · your credentials never leave this machine
        </p>
      </div>
    </div>
  )
}
