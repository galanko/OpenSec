/** Minimal API client for the OpenSec FastAPI backend. */

const BASE = '';  // Uses Vite proxy in dev

export interface SessionSummary {
  id: string;
  created_at?: string;
}

export interface SessionDetail extends SessionSummary {
  messages: MessageInfo[];
}

export interface MessageInfo {
  id: string;
  role: string;
  content: string;
  created_at?: string;
}

export interface HealthStatus {
  opensec: string;
  opencode: string;
  opencode_version: string;
  model: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status}: ${text}`);
  }
  return resp.json();
}

export const api = {
  health: () => request<HealthStatus>('/health'),

  createSession: () =>
    request<SessionSummary>('/api/sessions', { method: 'POST' }),

  listSessions: () => request<SessionSummary[]>('/api/sessions'),

  getSession: (id: string) => request<SessionDetail>(`/api/sessions/${id}`),

  sendMessage: (sessionId: string, content: string) =>
    request<{ session_id: string; status: string }>(
      `/api/chat/${sessionId}/send`,
      { method: 'POST', body: JSON.stringify({ content }) },
    ),

  streamEvents: (sessionId: string): EventSource =>
    new EventSource(`/api/chat/${sessionId}/stream`),
};
