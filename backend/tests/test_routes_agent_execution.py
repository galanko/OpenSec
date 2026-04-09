"""Tests for the agent execution API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from opensec.agents.errors import AgentBusyError
from opensec.agents.executor import AgentExecutionResult
from opensec.agents.output_parser import ParseResult
from opensec.api.routes.agent_execution import router
from opensec.db.connection import get_db
from opensec.models import Workspace

# ---------------------------------------------------------------------------
# App fixture with mock DB dependency
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def app(mock_db):
    test_app = FastAPI()
    test_app.include_router(router, prefix="/api")

    # Override get_db dependency
    async def _mock_get_db():
        yield mock_db

    test_app.dependency_overrides[get_db] = _mock_get_db

    # Mock executor and context builder
    test_app.state.agent_executor = AsyncMock()
    test_app.state.context_builder = AsyncMock()

    return test_app


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


def _make_workspace(workspace_id="ws-1"):
    return Workspace(
        id=workspace_id,
        finding_id="f-1",
        state="open",
        workspace_dir="/tmp/workspaces/ws-1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_execution_result(agent_type="finding_enricher", status="completed"):
    return AgentExecutionResult(
        agent_run_id="run-123",
        agent_type=agent_type,
        status=status,
        parse_result=ParseResult(success=True, raw_text="test"),
    )


# ---------------------------------------------------------------------------
# Execute endpoint
# ---------------------------------------------------------------------------


class TestExecuteEndpoint:
    @pytest.mark.asyncio
    async def test_execute_returns_202(self, app, client):
        """Execute returns 202 immediately (background task)."""
        executor = app.state.agent_executor
        executor._check_not_busy = AsyncMock()
        executor.get_active_run_id = lambda ws_id: "run-123"
        executor.execute = AsyncMock(return_value=_make_execution_result())

        with patch(
            "opensec.api.routes.agent_execution.get_workspace",
            return_value=_make_workspace(),
        ):
            resp = await client.post(
                "/api/workspaces/ws-1/agents/finding_enricher/execute"
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data["agent_type"] == "finding_enricher"
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_execute_workspace_not_found(self, client):
        with patch(
            "opensec.api.routes.agent_execution.get_workspace",
            return_value=None,
        ):
            resp = await client.post(
                "/api/workspaces/ws-999/agents/finding_enricher/execute"
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_execute_invalid_agent_type(self, client):
        with patch(
            "opensec.api.routes.agent_execution.get_workspace",
            return_value=_make_workspace(),
        ):
            resp = await client.post(
                "/api/workspaces/ws-1/agents/invalid_agent/execute"
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_execute_busy_returns_409(self, app, client):
        """Pre-flight busy check returns 409 before launching background task."""
        executor = app.state.agent_executor
        executor._check_not_busy = AsyncMock(side_effect=AgentBusyError("busy"))

        with patch(
            "opensec.api.routes.agent_execution.get_workspace",
            return_value=_make_workspace(),
        ):
            resp = await client.post(
                "/api/workspaces/ws-1/agents/finding_enricher/execute"
            )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Suggest-next endpoint
# ---------------------------------------------------------------------------


class TestSuggestNextEndpoint:
    @pytest.mark.asyncio
    async def test_suggest_enricher(self, app, client):
        app.state.context_builder.get_context_snapshot.return_value = {
            "finding": {"id": "f-1"},
            "enrichment": None,
            "ownership": None,
            "exposure": None,
            "plan": None,
            "validation": None,
            "agent_run_history": [],
        }

        with patch(
            "opensec.api.routes.agent_execution.get_workspace",
            return_value=_make_workspace(),
        ):
            resp = await client.get(
                "/api/workspaces/ws-1/pipeline/suggest-next"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "finding_enricher"
        assert data["priority"] == "recommended"

    @pytest.mark.asyncio
    async def test_suggest_none_when_complete(self, app, client):
        app.state.context_builder.get_context_snapshot.return_value = {
            "finding": {"id": "f-1"},
            "enrichment": {"normalized_title": "T"},
            "ownership": {"recommended_owner": "A"},
            "exposure": {"recommended_urgency": "high"},
            "plan": {"plan_steps": ["1"]},
            "validation": {"verdict": "fixed", "recommendation": "close"},
            "agent_run_history": [],
        }

        with patch(
            "opensec.api.routes.agent_execution.get_workspace",
            return_value=_make_workspace(),
        ):
            resp = await client.get(
                "/api/workspaces/ws-1/pipeline/suggest-next"
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] is None


# ---------------------------------------------------------------------------
# Cancel endpoint
# ---------------------------------------------------------------------------


class TestCancelEndpoint:
    @pytest.mark.asyncio
    async def test_cancel_running_agent(self, client):
        from opensec.models import AgentRun

        mock_run = AgentRun(
            id="run-1",
            workspace_id="ws-1",
            agent_type="finding_enricher",
            status="running",
        )

        with (
            patch(
                "opensec.api.routes.agent_execution.get_agent_run",
                return_value=mock_run,
            ),
            patch(
                "opensec.api.routes.agent_execution.update_agent_run",
            ),
        ):
            resp = await client.post(
                "/api/workspaces/ws-1/agent-runs/run-1/cancel"
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_returns_400(self, client):
        from opensec.models import AgentRun

        mock_run = AgentRun(
            id="run-1",
            workspace_id="ws-1",
            agent_type="finding_enricher",
            status="completed",
        )

        with patch(
            "opensec.api.routes.agent_execution.get_agent_run",
            return_value=mock_run,
        ):
            resp = await client.post(
                "/api/workspaces/ws-1/agent-runs/run-1/cancel"
            )

        assert resp.status_code == 400
