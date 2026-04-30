# Secure-Repo Dogfooding — Bug & Improvement Log

**Session date:** 2026-04-30
**Driver:** Claude Code (Opus 4.7) running `/secure-repo@opensec` skill against the OpenSec repo itself.
**Goal:** Drive OpenSec end-to-end on its own repo until clean, log every rough edge.

This file is the running notebook for everything that goes wrong, feels wrong, or could be better — to be triaged into PRs after the session.

---

## Format

Each entry:

- **Severity:** `bug` (broken), `papercut` (annoying), `improvement` (nice-to-have), `posture` (skill / CLI guidance issue)
- **Where:** CLI command, skill step, or file
- **What:** what happened / what's wrong
- **Why it matters:** user-visible impact
- **Suggested fix:** if obvious

---

## Findings

### 1. CLI has no way to view or change the model
- **Severity:** improvement / posture
- **Where:** `opensec` CLI — no `settings`, `config`, or `model` subcommand
- **What:** To switch model from `gpt-4.1-nano` to `gpt-5-nano`, the only path was hitting `PUT /api/settings/model` with curl. The skill explicitly says "the user fixes config; don't try to fix it from the skill" — but the CLI gives no agent-friendly way to list available models or set one.
- **Why it matters:** Model choice is the #1 thing a user wants to tweak after install (cost, speed, quality). Forcing them into the web UI breaks the "live in your terminal" promise. Agents driving the skill cannot help.
- **Suggested fix:** Add `opensec model get` / `opensec model set <full_id>` / `opensec model list [--provider X]` returning JSON. Surface the same exit-code contract.
- **Status:** fixed in `fix/secure-repo-cli-bugs` — added `opensec model get/set/list` subgroup; `list` projects the catalog locally to `[{id, name}]`.

### 2. PUT `/api/settings/model` field naming is unintuitive
- **Severity:** papercut
- **Where:** `PUT /api/settings/model`
- **What:** Body requires `model_full_id` (e.g. `"openai/gpt-5-nano"`). I first tried `{provider, model_id}` — which is what the GET response *also* returns alongside `model_full_id`. The endpoint validation rejects the structured form even though it round-trips its own response shape.
- **Why it matters:** Echo-back-the-GET is the most natural shape for any client. Right now you have to know to drop two fields and synthesize a slash-joined string.
- **Suggested fix:** Accept either `{model_full_id}` OR `{provider, model_id}` on PUT. Or, better, return a single canonical shape on GET and accept that same shape on PUT.
- **Status:** fixed in `fix/secure-repo-cli-bugs` — `ModelUpdateRequest` now synthesizes `model_full_id` from `{provider, model_id}` when the slash-joined form is missing.

### 3. `/api/settings/api-keys` is misleading when keys come from env vars
- **Severity:** papercut / posture
- **Where:** `GET /api/settings/api-keys`
- **What:** Returns `[]` even when `OPENAI_API_KEY` is set in the daemon environment and obviously working (scan succeeded). The truth lives in `/api/settings/providers/configured`, where each provider has a `source: "env" | "db"` field.
- **Why it matters:** "Is my key configured?" is the most common pre-scan question. If the dedicated endpoint says "no keys" while the system is happily using one, users will set the key twice or get confused. Same problem in the UI Settings page.
- **Suggested fix:** `/settings/api-keys` should return entries for env-sourced keys too, with `source: "env"` and `key: null` (or `"•••• (env)"`). The frontend can decide how to render it.
- **Status:** fixed in `fix/secure-repo-cli-bugs` — `get_api_keys` merges env-sourced providers (`source: "env"`, `key_masked: null`) and tags DB rows with `source: "db"`. DB wins on dedup.

### 4. `opensec fix` exits 1 on first run with "Sidebar state not found"
- **Severity:** **bug** — blocks the happy path
- **Where:** `cli/opensec_cli/cli.py:268-285` (`fix`) and `cli/opensec_cli/client.py:151-174` (`poll`)
- **What:** `fix` creates the workspace, POSTs `/pipeline/run-all`, then immediately polls `GET /api/workspaces/{id}/sidebar`. The sidebar row is created only when the **first agent writes to it** — so the initial poll races the enricher and 404s. `poll()` treats a 404 as a hard error and re-raises, causing exit 1 with `{"error":"Sidebar state not found"}` and exposing an internal phrase that contradicts the exit-code contract (the user sees "broken" when the pipeline is actually running fine in the background).
- **Why it matters:** This is the very first thing every user does after a scan. On `gpt-5-nano` (slower first response), it fails ~100% of the time on first try. Re-running `opensec fix <id>` works because by then the enricher has written the sidebar.
- **Suggested fix:** In `poll()`, treat HTTP 404 as a transient "not ready yet" — sleep and retry until the deadline. Alternatively, `pipeline/run-all` should synchronously seed an empty `SidebarState` row before returning so the first GET succeeds.
- **Bonus:** Either way, when this *does* time out, the error message should say "pipeline didn't produce a plan within Xs" not "Sidebar state not found" — the latter is an implementation leak.
- **Status:** fixed in `fix/secure-repo-cli-bugs` — `poll()` accepts a `tolerate_status` tuple; `fix` and `approve` pass `(404,)`. Timeouts now surface as JSON with `code: "timeout"` via the `_with_client` wrapper instead of a Python traceback.

