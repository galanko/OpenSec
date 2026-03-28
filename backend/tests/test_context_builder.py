"""Tests for Layer 2: WorkspaceContextBuilder — orchestrates L0 + L1 + DB."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import aiosqlite
import pytest

from opensec.agents import AgentTemplateEngine
from opensec.db.migrations import run_migrations
from opensec.db.repo_finding import create_finding
from opensec.db.repo_workspace import get_workspace
from opensec.models import FindingCreate
from opensec.workspace import WorkspaceContextBuilder, WorkspaceDirManager

if TYPE_CHECKING:
    from pathlib import Path

    from opensec.models import Finding


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db():
    """In-memory aiosqlite database with all migrations applied."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    await run_migrations(conn)
    yield conn
    await conn.close()


@pytest.fixture
async def sample_finding(db: aiosqlite.Connection) -> Finding:
    """A fully-populated Finding inserted into the test DB."""
    return await create_finding(
        db,
        FindingCreate(
            source_type="snyk",
            source_id="SNYK-JAVA-LOG4J-2314720",
            title="Remote Code Execution in log4j (CVE-2021-44228)",
            description=(
                "A critical RCE vulnerability in Apache Log4j 2.x allows "
                "attackers to execute arbitrary code via JNDI lookup."
            ),
            raw_severity="critical",
            normalized_priority="P1",
            asset_id="svc-api-gateway",
            asset_label="api-gateway (prod)",
            status="new",
            likely_owner="platform-team",
            why_this_matters="Public exploit available. Internet-facing service.",
            raw_payload={"cve": "CVE-2021-44228", "cvss": 10.0},
        ),
    )


@pytest.fixture
def dir_manager(tmp_path: Path) -> WorkspaceDirManager:
    return WorkspaceDirManager(base_dir=tmp_path / "workspaces")


@pytest.fixture
def template_engine() -> AgentTemplateEngine:
    return AgentTemplateEngine()


@pytest.fixture
def builder(
    dir_manager: WorkspaceDirManager, template_engine: AgentTemplateEngine
) -> WorkspaceContextBuilder:
    return WorkspaceContextBuilder(
        dir_manager=dir_manager, template_engine=template_engine
    )


# ---------------------------------------------------------------------------
# create_workspace
# ---------------------------------------------------------------------------


async def test_create_workspace_creates_dir_and_db(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
    dir_manager: WorkspaceDirManager,
):
    """create_workspace creates DB row + directory + agents."""
    workspace = await builder.create_workspace(db, sample_finding)

    # DB row exists with workspace_dir set
    assert workspace is not None
    assert workspace.finding_id == sample_finding.id
    assert workspace.workspace_dir is not None
    assert workspace.context_version == 0

    # Directory exists on disk
    ws_dir = dir_manager.get(workspace.id)
    assert ws_dir is not None
    assert ws_dir.exists()
    assert ws_dir.finding_json.is_file()
    assert ws_dir.context_md.is_file()

    # 6 agent files rendered
    agent_files = list(ws_dir.agents_dir.glob("*.md"))
    assert len(agent_files) == 6


async def test_create_workspace_agents_contain_finding(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
    dir_manager: WorkspaceDirManager,
):
    """Rendered agents contain the finding title."""
    workspace = await builder.create_workspace(db, sample_finding)
    ws_dir = dir_manager.get(workspace.id)
    assert ws_dir is not None

    orchestrator = (ws_dir.agents_dir / "orchestrator.md").read_text()
    assert "Remote Code Execution in log4j" in orchestrator
    assert "mode: primary" in orchestrator


# ---------------------------------------------------------------------------
# update_context
# ---------------------------------------------------------------------------


async def test_update_context_writes_section(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
    dir_manager: WorkspaceDirManager,
):
    """update_context writes the section file and regenerates CONTEXT.md."""
    workspace = await builder.create_workspace(db, sample_finding)

    enrichment = {"summary": "Log4Shell RCE", "cvss_score": 10.0, "known_exploits": True}
    await builder.update_context(
        db, workspace.id, "finding_enricher", enrichment, summary="Log4Shell"
    )

    # Section file exists
    ws_dir = dir_manager.get(workspace.id)
    assert ws_dir is not None
    data = json.loads(ws_dir.context_file("enrichment").read_text())
    assert data["summary"] == "Log4Shell RCE"

    # CONTEXT.md updated
    context_md = ws_dir.context_md.read_text()
    assert "What we know so far" in context_md


async def test_update_context_re_renders_agents(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
    dir_manager: WorkspaceDirManager,
):
    """After context update, agents are re-rendered with new data."""
    workspace = await builder.create_workspace(db, sample_finding)

    orchestrator_before = (
        dir_manager.get(workspace.id).agents_dir / "orchestrator.md"  # type: ignore[union-attr]
    ).read_text()
    assert "- [x] **Enrichment**" not in orchestrator_before

    await builder.update_context(
        db,
        workspace.id,
        "finding_enricher",
        {"summary": "Log4Shell confirmed", "cve_ids": ["CVE-2021-44228"]},
    )

    orchestrator_after = (
        dir_manager.get(workspace.id).agents_dir / "orchestrator.md"  # type: ignore[union-attr]
    ).read_text()
    assert "- [x] **Enrichment**" in orchestrator_after
    assert "CVE-2021-44228" in orchestrator_after


