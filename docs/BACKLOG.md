# OpenSec Backlog

> Tactical task list for both development verticals. Each skill reads this at startup to find the next unchecked item. Check off items in commits as they're completed.

## Agent Orchestration (Vertical 1)

Phase 6b — Wire sub-agents into the isolated workspace runtime:

- [ ] Implement agent execution entry point (orchestrator delegates to sub-agent via OpenCode process)
- [ ] Implement Finding Enricher execution (run agent, parse JSON output, update sidebar + chat)
- [ ] Implement Owner Resolver execution
- [ ] Implement Exposure/Context Analyzer execution
- [ ] Implement Remediation Planner execution
- [ ] Implement Validation Checker execution
- [ ] Build orchestrator "what should we do next?" logic
- [ ] Handle missing data gracefully (agent suggests what's needed)
- [ ] Support rerun / retry / cancel for agent runs
- [ ] E2E test: finding -> enrichment -> owner -> plan -> validation -> closure

Phase 7 — Ticket workflow (depends on Phase 6b):

- [ ] Ticket preview panel in workspace sidebar
- [ ] "Create ticket" action using mock Ticketing adapter
- [ ] Ticket state visible in sidebar (key, status, assignee, link)
- [ ] Close/reopen logic tied to ticket + validation state

## App Builder (Vertical 2)

### Priority 1: Simplification (tech debt from architecture review, 2026-04-06)

These clean up over-engineering identified during the integration strategy review. Do these first — they reduce code surface before adding new features.

- [ ] Remove audit hash-chain: strip `prev_hash`, `event_hash`, `verify_chain()` from `audit.py`, remove `GET /api/audit/verify` route, simplify `_write_event` to direct insert without hash computation. Keep structured audit logging and async queue. (~40 lines removed from production, simplify `repo_audit` accordingly)
- [ ] Remove hash-chain from audit DB schema: drop `prev_hash` and `event_hash` columns from `audit_log` table migration, add a new migration to remove them if table exists
- [ ] Remove hash-chain tests: strip chain-related assertions from `tests/test_audit.py` (keep event logging tests)
- [ ] Simplify registry loader: remove `clear_cache()`, `_cache` global, and `registry_dir` override from `registry/__init__.py`. Load once at import time. For tests, use monkeypatch on the loaded list directly

### Priority 2: Merge and stabilize current branch

- [ ] Merge connection testing framework branch (`feat/connection-testing-framework`) into main via PR

### Priority 3: Core integration wiring (agentic plane only)

These wire integrations into the workspace runtime so agents can use MCP tools during remediation.

- [ ] Integrations page: connection status indicators and test-from-UI flow (uses existing health monitor + connection testers)
- [ ] Finding normalization pipeline (raw source -> normalized Finding). Start with Wiz format, keep it simple — a single `normalize(source, raw_data) -> Finding` function, not an abstract pipeline
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

## Cross-cutting

- [ ] ADR for agent execution model (if Phase 6b approach warrants one)
