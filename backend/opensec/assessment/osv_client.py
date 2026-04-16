"""OSV.dev client + shared `lookup_with_fallback` helper.

`lookup_with_fallback` tries OSV first, GHSA on OSV failure, and returns an
`AdvisoryLookupResult(unable_to_verify=True)` when both are down. An
assessment never fails on advisory lookups — it degrades per ADR-0025.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

import httpx

if TYPE_CHECKING:
    from opensec.assessment.parsers.base import ParsedDependency

OSV_URL = "https://api.osv.dev/v1/query"


@dataclass(frozen=True)
class Advisory:
    id: str
    summary: str
    severity: str  # CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN
    fixed_version: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdvisoryLookupResult:
    advisories: list[Advisory]
    unable_to_verify: bool = False


class AdvisoryLookup(Protocol):
    async def lookup(self, dep: ParsedDependency) -> list[Advisory]: ...


class OsvClient:
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

    async def lookup(self, dep: ParsedDependency) -> list[Advisory]:
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
            return _parse_osv_response(response.json())

        assert last_exc is not None  # noqa: S101
        raise last_exc

    async def _sleep_backoff(self, attempt: int) -> None:
        if self._retry_backoff <= 0:
            return
        await asyncio.sleep(self._retry_backoff * (attempt + 1))


async def lookup_with_fallback(
    dep: ParsedDependency,
    *,
    osv: AdvisoryLookup,
    ghsa: AdvisoryLookup | None,
) -> AdvisoryLookupResult:
    try:
        return AdvisoryLookupResult(advisories=await osv.lookup(dep))
    except Exception:  # noqa: BLE001 — degrade per ADR-0025
        pass

    if ghsa is None:
        return AdvisoryLookupResult(advisories=[], unable_to_verify=True)

    try:
        return AdvisoryLookupResult(advisories=await ghsa.lookup(dep))
    except Exception:  # noqa: BLE001 — degrade per ADR-0025
        return AdvisoryLookupResult(advisories=[], unable_to_verify=True)


def _osv_ecosystem(ecosystem: str) -> str:
    return {"npm": "npm", "pip": "PyPI", "go": "Go"}.get(ecosystem, ecosystem)


def _parse_osv_response(payload: dict[str, Any]) -> list[Advisory]:
    out: list[Advisory] = []
    for v in payload.get("vulns") or []:
        if not isinstance(v, dict):
            continue
        advisory_id = v.get("id") or ""
        if not advisory_id:
            continue
        out.append(
            Advisory(
                id=advisory_id,
                summary=v.get("summary") or v.get("details") or "",
                severity=_extract_severity(v),
                fixed_version=_extract_fixed_version(v),
                raw=v,
            )
        )
    return out


def _extract_severity(vuln: dict[str, Any]) -> str:
    database_specific = vuln.get("database_specific") or {}
    if isinstance(database_specific, dict):
        raw = database_specific.get("severity")
        if isinstance(raw, str) and raw:
            return raw.upper()
    return "UNKNOWN"


def _extract_fixed_version(vuln: dict[str, Any]) -> str | None:
    for affected in vuln.get("affected") or []:
        if not isinstance(affected, dict):
            continue
        for rng in affected.get("ranges") or []:
            if not isinstance(rng, dict):
                continue
            for event in rng.get("events") or []:
                if isinstance(event, dict):
                    fixed = event.get("fixed")
                    if isinstance(fixed, str) and fixed:
                        return fixed
    return None
