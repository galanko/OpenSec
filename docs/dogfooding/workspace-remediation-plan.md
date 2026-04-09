# Workspace remediation plan — dogfooding our own findings

**Date:** 2026-03-29

---

## Overview

This document maps each of the 13 findings from our security scan to what a workspace needs in order to guide remediation. It covers finding dependencies, required agents, and what the ideal UX should feel like when Gal sits down to fix them hands-on.

## Finding dependency graph

Some findings block or interact with others. Fixing them in the right order avoids rework.

```
OSSEC-003 (Docker root)           — standalone, fix first for credibility
OSSEC-011 (SECURITY.md)          — standalone, quick win

OSSEC-001 (Plaintext API keys)   — blocks nothing but is highest impact
  └── depends on: nothing

OSSEC-004 (No auth)              — unlocks security for everything else
  └── OSSEC-008 (No rate limit)  — should be added alongside or after auth
  └── OSSEC-001 benefits from auth (reduces exposure of key endpoints)

OSSEC-002 (Jinja2 SSTI)          — standalone, high priority
OSSEC-005 (SQL construction)      — standalone, defense-in-depth

OSSEC-006 (Path traversal)       — standalone, quick fix
OSSEC-007 (CORS config)          — standalone, config change
OSSEC-009 (npm brace-expansion)  — standalone, npm audit fix
OSSEC-010 (Binary integrity)     — standalone, script change
OSSEC-012 (Security headers)     — standalone, middleware addition
OSSEC-013 (Exception handling)   — standalone, code quality
```

### Recommended fix order

**Wave 1 — Quick wins (30 min each, build momentum):**
1. OSSEC-011: Create SECURITY.md
2. OSSEC-009: `npm audit fix`
3. OSSEC-013: Fix exception handling

**Wave 2 — High-impact security (1-2 hours each):**
4. OSSEC-003: Add non-root USER to Dockerfile
5. OSSEC-002: Switch to SandboxedEnvironment + autoescape
6. OSSEC-001: Encrypt API keys at rest

**Wave 3 — Defense-in-depth (1-2 hours each):**
7. OSSEC-004: Add bearer token auth middleware
8. OSSEC-006: Fix path traversal with `is_relative_to()`
9. OSSEC-005: Add column name allowlist to SQL layer
10. OSSEC-007: Tighten CORS to specific methods/headers

**Wave 4 — Hardening (30 min - 1 hour each):**
11. OSSEC-008: Add rate limiting middleware
12. OSSEC-012: Add security headers middleware
13. OSSEC-010: Add SHA256 checksum verification to install script

## What each workspace needs

### Agent requirements per finding

| Finding | Enricher | Owner Resolver | Exposure Analyzer | Remediation Planner | Validation |
|---------|----------|---------------|-------------------|--------------------:|------------|
| OSSEC-001 | CVE/best practices for key storage | Backend team | API key exposure surface | Fernet encryption plan | Check DB for plaintext |
| OSSEC-002 | SSTI attack vectors, Jinja2 docs | Backend team | Template injection surface | SandboxedEnvironment migration | Test template rendering |
| OSSEC-003 | CIS Docker benchmarks | DevOps | Container escape risk | Dockerfile USER directive | Rebuild & verify |
| OSSEC-004 | OWASP auth guidance | Backend team | Network exposure surface | Bearer token middleware plan | Test auth enforcement |
| OSSEC-005 | SQL injection patterns | Backend team | Query injection surface | Column allowlist design | Test with malicious input |
| OSSEC-006 | Path traversal patterns | Backend team | File access surface | `is_relative_to()` fix | Test traversal payloads |
| OSSEC-007 | CORS security best practices | Backend team | Cross-origin attack surface | Config tightening plan | Test CORS headers |
| OSSEC-008 | Rate limiting patterns | Backend team | DoS/cost surface | slowapi integration plan | Load test |
| OSSEC-009 | CVE details for GHSA-f886 | Frontend team | Build-time only | npm audit fix | Verify clean audit |
| OSSEC-010 | Supply chain attack examples | DevOps | Binary integrity surface | Checksum verification plan | Test download + verify |
| OSSEC-011 | OSS security policy examples | Project | Community trust | SECURITY.md template | Check file exists |
| OSSEC-012 | Security header standards | Backend team | Browser attack surface | Middleware addition plan | Check response headers |
| OSSEC-013 | Error handling best practices | Backend team | Debug info leakage | Specific exception types | Test error paths |

### Workspace context needed

Each workspace should be populated with:

1. **Finding context** (auto-populated from MD adapter):
   - The finding description, evidence, and remediation hint
   - Severity and priority

