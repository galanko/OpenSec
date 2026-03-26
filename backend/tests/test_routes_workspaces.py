"""Tests for Workspace CRUD endpoints."""

from __future__ import annotations

import pytest


@pytest.fixture
async def finding_id(db_client):
    """Create a finding and return its ID (workspaces need a valid finding_id FK)."""
    resp = await db_client.post(
        "/api/findings",
        json={"source_type": "test", "source_id": "f-1", "title": "Test finding"},
    )
    return resp.json()["id"]


async def test_create_workspace(db_client, finding_id):
    resp = await db_client.post("/api/workspaces", json={"finding_id": finding_id})
    assert resp.status_code == 201
    data = resp.json()
    assert data["finding_id"] == finding_id
    assert data["state"] == "open"
    assert data["id"]


async def test_list_workspaces(db_client, finding_id):
    await db_client.post("/api/workspaces", json={"finding_id": finding_id})
    await db_client.post("/api/workspaces", json={"finding_id": finding_id})

    resp = await db_client.get("/api/workspaces")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_workspaces_filter_by_state(db_client, finding_id):
    await db_client.post("/api/workspaces", json={"finding_id": finding_id})

    resp = await db_client.get("/api/workspaces", params={"state": "open"})
    assert len(resp.json()) == 1

    resp = await db_client.get("/api/workspaces", params={"state": "closed"})
    assert len(resp.json()) == 0


async def test_list_workspaces_filter_by_finding(db_client, finding_id):
    await db_client.post("/api/workspaces", json={"finding_id": finding_id})

    resp = await db_client.get("/api/workspaces", params={"finding_id": finding_id})
    assert len(resp.json()) == 1

    resp = await db_client.get("/api/workspaces", params={"finding_id": "nonexistent"})
    assert len(resp.json()) == 0


async def test_get_workspace(db_client, finding_id):
    create_resp = await db_client.post("/api/workspaces", json={"finding_id": finding_id})
    ws_id = create_resp.json()["id"]

    resp = await db_client.get(f"/api/workspaces/{ws_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == ws_id


async def test_get_workspace_not_found(db_client):
    resp = await db_client.get("/api/workspaces/nonexistent")
    assert resp.status_code == 404


async def test_update_workspace(db_client, finding_id):
    create_resp = await db_client.post("/api/workspaces", json={"finding_id": finding_id})
    ws_id = create_resp.json()["id"]

    resp = await db_client.patch(
        f"/api/workspaces/{ws_id}",
        json={"state": "waiting", "current_focus": "enrichment"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "waiting"
    assert data["current_focus"] == "enrichment"


async def test_delete_workspace(db_client, finding_id):
    create_resp = await db_client.post("/api/workspaces", json={"finding_id": finding_id})
    ws_id = create_resp.json()["id"]

    resp = await db_client.delete(f"/api/workspaces/{ws_id}")
    assert resp.status_code == 204

    resp = await db_client.get(f"/api/workspaces/{ws_id}")
    assert resp.status_code == 404
