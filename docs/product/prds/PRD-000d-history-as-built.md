# PRD-000d: History page (as-built)

**Status:** Approved (as-built)
**Author:** Product team (bootstrap)
**Date:** 2026-04-09
**Approver:** @galanko (CEO)

---

## Problem statement

Remediation is not a one-shot activity. Teams need to look back at how past findings were resolved — for compliance audits, to learn from similar vulnerabilities, or to reopen a workspace when a fix doesn't hold. Without searchable history, completed work disappears into the void and the same mistakes get repeated.

## User persona

**Security engineer** — finished remediating findings and needs to reference past work, prove compliance, or reopen a case. Also: **auditors** (future) who need to review remediation evidence.

## User stories

### Story 1: Browse completed work

**As a** security engineer, **I want to** see all completed workspaces, **so that** I can reference past remediations.

**Given** workspaces have been resolved,
**When** I open the History page,
**Then** I see a list of completed workspaces with finding title, outcome, agents run, and ticket info.

**The user should feel:** Accomplished — "I can see everything my team has resolved."

### Story 2: Search and filter history

**As a** security engineer, **I want to** search across findings, assets, and owners, **so that** I can quickly find a specific past remediation.

**Given** the History page is loaded,
**When** I type a search query and select state tabs (closed / ready-to-close),
**Then** the list filters to matching workspaces.

**The user should feel:** Efficient — "I found what I needed in seconds."

### Story 3: Replay a past workspace

**As a** security engineer, **I want to** view the full chat history and agent outputs of a past workspace, **so that** I can understand how a finding was resolved.

**Given** I click on a workspace in history,
**When** the detail view opens,
**Then** I see the full chat replay, agent runs, and context tabs.

**The user should feel:** Informed — "I can see exactly what happened, step by step."

### Story 4: Export as evidence

**As a** security engineer, **I want to** export a workspace summary as markdown, **so that** I can share remediation evidence for compliance or documentation.

**Given** I'm viewing a workspace in history,
**When** I click "Export",
**Then** a markdown file is generated with all messages and agent outputs.

**The user should feel:** Prepared — "I have the evidence I need."

## What exists today

- History page with completed workspace list
- State tabs: closed, ready-to-close
- Sort: newest/oldest
- Text search across findings, assets, owners (client-side filtering)
- History cards with finding info, ticket state, agent run summary
- Full chat replay with 3 tabs: Chat, Agent runs, Context
- Markdown export of workspace summary
- Reopen functionality (navigate back to workspace)

## Known gaps

- [ ] Server-side search (currently client-side — won't scale)
- [ ] Date range filter
- [ ] Compliance report export (structured, not just markdown)

## Scope boundaries

**In scope for MVP:** Browse, search, replay, export.
**Out of scope:** Analytics/dashboards, trend reports, team performance metrics.

---

_As-built PRD — documents what exists as of 2026-04-09. Not a future spec._
