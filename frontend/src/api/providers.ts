/**
 * Provider probe client + hook (PRD-0004 Story 4 / ADR-0031).
 *
 * Wraps ``POST /api/settings/providers/test``. Always resolves to a
 * ``ProviderTestResult`` — the backend encodes failure as ``ok=false`` with
 * an ``error_code`` rather than raising.
 */

import { useMutation } from '@tanstack/react-query'
import { request } from './client'

export type ProviderTestErrorCode =
  | 'auth_failed'
  | 'model_not_found'
  | 'timeout'
  | 'rate_limited'
  | 'other'

export interface ProviderTestRequest {
  provider?: string | null
  model?: string | null
  api_key?: string | null
}

export interface ProviderTestResult {
  ok: boolean
  latency_ms: number
  error_code: ProviderTestErrorCode | null
  error_message: string | null
}

export const providersApi = {
  test: (body: ProviderTestRequest = {}) =>
    request<ProviderTestResult>('/api/settings/providers/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
}

export function useProviderTest() {
  return useMutation({
    mutationFn: (body: ProviderTestRequest = {}) => providersApi.test(body),
  })
}
