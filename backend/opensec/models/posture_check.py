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

# Seven checks from IMPL-0002 B5 plus the two scanner-facing ones.
PostureCheckName = Literal[
    "branch_protection",
    "no_force_pushes",
    "no_secrets_in_code",
    "security_md",
    "lockfile_present",
    "dependabot_config",
    "signed_commits",
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
