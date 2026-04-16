"""Feature-flag config route."""

from __future__ import annotations


async def test_feature_flags_reports_current_value(db_client, monkeypatch) -> None:
    """Endpoint mirrors the current flag + bootstrap signals for the SPA."""
    from opensec.config import settings

    monkeypatch.setattr(settings, "v1_1_from_zero_to_secure_enabled", False)
    resp = await db_client.get("/api/config/feature-flags")
    assert resp.status_code == 200
    assert resp.json() == {
        "v1_1_from_zero_to_secure_enabled": False,
        "onboarding_completed": False,
        "has_any_assessment": False,
    }


async def test_feature_flags_reports_assessment_presence(db_client) -> None:
    """``has_any_assessment`` flips to True once at least one row exists."""
    from opensec.db.connection import _db
    from opensec.db.dao.assessment import create_assessment
    from opensec.models import AssessmentCreate

    assert _db is not None
    await create_assessment(_db, AssessmentCreate(repo_url="https://github.com/acme/x"))

    resp = await db_client.get("/api/config/feature-flags")
    body = resp.json()
    assert body["has_any_assessment"] is True
    assert body["onboarding_completed"] is False


async def test_feature_flags_reports_onboarding_completed(db_client) -> None:
    """``onboarding_completed`` mirrors the app_setting written by the complete endpoint."""
    from opensec.db.connection import _db
    from opensec.db.repo_setting import upsert_setting

    assert _db is not None
    await upsert_setting(_db, "onboarding.completed", {"completed": True})

    resp = await db_client.get("/api/config/feature-flags")
    body = resp.json()
    assert body["onboarding_completed"] is True


def test_settings_flag_defaults_off() -> None:
    """A fresh ``Settings()`` with no env override has the flag off by default."""
    from opensec.config import Settings

    assert Settings().v1_1_from_zero_to_secure_enabled is False


def test_settings_exposes_flag_from_env(monkeypatch) -> None:
    """Setting ``OPENSEC_V1_1_FROM_ZERO_TO_SECURE_ENABLED=true`` enables it."""
    from opensec.config import Settings

    monkeypatch.setenv("OPENSEC_V1_1_FROM_ZERO_TO_SECURE_ENABLED", "true")
    s = Settings()
    assert s.v1_1_from_zero_to_secure_enabled is True


async def test_gated_routes_return_404_when_flag_off(
    db_client, monkeypatch
) -> None:
    """Onboarding + assessment writes must be unreachable when the flag is off.

    Defence in depth for the frontend gate: a direct API call (stale tab, curl,
    a forgotten automation) must not be able to bypass the canary.
    """
    from opensec.config import settings

    monkeypatch.setattr(settings, "v1_1_from_zero_to_secure_enabled", False)

    r1 = await db_client.post(
        "/api/onboarding/repo",
        json={"repo_url": "https://github.com/acme/x", "github_token": "ghp_x"},
    )
    assert r1.status_code == 404

    r2 = await db_client.post(
        "/api/onboarding/complete", json={"assessment_id": "x"}
    )
    assert r2.status_code == 404

    r3 = await db_client.post(
        "/api/assessment/run", json={"repo_url": "https://github.com/acme/x"}
    )
    assert r3.status_code == 404
