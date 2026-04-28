# Changelog

All notable changes to OpenSec are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
