"""Background orchestration for assessment runs (EXEC-0002 Session B).

Both ``/api/assessment/run`` and ``/api/onboarding/repo`` need to kick off an
engine run without blocking the response. This module owns:

  * ``run_and_persist_assessment`` — the single coroutine that drives the engine
    and writes its results to the DB. Public (no underscore) so other routes can
    import it without reaching across a module-private boundary.
  * ``schedule_assessment_run`` — fires the coroutine as a task tracked in
    ``app.state.assessment_tasks`` and self-evicts on completion so the set
    doesn't grow unboundedly over a long-running process.
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
from opensec.db.dao.posture_check import upsert_posture_check
from opensec.db.repo_finding import create_finding
from opensec.models import (
    AssessmentUpdate,
    CompletionCreate,
    FindingCreate,
    PostureCheckCreate,
)

if TYPE_CHECKING:
    import aiosqlite
    from fastapi import FastAPI

    from opensec.api._engine_dep import AssessmentEngineProtocol

logger = logging.getLogger(__name__)


# In-memory "current phase" per in-flight assessment. Lives next to the
# running task; the status endpoint reads it back. A dict is sufficient:
# state dies with the process, and a ``failed`` or ``complete`` row in the
# DB is the durable signal.
_ASSESSMENT_STEPS: dict[str, str] = {}


def get_assessment_step(assessment_id: str) -> str | None:
    """Current phase for an in-flight assessment, or ``None`` if unknown."""
    return _ASSESSMENT_STEPS.get(assessment_id)


async def run_and_persist_assessment(
    db: aiosqlite.Connection,
    engine: AssessmentEngineProtocol,
    assessment_id: str,
    repo_url: str,
) -> None:
    """Drive the engine for one assessment and persist every output it emits."""
    async def _on_step(step: str) -> None:
        _ASSESSMENT_STEPS[assessment_id] = step

    try:
        await update_assessment(db, assessment_id, AssessmentUpdate(status="running"))
        _ASSESSMENT_STEPS[assessment_id] = "cloning"
        result = await engine.run_assessment(
            repo_url, assessment_id=assessment_id, on_step=_on_step
        )
    except Exception:
        logger.exception("assessment engine failed for %s", assessment_id)
        await update_assessment(db, assessment_id, AssessmentUpdate(status="failed"))
        _ASSESSMENT_STEPS.pop(assessment_id, None)
        return

    for check in result.posture_checks:
        try:
            await upsert_posture_check(
                db,
                PostureCheckCreate(
                    assessment_id=assessment_id,
                    check_name=check["check_name"],
                    status=check["status"],
                    detail=check.get("detail"),
                ),
            )
        except Exception:
            logger.exception(
                "failed to persist posture check %s for assessment %s",
                check.get("check_name"),
                assessment_id,
            )

    # Persist each finding independently. A single malformed advisory must not
    # abort the whole assessment and leave the row stuck in ``running``.
    for finding_data in result.findings:
        try:
            payload = {**finding_data, "source_type": "opensec-assessment"}
            await create_finding(db, FindingCreate(**payload))
        except Exception:
            logger.exception(
                "failed to persist finding for assessment %s: %r",
                assessment_id,
                finding_data.get("cve_id") or finding_data.get("title"),
            )

    await set_assessment_result(
        db, assessment_id, grade=result.grade, criteria_snapshot=result.criteria_snapshot
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


def schedule_assessment_run(
    app: FastAPI,
    db: aiosqlite.Connection,
    engine: AssessmentEngineProtocol,
    assessment_id: str,
    repo_url: str,
) -> asyncio.Task[None]:
    """Fire-and-track an assessment run. Tasks self-evict on completion."""
    tasks: set[asyncio.Task[None]] = getattr(app.state, "assessment_tasks", None) or set()
    task = asyncio.create_task(
        run_and_persist_assessment(db, engine, assessment_id, repo_url),
        name=f"assessment:{assessment_id}",
    )
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    app.state.assessment_tasks = tasks
    return task
