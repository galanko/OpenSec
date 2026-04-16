"""GitHub Advisory Database client (IMPL-0002 B4, ADR-0025 §1).

Thin GraphQL client over https://api.github.com/graphql. Used only as a
fallback when OSV.dev is unreachable. Requires a PAT with read access — if
no token is configured, we return an empty advisory list so the orchestrator
can degrade to `unable_to_verify`.

The response shape is normalised into the same `Advisory` dataclass that
`OsvClient` produces so the orchestrator never has to care which source
served a given advisory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from opensec.assessment.osv_client import Advisory

if TYPE_CHECKING:
    import httpx

    from opensec.assessment.parsers.base import ParsedDependency

GHSA_URL = "https://api.github.com/graphql"

_QUERY = """
query($ecosystem: SecurityAdvisoryEcosystem!, $package: String!) {
  securityVulnerabilities(ecosystem: $ecosystem, package: $package, first: 20) {
    nodes {
      advisory { ghsaId summary severity }
      vulnerableVersionRange
      firstPatchedVersion { identifier }
    }
  }
}
"""


class GhsaClient:
    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        token: str | None,
        timeout: float = 10.0,
    ) -> None:
        self._http = http
        self._token = token
        self._timeout = timeout

    async def lookup(self, dep: ParsedDependency) -> list[Advisory]:
        if not self._token:
            return []

        variables = {
            "ecosystem": _ghsa_ecosystem(dep.ecosystem),
            "package": dep.name,
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
        }

        response = await self._http.post(
            GHSA_URL,
            json={"query": _QUERY, "variables": variables},
            headers=headers,
            timeout=self._timeout,
        )
        response.raise_for_status()
        body = response.json()
        return _parse_ghsa_response(body, dep.version)


def _ghsa_ecosystem(ecosystem: str) -> str:
    return {"npm": "NPM", "pip": "PIP", "go": "GO"}.get(ecosystem, ecosystem.upper())


def _parse_ghsa_response(payload: dict[str, Any], version: str) -> list[Advisory]:
    data = payload.get("data") or {}
    vulns = (data.get("securityVulnerabilities") or {}).get("nodes") or []
    out: list[Advisory] = []
    for node in vulns:
        if not isinstance(node, dict):
            continue
        advisory = node.get("advisory") or {}
        ghsa_id = advisory.get("ghsaId") or ""
        if not ghsa_id:
            continue
        patched = node.get("firstPatchedVersion") or {}
        fixed_version = patched.get("identifier") if isinstance(patched, dict) else None
        out.append(
            Advisory(
                id=ghsa_id,
                summary=advisory.get("summary") or "",
                severity=(advisory.get("severity") or "UNKNOWN").upper(),
                fixed_version=fixed_version or None,
                raw=node,
            )
        )
    return out
