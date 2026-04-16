"""OSV.dev client (IMPL-0002 B4, ADR-0025 §1).

Queries https://api.osv.dev/v1/query for a single `(ecosystem, name, version)`
and normalizes the response into a list of `Advisory` dataclasses. Retries
5xx with linear backoff. Caches per-instance (one instance per assessment run
-> per-assessment cache, as the ADR requires).

`lookup_with_fallback` wraps OSV and a `GhsaClient` into a degrade-gracefully
pipeline: if OSV fails after retries, try GHSA; if both fail, return an
`AdvisoryLookupResult(unable_to_verify=True)` rather than raising. This is
explicit per ADR-0025 Consequences — an entire assessment never fails, only
individual lookups degrade.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

import httpx

if TYPE_CHECKING:
    from opensec.assessment.parsers.base import ParsedDependency

OSV_URL = "https://api.osv.dev/v1/query"

_Severity = str  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"


@dataclass(frozen=True)
class Advisory:
    id: str
    summary: str
    severity: _Severity
    fixed_version: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdvisoryLookupResult:
    advisories: list[Advisory]
    unable_to_verify: bool = False


class AdvisoryLookup(Protocol):
    async def lookup(self, dep: ParsedDependency) -> list[Advisory]: ...


class OsvClient:
    """HTTP client for https://osv.dev. One instance per assessment run."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
    ) -> None:
        self._http = http
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._cache: dict[tuple[str, str, str], list[Advisory]] = {}

    async def lookup(self, dep: ParsedDependency) -> list[Advisory]:
        key = (dep.ecosystem, dep.name, dep.version)
        cached = self._cache.get(key)
        if cached is not None:
            return list(cached)

        payload = {
            "version": dep.version,
            "package": {"name": dep.name, "ecosystem": _osv_ecosystem(dep.ecosystem)},
        }

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                response = await self._http.post(
                    OSV_URL, json=payload, timeout=self._timeout
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                await self._sleep_backoff(attempt)
                continue

            if response.status_code >= 500:
                last_exc = httpx.HTTPStatusError(
                    f"OSV {response.status_code}",
                    request=response.request,
                    response=response,
                )
                await self._sleep_backoff(attempt)
                continue

            response.raise_for_status()
            advisories = _parse_osv_response(response.json())
            self._cache[key] = advisories
            return list(advisories)

        assert last_exc is not None  # noqa: S101
        raise last_exc

    async def _sleep_backoff(self, attempt: int) -> None:
        if self._retry_backoff <= 0:
            return
        await asyncio.sleep(self._retry_backoff * (attempt + 1))


async def lookup_with_fallback(
    dep: ParsedDependency,
    *,
    osv: OsvClient,
    ghsa: AdvisoryLookup | None,
) -> AdvisoryLookupResult:
    """OSV first, GHSA if OSV fails, unable-to-verify if both fail."""
    try:
        advisories = await osv.lookup(dep)
        return AdvisoryLookupResult(advisories=advisories)
    except Exception:  # noqa: BLE001 — degrade per ADR-0025
        pass

    if ghsa is None:
        return AdvisoryLookupResult(advisories=[], unable_to_verify=True)

    try:
        advisories = await ghsa.lookup(dep)
        return AdvisoryLookupResult(advisories=advisories)
    except Exception:  # noqa: BLE001 — degrade per ADR-0025
        return AdvisoryLookupResult(advisories=[], unable_to_verify=True)


def _osv_ecosystem(ecosystem: str) -> str:
    return {"npm": "npm", "pip": "PyPI", "go": "Go"}.get(ecosystem, ecosystem)


def _parse_osv_response(payload: dict[str, Any]) -> list[Advisory]:
    vulns = payload.get("vulns") or []
    out: list[Advisory] = []
    for v in vulns:
        if not isinstance(v, dict):
            continue
        advisory_id = v.get("id") or ""
        if not advisory_id:
            continue
        summary = v.get("summary") or v.get("details") or ""
        severity = _extract_severity(v)
        fixed_version = _extract_fixed_version(v)
        out.append(
            Advisory(
                id=advisory_id,
                summary=summary,
                severity=severity,
                fixed_version=fixed_version,
                raw=v,
            )
        )
    return out


def _extract_severity(vuln: dict[str, Any]) -> _Severity:
    database_specific = vuln.get("database_specific") or {}
    if isinstance(database_specific, dict):
        raw = database_specific.get("severity")
        if isinstance(raw, str) and raw:
            return raw.upper()
    # Fallback: CVSS score band.
    severity_list = vuln.get("severity") or []
    if isinstance(severity_list, list) and severity_list:
        first = severity_list[0]
        if isinstance(first, dict):
            score = first.get("score")
            if isinstance(score, str) and score:
                return "UNKNOWN"  # Numeric CVSS parsing is out of scope for v1.1.
    return "UNKNOWN"


def _extract_fixed_version(vuln: dict[str, Any]) -> str | None:
    for affected in vuln.get("affected") or []:
        if not isinstance(affected, dict):
            continue
        for rng in affected.get("ranges") or []:
            if not isinstance(rng, dict):
                continue
            for event in rng.get("events") or []:
                if isinstance(event, dict) and "fixed" in event:
                    fixed = event.get("fixed")
                    if isinstance(fixed, str) and fixed:
                        return fixed
    return None
