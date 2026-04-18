"""RepoAgentRunner — execute a single-shot generator agent in a repo workspace.

Closes bug B6 from the dogfooding report. `WorkspaceDirManager.create_repo_workspace`
scaffolds a directory and a rendered prompt but historically stopped there — the
posture-fix route returned a ``workspace_id`` pointing at an inert folder and no
PR was ever opened.

This runner:

1. Starts an OpenCode process in the workspace via the shared
   ``WorkspaceProcessPool`` with ``GH_TOKEN``/``OPENSEC_REPO_URL`` injected.
2. Creates a fresh session, sends the rendered agent prompt, collects the
   streamed response.
3. Parses the JSON contract the template requires and extracts ``pr_url``.
4. Persists the outcome to ``history/status.json`` inside the workspace so the
   posture route can report status back to the UI without a new DB table.
5. Stops the workspace process — repo-action workspaces are ephemeral.

The permission model for repo workspaces is ``"allow"`` for bash/edit/webfetch
(set up in the spawner via ``_build_repo_action_opencode_config``) because the
user already authorised the single action by clicking "Let OpenSec open a PR".
No SSE permission queue is needed here.

Contract: the runner never raises. All outcomes — success, bad LLM output,
OpenCode process failure, timeout — collapse into a ``RepoAgentStatus`` row
persisted to disk. Callers poll the status file.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel

from opensec.agents.output_parser import parse_agent_response
from opensec.agents.template_engine import AgentTemplateEngine
from opensec.engine.pool import WorkspaceProcessPool
from opensec.workspace.workspace_dir_manager import WorkspaceKind

logger = logging.getLogger(__name__)


# Give the generator up to 10 minutes end-to-end. Git clone + push + gh PR
# create is measured in tens of seconds on GitHub; the rest is LLM latency.
DEFAULT_TIMEOUT_SECONDS = 600.0

# Stall detection is intentionally absent: OpenCode's SSE stream for tool
# agents can go silent for long stretches while the model thinks between
# tool invocations (especially after file reads during a multi-step
# clone→detect→write→commit→push→PR flow). Premature stall cancels the
# run after the agent has already produced side effects (cloned repo,
# checked out a branch) but before it emits the final JSON contract, which
# surfaces as confusing "No JSON block found" failures. We rely on the
# overall ``DEFAULT_TIMEOUT_SECONDS`` (10 min) to bound the run instead.

RepoAgentPhase = Literal["queued", "running", "pr_created", "already_present", "failed"]


class RepoAgentStatus(BaseModel):
    """On-disk status snapshot. One JSON file per repo workspace."""

    workspace_id: str
    kind: str  # WorkspaceKind.value
    status: RepoAgentPhase
    pr_url: str | None = None
    branch_name: str | None = None
    error: str | None = None
    started_at: str
    finished_at: str | None = None
    # Raw JSON payload from the generator's structured_output block, kept so
    # the UI can surface rich per-kind details (e.g. the file_path an agent
    # wrote) without us having to bake every template's schema into this model.
    structured_output: dict[str, Any] | None = None


def _status_path(workspace_root: Path) -> Path:
    return workspace_root / "history" / "status.json"


def read_status(workspace_root: Path) -> RepoAgentStatus | None:
    """Return the last persisted status for a repo workspace, or None.

    Posture route handlers call this on every poll — must never raise.
    """
    path = _status_path(workspace_root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
        return RepoAgentStatus.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("corrupt status file at %s: %s", path, exc)
        return None


def _write_status(workspace_root: Path, status: RepoAgentStatus) -> None:
    path = _status_path(workspace_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic-ish write so a concurrent poll never reads half a file.
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(status.model_dump_json(indent=2))
    tmp.replace(path)


class RepoAgentRunner:
    """Runs the generator agent attached to a repo-action workspace.

    Decoupled from ``AgentExecutor``: no DB row, no SSE permission queue, no
    ``AgentRun`` schema validation. Posture workspaces have exactly one agent
    run and discard themselves when it's done.
    """

    def __init__(self, pool: WorkspaceProcessPool) -> None:
        self._pool = pool

    async def run(
        self,
        *,
        workspace_id: str,
        workspace_root: Path,
        kind: WorkspaceKind,
        repo_url: str,
        gh_token: str | None,
        params: dict[str, Any] | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> RepoAgentStatus:
        """Execute the generator agent end-to-end.

        Never raises. Failures are captured in the returned ``RepoAgentStatus``
        with ``status="failed"`` and ``error`` filled in.
        """
        started = datetime.now(UTC).isoformat()
        running = RepoAgentStatus(
            workspace_id=workspace_id,
            kind=kind.value,
            status="running",
            started_at=started,
        )
        _write_status(workspace_root, running)

        try:
            prompt = _render_prompt(
                kind, repo_url=repo_url, gh_token=gh_token, params=params or {}
            )
        except Exception as exc:  # noqa: BLE001 — never leak to caller
            return self._finalize(
                workspace_root,
                running,
                status="failed",
                error=f"Failed to render agent prompt: {exc}",
            )

        env_vars: dict[str, str] = {"OPENSEC_REPO_URL": repo_url}
        if gh_token:
            env_vars["GH_TOKEN"] = gh_token
            # Some gh commands prefer GITHUB_TOKEN; export both.
            env_vars["GITHUB_TOKEN"] = gh_token

        client = None
        try:
            client = await self._pool.get_or_start(
                workspace_id, workspace_root, env_vars=env_vars
            )
            session = await client.create_session()
            response_text = await _send_and_collect(
                client, session.id, prompt, timeout=timeout
            )
        except (RuntimeError, TimeoutError, httpx.HTTPError) as exc:
            logger.exception("repo agent process failed for %s", workspace_id)
            return self._finalize(
                workspace_root,
                running,
                status="failed",
                error=f"OpenCode process failure: {exc}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "unexpected error in repo agent runner for %s", workspace_id
            )
            return self._finalize(
                workspace_root,
                running,
                status="failed",
                error=f"Unexpected error: {exc}",
            )
        finally:
            # Repo workspaces are one-shot: release the process + port so we
            # don't leak a subprocess per "Generate and open PR" click.
            with contextlib.suppress(Exception):
                await self._pool.stop(workspace_id)

        # Persist raw text so operators can see exactly what the agent said
        # when something goes wrong — especially helpful for "No JSON block
        # found" because the UI otherwise can't show the reasoning that
        # happened before the stall.
        with contextlib.suppress(Exception):
            (workspace_root / "history" / "agent-response.txt").write_text(
                response_text
            )

        if not response_text.strip():
            return self._finalize(
                workspace_root,
                running,
                status="failed",
                error="Agent returned an empty response",
            )

        parsed = parse_agent_response(response_text, agent_type=_agent_type_for(kind))
        structured = parsed.structured_output or {}

        if not parsed.success:
            return self._finalize(
                workspace_root,
                running,
                status="failed",
                error=parsed.error or "Agent output did not match contract",
                structured_output=structured or None,
            )

        agent_status = (structured.get("status") or "").lower()
        pr_url = structured.get("pr_url")
        branch_name = structured.get("branch_name")

        if agent_status == "pr_created" and pr_url:
            return self._finalize(
                workspace_root,
                running,
                status="pr_created",
                pr_url=pr_url,
                branch_name=branch_name,
                structured_output=structured,
            )
        if agent_status == "already_present":
            return self._finalize(
                workspace_root,
                running,
                status="already_present",
                structured_output=structured,
            )
        # Fall through: the agent claimed success but didn't give us a PR.
        return self._finalize(
            workspace_root,
            running,
            status="failed",
            error=structured.get("error_details")
            or "Agent finished without opening a PR",
            structured_output=structured,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _finalize(
        self,
        workspace_root: Path,
        running: RepoAgentStatus,
        *,
        status: RepoAgentPhase,
        pr_url: str | None = None,
        branch_name: str | None = None,
        error: str | None = None,
        structured_output: dict[str, Any] | None = None,
    ) -> RepoAgentStatus:
        final = running.model_copy(
            update={
                "status": status,
                "pr_url": pr_url,
                "branch_name": branch_name,
                "error": error,
                "structured_output": structured_output,
                "finished_at": datetime.now(UTC).isoformat(),
            }
        )
        _write_status(workspace_root, final)
        logger.info(
            "repo agent %s (%s) finished: status=%s pr_url=%s error=%s",
            running.workspace_id,
            running.kind,
            status,
            pr_url,
            error,
        )
        return final


# ---------------------------------------------------------------------------
# Private helpers — separated from the class to keep it mockable without
# monkey-patching instance methods.
# ---------------------------------------------------------------------------


def _render_prompt(
    kind: WorkspaceKind,
    *,
    repo_url: str,
    gh_token: str | None,
    params: dict[str, Any],
) -> str:
    """Re-render the generator prompt (idempotent with WorkspaceDirManager)."""
    engine = AgentTemplateEngine()
    rendered = engine.render_repo_action(
        kind, repo_url=repo_url, params=params, gh_token=gh_token
    )
    return rendered.content


def _agent_type_for(kind: WorkspaceKind) -> str:
    """Map workspace kind to the agent_type string the parser expects.

    The output parser uses agent_type only for ``validate_structured_output``
    schema lookup; posture generator schemas are registered under these names
    in ``opensec.agents.schemas``. Unknown agent_type is allowed — the parser
    skips per-agent validation and still extracts ``structured_output``.
    """
    return {
        WorkspaceKind.repo_action_security_md: "security_md_generator",
        WorkspaceKind.repo_action_dependabot: "dependabot_config_generator",
    }.get(kind, kind.value)


async def _send_and_collect(
    client: Any,
    session_id: str,
    prompt: str,
    *,
    timeout: float,
) -> str:
    """Send the prompt, accumulate text events until done/stall/timeout.

    Simpler than ``AgentExecutor._send_and_collect`` because repo workspaces
    pre-approve bash/edit/webfetch — we never see ``permission_request``
    events and therefore don't need an approval queue.
    """

    async def _send() -> None:
        # Small delay matches the executor's pattern: give the SSE stream
        # time to connect before the message lands.
        await asyncio.sleep(0.5)
        with contextlib.suppress(httpx.ReadTimeout):
            await client.send_message(session_id, prompt)

    send_task = asyncio.create_task(_send())
    try:
        return await _collect_response(client, session_id, timeout=timeout)
    finally:
        if not send_task.done():
            send_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await send_task


async def _collect_response(
    client: Any,
    session_id: str,
    *,
    timeout: float,
) -> str:
    """Consume the SSE event stream until ``done`` or the overall timeout.

    Text events from OpenCode carry the cumulative response so far — each
    successive event replaces the prior content, and the last event before
    ``done`` has the full text. We keep the latest and return it either
    when we see ``done`` or when the outer timeout wins.
    """
    collected = ""

    async def _stream() -> str:
        nonlocal collected
        async for event in client.stream_events(session_id):
            etype = event.get("type")
            if etype == "text":
                collected = event.get("content", "") or collected
            elif etype == "done":
                return collected
            elif etype == "error":
                raise RuntimeError(
                    f"OpenCode error event: {event.get('message', 'unknown')}"
                )
        return collected

    try:
        return await asyncio.wait_for(_stream(), timeout=timeout)
    except asyncio.TimeoutError:
        # Outer timeout — surface whatever we collected so the caller still
        # gets diagnostic text in ``history/agent-response.txt`` instead of
        # a blanket "Unexpected error".
        logger.warning("repo agent response stream timed out after %ss", timeout)
        return collected
