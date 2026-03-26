import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '@/api/client'
import Markdown from '@/components/Markdown'

interface ChatMessage {
  role: 'user' | 'assistant' | 'error'
  content: string
}

export default function WorkspacePage() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [streaming, setStreaming] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const lastUserMessageRef = useRef('')

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  // Track latest streaming text in a ref so the done handler reads current value
  const streamingRef = useRef('')

  // Connect SSE when session exists
  useEffect(() => {
    if (!sessionId) return

    // Guard against React StrictMode double-mount
    let active = true

    const es = api.streamEvents(sessionId)
    eventSourceRef.current = es

    es.addEventListener('text', (event) => {
      if (!active) return
      // Skip if OpenCode echoes back the user's message
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
      } catch {
        // SSE connection error
      }
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

  const createSession = useCallback(async () => {
    try {
      const session = await api.createSession()
      setSessionId(session.id)
      setMessages([])
      setStreaming('')
    } catch (err) {
      console.error('Failed to create session:', err)
    }
  }, [])

  const sendMessage = useCallback(async () => {
    if (!sessionId || !input.trim() || sending) return

    const content = input.trim()
    setInput('')
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
  }, [sessionId, input, sending])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // No session yet — show start screen
  if (!sessionId) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-4rem)] px-8">
        <div className="w-16 h-16 rounded-full bg-primary-container flex items-center justify-center mb-6">
          <span className="material-symbols-outlined text-3xl text-primary">auto_awesome</span>
        </div>
        <h2 className="text-2xl font-bold text-on-surface mb-2">Remediation workspace</h2>
        <p className="text-on-surface-variant text-sm text-center max-w-md mb-8">
          Start a session to chat with the OpenSec AI. Ask about vulnerabilities, get remediation plans, or explore your security posture.
        </p>
        <button
          onClick={createSession}
          className="bg-primary hover:bg-primary-dim text-white px-8 py-3 rounded-lg font-bold text-sm transition-all shadow-lg shadow-primary/20 active:scale-95"
        >
          Start session
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Session header */}
      <section className="bg-surface-container-lowest px-8 py-3 flex items-center justify-between border-b border-surface-container">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-primary-container rounded-lg">
            <span className="material-symbols-outlined text-primary text-sm">terminal</span>
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight">Workspace session</h1>
            <span className="text-xs text-on-surface-variant font-mono">{sessionId.slice(0, 12)}...</span>
          </div>
        </div>
        <button
          onClick={createSession}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-outline-variant/30 text-xs font-medium hover:bg-surface-container transition-colors"
        >
          <span className="material-symbols-outlined text-sm">add</span>
          New session
        </button>
      </section>

      {/* Chat thread */}
      <section className="flex-1 overflow-y-auto px-8 py-8 bg-surface-container-low flex flex-col gap-6 scroll-smooth">
        {messages.length === 0 && !streaming && (
          <div className="flex-1 flex flex-col items-center justify-center text-center py-16">
            <span className="material-symbols-outlined text-4xl text-on-surface-variant/30 mb-4">chat</span>
            <p className="text-on-surface-variant text-sm">Send a message to start the conversation</p>
          </div>
        )}

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

      {/* Chat input */}
      <div className="px-8 py-4 bg-surface-container-lowest border-t border-surface-container">
        <div className="max-w-3xl mx-auto flex items-end gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            disabled={sending}
            rows={1}
            className="flex-1 bg-surface-container-low border-none rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-primary/20 transition-all resize-none"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || sending}
            className="bg-primary text-white p-3 rounded-xl hover:bg-primary-dim disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-primary/20 active:scale-95"
          >
            <span className="material-symbols-outlined">send</span>
          </button>
        </div>
      </div>
    </div>
  )
}
