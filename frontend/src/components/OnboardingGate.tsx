import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useBootstrap } from '@/api/featureFlags'

/**
 * Wraps every ``/onboarding/*`` route. If the user has already finished
 * onboarding, send them to ``/dashboard`` instead of trapping them in the
 * wizard after a browser-back.
 *
 * Renders ``null`` while the bootstrap fetch is in flight so the wizard
 * doesn't flash before the redirect fires.
 */
export default function OnboardingGate({ children }: { children: ReactNode }) {
  const { data, isLoading } = useBootstrap()

  if (isLoading) return null

  if (data?.onboarding_completed) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
