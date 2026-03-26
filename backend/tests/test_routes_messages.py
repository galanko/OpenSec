"""Tests for Message endpoints."""

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


async def test_create_message(db_client, workspace_id):
    resp = await db_client.post(
        f"/api/workspaces/{workspace_id}/messages",
        json={"role": "user", "content_markdown": "Hello"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["role"] == "user"
    assert data["content_markdown"] == "Hello"
    assert data["workspace_id"] == workspace_id


async def test_list_messages(db_client, workspace_id):
    await db_client.post(
        f"/api/workspaces/{workspace_id}/messages",
        json={"role": "user", "content_markdown": "First"},
    )
    await db_client.post(
        f"/api/workspaces/{workspace_id}/messages",
        json={"role": "assistant", "content_markdown": "Second"},
    )

    resp = await db_client.get(f"/api/workspaces/{workspace_id}/messages")
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) == 2
    # Messages sorted by created_at ASC.
    assert msgs[0]["content_markdown"] == "First"
    assert msgs[1]["content_markdown"] == "Second"


async def test_get_message(db_client, workspace_id):
    create_resp = await db_client.post(
        f"/api/workspaces/{workspace_id}/messages",
        json={"role": "user", "content_markdown": "Test"},
    )
    msg_id = create_resp.json()["id"]

    resp = await db_client.get(f"/api/workspaces/{workspace_id}/messages/{msg_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == msg_id


async def test_get_message_not_found(db_client, workspace_id):
    resp = await db_client.get(f"/api/workspaces/{workspace_id}/messages/nonexistent")
    assert resp.status_code == 404


async def test_get_message_wrong_workspace(db_client, workspace_id):
    create_resp = await db_client.post(
        f"/api/workspaces/{workspace_id}/messages",
        json={"role": "user", "content_markdown": "Test"},
    )
    msg_id = create_resp.json()["id"]

    resp = await db_client.get(f"/api/workspaces/other-ws/messages/{msg_id}")
    assert resp.status_code == 404


async def test_delete_message(db_client, workspace_id):
    create_resp = await db_client.post(
        f"/api/workspaces/{workspace_id}/messages",
        json={"role": "user", "content_markdown": "Delete me"},
    )
    msg_id = create_resp.json()["id"]

    resp = await db_client.delete(f"/api/workspaces/{workspace_id}/messages/{msg_id}")
    assert resp.status_code == 204

    resp = await db_client.get(f"/api/workspaces/{workspace_id}/messages/{msg_id}")
    assert resp.status_code == 404
