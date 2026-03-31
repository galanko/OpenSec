"""WorkspaceContextBuilder — orchestrates L0 (filesystem) + L1 (templates) + DB metadata."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from opensec.db.repo_workspace import (
    create_workspace,
    delete_workspace,
    get_workspace,
    increment_context_version,
    update_workspace,
    update_workspace_dir,
)
from opensec.models import WorkspaceCreate, WorkspaceUpdate
from opensec.workspace.agent_run_log import AgentRunLog
from opensec.workspace.workspace_dir import AGENT_TYPE_TO_SECTION

if TYPE_CHECKING:
    from pathlib import Path

    import aiosqlite

    from opensec.agents.template_engine import AgentTemplateEngine
    from opensec.integrations.gateway import MCPConfigResolver
    from opensec.models import Finding, Workspace
    from opensec.workspace.workspace_dir_manager import WorkspaceDirManager

logger = logging.getLogger(__name__)


class WorkspaceContextBuilder:
    """Orchestrates workspace lifecycle: directory + agents + DB metadata.

    Wires Layer 0 (WorkspaceDirManager) and Layer 1 (AgentTemplateEngine)
    together into a single service that manages the full workspace lifecycle.
    Future API routes (Layer 4) will call this instead of raw repo functions.

    All public methods are async (called from FastAPI routes) but delegate
    to synchronous L0/L1 operations directly — filesystem ops are fast local
    I/O and aiosqlite is already the serialization point.
    """

    def __init__(
        self,
        dir_manager: WorkspaceDirManager,
        template_engine: AgentTemplateEngine,
        *,
        mcp_resolver: MCPConfigResolver | None = None,
    ) -> None:
        self._dir_manager = dir_manager
        self._template_engine = template_engine
        self._mcp_resolver = mcp_resolver

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create_workspace(
        self,
        db: aiosqlite.Connection,
        finding: Finding,
        *,
        initial_focus: str | None = None,
    ) -> Workspace:
        """Create a complete workspace: DB row + directory + rendered agents.

        Steps:
            1. Create DB row
            2. Resolve MCP configs from vault (if configured)
            3. Create directory structure with finding context + MCP configs
            4. Render and write agent templates
            5. Store directory path in DB

        Returns the fully populated Workspace model.
        """
        # 1. DB row
        ws_data = WorkspaceCreate(
            finding_id=finding.id,
            state="open",
            current_focus=initial_focus,
        )
        workspace = await create_workspace(db, ws_data)

        # 2. Resolve MCP configs (if vault is configured)
        mcp_servers = None
        if self._mcp_resolver is not None:
            try:
                mcp_servers = await self._mcp_resolver.resolve_workspace_mcp_configs(db)
            except Exception:
                logger.warning(
                    "Failed to resolve MCP configs for workspace %s", workspace.id,
                    exc_info=True,
                )

        # 3. Filesystem directory
        ws_dir = self._dir_manager.create(workspace.id, finding, mcp_servers=mcp_servers)

        # 4. Render agent templates (finding only — no enrichment yet)
        finding_dict = finding.model_dump(mode="json")
        self._template_engine.write_agents(ws_dir.agents_dir, finding=finding_dict)

        # 5. Store path in DB
        await update_workspace_dir(db, workspace.id, str(ws_dir.root))

        logger.info("Created workspace %s at %s", workspace.id, ws_dir.root)
        return await get_workspace(db, workspace.id)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Update context
    # ------------------------------------------------------------------

    async def update_context(
        self,
        db: aiosqlite.Connection,
        workspace_id: str,
        agent_type: str,
        structured_output: dict[str, Any],
        *,
        summary: str | None = None,
    ) -> int:
        """Write agent output to context, re-render agents, bump version.

        Args:
            db: Database connection.
            workspace_id: The workspace to update.
            agent_type: One of the AgentType literals (e.g. "finding_enricher").
            structured_output: The agent's structured output dict.
            summary: Optional one-line summary for the agent run log.

        Returns:
            The new context_version number.

        Raises:
            ValueError: If agent_type is not recognized.
            FileNotFoundError: If workspace directory doesn't exist.
        """
        if agent_type not in AGENT_TYPE_TO_SECTION:
            raise ValueError(
                f"Unknown agent_type: {agent_type!r}. "
                f"Must be one of {list(AGENT_TYPE_TO_SECTION.keys())}"
            )

        section = AGENT_TYPE_TO_SECTION[agent_type]

        # 1. Write context section (auto-regenerates CONTEXT.md)
        self._dir_manager.write_context_section(workspace_id, section, structured_output)

        # 2. Re-render agent templates with full updated context
        ws_dir = self._dir_manager.get(workspace_id)
        if ws_dir is None:
            raise FileNotFoundError(f"Workspace directory not found: {workspace_id}")

        finding_data = json.loads(ws_dir.finding_json.read_text())
        all_context = self._dir_manager.read_all_context(workspace_id)
        self._template_engine.write_agents(
            ws_dir.agents_dir, finding=finding_data, **all_context
        )

        # 3. Log to agent-runs.jsonl
        run_log = AgentRunLog(ws_dir.agent_runs_log)
        run_log.append(agent_type=agent_type, status="completed", summary=summary)

        # 4. Bump version in DB
        new_version = await increment_context_version(db, workspace_id)

        logger.info(
            "Updated context for workspace %s: %s -> v%d",
            workspace_id, agent_type, new_version,
        )
        return new_version

    # ------------------------------------------------------------------
    # Read context
    # ------------------------------------------------------------------

    async def get_context_snapshot(
        self,
        workspace_id: str,
    ) -> dict[str, Any]:
        """Return full context state for the sidebar/API.

        Returns dict with keys: finding, enrichment, ownership, exposure,
        plan, validation, agent_run_history. Values are dicts or None.

        Raises:
            FileNotFoundError: If workspace directory doesn't exist.
        """
        ws_dir = self._dir_manager.get(workspace_id)
        if ws_dir is None:
            raise FileNotFoundError(f"Workspace directory not found: {workspace_id}")

        finding_data = json.loads(ws_dir.finding_json.read_text())
        all_context = self._dir_manager.read_all_context(workspace_id)
        run_log = AgentRunLog(ws_dir.agent_runs_log)

        return {
            "finding": finding_data,
            **all_context,
            "agent_run_history": run_log.read_all(),
        }

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_workspace(
        self,
        db: aiosqlite.Connection,
        workspace_id: str,
    ) -> bool:
        """Delete workspace directory and DB row.

        Tolerates missing directory — always attempts DB deletion.
        Returns True if the DB row existed.
        """
        self._dir_manager.delete(workspace_id)
        return await delete_workspace(db, workspace_id)

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    async def archive_workspace(
        self,
        db: aiosqlite.Connection,
        workspace_id: str,
    ) -> Path:
        """Archive workspace directory and update DB state to 'closed'.

        Returns the path to the created archive.

        Raises:
            FileNotFoundError: If workspace directory doesn't exist.
        """
        archive_path = self._dir_manager.archive(workspace_id)
        await update_workspace(
            db, workspace_id, WorkspaceUpdate(state="closed")
        )
        logger.info("Archived workspace %s to %s", workspace_id, archive_path)
        return archive_path
