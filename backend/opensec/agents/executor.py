"""AgentExecutor — runs a single sub-agent end-to-end.

The executor is the bridge between "user wants to run an agent" and
"agent results are persisted everywhere." It sends a prompt to the
workspace's OpenCode process, collects the response, parses it, and
persists results to context files, sidebar state, and the DB.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import httpx

from opensec.agents.errors import (
    AgentBusyError,
    AgentProcessError,
    AgentTimeoutError,
)
from opensec.agents.output_parser import ParseResult, parse_agent_response
from opensec.agents.sidebar_mapper import map_and_upsert
from opensec.db.repo_agent_run import (
    create_agent_run,
    list_agent_runs,
    update_agent_run,
)
from opensec.models import AgentRunCreate, AgentRunUpdate

if TYPE_CHECKING:
    from collections.abc import Callable

    import aiosqlite

    from opensec.engine.pool import WorkspaceProcessPool
    from opensec.workspace.context_builder import WorkspaceContextBuilder

logger = logging.getLogger(__name__)

# Default timeout for a single agent run (seconds).
DEFAULT_TIMEOUT: float = 120.0

# Prompt template sent to OpenCode to invoke a sub-agent.
_AGENT_PROMPT = (
    "Run the {agent_type} analysis on this finding. "
    "The workspace context files (CONTEXT.md, context/finding.json) contain "
    "the full details. Respond directly with your analysis as a JSON block "
    "with these fields: summary (string), result_card_markdown (markdown string), "
    "structured_output (object with your analysis), confidence (0.0-1.0), "
    "evidence_sources (list of strings), suggested_next_action (string). "
    "Do not use any tools — just analyze based on the context already available."
)


@dataclass
class AgentExecutionResult:
    """Result returned by the executor after running an agent."""

    agent_run_id: str
    agent_type: str
    status: Literal["completed", "failed"]
    parse_result: ParseResult
    sidebar_updated: bool = False
    context_version: int | None = None
    error: str | None = None
    duration_seconds: float = 0.0


class AgentExecutor:
    """Executes a single sub-agent within a workspace.

    Lifecycle:
        1. Check no other agent is running (→ AgentBusyError)
        2. Create AgentRun DB row (status=running)
        3. Get/start workspace OpenCode process
        4. Create fresh session, send prompt, collect response
        5. Parse response, persist to context + sidebar + DB
        6. Return AgentExecutionResult
    """

    def __init__(
        self,
        pool: WorkspaceProcessPool,
        context_builder: WorkspaceContextBuilder,
    ) -> None:
        self._pool = pool
        self._context_builder = context_builder

    async def execute(
        self,
        workspace_id: str,
        agent_type: str,
        db: aiosqlite.Connection,
        *,
        workspace_dir: str,
        timeout: float = DEFAULT_TIMEOUT,
        on_progress: Callable[[str], None] | None = None,
    ) -> AgentExecutionResult:
        """Execute a single agent run.

        Args:
            workspace_id: The workspace to run in.
            agent_type: One of the AgentType literals.
            db: Database connection.
            workspace_dir: Path to the workspace directory on disk.
            timeout: Maximum seconds to wait for the agent.
            on_progress: Optional callback for streaming text chunks.

        Returns:
            AgentExecutionResult with status and parsed output.

        Raises:
            AgentBusyError: If another agent is already running.
            AgentProcessError: If the workspace process can't start.
        """
        start_time = time.monotonic()

        # 1. Check no other agent is running
        await self._check_not_busy(db, workspace_id)

        # 2. Create AgentRun record
        agent_run = await create_agent_run(
            db,
            workspace_id,
            AgentRunCreate(agent_type=agent_type, status="running"),
        )

        try:
            # 3. Get or start workspace OpenCode process
            try:
                from pathlib import Path

                client = await self._pool.get_or_start(
                    workspace_id, Path(workspace_dir)
                )
            except (RuntimeError, TimeoutError) as exc:
                raise AgentProcessError(str(exc)) from exc

            # 4. Create fresh session
            session = await client.create_session()

            # 5+6. Subscribe to SSE event stream FIRST, then send the
            # message. OpenCode's POST /message may block for the entire
            # LLM call, so we need the stream connected before sending
            # to avoid missing early events.
            prompt = _AGENT_PROMPT.format(agent_type=agent_type)

            async def _send_after_delay() -> None:
                """Send message after a brief delay to let the stream connect."""
                await asyncio.sleep(0.5)
                with contextlib.suppress(httpx.ReadTimeout):
                    await client.send_message(session.id, prompt)

            send_task = asyncio.create_task(_send_after_delay())
            try:
                response_text = await self._collect_response(
                    client, session.id, timeout=timeout, on_progress=on_progress
                )
            finally:
                if not send_task.done():
                    send_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await send_task

            # 7. Parse response
            parse_result = parse_agent_response(
                response_text, agent_type=agent_type
            )

            # 8. Persist results
            sidebar_updated = False
            context_version = None

            if parse_result.success and parse_result.structured_output:
                # 8a. Update context files + re-render templates
                context_version = await self._context_builder.update_context(
                    db,
                    workspace_id,
                    agent_type,
                    parse_result.structured_output,
                    summary=parse_result.summary,
                )

                # 8b. Update sidebar state (read-merge-write)
                await map_and_upsert(
                    db,
                    workspace_id,
                    agent_type,
                    parse_result.structured_output,
                )
                sidebar_updated = True

            # 9. Update AgentRun in DB
            duration = time.monotonic() - start_time
            await update_agent_run(
                db,
                agent_run.id,
                AgentRunUpdate(
                    status="completed",
                    summary_markdown=parse_result.summary,
                    confidence=parse_result.confidence,
                    structured_output=parse_result.structured_output,
                    next_action_hint=parse_result.suggested_next_action,
                ),
            )

            return AgentExecutionResult(
                agent_run_id=agent_run.id,
                agent_type=agent_type,
                status="completed",
                parse_result=parse_result,
                sidebar_updated=sidebar_updated,
                context_version=context_version,
                duration_seconds=duration,
            )

        except AgentTimeoutError:
            duration = time.monotonic() - start_time
            await update_agent_run(
                db,
                agent_run.id,
                AgentRunUpdate(
                    status="failed",
                    summary_markdown="Agent timed out. Partial response may be available.",
                ),
            )
            return AgentExecutionResult(
                agent_run_id=agent_run.id,
                agent_type=agent_type,
                status="failed",
                parse_result=ParseResult(
                    success=False, raw_text="", error="timeout"
                ),
                error=f"Agent timed out after {timeout:.0f}s",
                duration_seconds=duration,
            )

        except AgentProcessError as exc:
            duration = time.monotonic() - start_time
            await update_agent_run(
                db,
                agent_run.id,
                AgentRunUpdate(
                    status="failed",
                    summary_markdown="Workspace AI engine unavailable.",
                    evidence_json={"error": str(exc)},
                ),
            )
            return AgentExecutionResult(
                agent_run_id=agent_run.id,
                agent_type=agent_type,
                status="failed",
                parse_result=ParseResult(
                    success=False, raw_text="", error=str(exc)
                ),
                error=str(exc),
                duration_seconds=duration,
            )

        except Exception as exc:
            duration = time.monotonic() - start_time
            logger.exception("Unexpected error during agent execution")
            await update_agent_run(
                db,
                agent_run.id,
                AgentRunUpdate(
                    status="failed",
                    summary_markdown=f"Unexpected error: {exc}",
                    evidence_json={"error": str(exc), "type": type(exc).__name__},
                ),
            )
            return AgentExecutionResult(
                agent_run_id=agent_run.id,
                agent_type=agent_type,
                status="failed",
                parse_result=ParseResult(
                    success=False, raw_text="", error=str(exc)
                ),
                error=str(exc),
                duration_seconds=duration,
            )

    async def _check_not_busy(
        self, db: aiosqlite.Connection, workspace_id: str
    ) -> None:
        """Raise AgentBusyError if another agent is already running."""
        runs = await list_agent_runs(db, workspace_id, limit=10)
        for run in runs:
            if run.status == "running":
                raise AgentBusyError(
                    f"Agent '{run.agent_type}' is already running "
                    f"in workspace {workspace_id}"
                )

    async def _collect_response(
        self,
        client: Any,
        session_id: str,
        *,
        timeout: float,
        on_progress: Callable[[str], None] | None = None,
        stall_timeout: float = 60.0,
    ) -> str:
        """Collect the full response from OpenCode via SSE stream.

        Accumulates text events until ``done`` or until no new events
        arrive for ``stall_timeout`` seconds (stall detection — OpenCode
        may not emit ``session.idle`` if the agent uses tools).

        Raises AgentTimeoutError if the overall timeout is exceeded.
        """
        collected_text = ""
        last_event_time = time.monotonic()

        async def _stream() -> str:
            nonlocal collected_text, last_event_time
            async for event in client.stream_events(session_id):
                last_event_time = time.monotonic()
                if event["type"] == "text":
                    collected_text = event["content"]
                    if on_progress:
                        on_progress(event["content"])
                elif event["type"] == "error":
                    raise AgentProcessError(
                        f"OpenCode error: {event.get('message', 'unknown')}"
                    )
                elif event["type"] == "done":
                    return collected_text
                # "activity" events (tool calls, etc.) also reset the timer
                # via last_event_time update above.
            return collected_text

        async def _stream_with_stall_detection() -> str:
            """Wrap stream with stall detection."""
            stream_task = asyncio.create_task(_stream())
            try:
                while not stream_task.done():
                    await asyncio.sleep(2.0)
                    idle = time.monotonic() - last_event_time
                    if idle > stall_timeout and collected_text:
                        # Stream stalled with content — treat as complete
                        stream_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await stream_task
                        return collected_text
                return stream_task.result()
            except asyncio.CancelledError:
                stream_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stream_task
                raise

        try:
            return await asyncio.wait_for(
                _stream_with_stall_detection(), timeout=timeout
            )
        except TimeoutError as exc:
            raise AgentTimeoutError(
                f"Agent did not complete within {timeout:.0f}s. "
                f"Collected {len(collected_text)} chars before timeout."
            ) from exc
