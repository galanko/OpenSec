# OpenSec

A free, self-hosted cybersecurity remediation copilot.

OpenSec helps security teams take vulnerability findings from "raw scanner output" to "validated, closed remediation" — using AI agents to enrich context, identify owners, plan fixes, manage tickets, and confirm closure.

Built on the [OpenCode](https://github.com/anomalyco/opencode) engine. Open source. AGPL-3.0 licensed.

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

## Quick Start (Development)

### Prerequisites

- Python 3.11+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- An LLM API key (e.g., `ANTHROPIC_API_KEY`)

### Run it

```bash
git clone https://github.com/galanko/OpenSec.git
cd OpenSec

# Install backend dependencies
cd backend && uv sync --extra dev && cd ..

# Install frontend dependencies
cd frontend && npm install && cd ..

# Start everything (backend + frontend)
scripts/dev.sh
```

Open [http://localhost:5173](http://localhost:5173)

The backend runs on port 8000 (with OpenCode engine on port 4096 internally). The frontend dev server on port 5173 proxies API calls to the backend.

### Run tests

```bash
cd backend && uv run pytest -v        # 28 tests
cd backend && uv run ruff check opensec/ tests/  # lint
```

### Docker (coming in Phase 9)

```bash
docker run -p 8000:8000 -v opensec-data:/data ghcr.io/galanko/opensec:latest
```

## Development

See [docs/guides/development-setup.md](docs/guides/development-setup.md) for full setup instructions.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the phased development plan.

## Architecture Decisions

All significant decisions are recorded as ADRs in [docs/adr/](docs/adr/).

## Contributing

See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

## License

AGPL-3.0 — see [LICENSE](LICENSE).
