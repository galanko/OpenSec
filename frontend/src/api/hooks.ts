import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './client'
import type { AgentRunCreate, AgentRunUpdate, MessageCreate, WorkspaceCreate } from './client'

// ---------------------------------------------------------------------------
// Health (Phase 1)
// ---------------------------------------------------------------------------

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30_000,
  })
}

// ---------------------------------------------------------------------------
// OpenCode sessions (Phase 1)
// ---------------------------------------------------------------------------

export function useSessions() {
  return useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.listSessions(),
  })
}

export function useSession(id: string | undefined) {
  return useQuery({
    queryKey: ['session', id],
    queryFn: () => api.getSession(id!),
    enabled: !!id,
  })
}

// ---------------------------------------------------------------------------
// Findings (Phase 4)
// ---------------------------------------------------------------------------

export function useFindings(params?: { status?: string }) {
  return useQuery({
    queryKey: ['findings', params],
    queryFn: () => api.listFindings(params),
  })
}

export function useFinding(id: string | undefined) {
  return useQuery({
    queryKey: ['finding', id],
    queryFn: () => api.getFinding(id!),
    enabled: !!id,
  })
}

// ---------------------------------------------------------------------------
// Workspaces (Phase 5)
// ---------------------------------------------------------------------------

export function useWorkspaces(params?: { state?: string; finding_id?: string }) {
  return useQuery({
    queryKey: ['workspaces', params],
    queryFn: () => api.listWorkspaces(params),
  })
}

export function useWorkspace(id: string | undefined) {
  return useQuery({
    queryKey: ['workspace', id],
    queryFn: () => api.getWorkspace(id!),
    enabled: !!id,
  })
}

export function useCreateWorkspace() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: WorkspaceCreate) => api.createWorkspace(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workspaces'] })
    },
  })
}

// ---------------------------------------------------------------------------
// Messages (Phase 5)
// ---------------------------------------------------------------------------

export function useMessages(workspaceId: string | undefined) {
  return useQuery({
    queryKey: ['messages', workspaceId],
    queryFn: () => api.listMessages(workspaceId!),
    enabled: !!workspaceId,
  })
}

export function useCreateMessage(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: MessageCreate) => api.createMessage(workspaceId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['messages', workspaceId] })
    },
  })
}

// ---------------------------------------------------------------------------
// Agent runs (Phase 5)
// ---------------------------------------------------------------------------

export function useAgentRuns(workspaceId: string | undefined) {
  return useQuery({
    queryKey: ['agent-runs', workspaceId],
    queryFn: () => api.listAgentRuns(workspaceId!),
    enabled: !!workspaceId,
    refetchInterval: 3_000,
  })
}

export function useCreateAgentRun(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AgentRunCreate) => api.createAgentRun(workspaceId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent-runs', workspaceId] })
    },
  })
}

export function useUpdateAgentRun(workspaceId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ runId, data }: { runId: string; data: AgentRunUpdate }) =>
      api.updateAgentRun(workspaceId, runId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent-runs', workspaceId] })
    },
  })
}

// ---------------------------------------------------------------------------
// Sidebar state (Phase 5)
// ---------------------------------------------------------------------------

export function useSidebar(workspaceId: string | undefined) {
  return useQuery({
    queryKey: ['sidebar', workspaceId],
    queryFn: () => api.getSidebar(workspaceId!),
    enabled: !!workspaceId,
    retry: false,
  })
}
