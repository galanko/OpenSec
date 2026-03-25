# Domain Model

## Entity Relationship Overview

```mermaid
erDiagram
    Finding ||--o{ Workspace : "has"
    Workspace ||--o{ Message : "contains"
    Workspace ||--o{ AgentRun : "triggers"
    Workspace ||--|| SidebarState : "has"
    Workspace ||--o| TicketLink : "links to"
    Workspace ||--o{ ValidationResult : "produces"

    Finding {
        string id PK
        string source_type
        string source_id
        string title
        text description
        string raw_severity
        string normalized_priority
        string asset_id
        string asset_label
        string status
        string likely_owner
        text why_this_matters
        json raw_payload
        datetime created_at
        datetime updated_at
    }

    Workspace {
        string id PK
        string finding_id FK
        string state
        string current_focus
        int active_plan_version
        string linked_ticket_id
        string validation_state
        datetime created_at
        datetime updated_at
    }

    Message {
        string id PK
        string workspace_id FK
        string role
        text content_markdown
        string linked_agent_run_id
        datetime created_at
    }

    AgentRun {
        string id PK
        string workspace_id FK
        string agent_type
        string status
        json input_json
        text summary_markdown
        float confidence
        json evidence_json
        json structured_output
        string next_action_hint
        datetime started_at
        datetime completed_at
    }

    SidebarState {
        string workspace_id PK
        json summary
        json evidence
        json owner
        json plan
        json definition_of_done
        json linked_ticket
        json validation
        json similar_cases
        datetime updated_at
    }

    TicketLink {
        string id PK
        string workspace_id FK
        string provider
        string external_key
        string title
        string status
        string assignee
        json payload_snapshot
        datetime last_synced_at
    }

    ValidationResult {
        string id PK
        string workspace_id FK
        string provider
        string state
        text details_markdown
        json evidence
        datetime created_at
    }

    AppSetting {
        string key PK
        json value
        datetime updated_at
    }

    IntegrationConfig {
        string id PK
        string adapter_type
        string provider_name
        boolean enabled
        json config
        json last_test_result
        datetime updated_at
    }
```

## State Machines

### Finding Status

```
new --> triaged --> in_progress --> remediated --> validated --> closed
  \                                                              ^
   \--> exception (accepted risk) -------------------------------|
```

| State | Meaning |
|-------|---------|
| `new` | Just imported from scanner, not yet reviewed |
| `triaged` | Reviewed, priority set, ready to work on |
| `in_progress` | Active remediation workspace open |
| `remediated` | Fix applied, awaiting validation |
| `validated` | Validation confirms fix works |
| `closed` | Done — finding resolved or risk accepted |
| `exception` | Risk accepted, documented, not fixing |

### Workspace State

```
open --> waiting --> ready_to_close --> closed
  ^                                      |
  |---------- reopened <-----------------|
```

| State | Meaning |
|-------|---------|
| `open` | Active work in progress |
| `waiting` | Blocked on external action (e.g., ticket assignee) |
| `ready_to_close` | Validation passed, ready for final review |
| `closed` | Work complete |
| `reopened` | Validation failed or new information surfaced |

### AgentRun Status

```
queued --> running --> completed
                  \-> failed
                  \-> cancelled
```

### ValidationResult State

```
not_started --> pending --> fixed
                       \-> still_active
                       \-> uncertain
```

## Key Design Rules

1. **SidebarState is always the latest truth.** After every agent run that produces relevant output, the orchestrator updates SidebarState. The UI reads SidebarState to render the sidebar, not individual agent runs.

2. **Agent output must never live only in chat.** Every meaningful agent result is persisted both as a Message (for the chat timeline) and as a SidebarState update (for structured context).

3. **Findings and Workspaces are 1:1 for MVP.** One Finding maps to one Workspace. Group remediation (multiple findings in one workspace) is a future enhancement.

4. **All IDs are UUIDs.** Generated server-side. No auto-increment integers.

5. **Timestamps are UTC ISO 8601.** Stored as TEXT in SQLite for portability.
