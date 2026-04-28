# Changelog

All notable changes to OpenSec are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **One-line installer** (`scripts/install.sh`) — `curl -fsSL ...install.sh | sh`
  bootstraps `~/opensec/`, generates `OPENSEC_CREDENTIAL_KEY`, prompts
  for an LLM API key, and runs `docker compose up -d` against the
  release image. Re-run any time to upgrade.
- **Docker boot smoke test** (`backend/tests/docker/test_docker_install.py`)
  using testcontainers — pulls the just-built image, boots it with stub
  credentials, and asserts `/health` reaches 200 within 90s. Wired into
  the release pipeline so a "builds-but-doesn't-start" regression
  blocks publish.
- **Platform-specific install notes** in [docs/install.md](docs/install.md)
  for Linux (SELinux, rootless), macOS Docker Desktop, and Windows WSL2.
- README troubleshooting table covering port conflicts, image pull
  failures, restart loops, and host bind-mount permissions.

### Changed

- `docker/docker-compose.yml` now resolves the image tag via
  `${OPENSEC_VERSION:-latest}` instead of hardcoding `0.1.0-alpha`.
  Existing users: set `OPENSEC_VERSION=0.1.0-alpha` in `.env` to pin.
- `docs/guides/docker-build.md` rewritten — was a "Phase 9 placeholder"
  stub, now documents the local-build path for contributors and points
  end users at [docs/install.md](docs/install.md).
- The release pipeline now uploads `install.sh`, `docker-compose.yml`,
  and `.env.example` as release assets, so
  `/releases/latest/download/install.sh` resolves the curl one-liner.

## [0.1.0-alpha] - 2026-04-28

First public alpha release of OpenSec — a self-hosted, single-container,
chat-led cybersecurity remediation copilot. The image is published to
`ghcr.io/galanko/opensec` and is signed via Sigstore keyless OIDC with
SLSA build provenance and a CycloneDX SBOM attestation.

### Added

- **Findings queue** — import (CSV/JSON/Markdown), filter, sort, triage.
- **Chat-led workspace** — persistent chat per finding with structured
  sidebar state (summary, evidence, owner, plan, ticket, validation).
- **Five sub-agents** — Finding Enricher, Owner Resolver, Exposure
  Analyzer, Remediation Planner, Validation Checker. Each agent's output
  persists into both the chat timeline and the SidebarState.
- **Isolated per-workspace runtime** — every workspace gets its own
  directory, finding-specific context, and dedicated OpenCode process
  on a port from the 4100–4199 pool (ADR-0014).
- **History** — searchable, replayable record of every remediation
  session.
- **Single-container Docker image** — multi-stage build with frontend,
  backend, OpenCode, Trivy, Semgrep, and `gh` CLI bundled. Runs on
  `linux/amd64` and `linux/arm64`.
- **Mock-first adapters** — every integration ships with a working
  fixture; real integrations slot into the same interface.
- **Serene Sentinel design system** — calm, editorial, light-mode-first.
- **Security assessment v2** — dashboard payload (ADR-0032) with
  unified findings model from Trivy + Semgrep subprocess execution
  (ADR-0028).

### Security

- **Image runs as non-root user** `opensec` (UID 10001) by default.
- **Image signing** — every published image is signed via Sigstore
  keyless OIDC. Verify with `cosign verify` (see
  [docs/verify-release.md](docs/verify-release.md)).
- **SLSA build provenance** — attached as an attestation. Verify with
  `gh attestation verify oci://ghcr.io/galanko/opensec:0.1.0-alpha
  --owner galanko`.
- **CycloneDX SBOM** — attached both as a Sigstore attestation and as
  a release asset for download.
- **Trivy CVE gate at release** — CRITICAL severities block the
  release; HIGH+CRITICAL are uploaded as SARIF to the GitHub Security
  tab.
- **GitHub Environment gate** — every publish requires reviewer
  approval before any push to `ghcr.io`.
- **All third-party GitHub Actions are SHA-pinned** — Dependabot keeps
  them current.
- **Tag protection** on `v*` prevents accidental tag creation.

### Known limitations (alpha)

- Adapters: only CSV / JSON / Markdown imports and the demo fixture
  are wired today. Real adapters (Snyk, GitHub Advanced Security,
  Tenable, Wiz, ServiceNow) are post-MVP — see [ROADMAP.md](ROADMAP.md).
- Single-user only. No multi-tenant authentication.
- Existing `opensec_data` volumes from pre-alpha dev builds are
  root-owned and will not be writable by the new non-root container.
  One-line migration:
  `docker run --rm --user 0 -v opensec_data:/data alpine chown -R 10001:10001 /data`.

[Unreleased]: https://github.com/galanko/OpenSec/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/galanko/OpenSec/releases/tag/v0.1.0-alpha
