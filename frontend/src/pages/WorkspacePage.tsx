import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { api, type Finding, type EnrichmentOutput, type ExposureOutput, type PlanOutput } from '@/api/client'
import { useQueryClient } from '@tanstack/react-query'
import { useAgentRuns, useFinding, useSidebar, useWorkspace, useWorkspaces } from '@/api/hooks'
import ActionButton from '@/components/ActionButton'
import ActionChips from '@/components/ActionChips'
import EmptyState from '@/components/EmptyState'
import EnricherResultCard from '@/components/EnricherResultCard'
import ErrorBoundary from '@/components/ErrorBoundary'
import ExposureResultCard from '@/components/ExposureResultCard'
import ListCard from '@/components/ListCard'
import Markdown from '@/components/Markdown'
import PageShell from '@/components/PageShell'
import PermissionApprovalCard from '@/components/PermissionApprovalCard'
import PlannerResultCard from '@/components/PlannerResultCard'
import SeverityBadge from '@/components/SeverityBadge'
import WorkspaceSidebar from '@/components/WorkspaceSidebar'

// ---------------------------------------------------------------------------
// Chat message type (local state for streaming)
// ---------------------------------------------------------------------------

interface ChatMessage {
  role: 'user' | 'assistant' | 'error'
  content: string
  agentType?: string
  structuredOutput?: Record<string, unknown>
  confidence?: number | null
}

// ---------------------------------------------------------------------------
// Landing: list open workspaces with finding context
// ---------------------------------------------------------------------------

function WorkspaceCard({ ws, onClick }: { ws: { id: string; finding_id: string; state: string; current_focus: string | null }; onClick: () => void }) {
  const { data: finding } = useFinding(ws.finding_id)

  return (
    <ListCard>
      <div className="p-2 bg-primary-container rounded-lg flex-shrink-0">
        <span className="material-symbols-outlined text-primary text-sm">terminal</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-base font-bold truncate">
          {finding?.title ?? 'Loading...'}
        </p>
        <div className="flex items-center gap-2 mt-1">
          {finding?.raw_severity && (
            <SeverityBadge severity={finding.raw_severity} />
          )}
          {finding?.asset_label && (
            <span className="text-xs text-on-surface-variant">{finding.asset_label}</span>
          )}
          {finding?.likely_owner && (
            <span className="text-xs text-on-surface-variant">
              &bull; {finding.likely_owner}
            </span>
          )}
        </div>
      </div>
      <ActionButton label="Continue" icon="login" onClick={onClick} />
    </ListCard>
  )
}

function WorkspaceLanding() {
  const navigate = useNavigate()
  const { data: workspaces, isLoading } = useWorkspaces({ state: 'open' })

  if (isLoading) {
    return (
      <PageShell title="Workspaces" subtitle="Active remediation sessions.">
        <div className="flex justify-center py-24">
          <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      </PageShell>
    )
  }

  if (!workspaces || workspaces.length === 0) {
    return (
      <PageShell title="Workspaces" subtitle="Active remediation sessions.">
        <EmptyState
          icon="terminal"
          title="No active workspaces"
          subtitle="Open a finding from Findings to start a remediation session."
          action={{ label: 'Go to findings', onClick: () => navigate('/findings') }}
        />
      </PageShell>
    )
  }

  return (
    <PageShell title="Workspaces" subtitle="Pick up where you left off.">
      <div className="space-y-3">
        {workspaces.map((ws) => (
          <WorkspaceCard
            key={ws.id}
            ws={ws}
            onClick={() => navigate(`/workspace/${ws.id}`)}
          />
        ))}
      </div>
    </PageShell>
  )
}

// ---------------------------------------------------------------------------
// Active workspace
// ---------------------------------------------------------------------------

export default function WorkspacePage() {
  const { id: workspaceId } = useParams<{ id: string }>()

  return (
    <ErrorBoundary fallbackTitle="Workspace error" fallbackSubtitle="Something went wrong loading this workspace.">
      {workspaceId ? <ActiveWorkspace workspaceId={workspaceId} /> : <WorkspaceLanding />}
    </ErrorBoundary>
  )
}

