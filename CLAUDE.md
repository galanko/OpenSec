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
| AI Engine | OpenCode (Go) — Git submodule | `engine/opencode/` |
| Database | SQLite (single file) | `data/opensec.db` |
| Deployment | Single Docker container, port 8000 | `docker/` |

See `docs/architecture/overview.md` for the full system diagram.

## Repository Layout

```
backend/          FastAPI app — API routes, domain models, adapters, agents, orchestrator
frontend/         React SPA — pages, components, API client
engine/opencode/  OpenCode Git submodule (AI runtime engine)
docker/           Dockerfile, docker-compose, supervisord config
docs/
  adr/            Architecture Decision Records (numbered, immutable once accepted)
  architecture/   System diagrams, domain model, adapter specs, agent pipeline
  guides/         Developer setup, Docker build, adding adapters
  api/            Auto-generated API docs (future)
scripts/          Build, dev, seed, and migration scripts
fixtures/         Mock/demo data for adapters
tests/            Cross-stack integration tests
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
# Backend
cd backend && uv run uvicorn opensec.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Docker (full stack)
docker compose up --build

# Tests
cd backend && uv run pytest
cd frontend && npm test
```

## Development Conventions

- **ADRs:** Every architectural decision gets a record in `docs/adr/`. Use the template in `docs/adr/README.md`
- **Adapters:** Mock-first. Real integrations implement the same interface. See `docs/architecture/adapter-interfaces.md`
- **Agent output rule:** Every agent result must persist into both the chat timeline AND the SidebarState. Never only chat
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)
- **Python style:** ruff for linting/formatting, strict type hints, Pydantic models
- **TypeScript style:** ESLint + Prettier, strict mode
- **Interaction grammar:** Every user action follows `ask -> run -> summarize -> persist -> decide next`

## Current Phase

See `ROADMAP.md` — currently in **Phase 0: Decisions & Setup**.
