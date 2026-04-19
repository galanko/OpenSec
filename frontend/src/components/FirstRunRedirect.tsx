import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useBootstrap } from '@/api/featureFlags'
import PageSpinner from '@/components/PageSpinner'

interface FirstRunRedirectProps {
  children: ReactNode
}

/**
 * Sends a fresh user to the onboarding wizard on the very first visit to `/`.
 * Onboarding is mandatory — the redirect fires whenever the user has neither
 * completed onboarding nor run an assessment. Both signals must be false, so
 * a manually-seeded DB or an outside-wizard assessment keeps users on the
 * normal home page.
 *
 * While ``useBootstrap`` resolves, render a ``PageSpinner`` rather than
 * ``return null``. On a fresh install the bootstrap call + AppLayout
 * chrome used to paint an empty content area for a beat, and a
 * cold-started user would see a blank main column flash before the
 * redirect navigated them away — reads as "is this broken?" on first
 * launch. The spinner both occupies the space and signals progress.
 */
export default function FirstRunRedirect({ children }: FirstRunRedirectProps) {
  const { data, isLoading } = useBootstrap()

  if (isLoading || !data) return <PageSpinner />

  const shouldOnboard = !data.onboarding_completed && !data.has_any_assessment

  if (shouldOnboard) {
    return <Navigate to="/onboarding/welcome" replace />
  }

  return <>{children}</>
}
