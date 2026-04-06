# ADR-0021: Agent Execution Model

**Date:** 2026-04-06
**Status:** Accepted

## Context

ADR-0008 defined the sub-agent architecture (1 orchestrator + 5 specialists) and ADR-0014 defined the workspace runtime (isolated directories, per-workspace processes). Phase 6b wires these together — but several non-obvious execution decisions need to be recorded for future contributors.

Key questions:
- How does the backend invoke a sub-agent? Through the orchestrator, or directly?
- What happens when the LLM returns text but not valid JSON?
- Can multiple agents run simultaneously in one workspace?
- How does the system recover from crashes mid-pipeline?

## Decision

### 1. Two execution modes: direct invocation and conversational delegation

**Programmatic mode (pipeline):** The backend sends a prompt directly to a fresh OpenCode session in the workspace process, bypassing the orchestrator agent. The prompt instructs the LLM to run a specific analysis and return structured JSON. This is used for action-chip triggers in the UI ("Run enricher", "Find owner").

**Conversational mode (chat):** The user types free-form messages that go to the orchestrator's session. The orchestrator reads CONTEXT.md (which includes the pipeline checklist) and decides what to do — it may delegate to a sub-agent, answer a question, or suggest an action.

**Why:** Direct invocation is predictable, fast, and testable — the backend controls which agent runs. Conversational mode is flexible and handles edge cases. Both paths persist results through the same code (`executor -> parser -> sidebar_mapper -> context_builder.update_context()`).

### 2. Parse failures are "completed", not "failed"

When the LLM returns a response but it doesn't contain valid structured JSON, the agent run status is set to `completed` (not `failed`). The raw text is preserved in `AgentRun.summary_markdown`. Context files and sidebar are NOT updated (no structured data to persist).

**Why:** "Failed" implies infrastructure broke. But the LLM did respond — the user can read its analysis. Marking it as "failed" would be misleading and frustrating. True failure states (timeout, process crash, connection error) are still marked as `failed`.

### 3. One agent at a time per workspace

Only one agent can be `status=running` in a workspace at any given time. The executor checks for running agents before starting a new one and raises `AgentBusyError` (HTTP 409) if busy.

**Why:** Multiple concurrent agents would create race conditions on context files — two agents writing to the same workspace directory simultaneously could produce inconsistent state. The filesystem is our checkpoint mechanism and must be consistent. This constraint can be relaxed later (for independent agents like enricher + owner) with careful context merge logic.

### 4. Filesystem is the checkpoint — no separate checkpoint mechanism

Crash recovery works by reading the workspace directory. After each agent run, `context_builder.update_context()` writes the structured output to `context/<section>.json` and regenerates CONTEXT.md. If the process crashes mid-pipeline:

1. Context files reflect all completed agent runs
2. `suggest_next()` reads the context snapshot and returns the next missing agent
3. Pipeline resumes from where it left off

**Why:** The workspace directory was designed as a self-contained project (ADR-0014: "the context is the product"). Adding a separate checkpoint mechanism would duplicate state and create consistency risks. The filesystem is durable, inspectable, and already the source of truth.

### 5. Advisory pipeline, not enforced sequence

The pipeline order (enricher → owner → exposure → planner → validator) is a recommendation, not a constraint. `suggest_next()` returns the first missing context section, but users can run agents in any order, skip agents, or re-run agents.

**Why:** Rigidly enforcing order blocks legitimate workflows. A security engineer might want to jump straight to the remediation planner if they already know the fix. Or re-run the enricher after new information surfaces. The pipeline state is derived from context file existence, not a state machine — so skipping or reordering is naturally supported.

## Consequences

- **Easier:** Two clear execution paths (programmatic + conversational) with shared persistence logic.
- **Easier:** Parse failures don't block the pipeline — users always see the LLM's response.
- **Easier:** Crash recovery is automatic — just read the directory.
- **Harder:** One-at-a-time limits throughput. Acceptable for MVP (single user), needs revisiting for multi-user.
- **Harder:** "Completed" with no structured output is a new state that UI must handle gracefully (show raw text, suggest retry).
