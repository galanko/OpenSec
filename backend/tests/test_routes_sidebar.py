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


# ---------------------------------------------------------------------------
# Plan approval (PRD-0006 Story 3 — Phase 1 stop-on-plan gate)
# ---------------------------------------------------------------------------


async def test_approve_plan_sets_approved_flag(db_client, workspace_id):
    """POST /workspaces/:id/plan/approve flips sidebar.plan.approved=True
    without overwriting other sidebar fields."""
    await db_client.put(
        f"/api/workspaces/{workspace_id}/sidebar",
        json={
            "summary": {"text": "Critical bug"},
            "plan": {"plan_steps": ["Step 1"], "estimated_effort": "2h"},
        },
    )
    resp = await db_client.post(f"/api/workspaces/{workspace_id}/plan/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"]["approved"] is True
    # Non-plan fields preserved.
    assert data["summary"] == {"text": "Critical bug"}
    # Plan internals preserved.
    assert data["plan"]["plan_steps"] == ["Step 1"]
    assert data["plan"]["estimated_effort"] == "2h"


async def test_approve_plan_404_when_no_plan(db_client, workspace_id):
    """Approving before the planner runs returns 404 (no plan to approve)."""
    resp = await db_client.post(f"/api/workspaces/{workspace_id}/plan/approve")
    assert resp.status_code == 404


async def test_approve_plan_404_when_workspace_missing(db_client):
    resp = await db_client.post("/api/workspaces/does-not-exist/plan/approve")
    assert resp.status_code == 404


async def test_approve_plan_idempotent(db_client, workspace_id):
    """Re-approving an already-approved plan is a no-op (still 200)."""
    await db_client.put(
        f"/api/workspaces/{workspace_id}/sidebar",
        json={"plan": {"plan_steps": ["x"]}},
    )
    await db_client.post(f"/api/workspaces/{workspace_id}/plan/approve")
    resp = await db_client.post(f"/api/workspaces/{workspace_id}/plan/approve")
    assert resp.status_code == 200
    assert resp.json()["plan"]["approved"] is True
