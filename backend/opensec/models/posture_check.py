"""PostureCheck domain model (IMPL-0002 Milestone A + B5).

A PostureCheck is the outcome of one of the seven repo-level checks that the
assessment engine runs. `unknown` means the check couldn't run (e.g. PAT lacks
admin scope), which is distinct from `fail`.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal

from pydantic import BaseModel

PostureCheckStatus = Literal["pass", "fail", "advisory", "unknown"]

# 15 checks total — the 7 frozen by IMPL-0002 plus 8 added in PRD-0003 v0.2.
# Every check belongs to exactly one PostureCheckCategory; the API layer
# (Epic 4) groups them into four sections on the report card.
PostureCheckName = Literal[
    # Repo configuration (carried from PRD-0002)
    "branch_protection",
    "no_force_pushes",
    "no_secrets_in_code",
    "security_md",
    "lockfile_present",
    # Code integrity
    "dependabot_config",
    "signed_commits",
    "code_owners_exists",
    "secret_scanning_enabled",
    # CI supply chain
    "actions_pinned_to_sha",
    "trusted_action_sources",
    "workflow_trigger_scope",
    # Collaborator hygiene
    "stale_collaborators",
    "broad_team_permissions",
    "default_branch_permissions",
]

PostureCheckCategory = Literal[
    "repo_configuration",
    "code_integrity",
    "ci_supply_chain",
    "collaborator_hygiene",
]


class PostureCheckCreate(BaseModel):
    assessment_id: str
    check_name: PostureCheckName
    status: PostureCheckStatus
    detail: dict[str, Any] | None = None


class PostureCheck(BaseModel):
    id: str
    assessment_id: str
    check_name: PostureCheckName
    status: PostureCheckStatus
    detail: dict[str, Any] | None = None
    created_at: datetime
