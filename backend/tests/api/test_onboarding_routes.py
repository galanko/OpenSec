"""Route tests for D1 onboarding (IMPL-0002)."""

from __future__ import annotations

import asyncio

import pytest

from opensec.api._engine_dep import get_assessment_engine
from opensec.main import app
from opensec.models import CriteriaSnapshot
from tests.fakes.assessment_engine import FakeAssessmentEngine


@pytest.fixture
def fake_engine():
    engine = FakeAssessmentEngine(
        grade="B",
        criteria=CriteriaSnapshot(posture_checks_total=2, posture_checks_passing=1),
        posture_checks=[{"check_name": "branch_protection", "status": "pass"}],
    )
    app.dependency_overrides[get_assessment_engine] = lambda: engine
    try:
        yield engine
    finally:
        app.dependency_overrides.pop(get_assessment_engine, None)


async def _drain() -> None:
    tasks = list(getattr(app.state, "assessment_tasks", []))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_connect_repo_creates_assessment(db_client, fake_engine):
    resp = await db_client.post(
        "/api/onboarding/repo",
        json={"repo_url": "https://github.com/a/b", "github_token": "ghp_xxx"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment_id"]
    assert data["repo_url"] == "https://github.com/a/b"

    await _drain()
    assert fake_engine.call_count == 1

    # Token persisted to the app_setting store (ad-hoc MVP storage — Session G
    # swaps in the credential vault; the test just confirms the route wires it).
    from opensec.db.connection import _db
    from opensec.db.repo_setting import get_setting

    setting = await get_setting(_db, "onboarding.github_token")
    assert setting is not None
    assert setting.value == {"token": "ghp_xxx"}


async def test_connect_repo_empty_url_returns_422(db_client, fake_engine):
    resp = await db_client.post(
        "/api/onboarding/repo",
        json={"repo_url": "   ", "github_token": "ghp_xxx"},
    )
    assert resp.status_code == 422


async def test_complete_onboarding_happy_path(db_client, fake_engine):
    run = await db_client.post(
        "/api/onboarding/repo",
        json={"repo_url": "https://github.com/a/b", "github_token": "ghp_xxx"},
    )
    aid = run.json()["assessment_id"]
    await _drain()

    resp = await db_client.post("/api/onboarding/complete", json={"assessment_id": aid})
    assert resp.status_code == 200
    assert resp.json() == {"onboarding_completed": True}

    from opensec.db.connection import _db
    from opensec.db.repo_setting import get_setting

    setting = await get_setting(_db, "onboarding.completed")
    assert setting.value == {"completed": True}


async def test_complete_onboarding_not_complete_returns_409(db_client):
    # Manually seed a pending assessment without running the fake engine.
    from opensec.db.connection import _db
    from opensec.db.dao.assessment import create_assessment
    from opensec.models import AssessmentCreate

    a = await create_assessment(_db, AssessmentCreate(repo_url="https://github.com/a/b"))

    resp = await db_client.post("/api/onboarding/complete", json={"assessment_id": a.id})
    assert resp.status_code == 409


async def test_complete_onboarding_unknown_assessment_returns_404(db_client):
    resp = await db_client.post("/api/onboarding/complete", json={"assessment_id": "nope"})
    assert resp.status_code == 404
