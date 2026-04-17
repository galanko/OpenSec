"""DI seam for the assessment engine.

Session B landed the protocol + a stub provider; Session G wires the real engine
here so callers don't have to change. Route code declares::

    engine: AssessmentEngineProtocol = Depends(get_assessment_engine)

Tests override via ``app.dependency_overrides[get_assessment_engine] = lambda: fake``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol

from opensec.config import settings

if TYPE_CHECKING:
    from opensec.models import AssessmentResult
    from opensec.workspace.workspace_dir_manager import WorkspaceKind


StepCallback = Callable[[str], Awaitable[None]]


class AssessmentEngineProtocol(Protocol):
    """Minimal contract for the assessment engine.

    ``on_step`` is an optional async callback invoked when the engine enters
    a new phase (``cloning``, ``parsing_lockfiles``, ``looking_up_cves``,
    ``checking_posture``, ``grading``) so the API layer can surface progress.
    Implementations may ignore it.
    """

    async def run_assessment(
        self,
        repo_url: str,
        *,
        assessment_id: str,
        on_step: StepCallback | None = None,
    ) -> AssessmentResult:
        ...


async def _github_token_from_integration() -> str | None:
    """Resolve the GitHub PAT from the ``github`` Integrations row + vault.

    This is the single accessor every consumer (assessment engine, posture-fix
    spawner, "solve a finding" workspace builder, onboarding's GitHub probe)
    calls. Returns ``None`` when the vault is not initialized or no GitHub
    integration has been configured yet.
    """
    # Late imports — avoid circulars with ``opensec.db.connection`` at module load.
    from opensec.db.connection import _db
    from opensec.db.repo_integration import list_integrations
    from opensec.main import app

    if _db is None:
        return None
    integrations = await list_integrations(_db)
    github = next((i for i in integrations if i.adapter_type == "github"), None)
    if github is None or not github.enabled:
        return None

    vault = getattr(app.state, "vault", None)
    if vault is None:
        return None

    # Canonical credential key, matched by the GitHub registry entry and the
    # remediation workspace's env setup. Onboarding writes under this exact
    # name; the engine/posture-fix spawner read from the same place.
    try:
        return await vault.retrieve(github.id, "github_personal_access_token")
    except Exception:
        return None


def get_assessment_engine() -> AssessmentEngineProtocol:
    """Return the production engine, or a fixture-backed variant under the E2E test seam.

    When both ``opensec_test_fixture_repo_dir`` and
    ``opensec_test_fixture_osv_dir`` are set in config (via env vars), this
    returns an engine that copies from the fixture directory instead of
    shelling out to git and mocks OSV/GitHub responses from JSON files on
    disk. That seam is for the Playwright E2E backend only — production
    deployments leave both empty and get the real shallow-clone path.
    """
    # Late imports — ``production_engine`` pulls in httpx which shouldn't be a
    # load-time cost for tests that never touch the real engine.
    from opensec.assessment.production_engine import ProductionAssessmentEngine

    tmp_root = settings.resolve_data_dir() / "clones"

    fixture_repo_dir = settings.test_fixture_repo_dir.strip()
    fixture_osv_dir = settings.test_fixture_osv_dir.strip()
    if fixture_repo_dir and fixture_osv_dir:
        # Deferred import so production doesn't load test-only helpers.
        from opensec.assessment._test_seam import build_fixture_engine

        return build_fixture_engine(
            fixture_repo_dir=fixture_repo_dir,
            fixture_osv_dir=fixture_osv_dir,
            tmp_root=tmp_root,
        )

    return ProductionAssessmentEngine(
        token_provider=_github_token_from_integration,
        tmp_root=tmp_root,
    )


# --- Workspace dir manager seam (Milestone D3) ----------------------------------


class RepoWorkspaceSpawnerProtocol(Protocol):
    """Minimal contract for spawning a posture-fix repo workspace (Session C)."""

    async def spawn_repo_workspace(
        self, *, kind: WorkspaceKind, repo_url: str
    ) -> str:  # returns workspace_id
        ...


class _DefaultRepoWorkspaceSpawner:
    """Production spawner backed by ``WorkspaceDirManager.create_repo_workspace``.

    Creates the on-disk workspace scaffolding and returns the workspace id. The
    posture-fix route relays the id to the SPA so the user can track agent
    progress. DB workspace rows (which require ``finding_id``) are not created
    here — repo-action workspaces are finding-less by design.
    """

    async def spawn_repo_workspace(
        self, *, kind: WorkspaceKind, repo_url: str
    ) -> str:
        from opensec.workspace.workspace_dir_manager import WorkspaceDirManager

        token = await _github_token_from_integration()
        data_dir = settings.resolve_data_dir()
        manager = WorkspaceDirManager(base_dir=data_dir / "workspaces")
        return manager.create_repo_workspace(
            kind, repo_url=repo_url, gh_token=token
        )


def get_repo_workspace_spawner() -> RepoWorkspaceSpawnerProtocol:
    """Default provider — returns the real spawner built on ``WorkspaceDirManager``.

    Route tests override this via ``app.dependency_overrides``.
    """
    return _DefaultRepoWorkspaceSpawner()


