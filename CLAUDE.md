# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

OpenSec is a self-hosted cybersecurity remediation copilot. It ingests vulnerability findings, enriches them with AI agents, and guides users through planning, ticketing, validating, and closing remediations — all from a chat-led web workspace.

Built on the [OpenCode](https://github.com/anomalyco/opencode) engine. Single-user community edition. MIT licensed.

## Architecture

| Layer | Technology | Location |
|-------|-----------|----------|
| Frontend | React + TypeScript + Vite + Tailwind | `frontend/` |
| Backend | FastAPI (Python 3.11+) | `backend/` |
| AI Engine | OpenCode (Go) — binary dependency, pinned in `.opencode-version` | managed subprocess |
| Database | SQLite (single file) | `data/opensec.db` |
| Deployment | Single Docker container, port 8000 | `docker/` |

See `docs/architecture/overview.md` for the full system diagram.

## Repository Layout

```
backend/              FastAPI app (Python)
  opensec/
    main.py           App entry point, lifespan, CORS
    config.py         Settings via env vars
    engine/           OpenCode integration (process manager + HTTP client)
    api/routes/       REST endpoints (health, sessions, chat)
frontend/             React SPA (TypeScript + Vite)
  src/
    pages/            Page components
    api/              API client
docker/               Dockerfile, docker-compose, supervisord config
docs/
  adr/                Architecture Decision Records
  architecture/       System diagrams, domain model, adapter specs, agent pipeline
  guides/             Developer setup, Docker build, adding adapters
scripts/              dev.sh, install-opencode.sh
fixtures/             Mock/demo data for adapters
tests/                Cross-stack integration tests
.opencode/agents/     Custom OpenCode agent definitions
.opencode-version     Pinned OpenCode version
opencode.json         OpenCode project config
```

## Key Domain Concepts

- **Finding** — A vulnerability from a scanner. Flows through: `new` -> `triaged` -> `in_progress` -> `remediated` -> `validated` -> `closed`
- **Workspace** — A remediation session for one Finding. Contains chat, agent runs, and structured sidebar state
- **AgentRun** — A single sub-agent execution (enricher, owner resolver, planner, etc.)
- **SidebarState** — Persistent structured context per workspace (summary, evidence, owner, plan, ticket, validation)
- **Adapter** — Interface to an external system. Four types: FindingSource, OwnershipContext, Ticketing, Validation

See `docs/architecture/domain-model.md` for entity details and state machines.

## Pages

| Page | Purpose |
|------|---------|
| Queue | List, filter, sort findings. "Solve" opens a Workspace |
| Workspace | Chat-led remediation with sidebar, agent cards, and actions |
| History | Browse completed workspaces, replay chats |
| Integrations | Configure adapter connections |
| Settings | Model/provider config, agent settings |

## Sub-Agents

1. **Finding Enricher** — CVE details, severity, exploit info -> updates `summary`, `evidence`
2. **Owner Resolver** — Team/person identification with evidence -> updates `owner`
3. **Exposure/Context Analyzer** — Reachability, environment, criticality -> updates `evidence`
4. **Remediation Planner** — Fix plan, mitigations, definition of done -> updates `plan`
5. **Validation Checker** — Confirms fix, recommends close/reopen -> updates `validation`

See `docs/architecture/agent-pipeline.md` for I/O contracts.

## Build & Development

### Prerequisites

- Python 3.11+ with uv
- Node.js 20+ with npm
- Docker (for containerized runs)

### Commands

```bash
# Full dev environment (backend + frontend)
scripts/dev.sh

# Backend only
cd backend && uv run uvicorn opensec.main:app --reload --port 8000

# Frontend only (needs backend running for API proxy)
cd frontend && npm run dev

# Install OpenCode binary (auto-downloads pinned version)
scripts/install-opencode.sh

# Tests
cd backend && uv run pytest
cd frontend && npm test
```

### How It Runs

1. FastAPI starts on port 8000 and launches OpenCode as a subprocess on port 4096 (internal)
2. Vite dev server starts on port 5173 and proxies `/api/*` to FastAPI
3. Browser talks to Vite (5173) in dev, or FastAPI (8000) in production
4. All OpenCode communication goes through FastAPI — frontend never talks to OpenCode directly

## Testing

Every phase must have tests passing before it is considered complete.

```bash
# Unit tests only (fast, no external deps)
cd backend && uv run pytest -v -m 'not e2e'

# E2E tests (needs OpenCode binary + OPENAI_API_KEY)
cd backend && uv run pytest tests/e2e/ -v

# All tests
cd backend && uv run pytest -v

# Lint
cd backend && uv run ruff check opensec/ tests/
```

### Unit tests (28, ~0.1s)

Mocked external dependencies — no real OpenCode needed:

- `test_config.py` — Settings and path resolution
- `test_models.py` — Pydantic model validation
- `test_engine_client.py` — OpenCode HTTP client (mocked httpx)
- `test_engine_process.py` — Subprocess lifecycle
- `test_routes_*.py` — API endpoint behavior with mocked engine

### E2E tests (10, ~12s)

Real OpenCode subprocess + real LLM calls. Skipped automatically if OpenCode binary or API key is missing:

- `e2e/test_health_e2e.py` — Health with real engine
- `e2e/test_session_flow.py` — Session create/list/get
- `e2e/test_chat_flow.py` — Send message, verify round-trip
- `e2e/test_error_handling.py` — Error cases

## Git Workflow

**Direct pushes to `main` are not allowed.** All changes must go through a pull request reviewed and merged by `@galanko`.

When working on any task, follow this workflow:

1. **Create a feature branch** from `main` with a descriptive name (e.g. `feat/add-adapter-api`, `fix/session-timeout`)
2. **Make changes and commit** using conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)
3. **Push the branch** to the remote (`git push -u origin <branch-name>`)
4. **Create a pull request** targeting `main`. Include a summary of changes and a test plan
5. **Wait for approval** — `@galanko` is the required code owner and must review and merge the PR. Do NOT merge pull requests yourself

Never commit directly to `main`. Never force-push to `main`. If tests or lint fail, fix them before requesting review.

## Development Conventions

- **ADRs:** Every architectural decision gets a record in `docs/adr/`. Use the template in `docs/adr/README.md`
- **Adapters:** Mock-first. Real integrations implement the same interface. See `docs/architecture/adapter-interfaces.md`
- **Agent output rule:** Every agent result must persist into both the chat timeline AND the SidebarState. Never only chat
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)
- **Python style:** ruff for linting/formatting, strict type hints, Pydantic models
- **TypeScript style:** ESLint + Prettier, strict mode
- **Interaction grammar:** Every user action follows `ask -> run -> summarize -> persist -> decide next`

## Current Phase

See `ROADMAP.md` — currently in **Phase 1: Fork & OpenCode Spike**.
