"""Shared test fixtures."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from opensec.engine.models import SessionDetail, SessionSummary


@asynccontextmanager
async def _noop_lifespan(app):
    yield


@pytest.fixture
def mock_opencode_process():
    """Mock the OpenCode process manager so tests don't need a real server."""
    with patch("opensec.api.routes.health.opencode_process") as mock_proc:
        mock_proc.health_check = AsyncMock(return_value=True)
        mock_proc.is_running = True
        mock_proc.is_healthy = True
        yield mock_proc


@pytest.fixture
def mock_opencode_client():
    """Mock the OpenCode HTTP client in all route modules."""
    with (
        patch("opensec.api.routes.sessions.opencode_client") as mock_sessions,
        patch("opensec.api.routes.chat.opencode_client") as mock_chat,
    ):
        # Default behaviors
        for m in (mock_sessions, mock_chat):
            m.create_session = AsyncMock(
                return_value=SessionSummary(id="test-session-123")
            )
            m.list_sessions = AsyncMock(
                return_value=[SessionSummary(id="test-session-123")]
            )
            m.get_session = AsyncMock(
                return_value=SessionDetail(id="test-session-123", messages=[])
            )
            m.send_message = AsyncMock(return_value={"status": "ok"})
            m.stream_events = AsyncMock()
            m.health_check = AsyncMock(return_value=True)

        # Return both mocks so tests can override per-module
        yield type("Mocks", (), {
            "sessions": mock_sessions,
            "chat": mock_chat,
        })()


@pytest.fixture
def client(mock_opencode_process, mock_opencode_client):
    """FastAPI test client with mocked dependencies."""
    from opensec.main import app

    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as c:
        yield c
