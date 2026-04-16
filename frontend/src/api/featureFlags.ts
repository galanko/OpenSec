/**
 * Read-only feature-flag snapshot from the backend.
 *
 * Default on the server is ``false`` for every flag; consumers treat "no data
 * yet" as flag-off so the gate is fail-closed during fetch + on error.
 */

import { useQuery } from '@tanstack/react-query'
import { request } from './client'

export interface FeatureFlags {
  v1_1_from_zero_to_secure_enabled: boolean
}

export function useFeatureFlags() {
  return useQuery({
    queryKey: ['feature-flags'],
    queryFn: () => request<FeatureFlags>('/api/config/feature-flags'),
    staleTime: 60_000,
    // Skip retries — a flag endpoint should fail fast so the gate redirects
    // instead of flashing a blank screen through backoff.
    retry: false,
  })
}
