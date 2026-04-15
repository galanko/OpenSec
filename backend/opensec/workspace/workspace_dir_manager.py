"""WorkspaceDirManager — CRUD for workspace directories on disk."""

from __future__ import annotations

import json
import shutil
import tarfile
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from opensec.workspace.context_document import ContextDocument
from opensec.workspace.workspace_dir import CONTEXT_SECTIONS, WorkspaceDir

if TYPE_CHECKING:
    from pathlib import Path

    from opensec.models import Finding


class WorkspaceKind(StrEnum):
    """Discriminator for workspace directories (IMPL-0002 Milestone E4).

    Finding workspaces (the existing kind) are implicit; the two repo-scoped
    actions get explicit enum values that route to their generator agents.
    """

    repo_action_security_md = "repo_action_security_md"
    repo_action_dependabot = "repo_action_dependabot"


class WorkspaceDirManager:
    """Creates, reads, updates, archives, and deletes workspace directories.

    Each workspace gets an isolated directory with context files, agent
    definitions, and an auto-generated CONTEXT.md. This is the filesystem
    foundation that the AI engine reads from.

    All operations are synchronous — filesystem I/O does not benefit from
    async. Accepts ``base_dir`` as a constructor parameter so tests can
    use ``tmp_path``.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        workspace_id: str,
        finding: Finding,
        *,
        mcp_servers: dict[str, dict] | None = None,
    ) -> WorkspaceDir:
        """Create the full directory structure and initial files for a workspace.

        Args:
            workspace_id: Unique workspace identifier.
            finding: The finding this workspace remediates.
            mcp_servers: Optional MCP server configs (from MCPConfigResolver)
                to include in the workspace's opencode.json.

        Raises:
            FileExistsError: If the workspace directory already exists.
            ValueError: If workspace_id contains path traversal characters.
        """
        _validate_workspace_id(workspace_id)
        self._base_dir.mkdir(parents=True, exist_ok=True)

        workspace_root = self._base_dir / workspace_id
        if workspace_root.exists():
            raise FileExistsError(
                f"Workspace directory already exists: {workspace_root}"
            )

        # Create directory tree
        workspace_root.mkdir()
        (workspace_root / "context").mkdir()
        (workspace_root / "context" / "code-snippets").mkdir()
        (workspace_root / "context" / "references").mkdir()
        (workspace_root / ".opencode" / "agents").mkdir(parents=True)
        (workspace_root / "history").mkdir()

        ws = WorkspaceDir(root=workspace_root)

        # Write finding data
        finding_data = finding.model_dump(mode="json")
        ws.finding_json.write_text(json.dumps(finding_data, indent=2) + "\n")
        ws.finding_md.write_text(_render_finding_md(finding))

        # Write opencode.json — workspace agents need bash + file access
        opencode_config: dict = {
            "$schema": "https://opencode.ai/config.json",
            "permission": {
                "bash": "ask",
                "edit": "ask",
                "webfetch": "allow",
            },
        }
        if mcp_servers:
            opencode_config["mcp"] = mcp_servers
        ws.opencode_json.write_text(json.dumps(opencode_config, indent=2) + "\n")

        # Create empty agent-runs log
        ws.agent_runs_log.touch()

        # Generate CONTEXT.md
        context_md_content = ContextDocument.generate(finding_data)
        ws.context_md.write_text(context_md_content)

        return ws

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, workspace_id: str) -> WorkspaceDir | None:
        """Return WorkspaceDir if the directory exists, else None."""
        ws = WorkspaceDir(root=self._base_dir / workspace_id)
        return ws if ws.exists() else None

    def list(self) -> list[WorkspaceDir]:
        """Return all workspace directories sorted by name."""
        if not self._base_dir.exists():
            return []
        return sorted(
            (
                WorkspaceDir(root=p)
                for p in self._base_dir.iterdir()
                if p.is_dir() and p.name != "archives"
            ),
            key=lambda ws: ws.workspace_id,
        )

    def read_context_section(
        self, workspace_id: str, section: str
    ) -> dict | None:
        """Read a context section JSON file. Returns None if file doesn't exist."""
        ws = self._require_workspace(workspace_id)
        path = ws.context_file(section)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def read_all_context(self, workspace_id: str) -> dict[str, dict | None]:
        """Read all context sections. Returns dict mapping section name to data."""
        return {
            section: self.read_context_section(workspace_id, section)
            for section in CONTEXT_SECTIONS
        }

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def write_context_section(
        self, workspace_id: str, section: str, data: dict
    ) -> None:
        """Write a context section JSON file and regenerate CONTEXT.md.

        Raises:
            FileNotFoundError: If the workspace directory doesn't exist.
        """
        ws = self._require_workspace(workspace_id)
        path = ws.context_file(section)
        path.write_text(json.dumps(data, indent=2) + "\n")
        self.regenerate_context_md(workspace_id)

    def regenerate_context_md(self, workspace_id: str) -> None:
        """Rebuild CONTEXT.md from current context files."""
        ws = self._require_workspace(workspace_id)
        finding_data = json.loads(ws.finding_json.read_text())

        sections = {}
        for section in CONTEXT_SECTIONS:
            path = ws.context_file(section)
            if path.exists():
                sections[section] = json.loads(path.read_text())

        content = ContextDocument.generate(finding_data, **sections)
        ws.context_md.write_text(content)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, workspace_id: str) -> bool:
        """Delete workspace directory recursively. Returns True if it existed."""
        ws = WorkspaceDir(root=self._base_dir / workspace_id)
        if not ws.exists():
            return False
        shutil.rmtree(ws.root)
        return True

    # ------------------------------------------------------------------
    # Archive
    # ------------------------------------------------------------------

    def archive(self, workspace_id: str) -> Path:
        """Create a tar.gz archive of the workspace directory.

        The archive is written to ``base_dir/archives/<workspace_id>.tar.gz``.
        The original directory is NOT deleted — the caller decides.

        Raises:
            FileNotFoundError: If the workspace directory doesn't exist.
        """
        ws = self._require_workspace(workspace_id)
        archives_dir = self._base_dir / "archives"
        archives_dir.mkdir(exist_ok=True)

        archive_path = archives_dir / f"{workspace_id}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(ws.root, arcname=workspace_id)
        return archive_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_workspace(self, workspace_id: str) -> WorkspaceDir:
        ws = self.get(workspace_id)
        if ws is None:
            raise FileNotFoundError(
                f"Workspace directory not found: {self._base_dir / workspace_id}"
            )
        return ws

    # ------------------------------------------------------------------
    # Repo-scoped workspaces (IMPL-0002 Milestone E — V1↔V2 interface stub)
    # ------------------------------------------------------------------

    def create_repo_workspace(
        self,
        kind: WorkspaceKind,
        repo_url: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        """Create an ephemeral repo-scoped workspace for a generator agent.

        Returns the workspace_id that V2 can poll for sidebar state (PR url,
        status). Implemented in Session C; this is the Session-0 contract stub
        so that downstream sessions can import ``WorkspaceKind`` and wire the
        signature into API routes without waiting on the real implementation.
        """
        raise NotImplementedError(
            "Session 0 stub — implemented in Session C (IMPL-0002 Milestone E)"
        )


def _validate_workspace_id(workspace_id: str) -> None:
    """Reject workspace IDs that could cause path traversal."""
    if not workspace_id:
        raise ValueError("Workspace ID must not be empty")
    if "/" in workspace_id or "\\" in workspace_id:
        raise ValueError(
            f"Workspace ID must not contain path separators: {workspace_id!r}"
        )
    if workspace_id in (".", ".."):
        raise ValueError(
            f"Workspace ID must not be a relative path component: {workspace_id!r}"
        )


def _render_finding_md(finding: Finding) -> str:
    """Render a human-readable markdown summary of a finding."""
    lines = [f"# {finding.title}", ""]

    lines.append(f"- **Source:** {finding.source_type} / {finding.source_id}")
    lines.append(f"- **Status:** {finding.status}")

    if finding.raw_severity:
        lines.append(f"- **Severity:** {finding.raw_severity}")
    if finding.normalized_priority:
        lines.append(f"- **Priority:** {finding.normalized_priority}")
    if finding.asset_label or finding.asset_id:
        asset = finding.asset_label or finding.asset_id
        lines.append(f"- **Asset:** {asset}")
    if finding.likely_owner:
        lines.append(f"- **Likely owner:** {finding.likely_owner}")

    lines.append("")

    if finding.description:
        lines.append("## Description")
        lines.append("")
        lines.append(finding.description)
        lines.append("")

    if finding.why_this_matters:
        lines.append("## Why this matters")
        lines.append("")
        lines.append(finding.why_this_matters)
        lines.append("")

    return "\n".join(lines)
