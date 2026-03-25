"""Tests for the health endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock


def test_health_opencode_up(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["opensec"] == "ok"
    assert data["opencode"] == "ok"


def test_health_opencode_down(client, mock_opencode_process):
    mock_opencode_process.health_check = AsyncMock(return_value=False)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["opensec"] == "ok"
    assert data["opencode"] == "unavailable"