async def test_update_context_increments_version(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
):
    """Each update_context call increments context_version."""
    workspace = await builder.create_workspace(db, sample_finding)

    v1 = await builder.update_context(
        db, workspace.id, "finding_enricher", {"summary": "enriched"}
    )
    v2 = await builder.update_context(
        db, workspace.id, "owner_resolver", {"recommended_owner": "team-a"}
    )
    v3 = await builder.update_context(
        db, workspace.id, "exposure_analyzer", {"reachable": "confirmed"}
    )

    assert v1 == 1
    assert v2 == 2
    assert v3 == 3

    # Verify in DB
    ws = await get_workspace(db, workspace.id)
    assert ws is not None
    assert ws.context_version == 3


async def test_update_context_invalid_agent_type(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
):
    """Unknown agent_type raises ValueError."""
    workspace = await builder.create_workspace(db, sample_finding)
    with pytest.raises(ValueError, match="Unknown agent_type"):
        await builder.update_context(db, workspace.id, "bogus_agent", {"x": 1})


async def test_update_context_logs_to_agent_runs(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
    dir_manager: WorkspaceDirManager,
):
    """update_context appends to agent-runs.jsonl."""
    workspace = await builder.create_workspace(db, sample_finding)
    await builder.update_context(
        db,
        workspace.id,
        "finding_enricher",
        {"summary": "test"},
        summary="Enriched the finding",
    )

    ws_dir = dir_manager.get(workspace.id)
    assert ws_dir is not None
    log_content = ws_dir.agent_runs_log.read_text().strip()
    entry = json.loads(log_content)
    assert entry["agent_type"] == "finding_enricher"
    assert entry["status"] == "completed"
    assert entry["summary"] == "Enriched the finding"


# ---------------------------------------------------------------------------
# get_context_snapshot
# ---------------------------------------------------------------------------


async def test_get_context_snapshot(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
):
    """get_context_snapshot returns finding + sections + history."""
    workspace = await builder.create_workspace(db, sample_finding)
    await builder.update_context(
        db, workspace.id, "finding_enricher", {"summary": "enriched"}
    )
    await builder.update_context(
        db, workspace.id, "owner_resolver", {"recommended_owner": "team-a"}
    )

    snapshot = await builder.get_context_snapshot(workspace.id)

    assert snapshot["finding"]["title"] == "Remote Code Execution in log4j (CVE-2021-44228)"
    assert snapshot["enrichment"] == {"summary": "enriched"}
    assert snapshot["ownership"] == {"recommended_owner": "team-a"}
    assert snapshot["exposure"] is None
    assert snapshot["plan"] is None
    assert snapshot["validation"] is None
    assert len(snapshot["agent_run_history"]) == 2


async def test_get_context_snapshot_nonexistent(builder: WorkspaceContextBuilder):
    """get_context_snapshot on nonexistent workspace raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        await builder.get_context_snapshot("nonexistent-ws")


# ---------------------------------------------------------------------------
# delete_workspace
# ---------------------------------------------------------------------------


async def test_delete_removes_dir_and_db(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
    dir_manager: WorkspaceDirManager,
):
    """delete_workspace removes both directory and DB row."""
    workspace = await builder.create_workspace(db, sample_finding)

    result = await builder.delete_workspace(db, workspace.id)
    assert result is True

    # Directory gone
    assert dir_manager.get(workspace.id) is None
    # DB row gone
    assert await get_workspace(db, workspace.id) is None


async def test_delete_missing_dir_still_deletes_db(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
    dir_manager: WorkspaceDirManager,
):
    """If directory is already gone, DB row is still deleted."""
    workspace = await builder.create_workspace(db, sample_finding)

    # Manually remove directory
    import shutil

    ws_dir = dir_manager.get(workspace.id)
    assert ws_dir is not None
    shutil.rmtree(ws_dir.root)

    # Should not crash
    result = await builder.delete_workspace(db, workspace.id)
    assert result is True
    assert await get_workspace(db, workspace.id) is None


# ---------------------------------------------------------------------------
# archive_workspace
# ---------------------------------------------------------------------------


async def test_archive_creates_tarball_and_closes(
    builder: WorkspaceContextBuilder,
    db: aiosqlite.Connection,
    sample_finding: Finding,
):
    """archive_workspace creates tar.gz and sets DB state to closed."""
    workspace = await builder.create_workspace(db, sample_finding)
    archive_path = await builder.archive_workspace(db, workspace.id)

    assert archive_path.exists()
    assert str(archive_path).endswith(".tar.gz")

    # DB state is closed
    ws = await get_workspace(db, workspace.id)
    assert ws is not None
    assert ws.state == "closed"


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


async def test_migration_adds_columns():
    """Migration 002 adds workspace_dir and context_version columns."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await run_migrations(conn)

    cursor = await conn.execute("PRAGMA table_info(workspace)")
    columns = {row["name"] for row in await cursor.fetchall()}
    assert "workspace_dir" in columns
    assert "context_version" in columns

    await conn.close()
