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

MVP — Agentic remediation (PRD-0001, IMPL-0001):

- [ ] **WP2: Repo access** — inject GH_TOKEN + OPENSEC_REPO_URL into workspace OpenCode process env from credential vault (ADR-0024). Agent handles clone/branch/push via bash
- [ ] **WP4: Pipeline update** — 4-agent MVP sequence (enricher → exposure → planner → executor), remove owner_resolver from defaults, update suggest_next()
- [ ] **WP5: Remediation executor agent** — new `remediation_executor.md.j2` template, tool-using conversational agent, output parser + sidebar mapper for PR data
- [ ] **WP5: PR creation** — agent pushes branch + creates draft PR via `gh pr create`, PR metadata in sidebar
- [ ] **WP6: Status flow** — auto-advance finding status after agent completions (new → triaged → in_progress → remediated → closed)

Phase 7 — Ticket workflow (depends on Phase 6b, deferred to post-MVP):

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

### Priority 5: Design system compliance (UX audit 2026-04-09)

Systematic violations found across 13 of 17 components. See `docs/design/specs/UX-000-current-state-audit.md` for full audit.

**P0 — Fix systematic violations (affects all pages):**

- [ ] Create `ghost-border` Tailwind utility: add `shadow-[0_0_0_1px_rgba(var(--outline-variant),0.15)]` to config. This replaces all `border` usage with the design system's ghost border pattern
- [ ] SideNav: replace `border-r border-outline-variant/20` with tonal bg shift, replace `border-r-2 border-primary` active indicator with background highlight (`bg-primary-container/30`)
- [ ] TopBar: replace `border-b-2 border-primary` active nav indicator with background highlight or box-shadow underline. Replace `bg-green-500` health dot with `bg-tertiary`
- [ ] ListCard: remove `border border-transparent` and `hover:border-primary/5`, rely on shadow-only hover
- [ ] WorkspaceSidebar: replace `border-l border-surface-container` with tonal bg shift, replace `border border-surface-container/50` section borders with spacing + background
- [ ] ActionChips: replace `border border-primary/10` with tonal background (`bg-primary-container/10`)
- [ ] ActionButton: replace `border border-outline-variant/30` (outline variant) with ghost-border utility or tonal bg
- [ ] ResultCard: replace 3 border instances (card, header divider, button area) with tonal layering
- [ ] AgentRunCard: replace 3 border instances across states, replace `bg-indigo-50/80`/`border-indigo-100` with `bg-primary-container/30`
- [ ] HistoryCard: replace state badge borders with bg-only badges, replace `text-green-700`/`bg-green-100`/`border-green-200` with `text-tertiary`/`bg-tertiary-container/30`
- [ ] HistoryDetail: replace `border-t border-surface-container/50` separator with spacing + tonal bg, replace `border border-surface-container/80` on message bubbles
- [ ] Replace all arbitrary green colors with `tertiary` tokens: grep `green-` in `frontend/src/` — affects ProviderSettings, IntegrationSettings, TopBar, HistoryCard
- [ ] Replace all arbitrary red colors with `error` tokens: grep `red-` in `frontend/src/` — affects IntegrationSettings

**P1 — Missing UX patterns (reliability and accessibility):**

- [ ] Create `ErrorState` component (like EmptyState but for API failures): icon, title, subtitle, retry button
- [ ] Add error boundaries to FindingsPage, HistoryPage, WorkspacePage, SettingsPage — catch render errors, show ErrorState
- [ ] Add `loading` prop to ActionButton: shows spinner, disables click during async
- [ ] Add `loading` prop to ActionChips: show spinner on the active chip while agent runs
- [ ] Add `focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2` to all interactive elements: ActionButton, ActionChips, ListCard, nav items, tabs
- [ ] Create `ConfirmDialog` component: modal with title, message, confirm/cancel buttons. Use for: resolve workspace, delete API key, delete integration

