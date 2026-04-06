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
- [ ] Handle `permission.asked` events — when the agent wants to use a tool (bash, MCP, scanner), surface the approval request to the user in the workspace chat. Three tiers: auto-approve (read files), user-approve (scan/query tools), explicit-approve (write-back actions like ticket creation, status updates). Inspired by Claude Code's "ask before acting" pattern — builds trust with security teams
- [ ] Executor prompt refinement — the orchestrator agent in workspaces with existing session history behaves differently than fresh workspaces (tries to read files instead of responding with JSON directly). Tune the prompt or use a dedicated session with a system prompt override so the executor always gets structured JSON back, regardless of workspace state

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
- [ ] Finding normalization via LLM: `POST /api/findings/ingest` accepts `{ source, raw_data }`, uses singleton OpenCode process to extract structured fields into `FindingCreate`, creates a Finding. Works with any scanner format — no hardcoded vendor mappings. See ADR-0022 for the app-level agent execution model
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
