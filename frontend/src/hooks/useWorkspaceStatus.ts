/**
 * useWorkspaceStatus — poll ``/api/posture/fix/status/{workspace_id}`` and
 * project the runner's filesystem status into the 4-state model the UX
 * spec uses for posture rows (PRD-0004 Story 3).
 *
 * Runner statuses (history/status.json):
 *   queued | running | pr_created | already_present | failed
 *
 * UI-facing states:
 *   to_do      — no workspace (not spawned yet)
 *   running    — queued / running
 *   succeeded  — pr_created / already_present
 *   failed     — failed
 */

import { usePostureFixStatus } from '@/api/dashboard'
import type { PostureFixStatus } from '@/api/dashboard'

export type PostureUIState = 'to_do' | 'running' | 'succeeded' | 'failed'

export interface PostureWorkspaceStatus {
  state: PostureUIState
  prUrl: string | null
  error: string | null
  raw: PostureFixStatus | null
  isLoading: boolean
}

export function useWorkspaceStatus(
  workspaceId: string | null | undefined,
): PostureWorkspaceStatus {
  const { data, isLoading } = usePostureFixStatus(workspaceId)

  if (!workspaceId) {
    return { state: 'to_do', prUrl: null, error: null, raw: null, isLoading: false }
  }

  if (!data) {
    // Between the optimistic flip and the first poll response.
    return { state: 'running', prUrl: null, error: null, raw: null, isLoading }
  }

  const s = data.status
  let state: PostureUIState = 'running'
  if (s === 'pr_created' || s === 'already_present') state = 'succeeded'
  else if (s === 'failed') state = 'failed'
  else if (s === 'queued' || s === 'running') state = 'running'

  return {
    state,
    prUrl: data.pr_url ?? null,
    error: data.error ?? null,
    raw: data,
    isLoading,
  }
}
