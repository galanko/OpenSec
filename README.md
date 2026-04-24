<!--
  README visual asset checklist — see also docs/README-assets-todo.md
  [ ] Logo / wordmark at docs/assets/brand/opensec-logo.svg (light) + -dark.svg — 240×64
  [ ] Social/OG card at docs/assets/brand/og-card.png — 1280×640
  [ ] Real hero screenshot at docs/assets/screenshots/hero-workspace.png
       (currently using frontend/mockups/screenshots/workspace.png as placeholder)
  [ ] Hero demo GIF at docs/assets/screenshots/hero-demo.gif — 30–60s workspace walkthrough
  [ ] "Earn the Badge" preview SVG at docs/assets/brand/badge-preview.svg
  [ ] Live demo URL at demo.opensec.dev (remove "(coming soon)" when live)
-->

<div align="center">

<img src="frontend/public/favicon.svg" alt="OpenSec" width="80" />

# OpenSec

**Your security team, in chat.**

Self-hosted, open-source AI copilot for vulnerability remediation — built for OSS maintainers who want their repo to earn the badge.

[![License: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-4d44e3.svg)](LICENSE)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-f59e0b.svg)](#status--roadmap)
[![Backend CI](https://github.com/galanko/OpenSec/actions/workflows/backend.yml/badge.svg?branch=main)](https://github.com/galanko/OpenSec/actions/workflows/backend.yml)
[![Frontend CI](https://github.com/galanko/OpenSec/actions/workflows/frontend.yml/badge.svg?branch=main)](https://github.com/galanko/OpenSec/actions/workflows/frontend.yml)
[![Built on OpenCode](https://img.shields.io/badge/built_on-OpenCode-2b3437.svg)](https://github.com/anomalyco/opencode)
[![GitHub Discussions](https://img.shields.io/github/discussions/galanko/OpenSec)](https://github.com/galanko/OpenSec/discussions)
[![GitHub stars](https://img.shields.io/github/stars/galanko/OpenSec?style=social)](https://github.com/galanko/OpenSec/stargazers)

[Quick start](#quick-start) · [How it works](#how-it-works) · [Earn the badge](#earn-the-badge) · [Docs](docs/architecture/overview.md) · [Roadmap](ROADMAP.md)

</div>

> **⚠️ OpenSec is in alpha.** Single-user community edition, currently in **Stage 3** of the roadmap (agent orchestration + ticketing). Expect rough edges, breaking changes, and missing adapters. Issues and PRs welcome — see [ROADMAP.md](ROADMAP.md).

<p align="center">
  <img src="frontend/mockups/screenshots/workspace.png" alt="OpenSec Workspace — chat-led vulnerability remediation" width="900" />
</p>

---

## What is OpenSec?

OpenSec is a self-hosted, chat-led cybersecurity remediation copilot — think **Claude Code, but for the security team**.

You drop in a vulnerability finding (from Snyk, Trivy, a CSV, or your own scanner) and OpenSec gives you a workspace where AI sub-agents enrich context, identify owners, build a fix plan, draft tickets, and confirm closure. You steer from a single chat. The product keeps structured state — summary, evidence, owner, plan, definition of done, ticket, validation — so nothing gets lost.

Built on the [OpenCode](https://github.com/anomalyco/opencode) engine. AGPL-3.0 licensed. Runs in a single Docker container.

---

## Sources × Actions

OpenSec is built around two axes. **Pull findings from anywhere. Take every action a security engineer would.**

<table>
<tr>
<th>Finding sources</th>
<th>Remediation actions</th>
</tr>
<tr>
<td valign="top">

- [x] CSV / JSON / Markdown imports
- [x] Demo fixture adapter
- [ ] Snyk
- [ ] Trivy
- [ ] GitHub Advanced Security
- [ ] Custom sources via `FindingSource` interface

</td>
<td valign="top">

- [x] **Enrich** — CVE details, severity, exploit maturity
- [x] **Resolve owner** — team/person with evidence
- [x] **Analyze exposure** — reachability, environment, blast radius
- [x] **Plan the fix** — steps, mitigations, definition of done
- [ ] **Draft the ticket** — Jira / GitHub issue with full context
- [x] **Validate** — confirm closure, recommend close or reopen

</td>
</tr>
</table>

Every action flows through chat and persists into structured sidebar state. Nothing lives only as chat text.

---

## Demo

Live hosted demo coming soon at `demo.opensec.dev`. Until then, spin it up locally in under two minutes — see [Quick start](#quick-start).

---

## Quick start

The fastest way to try OpenSec is Docker Compose.

### Prerequisites

- Docker and Docker Compose
- An LLM API key — `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`

### Run it

```bash
git clone https://github.com/galanko/OpenSec.git
cd OpenSec

# Set your LLM API key
export ANTHROPIC_API_KEY=sk-ant-...

# Start the full stack
docker compose -f docker/docker-compose.yml up
```

Open [http://localhost:8000](http://localhost:8000) and OpenSec is ready.

> A published image on GHCR (`ghcr.io/galanko/opensec`) and a one-line install will land with the **v0.1.0-alpha** tag — see [Stage 4](ROADMAP.md#stage-4-polish--ship).

<details>
<summary><strong>Run from source (for development)</strong></summary>

Use this if you want to hack on OpenSec itself.

**Prerequisites:** Python 3.11+ with [uv](https://docs.astral.sh/uv/), Node.js 20+, an LLM API key.

```bash
git clone https://github.com/galanko/OpenSec.git
cd OpenSec

# Backend deps
cd backend && uv sync --extra dev && cd ..

# Frontend deps
cd frontend && npm install && cd ..

# Install the pinned OpenCode binary
scripts/install-opencode.sh

# Start backend + frontend together
scripts/dev.sh
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api/*` to FastAPI on port 8000.

Full walkthrough: [`docs/guides/development-setup.md`](docs/guides/development-setup.md).

</details>

### Your first remediation

1. **Queue** — Import findings (CSV, demo fixture, or your scanner's JSON export)
2. **Solve** — Click a finding. Chat with your copilot. Let the sub-agents do the heavy lifting.
3. **History** — Review closed workspaces, replay chats, reopen work.

---

## How it works

```mermaid
graph LR
    Queue[Findings queue]
    WS[Workspace chat]
    Agents[Sub-agents]
    State[Sidebar state]
    Ticket[Ticket draft]
    Close[Validated close]

    Queue -->|Solve| WS
    WS -->|You steer| Agents
    Agents -->|Enrich · Resolve · Plan · Validate| State
    State -->|Plan ready| Ticket
    Ticket -->|Fix shipped| Close
```

Each workspace runs in an **isolated environment** — its own OpenCode process, its own directory on disk, its own finding-specific context. Five sub-agents take the finding from raw to closed:

| Agent | Does what | Updates |
|-------|-----------|---------|
| Finding Enricher | CVE details, severity, exploit info | `summary`, `evidence` |
| Owner Resolver | Team / person identification with evidence | `owner` |
| Exposure Analyzer | Reachability, environment, criticality | `evidence` |
| Remediation Planner | Fix plan, mitigations, definition of done | `plan` |
| Validation Checker | Confirms fix, recommends close or reopen | `validation` |

See [`docs/architecture/overview.md`](docs/architecture/overview.md) and [`docs/architecture/agent-pipeline.md`](docs/architecture/agent-pipeline.md) for the full walkthrough.

---

## Features

### Today (v0.x alpha)

- [x] **Findings queue** — import, filter, sort, triage
- [x] **Chat-led workspace** — persistent chat + structured sidebar per finding
- [x] **5 sub-agents** — enricher, owner, exposure, planner, validator
- [x] **Isolated per-workspace runtime** — each finding gets its own OpenCode process and context ([ADR-0014](docs/adr/))
- [x] **History replay** — every remediation session is searchable and re-openable
- [x] **Mock-first adapters** — every integration ships with a working fixture
- [x] **Single-container Docker** — one `docker compose up` and you're live
- [x] **Serene Sentinel design system** — calm, editorial, light-mode-first

### On deck

- [ ] Real ticket creation — Jira, GitHub Issues (Phase 7)
- [ ] Permission-approval UX for agent tool use (Phase 6b)
- [ ] `v0.1.0-alpha` tag + published GHCR image (Phase 9b)

### Post-MVP

- Real adapters — Tenable, Wiz, Snyk, ServiceNow, GitHub
- Webhook-driven ingestion (push, not just pull)
- Scheduled scans and auto-triage
- The **Earn the Badge** assessment engine (see below)

Full plan in [ROADMAP.md](ROADMAP.md).

---

## Earn the badge

OpenSec has a bigger story. Our V1.1 goal: **give OSS maintainers a security badge their users can trust.**

Run OpenSec against your repo. It runs a posture assessment — dependencies (via OSV.dev), secrets, config, GitHub posture, maintainer attack surface. You get a letter grade A–F and a badge SVG to drop in your README:

```md
[![OpenSec · A](https://opensec.dev/badge/your-repo.svg)](https://opensec.dev/assessment/your-repo)
```

Anyone hovering the badge sees what was checked, when, and by whom. Downstream users get a signal they can rely on. Maintainers get a free posture audit that ships as a trust artifact.

**Shipping in V1.1.** Track progress on the [roadmap](ROADMAP.md).

---

## Architecture

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite + Tailwind |
| Backend | FastAPI (Python 3.11+) |
| AI engine | [OpenCode](https://github.com/anomalyco/opencode) — Go binary, pinned in `.opencode-version` |
| Workspace runtime | Per-workspace isolated OpenCode processes ([ADR-0014](docs/adr/)) |
| Database | SQLite (single file, WAL mode) |
| Deployment | Single Docker container, port 8000 |

Full system diagram: [`docs/architecture/overview.md`](docs/architecture/overview.md). Every significant decision is captured as an ADR in [`docs/adr/`](docs/adr/).

---

## Status & roadmap

| Stage | What | Status |
|-------|------|--------|
| Stage 1 | Foundation — persistence, agents, docker skeleton | Complete |
| Stage 2 | Features — queue, workspace, history | Complete |
| **Stage 3** | **Agent orchestration + tickets** | **In progress** |
| Stage 4 | Polish & ship (`v0.1.0-alpha`) | Pending |

Full phase breakdown in [ROADMAP.md](ROADMAP.md). Architecture decisions in [`docs/adr/`](docs/adr/).

---

## Documentation

- [Architecture overview](docs/architecture/overview.md)
- [Domain model](docs/architecture/domain-model.md)
- [Agent pipeline](docs/architecture/agent-pipeline.md)
- [Adapter interfaces](docs/architecture/adapter-interfaces.md)
- [Adding an adapter](docs/guides/adding-an-adapter.md)
- [Docker build guide](docs/guides/docker-build.md)
- [All architecture decisions (ADRs)](docs/adr/)

---

## Community & contributing

OpenSec is early and ambitious. The best contributions right now:

- **Write an adapter** — see [`docs/guides/adding-an-adapter.md`](docs/guides/adding-an-adapter.md)
- **Try it and report what broke** — [open an issue](https://github.com/galanko/OpenSec/issues/new) or start a discussion
- **Improve the docs** — the best PRs are the ones a newcomer would have wanted
- **Star the repo** if you want to see this built faster

Full contributing guide: [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md). Ground rules: conventional commits, tests with every phase, no direct pushes to `main`.

---

## Security

Found a vulnerability in OpenSec itself? Please don't open a public issue. Email security reports to `galank@gmail.com` with `[OpenSec Security]` in the subject line. We'll respond within 72 hours.

---

## License

OpenSec is licensed under [AGPL-3.0](LICENSE). In plain English:

- You can self-host OpenSec in your company
- You can fork, modify, and redistribute
- If you offer OpenSec as a hosted service, your modifications must be open-sourced
- A commercial license for enterprise features is on the roadmap

See [LICENSE](LICENSE) for the full text.

---

<div align="center">
  <sub>Built by <a href="https://github.com/galanko">@galanko</a> — because security should feel like shipping, not filing tickets.</sub>
</div>
