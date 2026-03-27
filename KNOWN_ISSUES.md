# Known Issues

Tracked problems to fix in focused sessions. Remove items once resolved.

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

---

### opencode.json can drift from runtime config

**Impact:** Model changes made via the Settings UI update OpenCode at runtime via `PUT /config`, but `opencode.json` must also be updated separately. If the write to the file fails silently, the next OpenCode restart will revert to the old model.

**Workaround:** ConfigManager writes to both the API and the file, but check `opencode.json` if the model reverts after a restart.

**Fix idea:** Add a startup check that compares `opencode.json` with the model stored in `app_setting` and reconciles if they differ.

---

### API keys set via Settings are lost on OpenCode restart

**Impact:** Keys set via `PUT /auth/{id}` only live in the OpenCode process memory. If OpenCode restarts (crash, deploy, manual restart), all keys are forgotten until our backend re-injects them.

**Workaround:** Keys are persisted in the `app_setting` table and re-injected on startup via `restore_keys_to_engine()`. If keys stop working after a crash, restart the backend.

**Fix idea:** Add a health-check hook that detects when OpenCode has restarted and automatically re-injects stored keys.

---

### Provider catalog may overwhelm the Settings UI

**Impact:** OpenCode supports 75+ providers. Showing all of them in the model selector or API key list can be noisy and hard to navigate.

**Workaround:** The UI shows providers with valid auth first, then a "show all" toggle for the rest.

**Fix idea:** Add a "favorites" or "pinned providers" feature so users can curate which providers appear by default.
