"""E2E: Session lifecycle with real OpenCode."""

from __future__ import annotations

import time


def test_create_session(app_client):
    resp = app_client.post("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"]
    assert data["id"].startswith("ses_")


def test_list_sessions_includes_new(app_client):
    # Create a session
    create_resp = app_client.post("/api/sessions")
    assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
    new_id = create_resp.json()["id"]
    time.sleep(0.5)  # Give OpenCode time to register

    # List should include it
    list_resp = app_client.get("/api/sessions")
    assert list_resp.status_code == 200
    ids = [s["id"] for s in list_resp.json()]
    assert new_id in ids


def test_get_session_details(app_client):
    create_resp = app_client.post("/api/sessions")
    assert create_resp.status_code == 200
    session_id = create_resp.json()["id"]
    time.sleep(0.5)

    detail_resp = app_client.get(f"/api/sessions/{session_id}")
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert data["id"] == session_id


def test_create_multiple_sessions(app_client):
    ids = set()
    for _ in range(3):
        resp = app_client.post("/api/sessions")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        ids.add(resp.json()["id"])
        time.sleep(0.3)  # Don't hammer OpenCode
    assert len(ids) == 3  # all unique