function ActiveWorkspace({ workspaceId }: { workspaceId: string }) {
  const { data: workspace } = useWorkspace(workspaceId)
  const { data: finding } = useFinding(workspace?.finding_id)
  const { data: sidebar } = useSidebar(workspaceId)

  // Agent runs — polled via TanStack Query every 3s
  const { data: agentRuns } = useAgentRuns(workspaceId)
  const queryClient = useQueryClient()
  const processedRunIds = useRef<Set<string>>(new Set())
  const activeRun = agentRuns?.find(r => r.status === 'running')

  // Chat state
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessionModel, setSessionModel] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const sending = chatSending || !!activeRun
  const [streaming, setStreaming] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const lastUserMessageRef = useRef('')
  const streamingRef = useRef('')

  // Permission approval state
  // The executor serializes permission requests (blocks on each one),
  // so a single pendingPermission state is sufficient.
  const [pendingPermission, setPendingPermission] = useState<{
    id: string; tool: string; patterns: string[]; runId: string; sessionId: string
  } | null>(null)
  const [permissionLoading, setPermissionLoading] = useState(false)
  const [permissionError, setPermissionError] = useState<string | null>(null)

  // Auto-scroll (includes pendingPermission to scroll to approval card)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming, pendingPermission])

  // Restore or create OpenCode session, load existing chat history.
  useEffect(() => {
    if (!workspace) return
    let cancelled = false

    async function initSession() {
      const storedSessionId = workspace!.current_focus

      if (storedSessionId) {
        // Try to restore existing session and load its messages.
        try {
          const detail = await api.getSession(storedSessionId)
          if (!cancelled) {
            setSessionId(detail.id)
            // Use model from session messages if available, otherwise fall back to runtime.
            if (detail.model) {
              setSessionModel(detail.model)
            } else {
              try {
                const mc = await api.getModelConfig()
                if (mc.model_full_id) setSessionModel(mc.model_full_id)
              } catch { /* non-critical */ }
            }
            // Load existing chat history from OpenCode.
            const history: ChatMessage[] = detail.messages
              .filter((m) => m.content.trim())
              .map((m) => ({
                role: m.role === 'user' ? 'user' as const : 'assistant' as const,
                content: m.content,
              }))
            setMessages(history)
          }
          return
        } catch {
          // Session no longer exists — create a new one.
        }
      }

      // Create a new session on this workspace's isolated OpenCode process.
      const session = await api.createWorkspaceSession(workspaceId)
      if (!cancelled) {
        setSessionId(session.session_id)
        // Capture the runtime model at session creation time.
        try {
          const mc = await api.getModelConfig()
          if (mc.model_full_id) setSessionModel(mc.model_full_id)
        } catch { /* non-critical */ }
        // Store the session ID on the workspace for future reconnection.
        api.updateWorkspace(workspaceId, { current_focus: session.session_id } as Parameters<typeof api.updateWorkspace>[1]).catch(console.error)
      }
    }

    initSession().then(async () => {
      // Restore completed agent runs as structured cards in the timeline.
      // Running agents are detected automatically via useAgentRuns polling.
      if (cancelled) return
      try {
        const runs = await api.listAgentRuns(workspaceId)
        if (cancelled) return

        // Seed processedRunIds so the completion useEffect doesn't re-add them
        for (const r of runs) {
          if (r.status !== 'running' && r.status !== 'queued') {
            processedRunIds.current.add(r.id)
          }
        }

        // Restore completed agent runs as structured cards in the timeline
        const completedRuns: ChatMessage[] = runs
          .filter((r) => r.status === 'completed' && r.structured_output)
          .map((r) => ({
            role: 'assistant' as const,
            content: r.summary_markdown ?? '',
            agentType: r.agent_type,
            structuredOutput: r.structured_output ?? undefined,
            confidence: r.confidence,
          }))
        if (completedRuns.length > 0 && !cancelled) {
          setMessages((prev) => [...prev, ...completedRuns])
        }
      } catch { /* non-critical */ }
    }).catch(console.error)
    return () => { cancelled = true }
  }, [workspace, workspaceId])

  // SSE connection
  useEffect(() => {
    if (!sessionId) return
    let active = true

    const es = api.streamWorkspaceEvents(workspaceId, sessionId)
    eventSourceRef.current = es

    es.addEventListener('text', (event) => {
      if (!active) return
      const text = event.data
      if (text.trim() === lastUserMessageRef.current.trim()) return
      streamingRef.current = text
      setStreaming(text)
      setChatSending(true)
    })

    es.addEventListener('error', (event: Event) => {
      if (!active) return
      try {
        const data = JSON.parse((event as MessageEvent).data)
        streamingRef.current = ''
        setStreaming('')
        setMessages((msgs) => [...msgs, { role: 'error', content: data.message || 'Unknown error' }])
      } catch { /* SSE connection error */ }
      setChatSending(false)
    })

    es.addEventListener('done', () => {
      if (!active) return
      const text = streamingRef.current
      if (text) {
        setMessages((msgs) => [...msgs, { role: 'assistant', content: text }])
      }
      streamingRef.current = ''
      setStreaming('')
      setChatSending(false)
      setPendingPermission(null)
    })

    // Listen for permission_request events on the chat SSE stream.
    // This handles the chat path (action chips like "Enrich finding")
    // where OpenCode emits permission.asked directly.
    es.addEventListener('permission_request', (event) => {
      if (!active) return
      try {
        const data = JSON.parse((event as MessageEvent).data)
        setPendingPermission({
          id: data.id,
          tool: data.tool,
          patterns: data.patterns || [],
          runId: '', // chat path has no agent run ID
          sessionId: data.session_id || '',
        })
        setPermissionError(null)
      } catch { /* parse error */ }
    })

    return () => {
      active = false
      es.close()
      eventSourceRef.current = null
    }
  }, [sessionId, workspaceId])

  // Agent completion detection — reacts to useAgentRuns polling data.
  // No async work, no closure races. Completion detected on next poll (≤3s).
  useEffect(() => {
    if (!agentRuns) return
    for (const run of agentRuns) {
      if (processedRunIds.current.has(run.id)) continue
      if (run.status === 'completed') {
        processedRunIds.current.add(run.id)
        setMessages((prev) => [...prev, {
          role: 'assistant' as const,
          content: run.summary_markdown ?? 'Agent completed.',
          agentType: run.agent_type,
          structuredOutput: run.structured_output ?? undefined,
          confidence: run.confidence,
        }])
        setPendingPermission(null)
        setPermissionLoading(false)
        setPermissionError(null)
      } else if (run.status === 'failed' || run.status === 'cancelled') {
        processedRunIds.current.add(run.id)
        setMessages((prev) => [...prev, {
          role: 'error' as const,
          content: run.summary_markdown ?? 'Agent execution failed. Try again or ask a question in the chat.',
        }])
        setPendingPermission(null)
        setPermissionLoading(false)
        setPermissionError(null)
      }
    }
  }, [agentRuns])

  // Permission SSE — lightweight connection only for permission_request events.
  // Completion is detected via polling above, so done/error events are ignored.
  useEffect(() => {
    if (!activeRun) return
    const es = api.streamAgentExecution(workspaceId)

    es.addEventListener('permission_request', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data)
        setPendingPermission({
          id: data.id,
          tool: data.tool,
          patterns: data.patterns || [],
          runId: data.run_id || activeRun.id,
          sessionId: data.session_id || '',
        })
        setPermissionError(null)
      } catch { /* parse error */ }
    })

    // Ignore done — completion detected via polling
    es.addEventListener('done', () => { /* no-op */ })
    es.addEventListener('error', () => { es.close() })

    return () => { es.close() }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- activeRun?.id is intentional; using the full object would reconnect on every poll cycle
  }, [activeRun?.id, workspaceId])

  // Permission approve/deny handler.
  // Uses the chat-path endpoint when runId is empty (action chips),
  // or the executor endpoint when runId is set (programmatic execute).
  // After approval, sending stays true — the SSE `done` event handles
  // clearing it. After deny, the agent won't produce more output, so
  // we reset sending immediately.
  const handlePermissionResponse = useCallback(async (approved: boolean) => {
    if (!pendingPermission) return
    setPermissionLoading(true)
    setPermissionError(null)
    try {
      if (pendingPermission.runId) {
        await api.respondToPermission(workspaceId, pendingPermission.runId, approved)
      } else {
        await api.respondToChatPermission(workspaceId, pendingPermission.id, pendingPermission.sessionId, approved)
      }
      setPendingPermission(null)
      if (!approved) {
        setChatSending(false)
      }
    } catch (err) {
      setPermissionError(`Failed to ${approved ? 'approve' : 'deny'}: ${err}`)
    } finally {
      setPermissionLoading(false)
    }
  }, [workspaceId, pendingPermission])

  // Send a chat message (used by text input).
  const sendChatMessage = useCallback(async (content: string) => {
    if (!sessionId || sending) return
    lastUserMessageRef.current = content
    setMessages((prev) => [...prev, { role: 'user', content }])
    setChatSending(true)
    setStreaming('')
    streamingRef.current = ''

    try {
      await api.sendWorkspaceMessage(workspaceId, sessionId, content)
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'error', content: `Failed to send: ${err}` }])
      setChatSending(false)
    }
  }, [workspaceId, sessionId, sending])

  // Handle text input submit.
  const handleSubmit = useCallback(() => {
    if (!input.trim()) return
    const content = input.trim()
    setInput('')
    sendChatMessage(content)
  }, [input, sendChatMessage])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Action chips trigger programmatic agent execution (not chat).
  // No manual state management — useAgentRuns polling detects the running agent.
  const handleAgentAction = useCallback(async (agentType: string) => {
    if (sending) return
    try {
      await api.executeAgent(workspaceId, agentType)
      // Immediate re-fetch so useAgentRuns picks up the running agent fast
      queryClient.invalidateQueries({ queryKey: ['agent-runs', workspaceId] })
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'error', content: `Failed to start agent: ${err}` }])
    }
  }, [workspaceId, sending, queryClient])

  const isResolved = workspace?.state === 'closed'

  return (
    <div className={`flex flex-col h-[calc(100vh-4rem)] ${isResolved ? 'opacity-80' : ''}`}>
      {/* Top bar with finding context */}
      <FindingHeader finding={finding} workspaceId={workspaceId} workspaceState={workspace?.state} sessionModel={sessionModel} />

      {/* Resolved banner */}
      {isResolved && (
        <div className="bg-green-50 border-b border-green-200 px-8 py-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-green-600 text-sm">check_circle</span>
          <span className="text-xs font-medium text-green-700">
            This workspace has been resolved. Chat and actions are read-only.
          </span>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        {/* Center: chat */}
        <section className="flex-1 overflow-y-auto px-8 py-8 bg-surface-container-low flex flex-col gap-6 scroll-smooth">
          {/* Finding summary card */}
          {finding?.description && (
            <div className="max-w-3xl">
              <div className="bg-white rounded-2xl p-6 shadow-md border border-surface-container/80">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center flex-shrink-0">
                    <span className="material-symbols-outlined text-primary">auto_awesome</span>
                  </div>
                  <div>
                    <h3 className="text-lg font-bold mb-2">Finding summary</h3>
                    <p className="text-on-surface-variant text-sm leading-relaxed mb-4">
                      {finding.description}
                    </p>
                    {finding.why_this_matters && (
                      <div className="p-3 bg-surface-container-low rounded-lg">
                        <p className="text-[10px] text-on-surface-variant uppercase font-bold tracking-widest mb-1">
                          Why this matters
                        </p>
                        <p className="text-sm font-medium">{finding.why_this_matters}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Action chips */}
          {!isResolved && (
            <ActionChips
              onAction={handleAgentAction}
              disabled={!sessionId || sending}
            />
          )}

          {/* Chat messages */}
          {messages.map((msg, i) => (
            <div key={i} className={`max-w-3xl ${msg.role === 'user' ? 'self-end' : 'self-start'}`}>
              {msg.role === 'user' ? (
                <div className="bg-primary text-white rounded-2xl rounded-br-md px-5 py-3 shadow-sm">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                </div>
              ) : msg.role === 'error' ? (
                <div className="bg-error-container/20 border border-error/20 rounded-2xl rounded-bl-md px-5 py-3">
                  <p className="text-sm text-error leading-relaxed">{msg.content}</p>
                </div>
              ) : msg.agentType === 'finding_enricher' && msg.structuredOutput ? (
                <EnricherResultCard
                  data={msg.structuredOutput as unknown as EnrichmentOutput}
                  confidence={msg.confidence}
                  markdown={msg.content}
                />
              ) : msg.agentType === 'exposure_analyzer' && msg.structuredOutput ? (
                <ExposureResultCard
                  data={msg.structuredOutput as unknown as ExposureOutput}
                  confidence={msg.confidence}
                  markdown={msg.content}
                />
              ) : msg.agentType === 'remediation_planner' && msg.structuredOutput ? (
                <PlannerResultCard
                  data={msg.structuredOutput as unknown as PlanOutput}
                  confidence={msg.confidence}
                  markdown={msg.content}
                />
              ) : (
                <div className="bg-white rounded-2xl rounded-bl-md px-5 py-4 shadow-sm border border-surface-container/80">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
                    <span className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">OpenSec</span>
                  </div>
                  <Markdown content={msg.content} />
                </div>
              )}
            </div>
          ))}

          {/* Streaming indicator */}
          {streaming && (
            <div className="max-w-3xl self-start">
              <div className="bg-white rounded-2xl rounded-bl-md px-5 py-4 shadow-sm border border-surface-container/80">
                <div className="flex items-center gap-2 mb-2">
                  <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
                  <span className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">OpenSec</span>
                </div>
                <Markdown content={streaming} />
                <span className="inline-block w-2 h-4 bg-primary/40 rounded-sm animate-pulse ml-0.5" />
              </div>
            </div>
          )}

          {/* Thinking / running indicator */}
          {sending && !streaming && !pendingPermission && (
            <div className="max-w-3xl self-start">
              <div className="bg-indigo-50/80 border border-indigo-100 rounded-xl px-4 py-3 flex items-center gap-3 shadow-sm">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/80 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <p className="text-sm text-on-primary-fixed-variant font-medium">
                  {activeRun ? 'Running agent...' : 'Thinking...'}
                </p>
              </div>
            </div>
          )}

          {/* Permission approval card */}
          {pendingPermission && (
            <PermissionApprovalCard
              tool={pendingPermission.tool}
              patterns={pendingPermission.patterns}
              onApprove={() => handlePermissionResponse(true)}
              onDeny={() => handlePermissionResponse(false)}
              loading={permissionLoading}
              error={permissionError}
            />
          )}

          <div ref={messagesEndRef} />
        </section>

        {/* Right sidebar */}
        <WorkspaceSidebar sidebar={sidebar} />
      </div>

      {/* Chat input */}
      {isResolved ? (
        <div className="px-8 py-4 bg-surface-container-low border-t border-surface-container">
          <div className="max-w-3xl mx-auto text-center text-xs text-on-surface-variant py-2">
            This workspace is resolved. Reopen it from the History page to continue.
          </div>
        </div>
      ) : (
        <div className="px-8 py-4 bg-surface-container-lowest border-t border-surface-container">
          <div className="max-w-3xl mx-auto flex items-end gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={pendingPermission ? "Approve or deny the tool request to continue..." : "Type a message or use action chips above..."}
              disabled={sending || !sessionId || !!pendingPermission}
              rows={1}
              className="flex-1 bg-surface-container-low border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-primary/20 transition-all resize-none"
            />
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || sending || !sessionId}
              className="bg-primary text-white p-3 rounded-xl hover:bg-primary-dim disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20 active:scale-95"
            >
              <span className="material-symbols-outlined">send</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Finding header bar
// ---------------------------------------------------------------------------

function FindingHeader({
  finding,
  workspaceId,
  workspaceState,
  sessionModel,
}: {
  finding: Finding | undefined
  workspaceId: string
  workspaceState: string | undefined
  sessionModel: string | null
}) {
  const navigate = useNavigate()
  const [resolving, setResolving] = useState(false)

  const isClosed = workspaceState === 'closed'

  const handleResolve = useCallback(async () => {
    setResolving(true)
    try {
      await api.updateWorkspace(workspaceId, { state: 'closed' } as Parameters<typeof api.updateWorkspace>[1])
      navigate('/findings')
    } catch (err) {
      console.error('Failed to resolve workspace:', err)
      setResolving(false)
    }
  }, [workspaceId, navigate])

  return (
    <section className="bg-surface-container-lowest px-8 py-4 flex items-center justify-between border-b border-surface-container">
      <div className="flex items-center gap-4">
        {finding?.raw_severity && (
          <div className="p-2 bg-error-container/20 rounded-lg">
            <span className="material-symbols-outlined text-error">warning</span>
          </div>
        )}
        <div>
          <h1 className="text-xl font-bold tracking-tight">
            {finding?.title ?? 'Loading...'}
          </h1>
          <div className="flex gap-3 mt-1 items-center">
            {finding?.raw_severity && <SeverityBadge severity={finding.raw_severity} size="md" />}
            {finding?.asset_label && (
              <span className="text-xs text-on-surface-variant">
                Asset: <span className="text-on-surface font-medium">{finding.asset_label}</span>
              </span>
            )}
            {finding?.likely_owner && (
              <span className="text-xs text-on-surface-variant">
                Owner: <span className="text-on-surface font-medium">{finding.likely_owner}</span>
              </span>
            )}
            {sessionModel && (
              <span className="text-xs text-on-surface-variant flex items-center gap-1">
                <span className="material-symbols-outlined text-[13px]">neurology</span>
                <span className="font-mono text-on-surface">{sessionModel}</span>
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        {isClosed ? (
          <span className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-100 text-green-700 text-sm font-bold">
            <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>check_circle</span>
            Resolved
          </span>
        ) : (
          <button
            onClick={handleResolve}
            disabled={resolving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-tertiary hover:bg-tertiary-dim text-on-tertiary text-sm font-bold transition-all shadow-sm disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-sm">done_all</span>
            {resolving ? 'Resolving...' : 'Resolve'}
          </button>
        )}
      </div>
    </section>
  )
}
