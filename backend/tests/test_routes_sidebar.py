"""Tests for SidebarState endpoints."""

from __future__ import annotations

import pytest


@pytest.fixture
async def workspace_id(db_client):
    """Create a finding + workspace and return the workspace ID."""
    f = await db_client.post(
        "/api/findings",
        json={"source_type": "test", "source_id": "f-1", "title": "Test"},
    )
    ws = await db_client.post("/api/workspaces", json={"finding_id": f.json()["id"]})
    return ws.json()["id"]


async def test_upsert_sidebar_create(db_client, workspace_id):
    resp = await db_client.put(
        f"/api/workspaces/{workspace_id}/sidebar",
        json={"summary": {"text": "Critical RCE in libfoo"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == workspace_id
    assert data["summary"] == {"text": "Critical RCE in libfoo"}
    assert data["updated_at"]


async def test_upsert_sidebar_update(db_client, workspace_id):
    # Initial create.
    await db_client.put(
        f"/api/workspaces/{workspace_id}/sidebar",
        json={"summary": {"text": "Initial"}},
    )
    # Update overwrites.
    resp = await db_client.put(
        f"/api/workspaces/{workspace_id}/sidebar",
        json={
            "summary": {"text": "Updated"},
            "owner": {"team": "platform", "confidence": 0.9},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == {"text": "Updated"}
    assert data["owner"]["team"] == "platform"


async def test_get_sidebar(db_client, workspace_id):
    await db_client.put(
        f"/api/workspaces/{workspace_id}/sidebar",
        json={"plan": {"steps": ["patch", "deploy", "verify"]}},
    )
    resp = await db_client.get(f"/api/workspaces/{workspace_id}/sidebar")
    assert resp.status_code == 200
    assert resp.json()["plan"]["steps"] == ["patch", "deploy", "verify"]


async def test_get_sidebar_not_found(db_client, workspace_id):
    resp = await db_client.get(f"/api/workspaces/{workspace_id}/sidebar")
    assert resp.status_code == 404


async def test_sidebar_all_fields(db_client, workspace_id):
    payload = {
        "summary": {"text": "summary"},
        "evidence": {"cve": "CVE-2024-1234"},
        "owner": {"team": "security"},
        "plan": {"steps": ["fix"]},
        "definition_of_done": {"criteria": ["scan clean"]},
        "linked_ticket": {"key": "SEC-100"},
        "validation": {"state": "pending"},
        "similar_cases": {"count": 3},
    }
    resp = await db_client.put(
        f"/api/workspaces/{workspace_id}/sidebar", json=payload
    )
    assert resp.status_code == 200
    data = resp.json()
    for key, value in payload.items():
        assert data[key] == value
