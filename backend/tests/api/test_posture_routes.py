"""Route tests for D3 posture fix (IMPL-0002)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from opensec.api._engine_dep import get_repo_workspace_spawner
from opensec.main import app
from opensec.workspace.workspace_dir_manager import WorkspaceKind


@dataclass
class FakeSpawner:
    """Records calls so tests can assert agent/template wiring."""

    fixed_workspace_id: str = "ws-123"
    calls: list[dict] = field(default_factory=list)

    async def spawn_repo_workspace(self, *, kind: WorkspaceKind, repo_url: str) -> str:
        self.calls.append({"kind": kind, "repo_url": repo_url})
        return self.fixed_workspace_id


@pytest.fixture
def fake_spawner():
    spawner = FakeSpawner()
    app.dependency_overrides[get_repo_workspace_spawner] = lambda: spawner
    try:
        yield spawner
    finally:
        app.dependency_overrides.pop(get_repo_workspace_spawner, None)


async def _seed_onboarded_repo(repo_url: str) -> None:
    """Minimum state so a posture fix has somewhere to run — the last assessment's repo."""
    from opensec.db.connection import _db
    from opensec.db.dao.assessment import create_assessment
    from opensec.models import AssessmentCreate

    assert _db is not None
    await create_assessment(_db, AssessmentCreate(repo_url=repo_url))


async def test_fix_security_md(db_client, fake_spawner):
    await _seed_onboarded_repo("https://github.com/a/b")

    resp = await db_client.post("/api/posture/fix/security_md")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == "ws-123"
    assert data["check_name"] == "security_md"
    assert fake_spawner.calls == [
        {
            "kind": WorkspaceKind.repo_action_security_md,
            "repo_url": "https://github.com/a/b",
        }
    ]


async def test_fix_dependabot_config(db_client, fake_spawner):
    await _seed_onboarded_repo("https://github.com/a/c")

    resp = await db_client.post("/api/posture/fix/dependabot_config")
    assert resp.status_code == 200
    assert fake_spawner.calls[0]["kind"] == WorkspaceKind.repo_action_dependabot


async def test_fix_unknown_check_returns_422(db_client, fake_spawner):
    resp = await db_client.post("/api/posture/fix/branch_protection")
    assert resp.status_code == 422
    assert fake_spawner.calls == []


async def test_fix_without_any_assessment_returns_409(db_client, fake_spawner):
    # No assessment ever run — posture fix has no repo target.
    resp = await db_client.post("/api/posture/fix/security_md")
    assert resp.status_code == 409
    assert fake_spawner.calls == []
