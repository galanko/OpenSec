# OpenSec security findings — dogfooding report

**Date:** 2026-03-29
**Scanned by:** Automated tools + manual architecture review
**Target:** OpenSec v0.1.0 (commit: current main)

---

## How to read this document

Each finding follows the **OpenSec FindingSource format** so it can be ingested directly into the Queue via the Markdown adapter. Fields map to the `FindingCreate` Pydantic model.

---

<!-- finding:start -->
## OSSEC-001: API keys stored in plaintext in SQLite

- **source_type:** manual-review
- **source_id:** OSSEC-001
- **raw_severity:** high
- **normalized_priority:** P1
- **asset_id:** backend/opensec/engine/config_manager.py
- **asset_label:** Config Manager — API key storage
- **likely_owner:** backend
- **status:** new

### Description

API keys (OpenAI, Anthropic, etc.) are stored as plaintext JSON in the `app_setting` table (`api_key:{provider}` rows). The `config_manager.set_api_key()` method writes the raw key to SQLite without encryption. On startup, `restore_keys_to_engine()` reads these plaintext keys and injects them into OpenCode processes.

While this is a single-user self-hosted tool (ADR-0009), plaintext key storage means any SQLite file leak exposes all provider credentials. The database file (`data/opensec.db`) is also mounted as a Docker volume, making it accessible outside the container.

### Evidence

- `config_manager.py:93` — `await upsert_setting(db, f"api_key:{provider_id}", {"key": key, ...})`
- `config_manager.py:144` — `key = value.get("key")` reads plaintext on restore
- No encryption layer between user input and DB write

### Remediation hint

Encrypt API keys at rest using a local key derived from a machine-specific secret (e.g., `OPENSEC_ENCRYPTION_KEY` env var) or OS keyring. Use `cryptography.fernet` for symmetric encryption. Mask keys in all log output (already done for API responses).

### Why this matters

A database backup, accidental commit, or path traversal exploit would expose all configured LLM provider API keys. For a security tool, this is a trust-breaking issue.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-002: Jinja2 templates rendered with autoescape disabled

- **source_type:** bandit
- **source_id:** OSSEC-002
- **raw_severity:** high
- **normalized_priority:** P1
- **asset_id:** backend/opensec/agents/template_engine.py
- **asset_label:** Agent Template Engine
- **likely_owner:** backend
- **status:** new

### Description

The `AgentTemplateEngine` creates a Jinja2 `Environment` with `autoescape=False` (the default). Bandit flagged this as B701. While these templates render Markdown for agent prompts (not HTML served to browsers), a malicious finding payload injected via a FindingSource adapter could include Jinja2 template syntax that gets interpreted during rendering, potentially leading to Server-Side Template Injection (SSTI).

### Evidence

- `template_engine.py:56` — `self._env = jinja2.Environment(loader=jinja2.FileSystemLoader(...))`
- No `autoescape=True` or `select_autoescape()` call
- Finding data (from scanner payloads) flows into template variables

### Remediation hint

Set `autoescape=True` or use `jinja2.select_autoescape()`. Additionally, use `SandboxedEnvironment` instead of `Environment` to prevent SSTI from untrusted finding data. Validate/sanitize all template variables derived from external scanner payloads.

### Why this matters

If a malicious scanner payload contains `{{ config.__class__.__init__.__globals__ }}` or similar, it could leak server-side information or execute arbitrary code during template rendering.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-003: Docker container runs as root

- **source_type:** dockerfile-review
- **source_id:** OSSEC-003
- **raw_severity:** high
- **normalized_priority:** P1
- **asset_id:** docker/Dockerfile
- **asset_label:** Docker container runtime
- **likely_owner:** devops
- **status:** new

### Description

The Dockerfile has no `USER` directive. The application (FastAPI + OpenCode subprocess) runs as `root` inside the container. If an attacker achieves code execution (e.g., via SSTI in OSSEC-002 or a future RCE), they have full root privileges within the container, making container escape easier and giving access to all mounted volumes.

### Evidence

- `docker/Dockerfile` — no `USER` directive found
- `docker/entrypoint.sh` — runs as whatever user the container starts with (root by default)
- OpenCode subprocess also inherits root privileges

### Remediation hint

Add a non-root user and switch to it before the entrypoint:
```dockerfile
RUN useradd -r -s /bin/false opensec && chown -R opensec:opensec /app /data
USER opensec
```

### Why this matters

Running containers as root violates CIS Docker Benchmark 4.1 and is flagged by most container security scanners. For a security product, this undermines credibility.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-004: No authentication on any API endpoint

- **source_type:** manual-review
- **source_id:** OSSEC-004
- **raw_severity:** medium
- **normalized_priority:** P2
- **asset_id:** backend/opensec/api/routes/
- **asset_label:** All API routes
- **likely_owner:** backend
- **status:** new

