# OpenSec

A free, self-hosted cybersecurity remediation copilot.

OpenSec helps security teams take vulnerability findings from "raw scanner output" to "validated, closed remediation" — using AI agents to enrich context, identify owners, plan fixes, manage tickets, and confirm closure.

Built on the [OpenCode](https://github.com/anomalyco/opencode) engine. Open source. MIT licensed.

## How It Works

1. **Queue** — Import findings from your vulnerability scanners. Triage and prioritize.
2. **Workspace** — Open a finding and work it with an AI copilot. Chat to steer, agents do the heavy lifting.
3. **Agents** — Automated enrichment, owner resolution, exposure analysis, remediation planning, and fix validation.
4. **Tickets** — Draft and create tickets in your project management tool directly from the workspace.
5. **History** — Full audit trail of every remediation session. Replay, search, learn.

## Architecture

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite + Tailwind |
| Backend | FastAPI (Python 3.11+) |
| AI Engine | OpenCode (Go) |
| Database | SQLite |
| Deployment | Single Docker container, port 8000 |

See [docs/architecture/overview.md](docs/architecture/overview.md) for the full system diagram.

## Quick Start

> Coming soon — the project is currently in Phase 0 (planning and architecture). See the [Roadmap](ROADMAP.md).

```bash
docker run -p 8000:8000 -v opensec-data:/data ghcr.io/galanko/opensec:latest
```

Open [http://localhost:8000](http://localhost:8000)

## Development

See [docs/guides/development-setup.md](docs/guides/development-setup.md) for local setup instructions.

```bash
git clone --recurse-submodules https://github.com/galanko/OpenSec.git
cd OpenSec
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the phased development plan.

## Architecture Decisions

All significant decisions are recorded as ADRs in [docs/adr/](docs/adr/).

## Contributing

See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
