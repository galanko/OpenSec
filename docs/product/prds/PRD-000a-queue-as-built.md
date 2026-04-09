# PRD-000a: Queue page (as-built)

**Status:** Approved (as-built)
**Author:** Product team (bootstrap)
**Date:** 2026-04-09
**Approver:** @galanko (CEO)

---

## Problem statement

Security teams receive vulnerability findings from multiple scanners but have no single place to see, prioritize, and act on them. Without a unified queue, findings get lost in scanner-specific dashboards, triaged inconsistently, or ignored entirely. The Queue is the entry point to the entire remediation workflow — if users can't quickly find and prioritize what matters, nothing downstream works.

## User persona

**Security engineer / analyst** — responsible for remediating vulnerabilities across their organization's infrastructure. They juggle multiple scanner tools, have limited time, and need to focus on what matters most. They may not have deep expertise in every CVE — they need the system to help them understand severity and urgency.

## User stories

### Story 1: Browse findings

**As a** security engineer, **I want to** see all my findings in one list, **so that** I don't have to switch between scanner dashboards.

**Given** findings have been ingested from one or more sources,
**When** I open the Queue page,
**Then** I see a list of findings with title, severity, asset, owner, and status.

**The user should feel:** Oriented and in control — "I can see everything in one place."

### Story 2: Filter and sort

**As a** security engineer, **I want to** filter by severity and status and sort by priority, **so that** I focus on the most urgent findings first.

**Given** the Queue page is loaded,
**When** I select filters (status: new/triaged/in-progress) and sort (latest/severity),
**Then** the list updates to show only matching findings in the chosen order.

**The user should feel:** Efficient — "I can quickly zero in on what needs attention."

### Story 3: Start remediation

**As a** security engineer, **I want to** click "Solve" on a finding, **so that** I enter a guided remediation workspace.

**Given** I see a finding in the queue,
**When** I click "Solve",
**Then** a workspace is created (or reopened if one exists) and I'm taken to it.

**The user should feel:** Confident — "I'm taking action, not just looking at a list."

## What exists today

- Finding list with severity badges, asset, owner, status columns
- Status filter (new, triaged, in-progress) and sort (latest, severity)
- "Solve" button creates/opens a workspace
- Auto-seeds demo data if queue is empty
- Data sourced from FindingSource fixture adapter
- LLM-powered finding normalization (ADR-0022) — any scanner format ingested and normalized

## Known gaps

- [ ] Search by title, asset, or CVE (Phase 4 gap)
- [ ] "Why this matters" preview on hover/expand (Phase 4 gap)
- [ ] Bulk selection / batch triage actions
- [ ] Saved filter presets

## Scope boundaries

**In scope for MVP:** Browse, filter, sort, and enter workspace.
**Out of scope:** Bulk actions, custom columns, saved views, real-time scanner webhooks.

---

_As-built PRD — documents what exists as of 2026-04-09. Not a future spec._
