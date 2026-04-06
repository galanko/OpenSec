"""Tests for the AgentExecutor."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opensec.agents.errors import AgentBusyError
from opensec.agents.executor import AgentExecutor, build_agent_prompt
from opensec.models import AgentRun

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_agent_response(**overrides):
    """Build a valid agent JSON response."""
    data = {
        "summary": "Found CVE-2026-1234 with CVSS 9.1",
        "result_card_markdown": "## CVE-2026-1234\n\nCritical RCE",
        "structured_output": {
            "normalized_title": "CVE-2026-1234 RCE",
            "cve_ids": ["CVE-2026-1234"],
            "cvss_score": 9.1,
            "known_exploits": True,
        },
        "confidence": 0.92,
        "evidence_sources": ["NVD", "ExploitDB"],
        "suggested_next_action": "find_owner",
    }
    data.update(overrides)
    return f"Analysis complete.\n\n```json\n{json.dumps(data)}\n```"


def _make_mock_agent_run(workspace_id="ws-1", agent_type="finding_enricher", status="running"):
    return AgentRun(
        id="run-123",
        workspace_id=workspace_id,
        agent_type=agent_type,
        status=status,
    )


def _make_stream_events(response_text):
    """Create an async generator that mimics OpenCode's stream_events."""
    async def stream_events(session_id):
        yield {"type": "text", "content": response_text}
        yield {"type": "done"}
    return stream_events


def _make_mock_client(response_text):
    """Create a mock OpenCodeClient that returns a canned response."""
    client = AsyncMock()
    client.create_session.return_value = MagicMock(id="session-1")
    client.send_message.return_value = None
    client.stream_events = _make_stream_events(response_text)
    return client


@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    return pool


@pytest.fixture
def mock_context_builder():
    builder = AsyncMock()
    builder.update_context.return_value = 1  # new context_version
    return builder


