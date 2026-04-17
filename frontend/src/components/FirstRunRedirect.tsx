import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useBootstrap } from '@/api/featureFlags'

interface FirstRunRedirectProps {
  children: ReactNode
}

/**
 * Sends a fresh user to the onboarding wizard on the very first visit to `/`.
 * Onboarding is mandatory — the redirect fires whenever the user has neither
 * completed onboarding nor run an assessment. Both signals must be false, so
 * a manually-seeded DB or an outside-wizard assessment keeps users on the
 * normal home page.
 */
export default function FirstRunRedirect({ children }: FirstRunRedirectProps) {
  const { data, isLoading } = useBootstrap()

  if (isLoading || !data) return null

  const shouldOnboard = !data.onboarding_completed && !data.has_any_assessment

  if (shouldOnboard) {
    return <Navigate to="/onboarding/welcome" replace />
  }

  return <>{children}</>
}
