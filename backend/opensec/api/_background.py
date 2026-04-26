"""Background orchestration for assessment runs (EXEC-0002 Session B).

Both ``/api/assessment/run`` and ``/api/onboarding/repo`` need to kick off an
engine run without blocking the response. This module owns:

  * ``run_and_persist_assessment`` — the single coroutine that drives the engine
    and writes its results to the DB. Public (no underscore) so other routes can
    import it without reaching across a module-private boundary.
  * ``schedule_assessment_run`` — fires the coroutine as a task tracked in
    ``app.state.assessment_tasks`` and self-evicts on completion so the set
    doesn't grow unboundedly over a long-running process.

PR-B (PRD-0003 v0.2): also wires the ``on_tool`` callback so the in-flight UI
gets live ``tools[]`` updates (ADR-0032) without polling the DB. Per-assessment
state lives in two in-memory dicts (``_ASSESSMENT_STEPS``, ``_ASSESSMENT_TOOLS``)
that the status route reads.
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
from opensec.integrations.normalizer import normalize_findings
from opensec.models import (
    AssessmentTool,
    AssessmentUpdate,
    CompletionCreate,
    FindingCreate,
    PostureCheckCreate,
)

# Batch size for the LLM normalizer pass.
_NORMALIZER_CHUNK_SIZE = 10

if TYPE_CHECKING:
    import aiosqlite
    from fastapi import FastAPI

    from opensec.api._engine_dep import AssessmentEngineProtocol

logger = logging.getLogger(__name__)


# In-memory step / tools state per in-flight assessment. Lives next to the
# running task; the status endpoint reads it back. State dies with the
# process — a ``failed`` or ``complete`` row in the DB is the durable signal.
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
    """Drive the engine for one assessment and persist every output it emits."""

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
            on_step=_on_step,
            on_tool=_on_tool,
        )
    except Exception:
        logger.exception("assessment engine failed for %s", assessment_id)
        await update_assessment(db, assessment_id, AssessmentUpdate(status="failed"))
        _ASSESSMENT_STEPS.pop(assessment_id, None)
        _ASSESSMENT_TOOLS.pop(assessment_id, None)
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

    # Findings land via the same ETL the /findings/ingest endpoint uses:
    # engine emits deterministic FindingCreate-shaped dicts → LLM normalizer
    # enriches them with ``plain_description`` (and re-confirms
    # ``normalized_priority``) → DB. Phase 1 keeps this path; Phase 2 swaps it
    # for the deterministic ``to_findings`` mappers + UPSERT.
    findings_to_persist: list[FindingCreate] = []

    if result.findings:
        # Phase 1 of IMPL-0003-p2 keeps the legacy single-source persistence
        # path: every assessment-emitted finding lands as ``opensec-assessment``
        # so the existing dashboard query and Findings page filter still work.
        # Phase 2 swaps this for the ``to_findings`` deterministic mappers
        # which preserve real ``source_type`` values (``trivy``, ``trivy-secret``,
        # ``semgrep``, ``opensec-posture``).
        raw_data = [
            {**f, "source_type": "opensec-assessment"} for f in result.findings
        ]
        normalized: list[FindingCreate] = []
        normalizer_errors: list[str] = []
        try:
            for chunk_start in range(0, len(raw_data), _NORMALIZER_CHUNK_SIZE):
                chunk = raw_data[chunk_start : chunk_start + _NORMALIZER_CHUNK_SIZE]
                valid, errors = await normalize_findings(
                    "opensec-assessment", chunk
                )
                normalized.extend(valid)
                normalizer_errors.extend(errors)
            if normalizer_errors:
                logger.warning(
                    "normalizer returned %d errors for assessment %s",
                    len(normalizer_errors),
                    assessment_id,
                )
        except Exception:
            logger.warning(
                "normalizer pass failed for assessment %s — falling back to "
                "deterministic engine output",
                assessment_id,
                exc_info=True,
            )
            normalized = []

        if normalized:
            findings_to_persist.extend(normalized)
        else:
            for finding_data in result.findings:
                try:
                    payload = {
                        **finding_data,
                        "source_type": "opensec-assessment",
                    }
                    findings_to_persist.append(FindingCreate(**payload))
                except Exception:
                    logger.exception(
                        "failed to build fallback FindingCreate for %r",
                        finding_data.get("source_id") or finding_data.get("title"),
                    )

    for fc in findings_to_persist:
        try:
            await create_finding(db, fc)
        except Exception:
            logger.exception(
                "failed to persist finding for assessment %s: %r",
                assessment_id,
                fc.source_id or fc.title,
            )

    # Persist final tools[] + grade + criteria.
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
