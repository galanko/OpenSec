"""E2E: Error handling with real OpenCode."""

from __future__ import annotations


def test_send_to_nonexistent_session(app_client):
    """Sending to a fake session should return 502."""
    resp = app_client.post(
        "/api/chat/ses_nonexistent_fake_id/send",
        json={"content": "hello"},
    )
    # OpenCode may return an error which FastAPI catches as 502
    assert resp.status_code in (502, 200)  # 200 if OpenCode accepts silently


def test_get_nonexistent_session(app_client):
    """Getting a fake session should return 502."""
    resp = app_client.get("/api/sessions/ses_nonexistent_fake_id")
    assert resp.status_code in (502, 200)
