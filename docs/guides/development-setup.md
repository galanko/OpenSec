# Development Setup

> This guide will be updated as the project tooling is established. Placeholder for Phase 1+.

## Prerequisites

- Python 3.11+ with [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Node.js 20+ with npm
- Docker (for containerized runs)
- Git (with submodule support)

## Clone

```bash
git clone --recurse-submodules https://github.com/galanko/OpenSec.git
cd OpenSec
```

## Backend

```bash
cd backend
uv sync               # install dependencies
uv run uvicorn opensec.main:app --reload --port 8000
```

## Frontend

```bash
cd frontend
npm install
npm run dev            # starts Vite dev server on port 5173
```

## Docker (full stack)

```bash
docker compose up --build
# App available at http://localhost:8000
```

## Running Tests

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm test
```