2. **Code context** (loaded per finding):
   - The affected file(s) — the workspace should have read access to the actual source
   - Git blame for the affected lines (who wrote this, when)
   - Related test files

3. **Reference context** (fetched by enricher agent):
   - Relevant OWASP references
   - CWE details for the vulnerability class
   - Best practice documentation links

4. **Dependency context** (from the dependency graph above):
   - Which other findings this one relates to
   - Whether blocking findings have been resolved

## Ideal UX flow for hands-on remediation

Here's what the experience should feel like when Gal opens a workspace to fix a finding:

### Step 1: Open workspace from Queue

Gal sees the 13 findings in the Queue page, sorted by severity. Each finding shows its title, severity badge, asset label, and a "Solve" button. Gal clicks "Solve" on OSSEC-003 (Docker root).

### Step 2: Workspace loads with context

The workspace opens with:
- **Left panel (chat):** The orchestrator greets with a summary — "This finding is about the Docker container running as root. I've loaded the Dockerfile and CIS benchmarks. Ready to plan the fix?"
- **Right panel (sidebar):**
  - **Summary card:** OSSEC-003, High severity, Docker container security
  - **Evidence card:** Shows the Dockerfile scan result, highlights missing USER directive
  - **Owner card:** DevOps (auto-resolved from file path being in `docker/`)
  - **Plan card:** Empty — waiting for Gal to start planning

### Step 3: Chat-driven remediation

Gal types: "Let's fix this. What's the plan?"

The orchestrator triggers the **Remediation Planner** agent, which returns:

> **Plan:**
> 1. Create a non-root user `opensec` in the Dockerfile
> 2. Set ownership of `/app` and `/data` directories
> 3. Add `USER opensec` before the ENTRYPOINT
> 4. Update `entrypoint.sh` to not require root
> 5. Test the build to ensure OpenCode binary still runs
>
> **Definition of done:**
> - `docker build` succeeds
> - Container runs as non-root (verify with `docker exec whoami`)
> - Health check passes
> - OpenCode process starts correctly

The plan appears in the sidebar Plan card.

### Step 4: Gal makes the fix

Gal edits the Dockerfile locally (this is the "hands-on" part). They add:

```dockerfile
RUN useradd -r -s /bin/false opensec && chown -R opensec:opensec /app
USER opensec
```

### Step 5: Validate

Gal types: "I made the fix. Can you validate?"

The orchestrator triggers the **Validation Checker** agent which:
- Reads the updated Dockerfile
- Checks for USER directive presence
- Verifies the user is non-root
- Returns: "Fix verified. The Dockerfile now creates and switches to a non-root `opensec` user."

### Step 6: Close

The finding status moves to `validated` → `closed`. The workspace state moves to `ready_to_close`. Gal clicks "Close workspace" and moves to the next finding.

## What's missing today vs. ideal

| Capability | Current state | Needed for dogfooding |
|-----------|--------------|----------------------|
| MD Finding import | Not implemented | MarkdownFindingSource adapter |
| Queue display | Working (demo data) | Needs real findings from adapter |
| Workspace creation | Working | Works as-is |
| Agent orchestration | Templates exist, wiring in progress (Phase 6b) | Needs agents to actually run |
| Sidebar population | Schema + API exists | Needs agent output to flow into sidebar |
| Code context in workspace | Workspace dir exists | Need to copy/link affected files |
| Validation agent | Template exists | Needs to read local file changes |
| Finding status updates | CRUD API exists | Needs workspace → finding status sync |

### Minimum viable dogfooding setup

Even before agents are fully wired (Phase 6b), Gal can dogfood by:

1. **Import findings:** Build the MD parser + sync endpoint → findings appear in Queue
2. **Open workspaces:** Click "Solve" → workspace opens with finding context in CONTEXT.md
3. **Chat for guidance:** The OpenCode orchestrator already has finding context and can discuss remediation (even without sub-agents, the main LLM can help)
4. **Fix manually:** Edit files locally, test, commit
5. **Close workspace:** Update finding status via the API or UI

This gives real UX feedback even with partial agent integration.

## UX improvements to capture from dogfooding

Things to watch for during hands-on use:
- Is the Queue sorting/filtering useful for triage?
- Does the workspace load fast enough?
- Is the sidebar summary actually helpful or just noise?
- Does the chat context include enough about the finding to be useful?
- How does it feel to switch between findings?
- Is the "definition of done" clear enough to validate against?
- Do we need a "diff view" in the workspace to see what changed?
- Should the workspace auto-detect git changes in the affected files?
