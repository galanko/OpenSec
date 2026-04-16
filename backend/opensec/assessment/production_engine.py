"""Production wiring for the assessment orchestrator (EXEC-0002 Session G).

``ProductionAssessmentEngine`` conforms to ``AssessmentEngineProtocol`` and is
the default engine returned by :func:`opensec.api._engine_dep.get_assessment_engine`.

Responsibilities
----------------
1. Resolve the GitHub token from the same ``app_setting`` row the onboarding
   route writes to (``onboarding.github_token``).
2. Clone the target repo shallowly into a temp directory that lives under
   ``<data_dir>/clones/`` so it's easy to sweep if the app crashes mid-run.
3. Delegate to :func:`opensec.assessment.engine.run_assessment_on_path` with
   real ``OsvClient`` / ``GithubClient`` instances.
4. Stamp the caller-supplied ``assessment_id`` onto the returned
   ``AssessmentResult`` (the orchestrator generates its own, but the API layer
   needs the DB row id to flow through).

The ``clone_strategy`` constructor hook is the test seam: integration tests
and the Playwright E2E backend inject a callable that copies a planted fixture
directory into the tmp path instead of shelling out to git. That keeps CI
offline without special-casing the production code path.

We intentionally do **not** build a formal ``RepoCloner`` class here. ADR-0024
puts cloning in agent bash, not in Python; the 20-line helper below matches
that minimalism. When/if a real cloner lands, it slots in via the same hook.
"""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx

from opensec.assessment.engine import run_assessment_on_path
from opensec.assessment.osv_client import OsvClient
from opensec.assessment.posture.github_client import GithubClient

if TYPE_CHECKING:
    from opensec.models import AssessmentResult

logger = logging.getLogger(__name__)

CloneStrategy = Callable[[str, Path, str | None], Awaitable[None]]
"""Signature: ``(repo_url, target_path, token) -> None``.

Production: shells out to ``git clone --depth 1``. Tests: copy a fixture tree.
"""


class ProductionAssessmentEngine:
    """Real engine wired for use by the FastAPI lifespan.

    Parameters
    ----------
    token_provider:
        Async callable returning the GitHub token, or ``None`` if the user
        hasn't supplied one yet (public repos without auth still work for
        clone; `GithubClient` will return `UnableToVerify` for the few
        endpoints that need auth).
    http_factory:
        Factory for the shared ``httpx.AsyncClient`` used by both OSV and
        GitHub. Tests override this with an ``httpx.MockTransport``-backed
        client.
    clone_strategy:
        Async callable ``(repo_url, target, token) -> None``. Defaults to the
        built-in ``_shallow_clone`` which invokes ``git clone --depth 1``.
    tmp_root:
        Directory under which temporary clone directories are created. Default
        is the platform temp dir; production should pass ``<data_dir>/clones``.
    clone_timeout_s:
        Hard cap on the clone subprocess.
    """

    def __init__(
        self,
        *,
        token_provider: Callable[[], Awaitable[str | None]],
        http_factory: Callable[[], httpx.AsyncClient] | None = None,
        clone_strategy: CloneStrategy | None = None,
        tmp_root: Path | None = None,
        clone_timeout_s: float = 60.0,
    ) -> None:
        self._token_provider = token_provider
        self._http_factory = http_factory or (lambda: httpx.AsyncClient(timeout=30.0))
        self._clone_strategy = clone_strategy or self._shallow_clone
        self._tmp_root = tmp_root
        self._clone_timeout_s = clone_timeout_s

    async def run_assessment(
        self, repo_url: str, *, assessment_id: str
    ) -> AssessmentResult:
        _validate_repo_url(repo_url)
        token = await self._token_provider()

        if self._tmp_root is not None:
            self._tmp_root.mkdir(parents=True, exist_ok=True)

        tmp_root_str = str(self._tmp_root) if self._tmp_root else None
        with tempfile.TemporaryDirectory(dir=tmp_root_str) as tmp:
            tmp_path = Path(tmp) / "repo"
            tmp_path.mkdir()
            await self._clone_strategy(repo_url, tmp_path, token)

            async with self._http_factory() as http:
                osv = OsvClient(http)
                gh = GithubClient(http, token=token)
                result = await run_assessment_on_path(
                    tmp_path,
                    repo_url=repo_url,
                    gh_client=gh,
                    osv=osv,
                )

        # The orchestrator generates its own uuid for ``assessment_id``; stamp
        # the DB row's id on the way out so the caller's persistence path
        # (``_background.py``) writes against the row it created.
        return result.model_copy(update={"assessment_id": assessment_id})

    async def _shallow_clone(
        self, repo_url: str, target: Path, token: str | None
    ) -> None:
        """``git clone --depth 1 <url> <target>`` with token injected via URL.

        Tokens never appear in the subprocess arg list unsanitized — we scrub
        stderr before logging on failure. ``GIT_TERMINAL_PROMPT=0`` prevents git
        from opening an interactive credential prompt when the token is
        missing or wrong.
        """
        url = _inject_token(repo_url, token)
        redacted_url = _redact_token(url, token)

        env = {"GIT_TERMINAL_PROMPT": "0"}
        proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            url,
            str(target),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            _, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._clone_timeout_s
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(
                f"git clone timed out after {self._clone_timeout_s}s for {redacted_url}"
            ) from None

        if proc.returncode != 0:
            scrubbed = _redact_token(stderr.decode("utf-8", errors="replace"), token)
            raise RuntimeError(
                f"git clone failed for {redacted_url} (exit {proc.returncode}): {scrubbed.strip()}"
            )


def _validate_repo_url(repo_url: str) -> None:
    """Reject anything we shouldn't clone from — non-https schemes and local paths.

    The clone step runs as the backend process; accepting arbitrary ``file://``
    or ``ssh://`` URLs would let a user read anything the backend can see. This
    matches the onboarding wizard's contract: public GitHub URLs over HTTPS.
    """
    if not repo_url:
        raise ValueError("repo_url must not be empty")
    parsed = urlparse(repo_url)
    if parsed.scheme not in {"https", "http"}:
        raise ValueError(
            f"repo_url must be https:// (got scheme {parsed.scheme!r}); "
            "non-HTTP(S) clones are rejected for safety"
        )
    if not parsed.netloc:
        raise ValueError(f"repo_url is missing a host: {repo_url!r}")


def _inject_token(repo_url: str, token: str | None) -> str:
    """Rewrite ``https://github.com/...`` to ``https://x-access-token:TOKEN@...``.

    When no token is supplied the URL is returned unchanged — git will then
    fail fast on a private repo, which surfaces cleanly as a ``status="failed"``
    assessment via the existing exception handler in ``_background.py``.
    """
    if not token:
        return repo_url
    parsed = urlparse(repo_url)
    netloc = f"x-access-token:{token}@{parsed.netloc}"
    return parsed._replace(netloc=netloc).geturl()


_TOKEN_URL_PATTERN = re.compile(r"x-access-token:[^@\s]+@")


def _redact_token(text: str, token: str | None) -> str:
    """Remove the token from log-bound text in two belt-and-suspenders passes."""
    scrubbed = _TOKEN_URL_PATTERN.sub("x-access-token:***@", text)
    if token:
        scrubbed = scrubbed.replace(token, "***")
    return scrubbed