### Description

All 10 API route modules have zero authentication or authorization. Any network-reachable client can create/delete findings, trigger agent runs, read/write API keys, and seed the database. While ADR-0009 explicitly scopes v1 as single-user, the app binds to `0.0.0.0` by default, meaning it's accessible from any network interface including LAN.

### Evidence

- No `Depends(authenticate)` or middleware on any router
- `config.py:25` — `app_host: str = "0.0.0.0"` (default listens on all interfaces)
- `settings.py:83-84` — `set_api_key` endpoint has no auth guard
- ADR-0009 acknowledges this as a known gap

### Remediation hint

For the single-user MVP: add a simple bearer token auth (`OPENSEC_API_TOKEN` env var) as middleware. Default to `127.0.0.1` binding instead of `0.0.0.0`. For the Docker deployment, add a reverse proxy (nginx/caddy) with basic auth or mTLS.

### Why this matters

Even on a home network, any device can access the API. Combined with OSSEC-001 (plaintext API keys), any LAN device could exfiltrate all stored credentials via `GET /api/settings/keys`.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-005: Dynamic SQL query construction in repository layer

- **source_type:** bandit
- **source_id:** OSSEC-005
- **raw_severity:** medium
- **normalized_priority:** P2
- **asset_id:** backend/opensec/db/
- **asset_label:** Repository layer (finding, workspace, agent_run, integration)
- **likely_owner:** backend
- **status:** new

### Description

Five instances of f-string SQL construction were flagged by Bandit (B608). While parameters are passed via `?` placeholders (preventing value injection), the column names in `SET` clauses and `WHERE` conditions are built from Pydantic model field names via `model_dump()`. If an attacker could influence the field names (unlikely with current Pydantic validation but possible if validation is loosened), this could allow SQL injection through column name manipulation.

### Evidence

- `repo_finding.py:121-124` — `set_clause = ", ".join(f"{k} = ?" for k in fields)` then `f"UPDATE finding SET {set_clause}..."`
- `repo_workspace.py:97-100` — same pattern
- `repo_agent_run.py:107` — same pattern
- `repo_integration.py:85-86` — same pattern
- `repo_finding.py:99-104` — dynamic WHERE clause

### Remediation hint

Use an allowlist of valid column names and validate against it before constructing queries. Alternatively, switch to a query builder (e.g., `sqlalchemy.text()` with bound parameters) that handles escaping. The `noqa: S608` comments suppress but don't fix the warnings.

### Why this matters

While Pydantic currently constrains field names, defense-in-depth requires the SQL layer to independently validate column names. A future code change could weaken the Pydantic layer without realizing the SQL layer depends on it.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-006: Path traversal partially mitigated in SPA fallback

- **source_type:** manual-review
- **source_id:** OSSEC-006
- **raw_severity:** medium
- **normalized_priority:** P2
- **asset_id:** backend/opensec/main.py
- **asset_label:** SPA fallback route
- **likely_owner:** backend
- **status:** new

### Description

The `_spa_fallback` handler serves files from `_static_dir` based on the URL path. It has a traversal check (`_static_dir in candidate.resolve().parents`), but this check has a subtle issue: it verifies the candidate's *parents* contain `_static_dir`, not that the candidate itself is *under* `_static_dir`. A path like `/../../etc/passwd` would be resolved, then the check would pass if the resolved path happens to have `_static_dir` as an ancestor (which it wouldn't for `/etc/passwd`, but edge cases with symlinks could bypass this).

### Evidence

- `main.py:152-154`:
  ```python
  candidate = _static_dir / full_path
  if full_path and candidate.is_file() and _static_dir in candidate.resolve().parents:
      return FileResponse(str(candidate))
  ```
- Symlinks in `_static_dir` could allow traversal outside the intended directory

### Remediation hint

Use `candidate.resolve().is_relative_to(_static_dir.resolve())` (Python 3.9+) which is the canonical path containment check. This handles symlinks, `..` sequences, and edge cases correctly. Also consider using FastAPI's `StaticFiles` mount instead of a custom handler.

### Why this matters

Path traversal in a web server can expose arbitrary files from the host filesystem. While the current check blocks most attacks, it's not the standard approach and could be bypassed with symlinks.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-007: CORS allows credentials with broad methods/headers

- **source_type:** manual-review
- **source_id:** OSSEC-007
- **raw_severity:** medium
- **normalized_priority:** P2
- **asset_id:** backend/opensec/main.py
- **asset_label:** CORS middleware configuration
- **likely_owner:** backend
- **status:** new

### Description

CORS is configured with `allow_credentials=True`, `allow_methods=["*"]`, and `allow_headers=["*"]`. While origins are limited to localhost:5173, the wildcard methods and headers combined with credentials is overly permissive. In production (Docker), no CORS origins are configured at all since the frontend is served from the same origin — but the dev CORS config ships in the production code.

