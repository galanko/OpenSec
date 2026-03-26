# OpenSec Roadmap

> **Convention:** Every phase must have automated tests passing before it is considered complete. Run `cd backend && uv run pytest -v` and `cd backend && uv run ruff check opensec/ tests/` before marking a phase done.

## Phase 0: Decisions & Setup (Complete)

Lock the MVP boundaries before writing code.

- [x] Define MVP scope (vulnerability remediation copilot, single-user, self-hosted)
- [x] Lock technical decisions (FastAPI, React+Vite, SQLite, OpenCode, Docker)
- [x] Create repository structure
- [x] Write Architecture Decision Records (ADRs)
- [x] Document domain model, adapter interfaces, and agent pipeline
- [x] Write ROADMAP.md

**Exit criteria:** A new contributor can read the docs and understand what to build, how, and why.

---

## Phase 1: OpenCode Spike (Complete)

Prove the OpenCode engine works behind a browser chat.

- [x] Pin OpenCode version (`.opencode-version`) and create download script
- [x] Create OpenCode project config (`opencode.json`) and custom agent
- [x] Create FastAPI backend skeleton with OpenCode process manager
- [x] Implement OpenCode HTTP client (sessions, messages, streaming)
- [x] Implement API routes (health, sessions, chat with SSE)
- [x] Create minimal React frontend spike (chat UI with SSE consumer)
- [x] Create dev runner script (`scripts/dev.sh`)
- [x] Update ADR-0001 (submodule → binary dependency)
- [x] Manual validation: health, session create, session list via curl
- [x] Backend test suite (28 tests): config, models, engine client, process, routes
- [x] Lint clean (ruff check passes)
- [x] End-to-end tests (10 tests): health, sessions, chat, error handling with real OpenCode

**Exit criteria:** One minimal web page can start an OpenCode session, send a prompt, and stream the response back.

---

## Phase 2: App Shell (Complete)

Create the product frame — all five pages as navigable shells.

- [x] Initialize React + Vite + Tailwind project in `frontend/`
- [x] Add routing for Queue / Workspace / History / Integrations / Settings
- [x] Create app layout (nav, top bar, content area)
- [x] Add global design tokens and shared component primitives
- [x] Create base API client (TanStack Query + fetch)
- [x] Add markdown rendering system for result cards
- [x] Create page shells with Stitch-matching UI (populated with demo data)
- [x] Set up dev proxy (Vite -> FastAPI)
- [x] Adopt Stitch design system "Serene Sentinel" (ADR-0011)
- [x] Lint clean + build passes

**Exit criteria:** All five pages exist as shells. App is navigable. Theme is coherent.

---

# Stages 1–4: Parallel Execution Plan

> Phases 0–2 were sequential. From here on, work is organized into **stages** that maximize parallelism. Within each stage, tracks run concurrently. A stage completes when all its tracks are done.

```
Stage 1:  Phase 3 ──────────────┐
          Phase 6a (agents) ─────┤  (parallel — no deps between them)
          Phase 9a (docker) ─────┘
                                 │
Stage 2:  Phase 4 (Queue) ──────┤
          Phase 5 (Workspace) ───┤  (parallel — all need Phase 3 only)
          Phase 8 (History) ─────┘
                                 │
Stage 3:  Phase 6b (orchestr.) ──┤  (needs Phase 5)
          Phase 7 (Tickets) ─────┘  (needs Phase 6b)
                                 │
Stage 4:  Phase 9b (ship) ───────┘  (needs everything)
```

**Critical path:** Phase 3 → Phase 5 → Phase 6b → Phase 7 → Phase 9b

---

## Stage 1: Foundation

Three parallel tracks with no dependencies between them. Stage 2 is blocked until all three complete.

### Phase 3: Persistence & Domain Model

Make the product stateful. Full vertical slice — backend schema, APIs, and tests.

- [ ] Set up SQLite with WAL mode
- [ ] Create migration system (numbered SQL scripts)
- [ ] Implement schema for all entities (Finding, Workspace, Message, AgentRun, SidebarState, TicketLink, ValidationResult, AppSetting, IntegrationConfig)
- [ ] Implement Finding CRUD API endpoints
- [ ] Implement Workspace CRUD API endpoints
- [ ] Implement Message storage and retrieval
- [ ] Implement AgentRun storage
- [ ] Implement SidebarState persistence
- [ ] Tests for all CRUD endpoints

**Exit criteria:** Reloading the app preserves all state. All CRUD endpoints tested.

### Phase 6a: Agent Definitions

Define the five cyber sub-agents. No code dependencies — just configs and prompts.

- [ ] Define OpenCode agent configs for all 5 sub-agents (`.opencode/agents/`)
- [ ] Define I/O contracts (input schema, output schema, sidebar field mapping)
- [ ] Write agent prompts for Finding Enricher, Owner Resolver, Exposure Analyzer, Remediation Planner, Validation Checker

**Exit criteria:** All 5 agent configs exist with documented I/O contracts.

### Phase 9a: Docker Skeleton

Build the container infrastructure. No dependency on app features.

