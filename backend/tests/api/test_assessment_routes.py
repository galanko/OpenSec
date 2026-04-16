"""Route tests for D2 assessment run/status/latest (IMPL-0002)."""

from __future__ import annotations

import asyncio

import pytest

from opensec.api._engine_dep import get_assessment_engine
from opensec.main import app
from opensec.models import CriteriaSnapshot
from tests.fakes.assessment_engine import FakeAssessmentEngine


def _all_criteria_met() -> CriteriaSnapshot:
    return CriteriaSnapshot(
        no_critical_vulns=True,
        posture_checks_passing=5,
        posture_checks_total=5,
        security_md_present=True,
        dependabot_present=True,
    )


def _partial_criteria() -> CriteriaSnapshot:
    return CriteriaSnapshot(
        no_critical_vulns=True,
        posture_checks_passing=3,
        posture_checks_total=5,
        security_md_present=True,
        dependabot_present=False,
    )


@pytest.fixture
def fake_engine():
    engine = FakeAssessmentEngine(
        grade="A",
        criteria=_all_criteria_met(),
        posture_checks=[
            {"check_name": "branch_protection", "status": "pass"},
            {"check_name": "security_md", "status": "pass"},
        ],
    )
    app.dependency_overrides[get_assessment_engine] = lambda: engine
    try:
        yield engine
    finally:
        app.dependency_overrides.pop(get_assessment_engine, None)


async def _drain_background_tasks() -> None:
    tasks: list[asyncio.Task] = list(getattr(app.state, "assessment_tasks", []))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_run_assessment_creates_row_and_runs_engine(db_client, fake_engine):
    resp = await db_client.post(
        "/api/assessment/run", json={"repo_url": "https://github.com/a/b"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment_id"]
    assert data["status"] == "pending"

    await _drain_background_tasks()
    assert fake_engine.call_count == 1


async def test_run_assessment_persists_result_and_posture(db_client, fake_engine):
    resp = await db_client.post(
        "/api/assessment/run", json={"repo_url": "https://github.com/a/b"}
    )
    aid = resp.json()["assessment_id"]
    await _drain_background_tasks()

    from opensec.db.connection import _db
    from opensec.db.dao.assessment import get_assessment
    from opensec.db.dao.completion import get_completion_for_assessment
    from opensec.db.dao.posture_check import list_posture_checks_for_assessment

    a = await get_assessment(_db, aid)
    assert a.status == "complete"
    assert a.grade == "A"
    assert a.criteria_snapshot.posture_checks_passing == 5

    checks = await list_posture_checks_for_assessment(_db, aid)
    assert {c.check_name for c in checks} == {"branch_protection", "security_md"}

    # All criteria met → completion row created.
    completion = await get_completion_for_assessment(_db, aid)
    assert completion is not None
    assert completion.repo_url == "https://github.com/a/b"


async def test_run_assessment_no_completion_when_criteria_unmet(db_client):
    engine = FakeAssessmentEngine(grade="D", criteria=_partial_criteria(), posture_checks=[])
    app.dependency_overrides[get_assessment_engine] = lambda: engine
    try:
        resp = await db_client.post(
            "/api/assessment/run", json={"repo_url": "https://github.com/a/c"}
        )
        aid = resp.json()["assessment_id"]
        await _drain_background_tasks()

        from opensec.db.connection import _db
        from opensec.db.dao.completion import get_completion_for_assessment

        completion = await get_completion_for_assessment(_db, aid)
        assert completion is None
    finally:
        app.dependency_overrides.pop(get_assessment_engine, None)


async def test_run_assessment_engine_failure_marks_failed(db_client):
    engine = FakeAssessmentEngine(raise_on_run=RuntimeError("boom"))
    app.dependency_overrides[get_assessment_engine] = lambda: engine
    try:
        resp = await db_client.post(
            "/api/assessment/run", json={"repo_url": "https://github.com/a/d"}
        )
        aid = resp.json()["assessment_id"]
        await _drain_background_tasks()

        from opensec.db.connection import _db
        from opensec.db.dao.assessment import get_assessment

        a = await get_assessment(_db, aid)
        assert a.status == "failed"
    finally:
        app.dependency_overrides.pop(get_assessment_engine, None)


async def test_get_assessment_status(db_client, fake_engine):
    resp = await db_client.post(
        "/api/assessment/run", json={"repo_url": "https://github.com/a/b"}
    )
    aid = resp.json()["assessment_id"]
    await _drain_background_tasks()

    resp = await db_client.get(f"/api/assessment/status/{aid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment_id"] == aid
    assert data["status"] == "complete"
    assert data["progress_pct"] == 100


async def test_get_assessment_status_not_found(db_client):
    resp = await db_client.get("/api/assessment/status/nope")
    assert resp.status_code == 404


async def test_get_latest_assessment(db_client, fake_engine):
    resp = await db_client.post(
        "/api/assessment/run", json={"repo_url": "https://github.com/a/b"}
    )
    aid = resp.json()["assessment_id"]
    await _drain_background_tasks()

    resp = await db_client.get("/api/assessment/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment"]["id"] == aid
    assert data["grade"] == "A"
    assert data["criteria"]["posture_checks_passing"] == 5
    assert data["posture_total_count"] == 2
    assert data["posture_pass_count"] == 2
    assert data["findings_count_by_priority"] == {}


async def test_get_latest_assessment_empty_returns_404(db_client):
    resp = await db_client.get("/api/assessment/latest")
    assert resp.status_code == 404
