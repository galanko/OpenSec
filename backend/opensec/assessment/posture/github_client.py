"""Thin GitHub REST client used by the posture checks.

We intentionally do not depend on PyGithub — three endpoints and a token is
all we need. On 403/404/429 we return a sentinel `UnableToVerify`, not raise,
so a PAT without admin scope degrades rather than failing the whole
assessment (ADR-0025 risk row).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"


@dataclass(frozen=True)
class UnableToVerify:
    reason: str


class GithubClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        token: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._http = http
        self._token = token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def get_branch_protection(
        self, owner: str, repo: str, branch: str
    ) -> dict[str, Any] | UnableToVerify | None:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/branches/{branch}/protection"
        try:
            response = await self._http.get(
                url, headers=self._headers(), timeout=self._timeout
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            return UnableToVerify(reason=f"network: {exc.__class__.__name__}")

        if response.status_code == 200:
            data = response.json()
            return data if isinstance(data, dict) else None
        if response.status_code == 404:
            return None  # No protection rule configured.
        if response.status_code in (401, 403, 429):
            return UnableToVerify(reason=f"http_{response.status_code}")
        return UnableToVerify(reason=f"http_{response.status_code}")

    async def list_recent_commits(
        self, owner: str, repo: str, branch: str, *, limit: int = 20
    ) -> list[dict[str, Any]] | UnableToVerify:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/commits"
        params = {"sha": branch, "per_page": str(limit)}
        try:
            response = await self._http.get(
                url, headers=self._headers(), params=params, timeout=self._timeout
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            return UnableToVerify(reason=f"network: {exc.__class__.__name__}")

        if response.status_code == 200:
            body = response.json()
            return body if isinstance(body, list) else []
        if response.status_code in (401, 403, 404, 429):
            return UnableToVerify(reason=f"http_{response.status_code}")
        return UnableToVerify(reason=f"http_{response.status_code}")
