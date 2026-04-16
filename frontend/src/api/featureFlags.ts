/**
 * Read-only feature-flag snapshot from the backend.
 *
 * The onboarding wizard + new v1.1 dashboard entry points are gated behind
 * ``v1_1_from_zero_to_secure_enabled``. Default is ``false`` on the server;
 * ``@galanko`` flips it on after the Session G PR merges for a canary.
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
    // Flags rarely change at runtime; don't thrash the network.
    staleTime: 60_000,
    // If the backend is momentarily down we don't want the wizard to wedge —
    // treat "no data yet" as flag-off via the consumer's default.
    retry: 1,
  })
}
