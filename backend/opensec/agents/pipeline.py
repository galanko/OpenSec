"""Pipeline orchestrator — determines agent sequence and runs pipelines.

Advisory, not enforcing. Users can run agents in any order, skip agents,
or re-run agents. ``suggest_next()`` is a recommendation based on current
workspace context state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from opensec.workspace.workspace_dir import AGENT_TYPE_TO_SECTION

if TYPE_CHECKING:
    import aiosqlite

    from opensec.agents.executor import AgentExecutionResult, AgentExecutor

logger = logging.getLogger(__name__)

# Standard pipeline order — derived from the canonical agent→section mapping.
PIPELINE_ORDER: list[str] = list(AGENT_TYPE_TO_SECTION.keys())

# Maximum retry iterations for the plan-validate loop.
MAX_RETRY_ITERATIONS = 3


@dataclass
class SuggestedAction:
    """A recommended next agent to run."""

    agent_type: str
    reason: str
    priority: Literal["recommended", "optional", "required"]
    prerequisites_met: bool = True


def suggest_next(
    context_snapshot: dict[str, Any],
    agent_run_history: list[dict[str, Any]] | None = None,
) -> SuggestedAction | None:
    """Determine the recommended next agent based on current context state.

    Args:
        context_snapshot: Dict with keys: finding, enrichment, ownership,
            exposure, plan, validation (values are dicts or None).
        agent_run_history: Optional list of past agent run dicts (from
            agent-runs.jsonl) to detect retry loops.

    Returns:
        SuggestedAction with the recommended agent, or None if pipeline
        is complete.
    """
    # Check which context sections exist
    has = {
        section: context_snapshot.get(section) is not None
        for section in ["enrichment", "ownership", "exposure", "plan", "validation"]
    }

    # Standard pipeline order — suggest first missing section
    if not has["enrichment"]:
        return SuggestedAction(
            agent_type="finding_enricher",
            reason="CVE details and exploit info not yet collected",
            priority="recommended",
        )
    if not has["ownership"]:
        return SuggestedAction(
            agent_type="owner_resolver",
            reason="Responsible team not yet identified",
            priority="recommended",
        )
    if not has["exposure"]:
        return SuggestedAction(
            agent_type="exposure_analyzer",
            reason="Reachability and blast radius not yet assessed",
            priority="recommended",
        )
    if not has["plan"]:
        return SuggestedAction(
            agent_type="remediation_planner",
            reason="No remediation plan created yet",
            priority="recommended",
        )
    if not has["validation"]:
        return SuggestedAction(
            agent_type="validation_checker",
            reason="Fix not yet validated",
            priority="recommended",
        )

    # All sections exist — check if validation failed (retry loop)
    validation = context_snapshot.get("validation", {})
    verdict = validation.get("verdict", "").lower() if validation else ""

    if verdict in ("not_fixed", "partially_fixed"):
        # Count how many plan-validate cycles we've done
        retry_count = _count_plan_retries(agent_run_history or [])
        if retry_count < MAX_RETRY_ITERATIONS:
            return SuggestedAction(
                agent_type="remediation_planner",
                reason=(
                    f"Validation found issues "
                    f"(attempt {retry_count + 1}/{MAX_RETRY_ITERATIONS}). "
                    f"Re-planning."
                ),
                priority="required",
            )
        else:
            logger.warning(
                "Validation retry limit reached (%d). Manual intervention needed.",
                MAX_RETRY_ITERATIONS,
            )

    # Pipeline complete
    return None


def _count_plan_retries(agent_run_history: list[dict[str, Any]]) -> int:
    """Count how many remediation_planner runs have completed."""
    return sum(
        1
        for run in agent_run_history
        if run.get("agent_type") == "remediation_planner"
        and run.get("status") == "completed"
    )


async def run_pipeline(
    executor: AgentExecutor,
    workspace_id: str,
    db: aiosqlite.Connection,
    *,
    workspace_dir: str,
    context_builder: Any,
    on_agent_complete: Any | None = None,
) -> list[AgentExecutionResult]:
    """Run all remaining agents in pipeline order.

    Stops on first failure. Returns list of results for agents that ran.
    """

    results: list[AgentExecutionResult] = []

    for _iteration in range(len(PIPELINE_ORDER) + MAX_RETRY_ITERATIONS):
        # Get current context to determine next step
        snapshot = await context_builder.get_context_snapshot(workspace_id)
        run_history = snapshot.get("agent_run_history", [])

        suggestion = suggest_next(snapshot, run_history)
        if suggestion is None:
            break  # Pipeline complete

        result = await executor.execute(
            workspace_id,
            suggestion.agent_type,
            db,
            workspace_dir=workspace_dir,
        )
        results.append(result)

        if on_agent_complete:
            on_agent_complete(result)

        if result.status == "failed":
            logger.warning(
                "Pipeline stopped: %s failed in workspace %s",
                suggestion.agent_type,
                workspace_id,
            )
            break

    return results
