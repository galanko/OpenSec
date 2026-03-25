# Known Issues

Tracked problems to fix in focused sessions. Remove items once resolved.

---

### OpenCode server requires full restart to pick up config changes

**Impact:** Changing the model in `opencode.json` requires killing and restarting the entire backend (OpenCode + FastAPI). Hot-reload doesn't propagate config changes to the running OpenCode subprocess.

**Workaround:** Kill all processes and run `scripts/dev.sh` again.

**Fix idea:** Add an API endpoint that restarts the OpenCode subprocess, or use OpenCode's config API to push changes at runtime.

---

### SSE stream uses global event bus — no per-session filtering at source

**Impact:** The OpenCode `/event` endpoint is a global stream. Our backend filters by `sessionID`, but still receives all events for all sessions. With many concurrent sessions this could become a bottleneck.

**Workaround:** None needed for single-user MVP. Revisit if performance degrades.

**Fix idea:** Check if OpenCode supports per-session event subscriptions. If not, add server-side event routing in the backend.

---

### Old sessions accumulate in OpenCode with no cleanup

**Impact:** Every "New Session" click creates a permanent session in OpenCode. There's no cleanup, expiry, or delete mechanism in our app.

**Workaround:** Restart OpenCode to clear sessions.

**Fix idea:** Add session delete API. Add session age/limit management.

---

### No error shown when ANTHROPIC_API_KEY or other provider keys are missing

**Impact:** If the configured model's provider has no API key, the error only appears after sending the first message ("Model not found"). The UI should warn at startup.

**Workaround:** Check the status bar — if the model shows but messages fail, you likely need to set the provider's API key.

**Fix idea:** Call OpenCode's `/provider` endpoint on startup to verify the configured model's provider has valid credentials. Show a warning banner if not.

---

### Frontend SSE connection doesn't auto-reconnect after backend restart

**Impact:** If the backend restarts while the frontend is open, the SSE stream dies silently. The user must refresh the page.

**Workaround:** Refresh the browser after restarting the backend.

**Fix idea:** Add reconnection logic in the EventSource handler with a status indicator.

---

### Chat history lost on page refresh

**Impact:** Messages are only in React state. Refreshing the page loses the conversation. The session still exists in OpenCode but we don't reload its messages.

**Workaround:** Don't refresh while chatting.

**Fix idea:** On session load, fetch message history from OpenCode's `GET /session/{id}` and populate the chat.

---

### Send button stays disabled after an error

**Impact:** If a message send fails or the model returns an error, the `sending` state may not reset properly, leaving the input disabled.

**Workaround:** Click "New Session" to reset.

**Fix idea:** Ensure all error paths in the SSE handler reset the `sending` state.

---

### opencode.json model must use provider-qualified ID

**Impact:** The model in `opencode.json` must be the full `provider/model-id` format (e.g., `openai/gpt-4.1-nano`). Short names like `gpt-4.1-nano` won't work. This is an OpenCode requirement but not obvious.

**Workaround:** Always use the full qualified model ID.

**Fix idea:** Document this clearly. Validate the model format in our config loader. Future Settings page should show a dropdown of available models.
