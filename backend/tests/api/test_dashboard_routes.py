"""Route tests for D4 dashboard (IMPL-0002)."""

from __future__ import annotations

import pytest

from opensec.models import (
    AssessmentCreate,
    CompletionCreate,
    CriteriaSnapshot,
    FindingCreate,
    PostureCheckCreate,
)


async def test_dashboard_empty(db_client):
    resp = await db_client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment"] is None
    assert data["grade"] is None
    assert data["criteria"] == CriteriaSnapshot().model_dump()
    assert data["findings_count_by_priority"] == {}
    assert data["posture_pass_count"] == 0
    assert data["posture_total_count"] == 0
    assert data["completion_id"] is None


@pytest.fixture
def criteria():
    return CriteriaSnapshot(
        no_critical_vulns=True,
        posture_checks_passing=3,
        posture_checks_total=4,
        security_md_present=True,
        dependabot_present=False,
    )


async def test_dashboard_seeded(db_client, criteria):
    from opensec.db.connection import _db
    from opensec.db.dao.assessment import create_assessment, set_assessment_result
    from opensec.db.dao.completion import create_completion
    from opensec.db.dao.posture_check import create_posture_check
    from opensec.db.repo_finding import create_finding

    assert _db is not None
    a = await create_assessment(_db, AssessmentCreate(repo_url="https://github.com/a/b"))
    await set_assessment_result(_db, a.id, grade="B", criteria_snapshot=criteria)

    # Posture: 3 pass, 1 fail, 1 advisory (advisory counts as neither pass nor fail).
    for name, status in [
        ("branch_protection", "pass"),
        ("no_force_pushes", "pass"),
        ("signed_commits", "pass"),
        ("security_md", "fail"),
        ("dependabot_config", "advisory"),
    ]:
        await create_posture_check(
            _db,
            PostureCheckCreate(assessment_id=a.id, check_name=name, status=status),
        )

    # Findings with mixed priorities — scoped to the current assessment so
    # the dashboard counts them (non-assessment findings are excluded by the
    # current-assessment scope filter).
    for pri in ["P1", "P1", "P2", "P3"]:
        await create_finding(
            _db,
            FindingCreate(
                source_type="opensec-assessment",
                source_id=f"v-{pri}-{id(pri)}",
                title=f"x-{pri}",
                normalized_priority=pri,
            ),
        )

    completion = await create_completion(
        _db,
        CompletionCreate(
            assessment_id=a.id,
            repo_url="https://github.com/a/b",
            criteria_snapshot=criteria,
        ),
    )

    resp = await db_client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessment"]["id"] == a.id
    assert data["grade"] == "B"
    assert data["criteria"]["posture_checks_passing"] == 3
    assert data["findings_count_by_priority"] == {"P1": 2, "P2": 1, "P3": 1}
    assert data["posture_pass_count"] == 3
    assert data["posture_total_count"] == 5
    assert data["completion_id"] == completion.id
