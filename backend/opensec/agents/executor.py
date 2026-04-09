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
from pathlib import Path
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
from opensec.workspace.context_document import ContextDocument
from opensec.workspace.workspace_dir import AGENT_TYPE_TO_SECTION, CONTEXT_SECTIONS

if TYPE_CHECKING:
    from collections.abc import Callable

    import aiosqlite

    from opensec.engine.pool import WorkspaceProcessPool
    from opensec.workspace.context_builder import WorkspaceContextBuilder

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT: float = 120.0
# Extra buffer for asyncio.wait_for when permission waits are possible.
# The real timeout is enforced by stall detection, which accounts for
# time spent waiting for user permission decisions.
PERMISSION_WAIT_BUFFER: float = 600.0

# ---------------------------------------------------------------------------
# Permission tier classification for tool-use approval.
# Keys are the "permission" field from OpenCode's permission.asked events.
# "auto" = grant immediately, "user" = surface to user for approval.
# Unknown tools default to "user" (safe default).
# ---------------------------------------------------------------------------

TOOL_TIERS: dict[str, str] = {
    "read": "auto",
    "webfetch": "auto",
    "bash": "user",
    "edit": "user",
    "mcp": "user",
}


@dataclass
class _PendingApproval:
    """Tracks a permission request waiting for user approval."""

    permission_id: str
    tool: str
    patterns: list[str]
    event: asyncio.Event
    approved: bool | None = None

# ---------------------------------------------------------------------------
# Per-agent output contracts (inlined in the prompt so the LLM always sees
# the exact schema, regardless of workspace state or session history).
# ---------------------------------------------------------------------------

_STRUCTURED_OUTPUT_CONTRACTS: dict[str, str] = {
    "finding_enricher": """\
"structured_output": {
    "normalized_title": "string — clear, jargon-free title",
    "cve_ids": ["CVE-YYYY-NNNNN"] or [],
    "cvss_score": 0.0-10.0 or null,
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/..." or null,
    "description": "what the vulnerability is and how it works",
    "affected_versions": "version range, e.g. '< 2.3.1'" or null,
    "fixed_version": "minimum fixed version" or null,
    "known_exploits": true/false,
    "exploit_details": "exploit maturity info" or null,
    "references": ["https://..."] or []
}""",
    "owner_resolver": """\
"structured_output": {
    "recommended_owner": "string — team or person name",
    "candidates": [{"name": "...", "confidence": 0.0-1.0, "reason": "..."}],
    "reasoning": "why this owner was chosen"
}""",
    "exposure_analyzer": """\
"structured_output": {
    "recommended_urgency": "critical/high/medium/low",
    "environment": "production/staging/development" or null,
    "internet_facing": true/false or null,
    "reachable": "description of reachability" or null,
    "reachability_evidence": "evidence for reachability assessment" or null,
    "business_criticality": "description" or null,
    "blast_radius": "description of impact scope" or null
}""",
    "remediation_planner": """\
"structured_output": {
    "plan_steps": ["step 1", "step 2", ...],
    "definition_of_done": ["criterion 1", ...],
    "interim_mitigation": "immediate mitigation" or null,
    "dependencies": ["dependency 1", ...],
    "estimated_effort": "e.g. 2-4 hours" or null,
    "validation_method": "how to verify the fix" or null
}""",
    "validation_checker": """\
"structured_output": {
    "verdict": "fixed/not_fixed/partially_fixed/inconclusive",
    "recommendation": "close/reopen/needs_more_info",
    "evidence": "what evidence supports the verdict" or null,
    "remaining_concerns": ["concern 1", ...]
}""",
}

_AGENT_TYPE_LABELS: dict[str, str] = {
    "finding_enricher": "vulnerability enrichment",
    "owner_resolver": "ownership resolution",
    "exposure_analyzer": "exposure and context analysis",
    "remediation_planner": "remediation planning",
    "validation_checker": "validation checking",
}