### 5. **CRITICAL: CLI ↔ backend plan-schema mismatch — `opensec fix` never detects a completed plan**
- **Severity:** **bug** — full pipeline blocker. This kills the happy path on every issue.
- **Where:** `cli/opensec_cli/cli.py:274-317` (`fix._done` and the rendering of `plan`) vs `backend/opensec/agents/sidebar_mapper.py:118-132` (`_map_planner`)
- **What:** The CLI's `_done` predicate checks `plan.steps` or `plan.summary`. The backend writes `plan.plan_steps`, `plan.interim_mitigation`, `plan.estimated_effort`, `plan.validation_method`, and `definition_of_done.items`. **Neither `plan.steps` nor `plan.summary` is ever written**, so `_done()` always returns False and `poll()` runs to its 900s timeout.
- **Symptom seen this session:** Pipeline finished in ~30s (enricher → exposure → evidence → planner all `completed`). Plan sat in the sidebar for 14+ minutes while the CLI happily polled and saw nothing.
- **Then it gets worse:** `TimeoutError` from `poll()` is **not** caught by the `_with_client` wrapper (`cli.py:46-83` only catches `DaemonDownError`, `VersionMismatchError`, `HTTPError`). The user gets a raw 30-line Python traceback to stderr, breaking the JSON-output contract.
- **The plan-display code is also broken** even if `_done` worked — it reads `plan.summary` (None), `plan.steps` (None), and `plan.definition_of_done` (None, because DoD is a sibling field, not nested under `plan`).
- **Why it matters:** Every single dependency finding hits this. The "agent-shaped, JSON output, exit codes encode state" promise is broken on the very first command the workflow needs.
- **Suggested fix:** Either (a) update CLI to read `plan.plan_steps`, fall back DoD to top-level `definition_of_done.items`; or (b) introduce a stable contract layer in the API: a `GET /api/workspaces/{id}/plan` that returns a CLI-shaped object (`{summary, steps, definition_of_done, status: "ready" | "running" | "approved"}`) decoupled from how the agents structure the sidebar internally.
- **Bonus fixes while there:**
  - Catch `TimeoutError` in `_with_client` and emit a JSON `code: "timeout"` error.
  - The plan display lacks an `summary` field server-side — generate one (e.g. first sentence of the planner's `summary_markdown` from the agent run) and store it under `plan.summary`.
- **Status:** fixed in `fix/secure-repo-cli-bugs` — CLI now reads `plan.plan_steps` and `definition_of_done.items`; emits `{steps, interim_mitigation, definition_of_done, approved}`. Dropped the never-populated `summary` field. Server-side `plan.summary` deferred to a future PR (planner's `summary_markdown` lives on the agent run row, not the sidebar; out of scope here).

### 6. `approve` will read `pull_request.branch` which the backend never writes
- **Severity:** papercut (cosmetic — `pr_url` is read correctly via fallback, so flow continues)
- **Where:** `cli/opensec_cli/cli.py:355` reads `pull_request.get("branch")`. Backend writes `pull_request.branch_name` (`sidebar_mapper.py:151`).
- **Why it matters:** The approve JSON will always show `"branch": null` even when a branch exists.
- **Suggested fix:** Same root cause as #5 — fix CLI field name or add a contract layer.
- **Status:** fixed in `fix/secure-repo-cli-bugs` — `approve` now reads `pull_request.branch_name` (with a `branch` fallback for forward-compat).

### 7. `/api/settings/providers` returns ~3 MB of JSON
- **Severity:** improvement
- **Where:** `GET /api/settings/providers`
- **What:** The full providers catalog dumps every model from every provider — 3 MB. Useful for the web UI's model picker, but agents asking "is gpt-5-nano available?" don't need pricing, capabilities, headers, etc.
- **Why it matters:** Token budget for any agent driving OpenSec. Also slow to render.
- **Suggested fix:** Add `?provider=openai&fields=models` query, or a thin `GET /api/settings/providers/{id}/models` returning just IDs + names.
- **Status:** deferred. The new `opensec model list` projects the existing endpoint locally inside the CLI process, so the agent context only sees `[{id, name}]`. Web UI keeps using the full catalog. Re-evaluate when another non-CLI client needs the slim form.

