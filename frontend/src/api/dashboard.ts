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

export interface PostureFixStatus {
  workspace_id: string
  kind: string
  status: 'queued' | 'running' | 'pr_created' | 'already_present' | 'failed'
  pr_url?: string | null
  branch_name?: string | null
  error?: string | null
  started_at: string
  finished_at?: string | null
  structured_output?: Record<string, unknown> | null
}

/**
 * Optional per-check parameters the UI can send with the fix call.
 * All fields are optional — omitting them renders the template with its
 * clearly-labelled placeholders that the maintainer edits before merging.
 */
export interface PostureFixParams {
  contact_email?: string
  contact_url?: string
  supported_versions?: string
  disclosure_window_days?: number
}

export interface RunAssessmentResponse {
  assessment_id: string
  status: string
}

export const dashboardApi = {
  getDashboard: () => request<DashboardPayload>('/api/dashboard'),
  getAssessmentLatest: () =>
    request<AssessmentLatestResponse>('/api/assessment/latest'),
  getAssessmentStatus: (id: string) =>
    request<AssessmentStatusResponse>(`/api/assessment/status/${id}`),
  runAssessment: (repoUrl: string) =>
    request<RunAssessmentResponse>('/api/assessment/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url: repoUrl }),
    }),
  fixPostureCheck: (
    checkName: PostureFixableCheck,
    params?: PostureFixParams,
  ) =>
    request<PostureFixResponse>(`/api/posture/fix/${checkName}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: params ? JSON.stringify(params) : undefined,
    }),
  getPostureFixStatus: (workspaceId: string) =>
    request<PostureFixStatus>(`/api/posture/fix/status/${workspaceId}`),
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: dashboardApi.getDashboard,
    // While an assessment is in flight the dashboard has to notice the
    // transition from running → complete so the running card can be replaced
    // by the report card. Without this the re-assessment flow lands on the
    // running state and stays there forever — the inner status endpoint
    // polls, but nothing refreshes the top-level /api/dashboard payload.
    refetchInterval: (query) => {
      const status = query.state.data?.assessment?.status
      // 1s while running — matches the assessment-status poll so the
      // Report Card swap doesn't lag a full extra beat behind the "all
      // done" visual in AssessmentProgressList.
      if (status === 'pending' || status === 'running') return 1_000
      return false
    },
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
    mutationFn: ({
      checkName,
      params,
    }: {
      checkName: PostureFixableCheck
      params?: PostureFixParams
    }) => dashboardApi.fixPostureCheck(checkName, params),
  })
}

/**
 * Kicks off a new assessment against the currently-connected repo
 * (PRD-0004 Story 1). The UI invalidates the ``['dashboard']`` query on
 * success so the header button flips to its running state without an
 * extra round-trip.
 */
export function useRunAssessment() {
  return useMutation({
    mutationFn: (repoUrl: string) => dashboardApi.runAssessment(repoUrl),
  })
}

/**
 * Polls the posture-fix status file while the agent is still running.
 * Terminal statuses (pr_created / already_present / failed) stop the poll.
 */
export function usePostureFixStatus(
  workspaceId: string | null | undefined,
  options?: { pollIntervalMs?: number },
) {
  const pollInterval = options?.pollIntervalMs ?? 2500
  return useQuery({
    queryKey: ['posture-fix-status', workspaceId],
    queryFn: () => dashboardApi.getPostureFixStatus(workspaceId!),
    enabled: Boolean(workspaceId),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (
        status === 'pr_created'
        || status === 'already_present'
        || status === 'failed'
      ) {
        return false
      }
      return pollInterval
    },
  })
}
