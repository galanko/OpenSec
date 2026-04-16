"""DI seam for the assessment engine.

Session B landed the protocol + a stub provider; Session G wires the real engine
here so callers don't have to change. Route code declares::

    engine: AssessmentEngineProtocol = Depends(get_assessment_engine)

Tests override via ``app.dependency_overrides[get_assessment_engine] = lambda: fake``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from opensec.config import settings

if TYPE_CHECKING:
    from opensec.models import AssessmentResult
    from opensec.workspace.workspace_dir_manager import WorkspaceKind


class AssessmentEngineProtocol(Protocol):
    """Minimal contract Session B builds against; Session A's real engine conforms."""

    async def run_assessment(self, repo_url: str, *, assessment_id: str) -> AssessmentResult:
        ...


async def _github_token_from_settings() -> str | None:
    """Resolve the stored GitHub token from the ``onboarding.github_token`` setting.

    The onboarding route (``POST /api/onboarding/repo``) stores the PAT as
    ``{"token": "..."}`` via ``upsert_setting``. Routing through the real
    credential vault is deferred; reading from the same row keeps the engine
    working end-to-end without a vault integration in this PR.
    """
    # Late imports — avoid circulars with ``opensec.db.connection`` at module load.
    from opensec.db.connection import _db
    from opensec.db.repo_setting import get_setting

    if _db is None:
        return None
    row = await get_setting(_db, "onboarding.github_token")
    if row is None or not isinstance(row.value, dict):
        return None
    token = row.value.get("token")
    return token if isinstance(token, str) and token else None


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
        token_provider=_github_token_from_settings,
        tmp_root=tmp_root,
    )


# --- Workspace dir manager seam (Milestone D3) ----------------------------------


class RepoWorkspaceSpawnerProtocol(Protocol):
    """Minimal contract for spawning a posture-fix repo workspace (Session C)."""

    async def spawn_repo_workspace(
        self, *, kind: WorkspaceKind, repo_url: str
    ) -> str:  # returns workspace_id
        ...


def get_repo_workspace_spawner() -> RepoWorkspaceSpawnerProtocol:
    """Default provider — raises until Session C + G wire ``create_repo_workspace``.

    Route tests in Session B override this via ``app.dependency_overrides``.
    """
    raise NotImplementedError(
        "Repo workspace spawner is not wired yet (Session C + G). "
        "Tests must override get_repo_workspace_spawner via FastAPI dependency_overrides."
    )
