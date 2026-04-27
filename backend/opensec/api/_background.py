"""Background orchestration for assessment runs (PRD-0003 v0.2 / IMPL-0003-p2).

Both ``/api/assessment/run`` and ``/api/onboarding/repo`` need to kick off an
engine run without blocking the response. This module owns:

  * ``run_and_persist_assessment`` — the single coroutine that drives the
    engine and finalises the assessment row. The engine itself persists every
    finding (Trivy / Semgrep / posture) via the unified UPSERT in Phase 2;
    this module only updates the assessment row's status, tools_json, grade,
    and criteria_snapshot, plus opens a completion row when the user hits
    Grade A.
  * ``schedule_assessment_run`` — fires the coroutine as a task tracked in
    ``app.state.assessment_tasks`` and self-evicts on completion.

Per-assessment in-memory state (``_ASSESSMENT_STEPS`` / ``_ASSESSMENT_TOOLS``)
backs the live ToolPillBar in the running-state UI; the durable signals are
the assessment row's ``status`` and ``tools_json``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from opensec.db.dao.assessment import set_assessment_result, update_assessment
from opensec.db.dao.completion import (
    create_completion,
    get_completion_for_assessment,
)
from opensec.models import AssessmentTool, AssessmentUpdate, CompletionCreate

if TYPE_CHECKING:
    import aiosqlite
    from fastapi import FastAPI

    from opensec.api._engine_dep import AssessmentEngineProtocol

logger = logging.getLogger(__name__)


_ASSESSMENT_STEPS: dict[str, str] = {}
_ASSESSMENT_TOOLS: dict[str, dict[str, AssessmentTool]] = {}


def get_assessment_step(assessment_id: str) -> str | None:
    """Current phase for an in-flight assessment, or ``None`` if unknown."""
    return _ASSESSMENT_STEPS.get(assessment_id)


def get_assessment_tools(assessment_id: str) -> list[AssessmentTool] | None:
    """Live ``tools[]`` payload for an in-flight assessment, or ``None``."""
    pills = _ASSESSMENT_TOOLS.get(assessment_id)
    if pills is None:
        return None
    return list(pills.values())


async def run_and_persist_assessment(
    db: aiosqlite.Connection,
    engine: AssessmentEngineProtocol,
    assessment_id: str,
    repo_url: str,
) -> None:
    """Drive the engine for one assessment and finalise the assessment row."""

    async def _on_step(step: str) -> None:
        _ASSESSMENT_STEPS[assessment_id] = step

    async def _on_tool(tool: AssessmentTool) -> None:
        pills = _ASSESSMENT_TOOLS.setdefault(assessment_id, {})
        pills[tool.id] = tool

    try:
        await update_assessment(db, assessment_id, AssessmentUpdate(status="running"))
        _ASSESSMENT_STEPS[assessment_id] = "detect"
        result = await engine.run_assessment(
            repo_url,
            assessment_id=assessment_id,
            db=db,
            on_step=_on_step,
            on_tool=_on_tool,
        )
    except Exception:
        logger.exception("assessment engine failed for %s", assessment_id)
        await update_assessment(db, assessment_id, AssessmentUpdate(status="failed"))
        _ASSESSMENT_STEPS.pop(assessment_id, None)
        _ASSESSMENT_TOOLS.pop(assessment_id, None)
        return

    # Persist final tools[] + grade + criteria. Findings + posture rows are
    # already in the unified ``finding`` table (engine handled it); this
    # finalises the assessment metadata.
    await update_assessment(
        db, assessment_id, AssessmentUpdate(tools=result.tools)
    )
    await set_assessment_result(
        db,
        assessment_id,
        grade=result.grade,
        criteria_snapshot=result.criteria_snapshot,
    )

    if result.criteria_snapshot.all_met():
        existing = await get_completion_for_assessment(db, assessment_id)
        if existing is None:
            await create_completion(
                db,
                CompletionCreate(
                    assessment_id=assessment_id,
                    repo_url=repo_url,
                    criteria_snapshot=result.criteria_snapshot,
                ),
            )

    _ASSESSMENT_STEPS.pop(assessment_id, None)
    _ASSESSMENT_TOOLS.pop(assessment_id, None)


def schedule_assessment_run(
    app: FastAPI,
    db: aiosqlite.Connection,
    engine: AssessmentEngineProtocol,
    assessment_id: str,
    repo_url: str,
) -> asyncio.Task[None]:
    """Fire-and-track an assessment run. Tasks self-evict on completion."""
    tasks: set[asyncio.Task[None]] = (
        getattr(app.state, "assessment_tasks", None) or set()
    )
    task = asyncio.create_task(
        run_and_persist_assessment(db, engine, assessment_id, repo_url),
        name=f"assessment:{assessment_id}",
    )
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    app.state.assessment_tasks = tasks
    return task