### Evidence

- `main.py:117-123`:
  ```python
  CORSMiddleware,
  allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  ```

### Remediation hint

Restrict `allow_methods` to the actual HTTP methods used (`GET`, `POST`, `PATCH`, `DELETE`). Restrict `allow_headers` to specific headers needed (e.g., `Content-Type`, `Authorization`). Consider making CORS configurable via environment variable for different deployment contexts. Only enable CORS middleware when `OPENSEC_ENV=development`.

### Why this matters

Overly broad CORS with credentials can be exploited if an attacker controls a subdomain or if the origin list is expanded. Defense-in-depth requires minimizing the CORS surface.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-008: No rate limiting on API endpoints

- **source_type:** manual-review
- **source_id:** OSSEC-008
- **raw_severity:** medium
- **normalized_priority:** P3
- **asset_id:** backend/opensec/api/
- **asset_label:** All API endpoints
- **likely_owner:** backend
- **status:** new

### Description

No rate limiting is implemented on any endpoint. The `POST /api/workspaces/{id}/chat/send` endpoint triggers LLM API calls (which cost money), and the `POST /api/seed/demo` endpoint populates the database. Without rate limiting, an attacker (or runaway script) could rapidly burn through LLM API credits or flood the database.

### Evidence

- No `slowapi`, `fastapi-limiter`, or custom rate limiting middleware found
- No request throttling in any route handler
- Workspace process pool limits ports (4100-4199) but not request rate

### Remediation hint

Add `slowapi` or a simple middleware that limits requests per IP/time window. Prioritize rate limiting on: chat endpoints (LLM cost), seed endpoint (DB flooding), and settings endpoints (credential enumeration).

### Why this matters

Combined with OSSEC-004 (no auth), anyone on the network can trigger unlimited LLM calls, burning API credits.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-009: npm dependency vulnerability (brace-expansion DoS)

- **source_type:** npm-audit
- **source_id:** GHSA-f886-m6hf-6m8v
- **raw_severity:** medium
- **normalized_priority:** P3
- **asset_id:** frontend/node_modules/brace-expansion
- **asset_label:** brace-expansion (transitive dependency)
- **likely_owner:** frontend
- **status:** new

### Description

`npm audit` found 1 moderate vulnerability in `brace-expansion` (<1.1.13): a zero-step sequence causes process hang and memory exhaustion (CWE-400, CVSS 6.5). This is a transitive dependency — not directly used by the frontend code.

### Evidence

- `npm audit` output: GHSA-f886-m6hf-6m8v
- Affects: `brace-expansion <1.1.13`
- CVSS: 6.5 (AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:N/A:H)
- Fix available via `npm audit fix`

### Remediation hint

Run `npm audit fix` to update `brace-expansion` to >=1.1.13. If the fix requires a major version bump of a parent dependency, add a `resolutions`/`overrides` field in `package.json`.

### Why this matters

While this is a build-time/dev dependency and unlikely to be exploited at runtime, having zero npm audit warnings is a trust signal for an open source security project.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-010: OpenCode binary downloaded over HTTP without integrity check

- **source_type:** manual-review
- **source_id:** OSSEC-010
- **raw_severity:** medium
- **normalized_priority:** P2
- **asset_id:** scripts/install-opencode.sh
- **asset_label:** OpenCode binary install script
- **likely_owner:** devops
- **status:** new

### Description

The `install-opencode.sh` script downloads the OpenCode binary from GitHub releases. The Dockerfile runs this script during build. If the download is intercepted (MITM) or the GitHub release is compromised, a malicious binary would be installed and run with the same privileges as the application. No checksum verification or signature validation is performed after download.

### Evidence

- `docker/Dockerfile:44-45` — `RUN bash scripts/install-opencode.sh || echo "WARNING: OpenCode download failed"`
- `process.py:129-136` — `_download_binary()` runs the install script at runtime too
- `.opencode-version` pins the version but not the hash

### Remediation hint

Add SHA256 checksum verification after download: store expected checksums in a `checksums.txt` file per version, download the binary, compute `sha256sum`, and compare. For Docker builds, consider using a multi-stage build that verifies the binary in a separate stage. Long-term, use cosign/sigstore to verify release signatures.

### Why this matters

Supply chain attacks via compromised binaries are a growing threat. A security tool that doesn't verify its own dependencies sends the wrong message.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-011: No SECURITY.md or vulnerability disclosure policy

- **source_type:** manual-review
- **source_id:** OSSEC-011
- **raw_severity:** low
- **normalized_priority:** P3
- **asset_id:** ./
- **asset_label:** Repository root
- **likely_owner:** project
- **status:** new

### Description

