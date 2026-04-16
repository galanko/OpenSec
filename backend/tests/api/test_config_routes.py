"""Feature-flag config route (Session G)."""

from __future__ import annotations


async def test_feature_flags_default_off(db_client) -> None:
    """``v1_1_from_zero_to_secure_enabled`` defaults to False on every load.

    This is the contract ``@galanko`` relies on: merging Session G must NOT
    turn on the onboarding wizard for existing deployments. The canary flip
    is a separate env-var change post-merge.
    """
    resp = await db_client.get("/api/config/feature-flags")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"v1_1_from_zero_to_secure_enabled": False}


def test_settings_exposes_flag_from_env(monkeypatch) -> None:
    """Setting ``OPENSEC_V1_1_FROM_ZERO_TO_SECURE_ENABLED=true`` enables it."""
    from opensec.config import Settings

    monkeypatch.setenv("OPENSEC_V1_1_FROM_ZERO_TO_SECURE_ENABLED", "true")
    s = Settings()
    assert s.v1_1_from_zero_to_secure_enabled is True
