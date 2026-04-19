/**
 * Read-only bootstrap state from the backend.
 *
 * The SPA fetches this once on load to decide whether to redirect to the
 * onboarding wizard (first-run signal: nothing in the DB) or to the
 * dashboard (returning user: already onboarded).
 */

import { useQuery } from '@tanstack/react-query'
import { request } from './client'

export interface BootstrapState {
  onboarding_completed: boolean
  has_any_assessment: boolean
}

export function useBootstrap() {
  return useQuery({
    queryKey: ['bootstrap'],
    queryFn: () => request<BootstrapState>('/api/config/bootstrap'),
    staleTime: 60_000,
    // Fail fast so guards can render their redirect state without a flicker.
    retry: false,
  })
}

// Backward-compat alias — older callsites imported ``useFeatureFlags``. The
// shape is identical; the flag-only field is gone.
export const useFeatureFlags = useBootstrap
export type FeatureFlags = BootstrapState
