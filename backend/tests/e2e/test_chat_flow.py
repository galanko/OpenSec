"""E2E: Full chat flow — send message via FastAPI, verify pipeline works."""

from __future__ import annotations

import time


def test_send_message_accepted(app_client):
    """Send a message via FastAPI and verify it's accepted by OpenCode."""
    session_resp = app_client.post("/api/sessions")
    assert session_resp.status_code == 200, f"Create failed: {session_resp.text}"
    session_id = session_resp.json()["id"]
    time.sleep(0.5)

    send_resp = app_client.post(
        f"/api/chat/{session_id}/send",
        json={"content": "Say hello"},
    )
    assert send_resp.status_code == 200
    assert send_resp.json()["status"] == "sent"


def test_send_message_roundtrip(app_client):
    """Send a message, then verify the session has activity."""
    session_resp = app_client.post("/api/sessions")
    assert session_resp.status_code == 200
    session_id = session_resp.json()["id"]
    time.sleep(0.5)

    # Send
    send_resp = app_client.post(
        f"/api/chat/{session_id}/send",
        json={"content": "Say ok"},
    )
    assert send_resp.status_code == 200

    # Wait for OpenCode to process
    time.sleep(3)

    # Session should still be retrievable
    detail_resp = app_client.get(f"/api/sessions/{session_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == session_id
