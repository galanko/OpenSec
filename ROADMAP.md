# OpenSec Roadmap

## Phase 0: Decisions & Setup (Current)

Lock the MVP boundaries before writing code.

- [x] Define MVP scope (vulnerability remediation copilot, single-user, self-hosted)
- [x] Lock technical decisions (FastAPI, React+Vite, SQLite, OpenCode, Docker)
- [x] Create repository structure
- [x] Write Architecture Decision Records (ADRs)
- [x] Document domain model, adapter interfaces, and agent pipeline
- [x] Write ROADMAP.md
- [ ] Create initial GitHub Issues for Phase 1

**Exit criteria:** A new contributor can read the docs and understand what to build, how, and why.

---

## Phase 1: Fork & OpenCode Spike

Prove the OpenCode engine works behind a browser chat.

- [ ] Add OpenCode as Git submodule in `engine/opencode/`
- [ ] Build and run OpenCode locally
- [ ] Identify session, agent, config, and model entry points in OpenCode
- [ ] Create minimal FastAPI app that starts OpenCode server as subprocess
- [ ] Prove a browser-triggered prompt creates an OpenCode-backed session
- [ ] Prove sub-agent invocation works via the REST API
- [ ] Prove partial response streaming works (SSE to browser)
- [ ] Map OpenCode config to future Settings UI

**Exit criteria:** One minimal web page can start an OpenCode session, send a prompt, and stream the response back.

---

## Phase 2: App Shell

Create the product frame — all five pages as navigable shells.

- [ ] Initialize React + Vite + Tailwind project in `frontend/`
- [ ] Add routing for Queue / Workspace / History / Integrations / Settings
- [ ] Create app layout (nav, top bar, content area)
- [ ] Add global design tokens and shared component primitives
- [ ] Create base API client (TanStack Query + fetch)
- [ ] Add markdown rendering system for result cards
- [ ] Add empty states for all pages
- [ ] Set up dev proxy (Vite -> FastAPI)

**Exit criteria:** All five pages exist as shells. App is navigable. Theme is coherent.

---

## Phase 3: Persistence & Domain Model

Make the product stateful.

- [ ] Set up SQLite with WAL mode
- [ ] Create migration system (numbered SQL scripts)
- [ ] Implement schema for all entities (Finding, Workspace, Message, AgentRun, SidebarState, TicketLink, ValidationResult, AppSetting, IntegrationConfig)
- [ ] Implement Finding CRUD API endpoints
- [ ] Implement Workspace CRUD API endpoints
- [ ] Implement Message storage and retrieval
- [ ] Implement AgentRun storage
- [ ] Implement SidebarState persistence
- [ ] Create seed fixture loader (demo findings + context data)

**Exit criteria:** Reloading the app preserves all state. Seed data loads correctly.

---

## Phase 4: Queue

First usable page — the entry point for remediation work.

- [ ] Findings list/table with columns: title, severity, asset, owner, status, updated
- [ ] Filtering by severity, status, source
- [ ] Search by title, asset, CVE
- [ ] Sort by severity, updated, status
- [ ] "Solve" button creates/opens a Workspace for the Finding
- [ ] Status badges and severity indicators
- [ ] Mock data from FindingSource fixture adapter
- [ ] "Why this matters" preview on hover/expand

**Exit criteria:** User can land on Queue, browse findings, and open one into a Workspace.

---

## Phase 5: Solve Workspace v1

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

**Exit criteria:** User can run at least one agent from chat, see the running state, get results, and see sidebar update.

---

## Phase 6: Core Cyber Sub-Agents

Support the full remediation user story with mock and partial real data.

- [ ] Define OpenCode agent configs for all 5 sub-agents
- [ ] Implement Finding Enricher (input/output contract, prompt, sidebar update)
- [ ] Implement Owner Resolver
- [ ] Implement Exposure/Context Analyzer
- [ ] Implement Remediation Planner
- [ ] Implement Validation Checker
- [ ] Build orchestrator logic ("what should we do next?")
- [ ] Handle missing data gracefully (agent suggests what's needed)
- [ ] Support rerun / retry / cancel for agent runs
- [ ] End-to-end test: finding -> enrichment -> owner -> plan -> validation with mock data

**Exit criteria:** A single finding can flow through all five agents and reach validated closure.

---

## Phase 7: Ticket Workflow

Turn remediation plans into actionable tickets.

- [ ] Ticket preview panel in Workspace sidebar
- [ ] "Create ticket" action using mock Ticketing adapter
- [ ] "Update ticket" action for status changes
- [ ] Ticket state visible in sidebar (key, status, assignee, link)
- [ ] Close/reopen logic tied to ticket + validation state
- [ ] Link ticket into History entries
- [ ] Request approval placeholder (for future enterprise edition)

**Exit criteria:** Workspace can produce a ticket draft, create it (mock), and reference it during closure.

---

## Phase 8: History

Turn completed work into searchable, reusable memory.

- [ ] History page with list of completed Workspaces
- [ ] Filter: open vs completed, by finding, asset, owner, date range
- [ ] Search across finding titles, agents used, outcomes
- [ ] Summary card per workspace (finding, outcome, agents run, ticket)
- [ ] Full chat replay for any past workspace
- [ ] Reopen a past workspace for continued work
- [ ] Export workspace summary as markdown

**Exit criteria:** Completed work is searchable and readable. Past workspaces can be reopened.

---

## Phase 9: Packaging & Release

Make it installable by real users.

- [ ] Multi-stage Dockerfile (Node build -> Python + Go runtime)
- [ ] Supervisord config for FastAPI + OpenCode processes
- [ ] Docker Compose example with volume mounts
- [ ] Environment variable handling (ports, data dir, model config)
- [ ] Health check endpoint (`/health`)
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