- [ ] Multi-stage Dockerfile (Node build -> Python + Go runtime)
- [ ] Supervisord config for FastAPI + OpenCode processes
- [ ] Docker Compose example with volume mounts
- [ ] Environment variable handling (ports, data dir, model config)
- [ ] Health check endpoint integration (`/health`)

**Exit criteria:** `docker compose up` builds and starts the app (feature-incomplete is fine).

---

## Stage 2: Features

Three full vertical slices (backend + frontend + wiring) that run in parallel. All depend on Phase 3 only.

### Phase 4: Queue

First usable page — the entry point for remediation work.

- [ ] Findings list/table with columns: title, severity, asset, owner, status, updated
- [ ] Filtering by severity, status, source
- [ ] Search by title, asset, CVE
- [ ] Sort by severity, updated, status
- [ ] "Solve" button creates/opens a Workspace for the Finding
- [ ] Status badges and severity indicators
- [ ] Data from FindingSource fixture adapter
- [ ] "Why this matters" preview on hover/expand

**Exit criteria:** User can land on Queue, browse findings, and open one into a Workspace. All backed by real APIs.

### Phase 5: Solve Workspace v1

The product center — chat-led remediation with persistent structured state.

- [ ] Workspace page layout: top bar + center chat + right sidebar
- [ ] Top bar: finding title, severity badge, status, action buttons
- [ ] Chat thread: message list with user/assistant/agent roles
- [ ] Chat input with send button
- [ ] Suggested action chips ("Enrich finding", "Find owner", "Build plan")
- [ ] Agent run cards (running state, spinner, status)
- [ ] Markdown result cards for agent outputs
- [ ] Persistent sidebar: Summary, Evidence, Owner, Plan, Definition of Done, Ticket, Validation
- [ ] Sidebar auto-updates after each agent run
- [ ] Activity timeline (chronological list of actions)
- [ ] Connect chat to OpenCode via FastAPI orchestrator

**Exit criteria:** User can run at least one agent from chat, see the running state, get results, and see sidebar update. All state persisted.

### Phase 8: History

Turn completed work into searchable, reusable memory.

- [ ] History page with list of completed Workspaces
- [ ] Filter: open vs completed, by finding, asset, owner, date range
- [ ] Search across finding titles, agents used, outcomes
- [ ] Summary card per workspace (finding, outcome, agents run, ticket)
- [ ] Full chat replay for any past workspace
- [ ] Reopen a past workspace for continued work
- [ ] Export workspace summary as markdown

**Exit criteria:** Completed work is searchable and readable. Past workspaces can be reopened. All backed by real APIs.

---

## Stage 3: Agent Integration & Tickets

Sequential within this stage — Phase 6b first, then Phase 7. Depends on Stage 2 (specifically Phase 5).

### Phase 6b: Agent Orchestration

Wire the agent definitions from Phase 6a into the workspace from Phase 5.

- [ ] Implement Finding Enricher (sidebar update, chat output)
- [ ] Implement Owner Resolver
- [ ] Implement Exposure/Context Analyzer
- [ ] Implement Remediation Planner
- [ ] Implement Validation Checker
- [ ] Build orchestrator logic ("what should we do next?")
- [ ] Handle missing data gracefully (agent suggests what's needed)
- [ ] Support rerun / retry / cancel for agent runs
- [ ] End-to-end test: finding -> enrichment -> owner -> plan -> validation

**Exit criteria:** A single finding can flow through all five agents and reach validated closure.

### Phase 7: Ticket Workflow

Turn remediation plans into actionable tickets. Depends on Phase 6b (needs agent output).

- [ ] Ticket preview panel in Workspace sidebar
- [ ] "Create ticket" action using mock Ticketing adapter
- [ ] "Update ticket" action for status changes
- [ ] Ticket state visible in sidebar (key, status, assignee, link)
- [ ] Close/reopen logic tied to ticket + validation state
- [ ] Link ticket into History entries
- [ ] Request approval placeholder (for future enterprise edition)

**Exit criteria:** Workspace can produce a ticket draft, create it (mock), and reference it during closure.

---

## Stage 4: Polish & Ship

Final packaging. Depends on everything above.

### Phase 9b: Packaging Finalization

- [ ] Startup migration runner
- [ ] Seed demo data mode (`OPENSEC_DEMO=true`)
- [ ] Install documentation
- [ ] Upgrade documentation
- [ ] First tagged release (v0.1.0-alpha)

**Exit criteria:** `docker run -p 8000:8000 opensec` starts the full app. Demo data works. Config survives restart.

---

## Future (Post-MVP)

These are explicitly **not in the MVP** but are on the horizon:

- Multi-user / team edition with RBAC
- SSO / enterprise authentication
- Real adapter integrations (Tenable, Wiz, Snyk, Jira, ServiceNow, GitHub)
- Webhook-driven finding ingestion (push, not just pull)
- Scheduled scanning and auto-triage
- Plugin system for custom agents
- Approval workflows for enterprise compliance
- PostgreSQL support for larger deployments
- Cloud SaaS edition
