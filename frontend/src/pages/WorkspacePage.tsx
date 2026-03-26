import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { api, type Finding } from '@/api/client'
import { useFinding, useSidebar, useWorkspace, useWorkspaces } from '@/api/hooks'
import ActionChips from '@/components/ActionChips'
import Markdown from '@/components/Markdown'
import SeverityBadge from '@/components/SeverityBadge'
import WorkspaceSidebar from '@/components/WorkspaceSidebar'

// ---------------------------------------------------------------------------
// Chat message type (local state for streaming)
// ---------------------------------------------------------------------------

interface ChatMessage {
  role: 'user' | 'assistant' | 'error'
  content: string
}

// ---------------------------------------------------------------------------
// Landing: list open workspaces with finding context
// ---------------------------------------------------------------------------

function WorkspaceCard({ ws, onClick }: { ws: { id: string; finding_id: string; state: string; current_focus: string | null }; onClick: () => void }) {
  const { data: finding } = useFinding(ws.finding_id)

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-surface-container-lowest rounded-xl p-5 hover:shadow-lg hover:border-primary/5 border border-transparent transition-all flex items-center gap-4"
    >
      <div className="p-2 bg-primary-container rounded-lg">
        <span className="material-symbols-outlined text-primary text-sm">terminal</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold truncate">
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
      <span className="text-xs font-medium text-primary">{ws.state}</span>
    </button>
  )
}

function WorkspaceLanding() {
  const navigate = useNavigate()
  const { data: workspaces, isLoading } = useWorkspaces({ state: 'open' })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="w-8 h-8 border-3 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    )
  }

  if (!workspaces || workspaces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-4rem)] px-8">
        <div className="w-16 h-16 rounded-full bg-primary-container flex items-center justify-center mb-6">
          <span className="material-symbols-outlined text-3xl text-primary">auto_awesome</span>
        </div>
        <h2 className="text-2xl font-bold text-on-surface mb-2">Remediation workspace</h2>
        <p className="text-on-surface-variant text-sm text-center max-w-md mb-8">
          Open a finding from the Queue to start a remediation session, or pick up
          where you left off from an existing workspace.
        </p>
        <button
          onClick={() => navigate('/queue')}
          className="bg-primary hover:bg-primary-dim text-white px-8 py-3 rounded-lg font-bold text-sm transition-all shadow-lg shadow-primary/20 active:scale-95"
        >
          Go to Queue
        </button>
      </div>
    )
  }

  return (
    <div className="p-8 lg:p-12">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-extrabold tracking-tight text-on-surface mb-2">
          Open workspaces
        </h1>
        <p className="text-on-surface-variant mb-8">
          Pick up where you left off.
        </p>
        <div className="space-y-3">
          {workspaces.map((ws) => (
            <WorkspaceCard
              key={ws.id}
              ws={ws}
              onClick={() => navigate(`/workspace/${ws.id}`)}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Active workspace
// ---------------------------------------------------------------------------

export default function WorkspacePage() {
  const { id: workspaceId } = useParams<{ id: string }>()

  if (!workspaceId) return <WorkspaceLanding />

  return <ActiveWorkspace workspaceId={workspaceId} />
}

function ActiveWorkspace({ workspaceId }: { workspaceId: string }) {
  const { data: workspace } = useWorkspace(workspaceId)
  const { data: finding } = useFinding(workspace?.finding_id)
  const { data: sidebar } = useSidebar(workspaceId)

  // Chat state
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [streaming, setStreaming] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const lastUserMessageRef = useRef('')
  const streamingRef = useRef('')

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

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

      // Create a new session and store its ID on the workspace.
      const session = await api.createSession()
      if (!cancelled) {
        setSessionId(session.id)
        // Store the session ID on the workspace for future reconnection.
        api.updateWorkspace(workspaceId, { current_focus: session.id } as Parameters<typeof api.updateWorkspace>[1]).catch(console.error)
      }
    }

    initSession().catch(console.error)
    return () => { cancelled = true }
  }, [workspace, workspaceId])

  // SSE connection
  useEffect(() => {
    if (!sessionId) return
    let active = true

    const es = api.streamEvents(sessionId)
    eventSourceRef.current = es

    es.addEventListener('text', (event) => {
      if (!active) return
      const text = event.data
      if (text.trim() === lastUserMessageRef.current.trim()) return
      streamingRef.current = text
      setStreaming(text)
      setSending(true)
    })

    es.addEventListener('error', (event: Event) => {
      if (!active) return
      try {
        const data = JSON.parse((event as MessageEvent).data)
        streamingRef.current = ''
        setStreaming('')
        setMessages((msgs) => [...msgs, { role: 'error', content: data.message || 'Unknown error' }])
      } catch { /* SSE connection error */ }
      setSending(false)
    })

    es.addEventListener('done', () => {
      if (!active) return
      const text = streamingRef.current
      if (text) {
        setMessages((msgs) => [...msgs, { role: 'assistant', content: text }])
      }
      streamingRef.current = ''
      setStreaming('')
      setSending(false)
    })

    return () => {
      active = false
      es.close()
      eventSourceRef.current = null
    }
  }, [sessionId])

  // Send a chat message (used by both text input and action chips).
  const sendChatMessage = useCallback(async (content: string) => {
    if (!sessionId || sending) return
    lastUserMessageRef.current = content
    setMessages((prev) => [...prev, { role: 'user', content }])
    setSending(true)
    setStreaming('')
    streamingRef.current = ''

    try {
      await api.sendMessage(sessionId, content)
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'error', content: `Failed to send: ${err}` }])
      setSending(false)
    }
  }, [sessionId, sending])

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

  // Action chips send their prompt as a chat message to OpenCode.
  const handleAgentAction = useCallback((prompt: string) => {
    sendChatMessage(prompt)
  }, [sendChatMessage])

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Top bar with finding context */}
      <FindingHeader finding={finding} />

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
          <ActionChips
            onAction={handleAgentAction}
            disabled={!sessionId || sending}
          />

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

          {/* Thinking indicator */}
          {sending && !streaming && (
            <div className="max-w-3xl self-start">
              <div className="bg-indigo-50/80 border border-indigo-100 rounded-xl px-4 py-3 flex items-center gap-3 shadow-sm">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary/80 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <p className="text-sm text-on-primary-fixed-variant font-medium">Thinking...</p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </section>

        {/* Right sidebar */}
        <WorkspaceSidebar sidebar={sidebar} />
      </div>

      {/* Chat input */}
      <div className="px-8 py-4 bg-surface-container-lowest border-t border-surface-container">
        <div className="max-w-3xl mx-auto flex items-end gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message or use action chips above..."
            disabled={sending || !sessionId}
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
    </div>
  )
}

// ---------------------------------------------------------------------------
// Finding header bar
// ---------------------------------------------------------------------------

function FindingHeader({ finding }: { finding: Finding | undefined }) {
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
          </div>
        </div>
      </div>
      <div className="flex gap-2">
        <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-outline-variant/30 text-sm hover:bg-surface-container transition-colors">
          <span className="material-symbols-outlined text-sm">share</span>
          Share
        </button>
      </div>
    </section>
  )
}
