# ADR-0013: Runtime model as source of truth

**Date:** 2026-03-27
**Status:** Accepted

## Context

After ADR-0012 introduced runtime model switching via OpenCode's `PATCH /config` API, the health endpoint continued reading the model from `opencode.json` (the static config file). This caused two problems:

1. **Stale model in health endpoint** — After changing the model via the Settings UI, `opencode.json` and OpenCode's in-memory state could diverge, causing `/health` to report the wrong model.

2. **Wrong model displayed in workspaces** — Workspaces showed the model from the health endpoint (file-based) rather than the model actually used by the OpenCode session. Each OpenCode session locks to the model configured at session creation time, so old sessions may use a different model than what's currently configured.

## Decision

### OpenCode's `GET /config` is the source of truth for the current model

The health endpoint now reads the model from OpenCode's runtime `GET /config` API instead of `opencode.json`. This ensures the displayed model always matches what OpenCode is actually using for new sessions.

Fallback to `opencode.json` remains for when OpenCode is unavailable.

### Session model is extracted from OpenCode message metadata

Each OpenCode message includes `providerID` and `modelID` in its metadata. The backend's `get_session()` method extracts the model from the first message and includes it in the `SessionDetail` response as a `model` field.

This means each workspace displays the model that was **actually used** for its chat, not the currently configured model. For sessions without messages (brand new), the frontend reads the current runtime model from `GET /api/settings/model`.

### Model display priority

1. **Session has messages** → model from message metadata (the actual model used)
2. **Session has no messages** → model from `GET /api/settings/model` (runtime config)
3. **OpenCode unavailable** → model from `opencode.json` (file fallback)

## Consequences

**Easier:**
- Workspaces always show the correct model they used, even after model changes
- Health endpoint is always accurate with the runtime state
- No database schema changes needed — model info comes from OpenCode's existing message metadata

**Harder:**
- Health endpoint now makes an HTTP call to OpenCode (`GET /config`) on every request — mitigated by OpenCode running locally on the same host
- Sessions without messages show the current model, which may differ from what the session will actually use if the model is changed before the first message