### Priority 6: Mockup drift fixes (UX audit 2026-04-09)

Closes gaps between Stitch mockups (`frontend/mockups/html/`) and current implementation. See `docs/design/specs/UX-000-current-state-audit.md`.

**History page (high drift):**

- [ ] Stats dashboard bento grid at top of History page: total resolved count, average time to fix, success rate — requires new API endpoint for workspace stats
- [ ] Pagination for history list (currently loads all, won't scale)
- [ ] Date range / calendar filter for history
- [ ] "Showing X of Y workspaces" counter text
- [ ] "Reuse Plan" button on HistoryCard — copy a past remediation plan into a new workspace

**Settings page (high drift):**

- [ ] Internal sidebar navigation: Model settings, Agent settings, Workspace defaults, App preferences — currently flat sections, mockup shows tabbed sidebar
- [ ] Agent settings section: threat hunting toggle, auto-remediation toggle, auto-update sidebar toggle
- [ ] Workspace defaults section: default action checkboxes (quarantine, notify admin, ignore low-risk, log only)
- [ ] App preferences section: language dropdown, notification channel checkboxes
- [ ] Save/Discard buttons fixed at page footer

**Findings page (medium drift):**

- [ ] "Sentinel Insights" right sidebar panel — contextual AI summary of findings state (e.g., "3 critical findings share the same CVE, consider batch remediation")
- [ ] Educational/promotional card ("Automated remediation is learning from your patterns")
- [ ] Blocked finding state with opacity/grayscale visual treatment

**Workspace page (low drift):**

- [ ] Structured agent result cards: replace raw markdown output with card-based results matching mockup — headers, confidence badges, evidence/recommendation sections
- [ ] Enhanced "Agent Running" card with animated dots + descriptive text

**Integrations page:**

- [ ] Create dedicated IntegrationsPage route (currently embedded in Settings) — mockup shows a standalone page with richer layout

### MVP — Frontend (PRD-0001, IMPL-0001):

- [x] **WP1: Docker first-run** — seed demo mode (OPENSEC_DEMO env var), `gh` CLI in Docker image
- [ ] **WP2: Repo settings UI** — RepoSettingsSection component (URL + PAT + test connection), "solve without repo" guard dialog
- [ ] **WP3: Import UX** — ImportDialog component (file upload + paste JSON tabs), ImportButton in toolbar, empty state with import CTA
- [ ] **WP7: Structured result cards** — EnricherResultCard, ExposureResultCard, PlannerResultCard, RemediationResultCard, ConfidenceBadge
- [ ] **WP7: Error handling** — ErrorState component, ErrorBoundary on all pages, API error states with retry
- [ ] **WP5: Plan approval card** — PlanApprovalCard component (approve/modify plan before executor runs)
- [ ] **WP5: PR display** — PRStatusBadge, sidebar "Pull request" section, PR link in FindingRow
- [ ] **WP6: Status badges** — status color progression per UX-0001, PR link icon in findings table
- [ ] **WP4: Suggest-next wiring** — highlight recommended action chip, SuggestedActionHighlight styling, chip states (default/suggested/running/completed/disabled)

### Priority 7: Findings page and UI gaps

- [ ] Findings page: search by title/asset/CVE (Phase 4 gap)
- [ ] Findings page: "Why this matters" preview on hover/expand (Phase 4 gap)
- [ ] Settings page: model/provider configuration improvements
- [x] Permission approval UI: SSE listener for `permission_request` events in WorkspacePage, approval card component (tool name, command patterns, approve/deny buttons), POST to `/api/workspaces/{id}/agent-runs/{run_id}/permission`. Backend plumbing done in Phase 6b PR #34. Also needs: flip workspace `opencode.json` from `"allow"` to `"ask"` for bash/edit

### Priority 8: Packaging (depends on Phase 6b + Phase 7 completion)

- [x] Startup migration runner
- [x] Seed demo data mode (`OPENSEC_DEMO=true`)
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