def _load_workspace_data(
    workspace_dir: str, agent_type: str
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Read finding data and prior agent results from the workspace directory.

    Returns (finding_dict, prior_context_dict). Prior context only includes
    sections from agents earlier in the pipeline than the current one.
    """
    import json

    ctx_dir = Path(workspace_dir) / "context"

    # Read finding — must exist
    finding_path = ctx_dir / "finding.json"
    if not finding_path.exists():
        raise AgentProcessError(
            f"finding.json missing from workspace: {workspace_dir}"
        )
    finding = json.loads(finding_path.read_text())

    # Read prior context — only sections before this agent in the pipeline
    current_section = AGENT_TYPE_TO_SECTION.get(agent_type)
    if current_section:
        cutoff = CONTEXT_SECTIONS.index(current_section)
        prior_sections = CONTEXT_SECTIONS[:cutoff]
    else:
        prior_sections = CONTEXT_SECTIONS

    prior_context: dict[str, dict[str, Any]] = {}
    for section in prior_sections:
        section_path = ctx_dir / f"{section}.json"
        if section_path.exists():
            prior_context[section] = json.loads(section_path.read_text())

    return finding, prior_context


def build_agent_prompt(
    agent_type: str,
    *,
    finding: dict[str, Any],
    prior_context: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Build the execution prompt for a specific agent type.

    Includes the actual finding data and any prior agent results inline,
    so the LLM has everything it needs without reading files.
    """
    label = _AGENT_TYPE_LABELS.get(agent_type, agent_type)
    contract = _STRUCTURED_OUTPUT_CONTRACTS.get(agent_type, "")
    structured_block = f",\n    {contract}" if contract else ""

    # Format finding data using the same renderer as CONTEXT.md
    finding_text = ContextDocument.finding_section(finding)

    # Format prior context if available
    prior_text = ""
    if prior_context:
        knowledge = ContextDocument.knowledge_section(
            prior_context.get("enrichment"),
            prior_context.get("ownership"),
            prior_context.get("exposure"),
        )
        if knowledge:
            prior_text = f"\n{knowledge}\n"

    return f"""\
IMPORTANT: This is a programmatic agent execution request. Respond with ONLY \
a JSON code block — no tool calls, no file reads, no conversation.

{finding_text}{prior_text}
Run {label} on the finding above. Respond with a single \
```json code block matching this exact schema:

```json
{{
    "summary": "one-line summary of your analysis",
    "result_card_markdown": "## Heading\\n\\nMarkdown-formatted detailed results",
    "confidence": 0.0-1.0,
    "evidence_sources": ["source1", "source2"],
    "suggested_next_action": "next agent type or action to take"{structured_block}
}}
```

Respond with ONLY the JSON block above. No preamble, no explanation, no tool use."""


_RETRY_PROMPT = """\
Your previous response could not be parsed as valid JSON. This is a \
programmatic execution — the output MUST be a single ```json code block and \
nothing else. Do not use tools, do not read files, do not add explanation \
text. Respond now with ONLY the JSON block in the exact schema requested."""


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
        self._pending_approvals: dict[str, _PendingApproval] = {}
        self._permission_queues: dict[str, asyncio.Queue] = {}  # workspace_id -> SSE queue
        self._active_runs: dict[str, str] = {}  # workspace_id -> agent_run_id
        self._permission_pending: dict[str, bool] = {}  # agent_run_id -> pauses stall detection

    def approve_tool(self, run_id: str) -> bool:
        """Approve a pending tool-use permission request.

        Returns True if a pending approval was found and resolved.
        """
        pending = self._pending_approvals.get(run_id)
        if not pending:
            return False
        pending.approved = True
        pending.event.set()
        return True

    def deny_tool(self, run_id: str) -> bool:
        """Deny a pending tool-use permission request.

        Returns True if a pending approval was found and resolved.
        """
        pending = self._pending_approvals.get(run_id)
        if not pending:
            return False
        pending.approved = False
        pending.event.set()
        return True

    def push_permission_event(self, workspace_id: str, event: dict) -> None:
        """Push a permission event to the workspace's SSE queue."""
        queue = self._permission_queues.get(workspace_id)
        if queue:
            queue.put_nowait(event)

    def get_permission_queue(self, workspace_id: str) -> asyncio.Queue | None:
        """Get the permission event queue for a workspace (for SSE streaming)."""
        return self._permission_queues.get(workspace_id)

    def get_active_run_id(self, workspace_id: str) -> str | None:
        """Get the currently active agent run ID for a workspace."""
        return self._active_runs.get(workspace_id)

    def _cleanup_workspace_state(
        self, workspace_id: str, agent_run_id: str
    ) -> None:
        """Clean up per-workspace state after execution completes."""
        self._pending_approvals.pop(agent_run_id, None)
        self._permission_pending.pop(agent_run_id, None)
        self._active_runs.pop(workspace_id, None)
        queue = self._permission_queues.pop(workspace_id, None)
        if queue:
            # Signal completion to any SSE listener
            queue.put_nowait({"type": "done"})

    async def execute(
        self,
        workspace_id: str,
        agent_type: str,
        db: aiosqlite.Connection,
        *,
        workspace_dir: str,
        timeout: float = DEFAULT_TIMEOUT,
        on_progress: Callable[[str], None] | None = None,
        on_permission: Callable[[dict], None] | None = None,
    ) -> AgentExecutionResult:
        """Execute a single agent run.

        Args:
            workspace_id: The workspace to run in.
            agent_type: One of the AgentType literals.
            db: Database connection.
            workspace_dir: Path to the workspace directory on disk.
            timeout: Maximum seconds to wait for the agent.
            on_progress: Optional callback for streaming text chunks.
            on_permission: Optional callback when a tool needs user approval.
                Called with {id, tool, patterns} dict.

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

        # Set up per-workspace state for permission event streaming
        self._permission_queues[workspace_id] = asyncio.Queue()
        self._active_runs[workspace_id] = agent_run.id

        try:
            # 3. Get or start workspace OpenCode process
            try:
                client = await self._pool.get_or_start(
                    workspace_id, Path(workspace_dir)
                )
            except (RuntimeError, TimeoutError) as exc:
                raise AgentProcessError(str(exc)) from exc

            # 4. Create fresh session
            session = await client.create_session()

            finding_data, prior_ctx = _load_workspace_data(
                workspace_dir, agent_type
            )
            prompt = build_agent_prompt(
                agent_type, finding=finding_data, prior_context=prior_ctx
            )

            response_text = await self._send_and_collect(
                client, session.id, prompt,
                timeout=timeout, on_progress=on_progress,
                on_permission=on_permission,
                agent_run_id=agent_run.id,
            )

            # 7. Parse response
            parse_result = parse_agent_response(
                response_text, agent_type=agent_type
            )

            # 7b. Retry once if parse failed — send a corrective follow-up
            # on the same session so the LLM sees its own bad output.
            if not parse_result.success and response_text.strip():
                logger.info(
                    "Agent %s parse failed (error=%s), retrying with corrective prompt",
                    agent_type,
                    parse_result.error,
                )
                retry_text = await self._send_and_collect(
                    client, session.id, _RETRY_PROMPT,
                    timeout=timeout, on_progress=on_progress,
                    on_permission=on_permission,
                    agent_run_id=agent_run.id,
                    send_delay=0.0,
                )
                retry_result = parse_agent_response(
                    retry_text, agent_type=agent_type
                )
                if retry_result.success:
                    parse_result = retry_result

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

            self._cleanup_workspace_state(workspace_id, agent_run.id)
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
            self._cleanup_workspace_state(workspace_id, agent_run.id)
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
            self._cleanup_workspace_state(workspace_id, agent_run.id)
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
            self._cleanup_workspace_state(workspace_id, agent_run.id)
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

    async def _send_and_collect(
        self,
        client: Any,
        session_id: str,
        prompt: str,
        *,
        timeout: float,
        on_progress: Callable[[str], None] | None = None,
        on_permission: Callable[[dict], None] | None = None,
        agent_run_id: str = "",
        send_delay: float = 0.5,
    ) -> str:
        """Send a prompt and collect the streamed response.

        The send_delay gives the SSE stream time to connect before the
        message is sent. Set to 0 for follow-up messages on an already-
        connected session.
        """

        async def _send() -> None:
            if send_delay > 0:
                await asyncio.sleep(send_delay)
            with contextlib.suppress(httpx.ReadTimeout):
                await client.send_message(session_id, prompt)

        send_task = asyncio.create_task(_send())
        try:
            return await self._collect_response(
                client, session_id,
                timeout=timeout,
                on_progress=on_progress,
                on_permission=on_permission,
                agent_run_id=agent_run_id,
            )
        finally:
            if not send_task.done():
                send_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await send_task

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
        on_permission: Callable[[dict], None] | None = None,
        agent_run_id: str = "",
        stall_timeout: float = 60.0,
    ) -> str:
        """Collect the full response from OpenCode via SSE stream.

        Accumulates text events until ``done`` or until no new events
        arrive for ``stall_timeout`` seconds (stall detection — OpenCode
        may not emit ``session.idle`` if the agent uses tools).

        Handles permission.asked events: auto-approves safe tools,
        waits for user approval on risky ones.

        Raises AgentTimeoutError if the overall timeout is exceeded.
        """
        collected_text = ""
        last_event_time = time.monotonic()
        permission_wait_total = 0.0  # Total seconds spent waiting for user approval

        async def _handle_permission(event: dict) -> None:
            """Handle a permission request based on tool tier."""
            tool = event.get("tool", "unknown")
            permission_id = event.get("id", "")
            tier = TOOL_TIERS.get(tool, "user")

            if tier == "auto":
                logger.info(
                    "Auto-approving %s tool (permission %s)",
                    tool, permission_id,
                )
                await client.grant_permission(
                    permission_id, session_id=session_id,
                )
                return

            # User-tier: store pending approval and wait
            logger.info(
                "Permission requested for %s tool (permission %s), "
                "waiting for user approval",
                tool, permission_id,
            )
            pending = _PendingApproval(
                permission_id=permission_id,
                tool=tool,
                patterns=event.get("patterns", []),
                event=asyncio.Event(),
            )
            self._pending_approvals[agent_run_id] = pending

            if on_permission:
                on_permission({
                    "id": permission_id,
                    "tool": tool,
                    "patterns": event.get("patterns", []),
                    "run_id": agent_run_id,
                })

            # Pause stall detection while waiting for user decision
            self._permission_pending[agent_run_id] = True
            wait_start = time.monotonic()
            await pending.event.wait()
            wait_elapsed = time.monotonic() - wait_start
            self._permission_pending.pop(agent_run_id, None)
            nonlocal permission_wait_total
            permission_wait_total += wait_elapsed
            # Extend the stall timer to exclude user decision time
            nonlocal last_event_time
            last_event_time = time.monotonic()

            if pending.approved:
                await client.grant_permission(
                    permission_id, session_id=session_id,
                )
            else:
                await client.deny_permission(
                    permission_id, session_id=session_id,
                )

            self._pending_approvals.pop(agent_run_id, None)

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
                elif event["type"] == "permission_request":
                    await _handle_permission(event)
                # "activity" events (tool calls, etc.) also reset the timer
                # via last_event_time update above.
            return collected_text

        async def _stream_with_stall_detection() -> str:
            """Wrap stream with stall detection.

            The overall timeout excludes time spent waiting for user
            permission decisions (tracked via permission_wait_total).
            """
            stream_start = time.monotonic()
            stream_task = asyncio.create_task(_stream())
            try:
                while not stream_task.done():
                    await asyncio.sleep(2.0)
                    # Skip stall detection while waiting for user permission
                    if self._permission_pending.get(agent_run_id):
                        continue
                    idle = time.monotonic() - last_event_time
                    if idle > stall_timeout and collected_text:
                        # Stream stalled with content — treat as complete
                        stream_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await stream_task
                        return collected_text
                    # Check effective timeout (wall clock minus permission wait)
                    effective_elapsed = (
                        time.monotonic() - stream_start - permission_wait_total
                    )
                    if effective_elapsed > timeout:
                        stream_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await stream_task
                        raise AgentTimeoutError(
                            f"Agent did not complete within {timeout:.0f}s "
                            f"(excludes {permission_wait_total:.0f}s user approval time)."
                        )
                return stream_task.result()
            except asyncio.CancelledError:
                stream_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stream_task
                raise

        max_wall_clock = timeout + PERMISSION_WAIT_BUFFER
        try:
            return await asyncio.wait_for(
                _stream_with_stall_detection(), timeout=max_wall_clock
            )
        except TimeoutError as exc:
            effective_timeout = timeout + permission_wait_total
            raise AgentTimeoutError(
                f"Agent did not complete within {effective_timeout:.0f}s "
                f"(includes {permission_wait_total:.0f}s user approval time). "
                f"Collected {len(collected_text)} chars before timeout."
            ) from exc
