"""Playwright E2E test seam for the assessment engine.

When both ``settings.opensec_test_fixture_repo_dir`` and
``settings.opensec_test_fixture_osv_dir`` are set, ``get_assessment_engine``
builds a ``ProductionAssessmentEngine`` with:

* a ``clone_strategy`` that copies the fixture repo directory into the
  caller's temp location instead of invoking git, and
* an ``httpx.MockTransport`` that replays OSV/GitHub responses from JSON
  files on disk.

This keeps the Playwright spec offline (no git, no OSV API, no GitHub API)
while still exercising every other moving part — parsers, posture checks,
grade derivation, finding persistence.

Never import this module from production code paths. The ``get_assessment_engine``
provider gates it behind the two env-only settings.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

import httpx

from opensec.assessment.production_engine import ProductionAssessmentEngine

logger = logging.getLogger(__name__)


def build_fixture_engine(
    *,
    fixture_repo_dir: str,
    fixture_osv_dir: str,
    tmp_root: Path,
) -> ProductionAssessmentEngine:
    """Construct a fixture-wired engine for the Playwright E2E backend.

    Parameters
    ----------
    fixture_repo_dir:
        Path to a directory that looks like a cloned repo — will be copied
        into the engine's temp clone location on every ``run_assessment`` call.
    fixture_osv_dir:
        Path to a directory containing OSV response JSON files keyed by
        ``<ecosystem>_<package>_<version>.json``. Unmatched lookups return
        ``{"vulns": []}`` so the engine still finishes.
    tmp_root:
        Where ``tempfile.TemporaryDirectory`` will create per-run clone dirs.
    """
    fixture_repo = Path(fixture_repo_dir)
    fixture_osv = Path(fixture_osv_dir)

    async def _copy_fixture_repo(
        repo_url: str, target: Path, token: str | None
    ) -> None:
        _ = repo_url, token  # unused — we ignore the incoming URL in test mode
        if not fixture_repo.is_dir():
            raise RuntimeError(
                f"fixture repo dir missing: {fixture_repo} "
                "(check OPENSEC_TEST_FIXTURE_REPO_DIR)"
            )
        # ``target`` is created empty by ProductionAssessmentEngine.run_assessment;
        # copytree requires the destination not to exist, so we remove it first.
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(fixture_repo, target)
        logger.info("E2E seam: copied %s into %s", fixture_repo, target)

    def _handle_osv(request: httpx.Request) -> httpx.Response:
        try:
            payload: dict[str, Any] = json.loads(request.content)
        except json.JSONDecodeError:
            return httpx.Response(200, json={"vulns": []})
        pkg = payload.get("package") or {}
        ecosystem = (pkg.get("ecosystem") or "").lower()
        name = (pkg.get("name") or "").lower()
        version = (payload.get("version") or "").lower()
        key = f"{ecosystem}_{name}_{version}.json".replace("/", "_")
        path = fixture_osv / key
        if path.is_file():
            return httpx.Response(200, json=json.loads(path.read_text()))
        return httpx.Response(200, json={"vulns": []})

    def _handle_github(request: httpx.Request) -> httpx.Response:
        # Return deterministic, passing responses so the E2E repo can reach
        # criteria.all_met() and trigger completion. Real deployments hit
        # the real GitHub API and get whatever posture the repo actually has.
        url = str(request.url)
        if "/branches/" in url and "/protection" in url:
            return httpx.Response(
                200,
                json={
                    "required_pull_request_reviews": {
                        "required_approving_review_count": 1,
                    },
                    "allow_force_pushes": {"enabled": False},
                },
            )
        if "/commits" in url:
            # Two signed commits — produces signed_commits=pass (100% signed).
            return httpx.Response(
                200,
                json=[
                    {
                        "sha": "abc123",
                        "commit": {"verification": {"verified": True}},
                    },
                    {
                        "sha": "def456",
                        "commit": {"verification": {"verified": True}},
                    },
                ],
            )
        return httpx.Response(404, json={"message": "E2E seam — unhandled gh path"})

    def _handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "api.osv.dev" in url:
            return _handle_osv(request)
        if "api.github.com" in url:
            return _handle_github(request)
        return httpx.Response(404, json={"message": "E2E seam — unhandled host"})

    transport = httpx.MockTransport(_handle)

    def _http_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport, timeout=10.0)

    async def _null_token() -> str | None:
        return None

    return ProductionAssessmentEngine(
        token_provider=_null_token,
        http_factory=_http_factory,
        clone_strategy=_copy_fixture_repo,
        tmp_root=tmp_root,
    )
