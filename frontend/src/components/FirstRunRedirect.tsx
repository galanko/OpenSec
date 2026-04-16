import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useFeatureFlags } from '@/api/featureFlags'

interface FirstRunRedirectProps {
  children: ReactNode
}

/**
 * Sends a fresh user to the onboarding wizard on the very first visit to `/`.
 * The redirect only fires when the v1.1 flag is on AND the user has neither
 * completed onboarding nor run an assessment — both signals must be false, so
 * a manually-seeded DB or an outside-wizard assessment keeps users on the
 * normal home page.
 */
export default function FirstRunRedirect({ children }: FirstRunRedirectProps) {
  const { data, isLoading } = useFeatureFlags()

  if (isLoading || !data) return null

  const shouldOnboard =
    data.v1_1_from_zero_to_secure_enabled &&
    !data.onboarding_completed &&
    !data.has_any_assessment

  if (shouldOnboard) {
    return <Navigate to="/onboarding/welcome" replace />
  }

  return <>{children}</>
}
