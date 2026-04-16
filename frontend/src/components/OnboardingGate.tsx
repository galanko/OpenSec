import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useFeatureFlags } from '@/api/featureFlags'

/**
 * Wraps every ``/onboarding/*`` route. Two responsibilities:
 *
 * 1. **Feature-flag gate** — if ``v1_1_from_zero_to_secure_enabled`` is off
 *    (or the backend is unreachable), redirect to ``/findings``.
 * 2. **Already-onboarded short-circuit** — if the user has already finished
 *    onboarding, send them to ``/dashboard`` instead of trapping them in
 *    the wizard after a browser-back.
 *
 * Fail-closed while the flag fetch is in flight: render ``null`` so the
 * wizard doesn't flash before the redirect fires.
 */
export default function OnboardingGate({ children }: { children: ReactNode }) {
  const { data, isLoading, isError } = useFeatureFlags()

  if (isLoading) return null

  if (isError || !data?.v1_1_from_zero_to_secure_enabled) {
    return <Navigate to="/findings" replace />
  }

  if (data.onboarding_completed) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