@pytest.fixture
def mock_db():
    return AsyncMock()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAgentExecutor:
    @pytest.mark.asyncio
    async def test_happy_path(self, mock_pool, mock_context_builder, mock_db):
        """Full successful execution: send -> collect -> parse -> persist."""
        response_text = _make_agent_response()
        mock_pool.get_or_start.return_value = _make_mock_client(response_text)

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
            patch("opensec.agents.executor.map_and_upsert") as mock_sidebar,
        ):
            result = await executor.execute(
                "ws-1", "finding_enricher", mock_db, workspace_dir="/tmp/ws"
            )

        assert result.status == "completed"
        assert result.parse_result.success is True
        assert result.sidebar_updated is True
        assert result.context_version == 1
        assert result.duration_seconds > 0

        # Context builder should have been called
        mock_context_builder.update_context.assert_called_once()
        # Sidebar should have been updated
        mock_sidebar.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_failure_still_completes(self, mock_pool, mock_context_builder, mock_db):
        """When LLM returns text but no valid JSON, status is still completed."""
        response_text = "I analyzed the vulnerability but forgot to return JSON."
        mock_pool.get_or_start.return_value = _make_mock_client(response_text)

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
            patch("opensec.agents.executor.map_and_upsert") as mock_sidebar,
        ):
            result = await executor.execute(
                "ws-1", "finding_enricher", mock_db, workspace_dir="/tmp/ws"
            )

        assert result.status == "completed"
        assert result.parse_result.success is False
        assert result.sidebar_updated is False
        # Context builder should NOT have been called (no structured output)
        mock_context_builder.update_context.assert_not_called()
        mock_sidebar.assert_not_called()

    @pytest.mark.asyncio
    async def test_busy_workspace_raises(self, mock_pool, mock_context_builder, mock_db):
        """Another agent running → AgentBusyError."""
        existing_run = _make_mock_agent_run(status="running")
        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.list_agent_runs",
                return_value=[existing_run],
            ),pytest.raises(AgentBusyError, match="already running")
        ):
            await executor.execute(
                "ws-1", "finding_enricher", mock_db, workspace_dir="/tmp/ws"
            )

    @pytest.mark.asyncio
    async def test_process_start_failure(self, mock_pool, mock_context_builder, mock_db):
        """OpenCode process fails to start → status=failed."""
        mock_pool.get_or_start.side_effect = RuntimeError("No free ports")

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run") as mock_update,
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
        ):
            result = await executor.execute(
                "ws-1", "finding_enricher", mock_db, workspace_dir="/tmp/ws"
            )

        assert result.status == "failed"
        assert "No free ports" in (result.error or "")
        # Agent run should be marked failed in DB
        mock_update.assert_called_once()
        update_data = mock_update.call_args[0][2]
        assert update_data.status == "failed"

    @pytest.mark.asyncio
    async def test_timeout(self, mock_pool, mock_context_builder, mock_db):
        """Agent exceeds timeout → status=failed with timeout error."""
        # Create a stream that never completes
        client = AsyncMock()
        client.create_session.return_value = MagicMock(id="session-1")
        client.send_message.return_value = None

        async def slow_stream(session_id):
            yield {"type": "text", "content": "Starting analysis..."}
            await asyncio.sleep(10)  # Will be cancelled by timeout
            yield {"type": "done"}

        client.stream_events = slow_stream
        mock_pool.get_or_start.return_value = client

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
        ):
            result = await executor.execute(
                "ws-1", "finding_enricher", mock_db,
                workspace_dir="/tmp/ws", timeout=0.1,
            )

        assert result.status == "failed"
        assert "timed out" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_opencode_error_event(self, mock_pool, mock_context_builder, mock_db):
        """OpenCode returns an error event → status=failed."""
        client = AsyncMock()
        client.create_session.return_value = MagicMock(id="session-1")
        client.send_message.return_value = None

        async def error_stream(session_id):
            yield {"type": "error", "message": "Model rate limited"}

        client.stream_events = error_stream
        mock_pool.get_or_start.return_value = client

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
        ):
            result = await executor.execute(
                "ws-1", "finding_enricher", mock_db, workspace_dir="/tmp/ws"
            )

        assert result.status == "failed"
        assert "rate limited" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, mock_pool, mock_context_builder, mock_db):
        """on_progress callback receives text chunks."""
        response_text = _make_agent_response()
        mock_pool.get_or_start.return_value = _make_mock_client(response_text)

        progress_calls = []

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
            patch("opensec.agents.executor.map_and_upsert"),
        ):
            await executor.execute(
                "ws-1", "finding_enricher", mock_db,
                workspace_dir="/tmp/ws",
                on_progress=progress_calls.append,
            )

        assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_completed_run_not_blocking(self, mock_pool, mock_context_builder, mock_db):
        """A completed agent run should NOT block new executions."""
        completed_run = _make_mock_agent_run(status="completed")
        response_text = _make_agent_response()
        mock_pool.get_or_start.return_value = _make_mock_client(response_text)

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch(
                "opensec.agents.executor.list_agent_runs",
                return_value=[completed_run],
            ),
            patch("opensec.agents.executor.map_and_upsert"),
        ):
            result = await executor.execute(
                "ws-1", "finding_enricher", mock_db, workspace_dir="/tmp/ws"
            )

        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_context_builder_failure(self, mock_pool, mock_context_builder, mock_db):
        """If context_builder.update_context fails, result persists in DB."""
        response_text = _make_agent_response()
        mock_pool.get_or_start.return_value = _make_mock_client(response_text)
        mock_context_builder.update_context.side_effect = OSError("Disk full")

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
        ):
            result = await executor.execute(
                "ws-1", "finding_enricher", mock_db, workspace_dir="/tmp/ws"
            )

        assert result.status == "failed"
        assert "Disk full" in (result.error or "")

    @pytest.mark.asyncio
    async def test_owner_resolver_agent_type(self, mock_pool, mock_context_builder, mock_db):
        """Verify executor works with different agent types."""
        data = {
            "summary": "Owner identified",
            "result_card_markdown": "## Owner\n\nPlatform Team",
            "structured_output": {
                "recommended_owner": "Platform Team",
                "candidates": [],
            },
            "confidence": 0.88,
            "evidence_sources": ["CODEOWNERS"],
            "suggested_next_action": "assess_exposure",
        }
        response_text = f"```json\n{json.dumps(data)}\n```"
        mock_pool.get_or_start.return_value = _make_mock_client(response_text)

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(agent_type="owner_resolver"),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
            patch("opensec.agents.executor.map_and_upsert"),
        ):
            result = await executor.execute(
                "ws-1", "owner_resolver", mock_db, workspace_dir="/tmp/ws"
            )

        assert result.status == "completed"
        assert result.parse_result.summary == "Owner identified"

    @pytest.mark.asyncio
    async def test_retry_on_parse_failure(self, mock_pool, mock_context_builder, mock_db):
        """When first attempt returns no JSON, retry with corrective prompt."""
        bad_response = "Let me read the context files to analyze this finding..."
        good_response = _make_agent_response()

        # Client that returns bad response first, then good on retry
        call_count = 0
        client = AsyncMock()
        client.create_session.return_value = MagicMock(id="session-1")
        client.send_message.return_value = None

        async def multi_stream(session_id):
            nonlocal call_count
            call_count += 1
            text = bad_response if call_count == 1 else good_response
            yield {"type": "text", "content": text}
            yield {"type": "done"}

        client.stream_events = multi_stream
        mock_pool.get_or_start.return_value = client

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
            patch("opensec.agents.executor.map_and_upsert"),
        ):
            result = await executor.execute(
                "ws-1", "finding_enricher", mock_db, workspace_dir="/tmp/ws"
            )

        assert result.status == "completed"
        assert result.parse_result.success is True
        assert result.sidebar_updated is True
        # Two send_message calls: initial prompt + retry
        assert client.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_still_fails(self, mock_pool, mock_context_builder, mock_db):
        """When both attempts fail to produce JSON, result is completed but not parsed."""
        bad_response = "I'll try to read the files instead of returning JSON."
        mock_pool.get_or_start.return_value = _make_mock_client(bad_response)

        executor = AgentExecutor(mock_pool, mock_context_builder)

        with (
            patch(
                "opensec.agents.executor.create_agent_run",
                return_value=_make_mock_agent_run(),
            ),
            patch("opensec.agents.executor.update_agent_run"),
            patch("opensec.agents.executor.list_agent_runs", return_value=[]),
            patch("opensec.agents.executor.map_and_upsert") as mock_sidebar,
        ):
            result = await executor.execute(
                "ws-1", "finding_enricher", mock_db, workspace_dir="/tmp/ws"
            )

        assert result.status == "completed"
        assert result.parse_result.success is False
        assert result.sidebar_updated is False
        mock_sidebar.assert_not_called()


class TestBuildAgentPrompt:
    def test_includes_output_contract(self):
        """Prompt includes the per-agent structured_output schema."""
        prompt = build_agent_prompt("finding_enricher")
        assert "normalized_title" in prompt
        assert "cve_ids" in prompt
        assert "cvss_score" in prompt

    def test_includes_json_instruction(self):
        """Prompt explicitly requests JSON-only output."""
        prompt = build_agent_prompt("finding_enricher")
        assert "programmatic agent execution" in prompt.lower()
        assert "no tool calls" in prompt.lower()
        assert "no file reads" in prompt.lower()

    def test_all_agent_types_have_contracts(self):
        """Every known agent type produces a prompt with its output contract."""
        agent_types = [
            "finding_enricher",
            "owner_resolver",
            "exposure_analyzer",
            "remediation_planner",
            "validation_checker",
        ]
        for agent_type in agent_types:
            prompt = build_agent_prompt(agent_type)
            assert "structured_output" in prompt, f"Missing contract for {agent_type}"
            assert "```json" in prompt

    def test_unknown_agent_type_still_works(self):
        """Unknown agent types produce a valid prompt without a specific contract."""
        prompt = build_agent_prompt("unknown_agent")
        assert "```json" in prompt
        assert "summary" in prompt
