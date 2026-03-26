"""Tests for AgentRun endpoints."""

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


async def test_create_agent_run(db_client, workspace_id):
    resp = await db_client.post(
        f"/api/workspaces/{workspace_id}/agent-runs",
        json={"agent_type": "finding_enricher"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["agent_type"] == "finding_enricher"
    assert data["status"] == "queued"
    assert data["workspace_id"] == workspace_id


async def test_create_agent_run_with_input(db_client, workspace_id):
    resp = await db_client.post(
        f"/api/workspaces/{workspace_id}/agent-runs",
        json={
            "agent_type": "owner_resolver",
            "input_json": {"asset_id": "srv-01"},
        },
    )
    assert resp.status_code == 201
    assert resp.json()["input_json"] == {"asset_id": "srv-01"}


async def test_list_agent_runs(db_client, workspace_id):
    await db_client.post(
        f"/api/workspaces/{workspace_id}/agent-runs",
        json={"agent_type": "finding_enricher"},
    )
    await db_client.post(
        f"/api/workspaces/{workspace_id}/agent-runs",
        json={"agent_type": "owner_resolver"},
    )

    resp = await db_client.get(f"/api/workspaces/{workspace_id}/agent-runs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_get_agent_run(db_client, workspace_id):
    create_resp = await db_client.post(
        f"/api/workspaces/{workspace_id}/agent-runs",
        json={"agent_type": "finding_enricher"},
    )
    run_id = create_resp.json()["id"]

    resp = await db_client.get(f"/api/workspaces/{workspace_id}/agent-runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


async def test_get_agent_run_not_found(db_client, workspace_id):
    resp = await db_client.get(f"/api/workspaces/{workspace_id}/agent-runs/nonexistent")
    assert resp.status_code == 404


async def test_update_agent_run_status(db_client, workspace_id):
    create_resp = await db_client.post(
        f"/api/workspaces/{workspace_id}/agent-runs",
        json={"agent_type": "finding_enricher"},
    )
    run_id = create_resp.json()["id"]

    # Transition to running.
    resp = await db_client.patch(
        f"/api/workspaces/{workspace_id}/agent-runs/{run_id}",
        json={"status": "running"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"
    assert data["started_at"] is not None

    # Transition to completed with results.
    resp = await db_client.patch(
        f"/api/workspaces/{workspace_id}/agent-runs/{run_id}",
        json={
            "status": "completed",
            "summary_markdown": "Found CVE details",
            "confidence": 0.95,
            "evidence_json": {"cve": "CVE-2024-1234"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None
    assert data["confidence"] == 0.95
    assert data["evidence_json"]["cve"] == "CVE-2024-1234"


async def test_update_agent_run_not_found(db_client, workspace_id):
    resp = await db_client.patch(
        f"/api/workspaces/{workspace_id}/agent-runs/nonexistent",
        json={"status": "running"},
    )
    assert resp.status_code == 404
