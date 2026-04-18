"""DI seam for the assessment engine.

Session B landed the protocol + a stub provider; Session G wires the real engine
here so callers don't have to change. Route code declares::

    engine: AssessmentEngineProtocol = Depends(get_assessment_engine)

Tests override via ``app.dependency_overrides[get_assessment_engine] = lambda: fake``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Protocol

import asyncio
import logging

from fastapi import Request

from opensec.config import settings

if TYPE_CHECKING:
    from opensec.engine.pool import WorkspaceProcessPool
    from opensec.models import AssessmentResult
    from opensec.workspace.workspace_dir_manager import WorkspaceKind

logger = logging.getLogger(__name__)


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
    """Minimal contract for spawning a posture-fix repo workspace (Session C).

    ``params`` are passed through to the generator template (e.g.
    ``contact_email`` for SECURITY.md). ``None`` keeps the pre-params
    call shape for existing callers/tests.
    """

    async def spawn_repo_workspace(
        self,
        *,
        kind: WorkspaceKind,
        repo_url: str,
        params: dict[str, Any] | None = None,
    ) -> str:  # returns workspace_id
        ...


class _DefaultRepoWorkspaceSpawner:
    """Production spawner backed by ``WorkspaceDirManager.create_repo_workspace``.

    Before IMPL-0002 B6 this class only scaffolded a directory — the generator
    agent never actually ran. Now the spawner also kicks off a background
    ``RepoAgentRunner.run`` task against the shared ``WorkspaceProcessPool``
    so ``POST /api/posture/fix/...`` produces a real draft PR.

    DB workspace rows (which require ``finding_id``) are still not created —
    repo-action workspaces are finding-less by design and persist their state
    in ``history/status.json`` instead.
    """

    def __init__(self, pool: WorkspaceProcessPool | None) -> None:
        # ``pool=None`` keeps the old stub behaviour for tests that haven't
        # provided one; in production ``get_repo_workspace_spawner`` always
        # supplies the app's pool.
        self._pool = pool

    async def spawn_repo_workspace(
        self,
        *,
        kind: WorkspaceKind,
        repo_url: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        from opensec.workspace.repo_workspace_runner import RepoAgentRunner
        from opensec.workspace.workspace_dir_manager import WorkspaceDirManager

        token = await _github_token_from_integration()
        data_dir = settings.resolve_data_dir()
        base_dir = data_dir / "workspaces"
        manager = WorkspaceDirManager(base_dir=base_dir)
        # The model is stored in the repo-root opencode.json (updated by the
        # AI onboarding step). Without it, the workspace process rejects every
        # message with "The requested model is not supported." — so we have
        # to copy it into each repo-workspace config.
        model = settings.opencode_model or None
        workspace_id = manager.create_repo_workspace(
            kind,
            repo_url=repo_url,
            params=params,
            gh_token=token,
            model=model,
        )

        if self._pool is None:
            # Tests / degraded deployments: scaffold only. The scaffolded
            # directory is still useful as an inspection artefact.
            logger.warning(
                "repo workspace %s created without a pool — agent will not run",
                workspace_id,
            )
            return workspace_id

        workspace_root = base_dir / workspace_id
        runner = RepoAgentRunner(self._pool)

        async def _run() -> None:
            try:
                await runner.run(
                    workspace_id=workspace_id,
                    workspace_root=workspace_root,
                    kind=kind,
                    repo_url=repo_url,
                    gh_token=token,
                    params=params,
                )
            except Exception:  # noqa: BLE001 — runner is supposed to swallow
                logger.exception(
                    "RepoAgentRunner raised unexpectedly for %s",
                    workspace_id,
                )

        asyncio.create_task(_run(), name=f"repo-agent:{workspace_id}")
        return workspace_id


def get_repo_workspace_spawner(request: Request) -> RepoWorkspaceSpawnerProtocol:
    """Default provider — returns the real spawner wired to the app's pool.

    Route tests override this via ``app.dependency_overrides``.
    """
    pool = getattr(request.app.state, "process_pool", None)
    return _DefaultRepoWorkspaceSpawner(pool=pool)


