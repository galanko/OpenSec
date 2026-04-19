"""Unit tests for the posture_check DAO (IMPL-0002 Milestone A2)."""

from __future__ import annotations

from opensec.models import AssessmentCreate, PostureCheckCreate


async def _new_assessment(db, repo_url: str = "https://github.com/acme/web"):
    from opensec.db.dao.assessment import create_assessment

    return await create_assessment(db, AssessmentCreate(repo_url=repo_url))


async def test_create_posture_check(db):
    from opensec.db.dao.posture_check import create_posture_check

    a = await _new_assessment(db)
    check = await create_posture_check(
        db,
        PostureCheckCreate(
            assessment_id=a.id,
            check_name="branch_protection",
            status="pass",
            detail={"protected_branches": ["main"]},
        ),
    )
    assert check.id
    assert check.assessment_id == a.id
    assert check.check_name == "branch_protection"
    assert check.status == "pass"
    assert check.detail == {"protected_branches": ["main"]}
    assert check.created_at is not None


async def test_list_posture_checks_for_assessment(db):
    from opensec.db.dao.posture_check import (
        create_posture_check,
        list_posture_checks_for_assessment,
    )

    a = await _new_assessment(db)
    await create_posture_check(
        db, PostureCheckCreate(assessment_id=a.id, check_name="branch_protection", status="pass")
    )
    await create_posture_check(
        db, PostureCheckCreate(assessment_id=a.id, check_name="signed_commits", status="advisory")
    )

    # Unrelated assessment's checks should not leak in.
    other = await _new_assessment(db, "https://github.com/z/z")
    await create_posture_check(
        db, PostureCheckCreate(assessment_id=other.id, check_name="no_force_pushes", status="pass")
    )

    checks = await list_posture_checks_for_assessment(db, a.id)
    names = {c.check_name for c in checks}
    assert names == {"branch_protection", "signed_commits"}


async def test_upsert_posture_check_is_idempotent_by_name(db):
    from opensec.db.dao.posture_check import (
        list_posture_checks_for_assessment,
        upsert_posture_check,
    )

    a = await _new_assessment(db)
    await upsert_posture_check(
        db,
        PostureCheckCreate(
            assessment_id=a.id,
            check_name="security_md",
            status="fail",
            detail={"reason": "missing"},
        ),
    )
    # Second write with same (assessment_id, check_name) — should replace, not duplicate.
    updated = await upsert_posture_check(
        db,
        PostureCheckCreate(
            assessment_id=a.id,
            check_name="security_md",
            status="pass",
            detail={"found": True},
        ),
    )
    assert updated.status == "pass"
    assert updated.detail == {"found": True}

    checks = await list_posture_checks_for_assessment(db, a.id)
    assert len(checks) == 1
    assert checks[0].status == "pass"


async def test_detail_nullable(db):
    from opensec.db.dao.posture_check import create_posture_check

    a = await _new_assessment(db)
    check = await create_posture_check(
        db,
        PostureCheckCreate(
            assessment_id=a.id, check_name="no_secrets_in_code", status="unknown", detail=None
        ),
    )
    assert check.detail is None
