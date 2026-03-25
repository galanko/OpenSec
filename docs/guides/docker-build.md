# Docker Build Guide

> This guide will be updated when the Dockerfile is created in Phase 9.

## Overview

OpenSec ships as a single Docker container that bundles:

- FastAPI backend (Python)
- Built frontend (static files)
- OpenCode server (Go binary)
- SQLite database (on a mounted volume)

## Build

```bash
docker build -t opensec .
```

## Run

```bash
docker run -p 8000:8000 -v opensec-data:/data opensec
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENSEC_PORT` | `8000` | Public port for the web UI and API |
| `OPENSEC_DATA_DIR` | `/data` | Directory for SQLite database and config |
| `OPENCODE_PORT` | `4096` | Internal port for OpenCode server |

## Volumes

| Mount | Purpose |
|-------|---------|
| `/data` | SQLite database, config files, uploaded fixtures |

## Health Check

```bash
curl http://localhost:8000/health
```
