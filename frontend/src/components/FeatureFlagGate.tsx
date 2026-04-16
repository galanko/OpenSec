/**
 * Wraps a subtree that should only render when the server has a given
 * feature flag enabled. When disabled, redirects to ``/findings`` — the
 * legacy home. This is the single entry point for feature-flag gating in
 * the router; add new guards by extending the ``flag`` literal rather than
 * spawning sibling guard components.
 *
 * While flags are loading we render nothing (not a spinner) to avoid a
 * layout flash between "wizard showing" and "redirecting away". The fetch
 * is fast and cached for 60s by ``useFeatureFlags``.
 */

import { Navigate } from 'react-router'
import type { ReactNode } from 'react'
import { useFeatureFlags, type FeatureFlags } from '@/api/featureFlags'

type FlagName = keyof FeatureFlags

export default function FeatureFlagGate({
  flag,
  children,
  redirectTo = '/findings',
}: {
  flag: FlagName
  children: ReactNode
  redirectTo?: string
}) {
  const { data, isLoading, isError } = useFeatureFlags()

  if (isLoading) return null

  // If the backend is unreachable we treat the flag as off. This is the
  // safer default for in-progress features — better to skip an experimental
  // flow than to show it against a broken backend.
  const enabled = !isError && Boolean(data?.[flag])
  if (!enabled) {
    return <Navigate to={redirectTo} replace />
  }

  return <>{children}</>
}
