"""End-to-end integration between the real assessment engine and the API.

Session G's deliverable: prove that the real orchestrator (``run_assessment_on_path``)
integrates cleanly with Session B's route + background persistence layer. The
route-level tests in ``test_assessment_routes.py`` keep using ``FakeAssessmentEngine``
because they're testing HTTP→DB plumbing, not engine semantics; this file is
the single place where the two halves run together.

The engine is wired with:

* ``clone_strategy`` — copies a planted fixture directory into the engine's
  tmp clone location (no git subprocess, no network).
* ``http_factory`` — returns an ``httpx.AsyncClient`` backed by a
  ``MockTransport`` that replays the real OSV response for ``braces@3.0.2``
  from ``backend/tests/fixtures/osv/`` and 403s every GitHub call (so posture
  checks degrade to ``UnableToVerify`` per ADR-0025).

What this test catches that route-level tests can't:

1. ``AssessmentResult`` shape contract (Gap #2) — if the engine's dict keys
   ever drift from what ``_background.py`` reads, it fails here.
2. ``result.findings`` persistence (Gap #3) — engine-emitted findings must
   land in the ``finding`` table with ``source_type='opensec-assessment'``.
3. The DI seam — swapping ``get_assessment_engine`` with a real
   ``ProductionAssessmentEngine`` instance exercises the exact code path a
   flag-on deployment uses.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from opensec.api._engine_dep import get_assessment_engine
from opensec.assessment.production_engine import ProductionAssessmentEngine
from opensec.main import app

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def planted_repo(tmp_path: Path) -> Path:
    """Tree laid out on disk that the engine will treat as the 'cloned' repo.

    One vulnerable npm lockfile + one planted AWS secret + no SECURITY.md —
    identical to the unit-level ``planted_repo`` in ``tests/assessment/test_engine.py``.
    Expected outcome after assessment:

    * 1 finding (braces@3.0.2 HIGH) → persisted with ``source_type='opensec-assessment'``
    * 7 posture checks → all persisted; ``no_secrets_in_code`` / ``security_md``
      / ``dependabot_config`` fail, ``branch_protection`` / ``no_force_pushes``
      unknown (403 from seam)
    * No completion row — criteria can't all be met with a HIGH finding present
    """
    repo = tmp_path / "fixture_repo"
    repo.mkdir()
    (repo / "package-lock.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "demo", "version": "1.0.0"},
                    "node_modules/braces": {"version": "3.0.2"},
                },
            }
        )
    )
    (repo / "src").mkdir()
    (repo / "src" / "config.js").write_text(
        "export const AWS = 'AKIAIOSFODNN7EXAMPLE';\n"
    )
    return repo


def _build_real_engine(planted: Path, tmp_root: Path) -> ProductionAssessmentEngine:
    """Construct a ``ProductionAssessmentEngine`` wired with fixture clones + canned OSV."""

    import shutil

    async def _clone_from_fixture(
        repo_url: str, target: Path, token: str | None
    ) -> None:
        _ = repo_url, token
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(planted, target)

    osv_payload = json.loads((FIXTURES / "osv" / "braces_3_0_2.json").read_text())

    def _handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "api.osv.dev" in url:
            body = json.loads(request.content)
            name = (body.get("package") or {}).get("name")
            if name == "braces":
                return httpx.Response(200, json=osv_payload)
            return httpx.Response(200, json={"vulns": []})
        if "api.github.com" in url:
            return httpx.Response(403, json={"message": "integration test"})
        return httpx.Response(404, json={"message": "unhandled"})

    transport = httpx.MockTransport(_handle)

    def _http_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=transport, timeout=5.0)

    async def _null_token() -> str | None:
        return None

    return ProductionAssessmentEngine(
        token_provider=_null_token,
        http_factory=_http_factory,
        clone_strategy=_clone_from_fixture,
        tmp_root=tmp_root,
    )


async def _drain_background_tasks() -> None:
    import asyncio

    tasks = list(getattr(app.state, "assessment_tasks", set()))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_real_engine_persists_findings_posture_and_assessment(
    db_client, tmp_path: Path, planted_repo: Path
) -> None:
    engine = _build_real_engine(planted_repo, tmp_root=tmp_path / "clones")
    app.dependency_overrides[get_assessment_engine] = lambda: engine
    try:
        resp = await db_client.post(
            "/api/assessment/run",
            json={"repo_url": "https://github.com/acme/demo"},
        )
        assert resp.status_code == 200, resp.text
        aid = resp.json()["assessment_id"]

        await _drain_background_tasks()

        from opensec.db.connection import _db
        from opensec.db.dao.assessment import get_assessment
        from opensec.db.dao.completion import get_completion_for_assessment
        from opensec.db.dao.posture_check import list_posture_checks_for_assessment
        from opensec.db.repo_finding import list_findings

        # Assessment row transitions all the way to ``complete``.
        assessment = await get_assessment(_db, aid)
        assert assessment is not None
        assert assessment.status == "complete"
        assert assessment.grade in {"B", "C", "D", "F"}  # HIGH present → not A

        # Posture: seven checks, all rows present.
        checks = await list_posture_checks_for_assessment(_db, aid)
        names = {c.check_name for c in checks}
        assert "no_secrets_in_code" in names
        assert "security_md" in names
        assert "dependabot_config" in names
        assert "lockfile_present" in names
        assert len(checks) == 7  # Session A's checklist

        # Gap #3: engine finding landed in the DB with the expected source_type.
        findings = await list_findings(_db)
        engine_findings = [f for f in findings if f.source_type == "opensec-assessment"]
        assert len(engine_findings) == 1
        assert engine_findings[0].source_id == "GHSA-grv7-fg5c-xmjg"
        assert engine_findings[0].raw_severity == "HIGH"
        assert engine_findings[0].asset_label == "braces@3.0.2"

        # No completion — criteria can't be met while a HIGH finding exists.
        assert await get_completion_for_assessment(_db, aid) is None
    finally:
        app.dependency_overrides.pop(get_assessment_engine, None)


async def test_real_engine_http_mock_surface(
    db_client, tmp_path: Path, planted_repo: Path
) -> None:
    """Sanity: the ``httpx.MockTransport`` seam the E2E depends on is exercised.

    Proves that the production engine actually hits ``api.osv.dev`` via the
    real OSV client and that our MockTransport intercepts the request. If this
    test breaks, the Playwright E2E's ``_test_seam.py`` wiring is broken too.
    """
    calls: list[str] = []

    import shutil

    async def _clone(repo_url: str, target: Path, token: str | None) -> None:
        _ = repo_url, token
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(planted_repo, target)

    def _handle(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "api.osv.dev" in str(request.url):
            return httpx.Response(200, json={"vulns": []})
        return httpx.Response(403, json={"message": "integration test"})

    transport = httpx.MockTransport(_handle)

    async def _null() -> str | None:
        return None

    engine = ProductionAssessmentEngine(
        token_provider=_null,
        http_factory=lambda: httpx.AsyncClient(transport=transport, timeout=5.0),
        clone_strategy=_clone,
        tmp_root=tmp_path / "clones",
    )

    app.dependency_overrides[get_assessment_engine] = lambda: engine
    try:
        resp = await db_client.post(
            "/api/assessment/run", json={"repo_url": "https://github.com/acme/x"}
        )
        assert resp.status_code == 200
        await _drain_background_tasks()

        assert any("api.osv.dev" in url for url in calls), (
            f"expected MockTransport to see an OSV call; saw {calls}"
        )
    finally:
        app.dependency_overrides.pop(get_assessment_engine, None)
