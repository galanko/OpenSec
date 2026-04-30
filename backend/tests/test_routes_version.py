"""Tests for the /api/version handshake endpoint."""

from __future__ import annotations


def test_version_returns_handshake(client):
    resp = client.get("/api/version")
    assert resp.status_code == 200
    data = resp.json()
    # All four fields are required by the CLI handshake.
    assert data["opensec"]
    assert data["opencode"]
    assert data["schema_version"] == "1"
    assert data["min_cli"]


def test_version_opensec_matches_version_file(client):
    """The opensec field should reflect the VERSION file at the repo root."""
    from opensec.config import settings

    resp = client.get("/api/version")
    assert resp.json()["opensec"] == settings.opensec_version


def test_version_opencode_matches_pinned_engine(client):
    """The opencode field should reflect .opencode-version."""
    from opensec.config import settings

    resp = client.get("/api/version")
    assert resp.json()["opencode"] == settings.opencode_version
