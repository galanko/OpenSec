"""Tests for chat endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock


def test_send_message_success(client):
    resp = client.post(
        "/api/chat/test-session-123/send",
        json={"content": "What is CVE-2024-1234?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "test-session-123"
    assert data["status"] == "sent"


def test_send_message_engine_down_still_returns_200(client, mock_opencode_client):
    """send_message is fire-and-forget — POST returns 200 even if the engine
    is down. Errors are logged in the background and surfaced via the SSE stream."""
    mock_opencode_client.chat.send_message = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    resp = client.post(
        "/api/chat/test-session-123/send",
        json={"content": "hello"},
    )
    assert resp.status_code == 200


def test_stream_events_endpoint_exists(client, mock_opencode_client):
    async def empty_iter():
        return
        yield  # makes this an async generator

    mock_opencode_client.chat.stream_events = AsyncMock(return_value=empty_iter())
    resp = client.get("/api/chat/test-session-123/stream")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")
