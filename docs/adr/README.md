# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for OpenSec.

ADRs document significant architectural decisions made during the project. Once accepted, they are immutable records of why a decision was made at a point in time. If a decision is reversed, a new ADR supersedes the old one.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](0001-opencode-engine-integration.md) | Use OpenCode as the AI engine (binary dependency) | Accepted |
| [0002](0002-fastapi-backend.md) | FastAPI for the backend | Accepted |
| [0003](0003-react-vite-tailwind-frontend.md) | React + TypeScript + Vite + Tailwind for the frontend | Accepted |
| [0004](0004-sqlite-persistence.md) | SQLite for persistence | Accepted |
| [0005](0005-single-docker-container.md) | Single Docker container deployment | Accepted |
| [0006](0006-mock-first-adapters.md) | Mock-first adapter integration strategy | Accepted |
| [0007](0007-domain-model.md) | Domain model design | Accepted |
| [0008](0008-sub-agent-architecture.md) | Sub-agent architecture | Accepted |
| [0009](0009-single-user-community-edition.md) | Single-user community edition | Accepted |
| [0010](0010-monorepo-structure.md) | Monorepo structure | Accepted |
| [0011](0011-stitch-design-system.md) | Stitch design system | Accepted |
| [0012](0012-runtime-settings-via-opencode-api.md) | Runtime settings via OpenCode API | Accepted |

## Template

Use this template when creating a new ADR:

```markdown
# ADR-NNNN: Title

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Deprecated | Superseded by [ADR-NNNN](link)

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?
```
