# OpenSec Backlog

> Tactical task list for both development verticals. Each skill reads this at startup to find the next unchecked item. Check off items in commits as they're completed.

## Agent Orchestration (Vertical 1)

Phase 6b — Wire sub-agents into the isolated workspace runtime:

- [x] Agent output parser + per-agent Pydantic schemas (PR 1+2)
- [x] Sidebar mapper with read-merge-write (PR 1+2)
- [x] Agent executor core engine (PR 3)
- [x] Execution API endpoints — execute, suggest-next, cancel (PR 4+5)
- [x] Pipeline orchestrator with retry loop (PR 4+5)
- [x] Error handling and resilience — stall detection, activity events (PR 6)
- [x] ADR-0021: Agent execution model
- [x] E2E tests with real OpenCode + LLM (PR 7)
- [x] Handle `permission.asked` events — backend plumbing for tool-use approval: detect OpenCode permission events, auto-approve read-tier, wait for user approval on bash/edit/mcp, grant/deny endpoints. Workspace config stays "allow" (plumbing ready for when we flip to "ask")
- [x] Executor prompt refinement — per-agent prompts with inline output contracts + retry-on-parse-failure with corrective follow-up

Phase 7 — Ticket workflow (depends on Phase 6b):

- [ ] Ticket preview panel in workspace sidebar
- [ ] "Create ticket" action using mock Ticketing adapter
- [ ] Ticket state visible in sidebar (key, status, assignee, link)
- [ ] Close/reopen logic tied to ticket + validation state

## App Builder (Vertical 2)

### Priority 1: Simplification (tech debt from architecture review, 2026-04-06)

These clean up over-engineering identified during the integration strategy review. Do these first — they reduce code surface before adding new features.

- [x] Remove audit hash-chain: strip `prev_hash`, `event_hash`, `verify_chain()` from `audit.py`, remove `GET /api/audit/verify` route, simplify `_write_event` to direct insert without hash computation. Keep structured audit logging and async queue. (~40 lines removed from production, simplify `repo_audit` accordingly)
- [x] Remove hash-chain from audit DB schema: drop `prev_hash` and `event_hash` columns from `audit_log` table migration, add a new migration to remove them if table exists
- [x] Remove hash-chain tests: strip chain-related assertions from `tests/test_audit.py` (keep event logging tests)
- [x] Simplify registry loader: remove `clear_cache()`, `_cache` global, and `registry_dir` override from `registry/__init__.py`. Load once at import time. For tests, use monkeypatch on the loaded list directly

### Priority 2: Merge and stabilize current branch

- [x] Merge connection testing framework branch (`feat/connection-testing-framework`) into main via PR

### Priority 3: Core integration wiring (agentic plane only)

These wire integrations into the workspace runtime so agents can use MCP tools during remediation.

- [x] Integrations page: connection status indicators and test-from-UI flow (uses existing health monitor + connection testers)
- [x] Finding normalization via dedicated agent: create `finding-normalizer` agent (`.opencode/agents/`), `POST /api/findings/ingest` route accepts `{ source, raw_data[] }`, uses singleton OpenCode process to extract structured fields into `FindingCreate`. Low-cost design: tight prompt with few-shot examples, no tool use, batch support. Works with any scanner format. See ADR-0022
- [x] Async chunked ingest: replace synchronous ingest with job-based async processing. `POST /api/findings/ingest` returns job ID immediately, background worker chunks raw data into batches of 10, processes each independently. Includes: `ingest_job` DB table + migration, background worker coroutine (FastAPI lifespan), `GET /api/findings/ingest/{job_id}` progress endpoint, cancel endpoint, token estimation, dry-run mode, model override field. See ADR-0023
- [x] Ingest progress UI: frontend polling for job status, progress bar, error display, cancel button. Replace existing synchronous ingest result handling
- [ ] Jira write-back workflow: ticket creation from workspace using Jira MCP server (zero custom code — registry entry + credential schema only)
- [ ] Status write-back from workspace to source system (Wiz `wiz_update_finding_status` tool already exists)

### Priority 4: Additional vendor wrappers

Connection testers are a UI convenience, not mandatory for new integrations. Only add a tester if the vendor has no MCP server that validates credentials on startup.

- [ ] Additional vendor wrapper: Snyk (thin MCP wrapper, follow Wiz pattern)
- [ ] Additional vendor wrapper: Tenable (thin MCP wrapper)

### Priority 5: Queue and UI gaps

- [ ] Queue page: search by title/asset/CVE (Phase 4 gap)
- [ ] Queue page: "Why this matters" preview on hover/expand (Phase 4 gap)
- [ ] Settings page: model/provider configuration improvements
- [ ] Permission approval UI: SSE listener for `permission_request` events in WorkspacePage, approval card component (tool name, command patterns, approve/deny buttons), POST to `/api/workspaces/{id}/agent-runs/{run_id}/permission`. Backend plumbing done in Phase 6b PR #34. Also needs: flip workspace `opencode.json` from `"allow"` to `"ask"` for bash/edit

### Priority 6: Packaging (depends on Phase 6b + Phase 7 completion)

- [ ] Startup migration runner
- [ ] Seed demo data mode (`OPENSEC_DEMO=true`)
- [ ] Install + upgrade documentation
- [ ] First tagged release (v0.1.0-alpha)

### Deferred (not in MVP scope)

These are parked until the operational plane is needed. ADR-0020 has been downgraded to "Proposed" status.

- Operational plane: scheduled sync/polling jobs (revisit when ADR-0020 is re-accepted)
- Webhook ingestion handlers for finding sources
- Hash-chain tamper evidence for audit log (re-add for enterprise/multi-user edition)
- App-level conversational interface: chat-as-shell for the main app (finding upload via conversation, collector configuration, integration setup, natural-language queries across findings). Requires ADR-0022 accepted + Phase 6b complete. Revisit after v0.1.0-alpha

## Cross-cutting

- [x] ADR-0021: Agent execution model (direct invocation, advisory pipeline, filesystem checkpoints)
