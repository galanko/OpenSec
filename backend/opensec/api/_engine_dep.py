"""DI seam for the assessment engine (Session B stub; real engine lands in Session G).

Session A owns ``backend/opensec/assessment/``; to avoid touching their tree we define
the protocol + provider here in the api package. Session G wires the real engine by
replacing ``get_assessment_engine``'s body (no callers change).

Route code declares::

    engine: AssessmentEngineProtocol = Depends(get_assessment_engine)

Tests override via ``app.dependency_overrides[get_assessment_engine] = lambda: fake``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from opensec.models import AssessmentResult
    from opensec.workspace.workspace_dir_manager import WorkspaceKind


class AssessmentEngineProtocol(Protocol):
    """Minimal contract Session B builds against; Session A's real engine conforms."""

    async def run_assessment(self, repo_url: str, *, assessment_id: str) -> AssessmentResult:
        ...


def get_assessment_engine() -> AssessmentEngineProtocol:
    """Default provider — raises until Session G swaps in the real engine.

    Route tests in Session B override this via ``app.dependency_overrides``.
    """
    raise NotImplementedError(
        "Assessment engine is not wired yet (Session A + G). "
        "Tests must override get_assessment_engine via FastAPI dependency_overrides."
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
