# ADR-0008: Sub-Agent Architecture

**Date:** 2026-03-25
**Status:** Accepted

## Context

Vulnerability remediation involves several distinct AI tasks: understanding the finding, finding the owner, assessing exposure, planning the fix, and validating the result. A single monolithic prompt would be brittle, hard to test, and impossible to improve incrementally.

OpenCode already supports configurable agents and subagents with custom prompts, models, and tool permissions.

## Decision

Use a **primary orchestrator + five specialized sub-agents** model:

**Primary Agent — Workspace Orchestrator**
- Talks to the user in the chat thread
- Decides which sub-agent to invoke based on context and user requests
- Summarizes results and suggests next actions
- The user feels like they have one copilot

**Sub-Agents:**

1. **Finding Enricher** — Normalizes and enriches raw finding data (CVE details, severity, affected versions, known exploits)
2. **Owner Resolver** — Identifies the responsible team/person with evidence (CODEOWNERS, CMDB, git history, cloud tags)
3. **Exposure/Context Analyzer** — Assesses reachability, environment exposure, business criticality
4. **Remediation Planner** — Generates fix plan, interim mitigations, definition of done, and due date suggestion
5. **Validation Checker** — Confirms whether the fix resolved the vulnerability

**Output contract:** Every sub-agent returns a short summary, a markdown result card, a structured JSON payload, and a suggested next action. Results are persisted into both the chat timeline and the sidebar state.

## Consequences

- **Easier:** Each agent can be tested, improved, and replaced independently.
- **Easier:** Maps naturally onto OpenCode's subagent configuration model.
- **Easier:** New agents (e.g., "similar case finder", "exception reviewer") can be added without changing the orchestrator.
- **Harder:** Orchestrator must manage context threading between agents. Solved by passing structured context forward.
- **Harder:** Five agents means five prompt engineering efforts. Start with simple prompts and iterate.
