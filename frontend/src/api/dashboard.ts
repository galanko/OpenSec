/**
 * Dashboard + assessment + posture fetchers and TanStack Query hooks.
 *
 * Shapes come straight from the frozen OpenAPI snapshot
 * (Session 0 / EXEC-0002). During Session E these calls hit MSW mocks in
 * dev + tests; Session B swaps in the real backend.
 */

import { useMutation, useQuery } from '@tanstack/react-query'
import type { components } from './types'

export type DashboardPayload = components['schemas']['DashboardPayload']
export type AssessmentStatusResponse =
  components['schemas']['AssessmentStatusResponse']
export type AssessmentLatestResponse =
  components['schemas']['AssessmentLatestResponse']
export type PostureFixResponse = components['schemas']['PostureFixResponse']
export type PostureFixableCheck = 'security_md' | 'dependabot_config'

const BASE = ''

async function getJson<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`)
  if (!resp.ok) throw new Error(`${resp.status}: ${await resp.text()}`)
  return (await resp.json()) as T
}

async function postJson<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, { method: 'POST' })
  if (!resp.ok) throw new Error(`${resp.status}: ${await resp.text()}`)
  return (await resp.json()) as T
}

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

export const dashboardApi = {
  getDashboard: () => getJson<DashboardPayload>('/api/dashboard'),
  getAssessmentLatest: () =>
    getJson<AssessmentLatestResponse>('/api/assessment/latest'),
  getAssessmentStatus: (id: string) =>
    getJson<AssessmentStatusResponse>(`/api/assessment/status/${id}`),
  fixPostureCheck: (checkName: PostureFixableCheck) =>
    postJson<PostureFixResponse>(`/api/posture/fix/${checkName}`),
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: dashboardApi.getDashboard,
  })
}

/**
 * Polls the assessment status endpoint while the assessment is running.
 * Session B upgrades the backend to SSE; until then, poll every second.
 */
export function useAssessmentStatus(
  assessmentId: string | null | undefined,
  options?: { pollIntervalMs?: number },
) {
  const pollInterval = options?.pollIntervalMs ?? 1000
  return useQuery({
    queryKey: ['assessment-status', assessmentId],
    queryFn: () => dashboardApi.getAssessmentStatus(assessmentId!),
    enabled: Boolean(assessmentId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      // Stop polling once terminal.
      if (status === 'complete' || status === 'failed') return false
      return pollInterval
    },
  })
}

export function useFixPostureCheck() {
  return useMutation({
    mutationFn: (checkName: PostureFixableCheck) =>
      dashboardApi.fixPostureCheck(checkName),
  })
}
