/**
 * Dashboard + assessment + posture fetchers and TanStack Query hooks.
 *
 * Shapes come straight from the frozen OpenAPI snapshot
 * (Session 0 / EXEC-0002). During Session E these calls hit MSW mocks in
 * dev + tests; Session B swaps in the real backend.
 */

import { useMutation, useQuery } from '@tanstack/react-query'
import { request } from './client'
import type { components } from './types'

// Names match backend/opensec/models/posture_check.py :: PostureCheckName.
// Frontend-owned so we don't wait on an OpenAPI regen every time we add
// state to the PostureCard.
export type PostureCheckName =
  | 'branch_protection'
  | 'no_force_pushes'
  | 'no_secrets_in_code'
  | 'security_md'
  | 'lockfile_present'
  | 'dependabot_config'
  | 'signed_commits'

export type PostureCheckStatus = 'pass' | 'fail' | 'advisory' | 'unknown'

export interface PostureCheckResult {
  id: string
  assessment_id: string
  check_name: PostureCheckName
  status: PostureCheckStatus
  detail?: Record<string, unknown> | null
  created_at: string
}

// The codegen snapshot doesn't know about `posture_checks` yet. Extend the
// generated shape with the field we ship from the backend now.
export type DashboardPayload = components['schemas']['DashboardPayload'] & {
  posture_checks?: PostureCheckResult[]
}
export type AssessmentStatusResponse =
  components['schemas']['AssessmentStatusResponse']
export type AssessmentLatestResponse =
  components['schemas']['AssessmentLatestResponse']
export type PostureFixResponse = components['schemas']['PostureFixResponse']
export type PostureFixableCheck = 'security_md' | 'dependabot_config'

// ---------------------------------------------------------------------------
// Fetchers
// ---------------------------------------------------------------------------

export const dashboardApi = {
  getDashboard: () => request<DashboardPayload>('/api/dashboard'),
  getAssessmentLatest: () =>
    request<AssessmentLatestResponse>('/api/assessment/latest'),
  getAssessmentStatus: (id: string) =>
    request<AssessmentStatusResponse>(`/api/assessment/status/${id}`),
  fixPostureCheck: (checkName: PostureFixableCheck) =>
    request<PostureFixResponse>(`/api/posture/fix/${checkName}`, {
      method: 'POST',
    }),
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