The repository has no `SECURITY.md` file, no `.github/SECURITY.md`, and no documented vulnerability disclosure process. For a security-focused open source project, this is a significant trust gap. Security researchers who find vulnerabilities have no guidance on how to report them responsibly.

### Evidence

- No `SECURITY.md` in repo root or `.github/`
- No security policy configured in GitHub repository settings
- No mention of security reporting in README or CONTRIBUTING docs

### Remediation hint

Create `SECURITY.md` with: supported versions, how to report (email or GitHub Security Advisories), expected response timeline, and scope. Enable GitHub Security Advisories for the repository. Add a `security.txt` at the well-known URI.

### Why this matters

This is the single most visible trust signal for a security open source project. The OpenSSF Scorecard checks for this specifically.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-012: No Content Security Policy or security headers

- **source_type:** manual-review
- **source_id:** OSSEC-012
- **raw_severity:** low
- **normalized_priority:** P3
- **asset_id:** backend/opensec/main.py
- **asset_label:** FastAPI application
- **likely_owner:** backend
- **status:** new

### Description

The FastAPI application does not set any security-related HTTP headers: no `Content-Security-Policy`, no `X-Content-Type-Options`, no `X-Frame-Options`, no `Strict-Transport-Security`. When served in production (via the SPA fallback), the application is vulnerable to clickjacking, MIME sniffing attacks, and XSS if any user content is reflected.

### Evidence

- No security header middleware in `main.py`
- No CSP meta tag in the frontend `index.html`
- FastAPI doesn't add security headers by default

### Remediation hint

Add a middleware that sets:
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000` (when behind TLS)

### Why this matters

Security headers are a quick win that demonstrates attention to defense-in-depth. Their absence is flagged by tools like Mozilla Observatory and SecurityHeaders.com.

<!-- finding:end -->

---

<!-- finding:start -->
## OSSEC-013: Exception handling swallows errors silently

- **source_type:** bandit
- **source_id:** OSSEC-013
- **raw_severity:** low
- **normalized_priority:** P4
- **asset_id:** backend/opensec/api/routes/health.py
- **asset_label:** Health endpoint
- **likely_owner:** backend
- **status:** new

### Description

Bandit flagged B110 (try/except/pass) in the health endpoint. Several other locations use bare `except Exception` with only logging. While not directly exploitable, swallowing exceptions can mask security-relevant errors (e.g., failed auth restoration, engine crashes) and make debugging harder.

### Evidence

- `health.py:25` — `except Exception: pass`
- `main.py:68-69` — `except Exception: logger.warning(...)` (swallows config restore failure)
- `config_manager.py:101` — `except Exception: logger.warning(...)` (swallows auth push failure)

### Remediation hint

Replace bare `except Exception: pass` with specific exception types and always log the exception. For security-relevant operations (key restoration), consider failing loudly or setting a health status flag.

### Why this matters

Silent exception handling can hide security failures. If API key restoration fails silently, the user might not realize their keys aren't configured.

<!-- finding:end -->

---

## Summary

| ID | Severity | Title | Category |
|----|----------|-------|----------|
| OSSEC-001 | High | API keys stored in plaintext in SQLite | Secrets management |
| OSSEC-002 | High | Jinja2 templates with autoescape disabled | Injection (SSTI) |
| OSSEC-003 | High | Docker container runs as root | Container security |
| OSSEC-004 | Medium | No authentication on any API endpoint | Access control |
| OSSEC-005 | Medium | Dynamic SQL query construction | Injection (SQLi) |
| OSSEC-006 | Medium | Path traversal in SPA fallback | File access |
| OSSEC-007 | Medium | CORS allows credentials with broad config | Web security |
| OSSEC-008 | Medium | No rate limiting on API endpoints | Availability |
| OSSEC-009 | Medium | npm brace-expansion DoS vulnerability | Supply chain (SCA) |
| OSSEC-010 | Medium | OpenCode binary downloaded without integrity check | Supply chain |
| OSSEC-011 | Low | No SECURITY.md or disclosure policy | Governance |
| OSSEC-012 | Low | No security headers (CSP, HSTS, etc.) | Web security |
| OSSEC-013 | Low | Exception handling swallows errors silently | Code quality |

**Totals:** 3 High, 7 Medium, 3 Low

---

## Tools used

| Tool | What it found | Findings |
|------|--------------|----------|
| `npm audit` | Frontend SCA — known CVEs in npm dependencies | OSSEC-009 |
| `bandit` | Python SAST — security anti-patterns | OSSEC-002, OSSEC-005, OSSEC-013 |
| Manual review | Architecture, auth, secrets, Docker, supply chain | OSSEC-001, OSSEC-003, OSSEC-004, OSSEC-006, OSSEC-007, OSSEC-008, OSSEC-010, OSSEC-011, OSSEC-012 |
