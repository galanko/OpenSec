"""Issue derivation logic (IMPL-0006 T1).

Pure function that maps a Finding plus its workspace state, sidebar, and
latest agent runs into the four-section / 13-stage UI model documented
inline in IMPL-0006. No DB access — the caller batch-loads everything.

The rules table lives in IMPL-0006 §"Derivation contract". Phase 1 adapts
two rules to the ``pull_request.status`` values the remediation_executor
template actually writes today (``pr_created`` / ``changes_made`` /
``failed`` / ``needs_approval``); see Q1 in the auto-execute plan.
"""

from __future__ import annotations

from collections.abc import Mapping

from opensec.models import AgentRun, SidebarState, Workspace
from opensec.models.finding import Finding, IssueDerived


def _is_running(run: AgentRun | None) -> bool:
    return run is not None and run.status == "running"


def _has_plan(sidebar: SidebarState | None) -> bool:
    return sidebar is not None and bool(sidebar.plan)


def _pull_request(sidebar: SidebarState | None) -> dict:
    if sidebar is None or not sidebar.pull_request:
        return {}
    return sidebar.pull_request


def derive(
    finding: Finding,
    *,
    workspace: Workspace | None,
    sidebar: SidebarState | None,
    latest_runs_by_type: Mapping[str, AgentRun],
) -> IssueDerived:
    """Compose the (section, stage, workspace_id, pr_url) tuple for a finding.

    ``latest_runs_by_type`` is keyed by ``AgentRun.agent_type`` and holds the
    most recent run for that type on this workspace (or absent if there isn't
    one). First-match-wins ordering — see the IMPL-0006 derivation table.
    """

    workspace_id = workspace.id if workspace else None
    pr_block = _pull_request(sidebar)
    pr_url = pr_block.get("pr_url") or None

    def out(section: str, stage: str) -> IssueDerived:
        return IssueDerived(
            section=section,  # type: ignore[arg-type]
            stage=stage,  # type: ignore[arg-type]
            workspace_id=workspace_id,
            pr_url=pr_url,
        )

    # ---------- Done verdicts (terminal) ------------------------------------
    if finding.status == "exception":
        reason = (finding.raw_payload or {}).get("exception_reason")
        return out("done", "false_positive" if reason == "false_positive" else "accepted")

    if finding.status in ("validated", "closed"):
        return out("done", "fixed")

    # Missing SidebarState means we have no signal (IMPL-0006 edge case 16) —
    # fall back to todo regardless of Finding.status.
    if sidebar is None:
        return out("todo", "todo")

    planner_run = latest_runs_by_type.get("remediation_planner")
    executor_run = latest_runs_by_type.get("remediation_executor")
    validator_run = latest_runs_by_type.get("validation_checker")

    if finding.status == "remediated" and _is_running(validator_run):
        return out("in_progress", "validating")

    if finding.status == "remediated" and validator_run is None and pr_url:
        return out("review", "pr_awaiting_val")

    if finding.status == "in_progress":
        # PR existence dominates planner re-runs (edge case 18 in IMPL plan).
        if pr_url:
            return out("review", "pr_ready")
        if _is_running(executor_run):
            return out("in_progress", "generating")
        if pr_block.get("status") == "changes_made":
            return out("in_progress", "opening_pr")
        if pr_block.get("branch_name"):
            return out("in_progress", "pushing")
        if _has_plan(sidebar):
            return out("review", "plan_ready")
        if _is_running(planner_run):
            return out("in_progress", "planning")

    return out("todo", "todo")
