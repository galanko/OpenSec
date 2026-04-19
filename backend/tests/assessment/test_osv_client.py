"""Tests for the OSV client + GHSA fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

from opensec.assessment.ghsa_client import GhsaClient
from opensec.assessment.osv_client import (
    OSV_URL,
    Advisory,
    AdvisoryLookup,
    OsvClient,
    lookup_with_fallback,
)
from opensec.assessment.parsers.base import ParsedDependency

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock

FIXTURES = Path(__file__).parent.parent / "fixtures" / "osv"
BRACES = ParsedDependency(name="braces", version="3.0.2", ecosystem="npm")


def _osv_braces_payload() -> dict:
    return json.loads((FIXTURES / "braces_3_0_2.json").read_text())


@pytest.mark.asyncio
async def test_osv_lookup_returns_advisories_for_braces_3_0_2(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(url=OSV_URL, method="POST", json=_osv_braces_payload())

    async with httpx.AsyncClient() as http:
        client = OsvClient(http=http)
        advisories = await client.lookup(BRACES)

    assert len(advisories) == 1
    a = advisories[0]
    assert a.id == "GHSA-grv7-fg5c-xmjg"
    assert a.severity == "HIGH"
    assert a.fixed_version == "3.0.3"
    assert "braces" in a.summary.lower()


@pytest.mark.asyncio
async def test_osv_lookup_retries_on_5xx_then_succeeds(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=OSV_URL, method="POST", status_code=502)
    httpx_mock.add_response(url=OSV_URL, method="POST", status_code=502)
    httpx_mock.add_response(url=OSV_URL, method="POST", json=_osv_braces_payload())

    async with httpx.AsyncClient() as http:
        client = OsvClient(http=http, max_retries=3, retry_backoff=0.0)
        advisories = await client.lookup(BRACES)

    assert len(advisories) == 1
    assert len(httpx_mock.get_requests(url=OSV_URL)) == 3


@pytest.mark.asyncio
async def test_osv_lookup_returns_empty_when_no_vulns(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=OSV_URL, method="POST", json={})

    async with httpx.AsyncClient() as http:
        client = OsvClient(http=http)
        advisories = await client.lookup(BRACES)

    assert advisories == []


@pytest.mark.asyncio
async def test_lookup_with_fallback_degrades_to_ghsa_when_osv_down(
    httpx_mock: HTTPXMock,
) -> None:
    for _ in range(2):
        httpx_mock.add_response(url=OSV_URL, method="POST", status_code=503)

    fallback_advisory = Advisory(
        id="GHSA-grv7-fg5c-xmjg",
        summary="from ghsa",
        severity="HIGH",
        fixed_version="3.0.3",
    )

    class _StubGhsa:
        async def lookup(self, dep: ParsedDependency) -> list[Advisory]:
            return [fallback_advisory]

    async with httpx.AsyncClient() as http:
        osv = OsvClient(http=http, max_retries=2, retry_backoff=0.0)
        result = await lookup_with_fallback(BRACES, osv=osv, ghsa=_StubGhsa())

    assert not result.unable_to_verify
    assert result.advisories[0].summary == "from ghsa"


@pytest.mark.asyncio
async def test_lookup_with_fallback_unable_to_verify_when_both_down(
    httpx_mock: HTTPXMock,
) -> None:
    for _ in range(2):
        httpx_mock.add_response(url=OSV_URL, method="POST", status_code=503)

    class _DownGhsa:
        async def lookup(self, dep: ParsedDependency) -> list[Advisory]:
            raise httpx.ConnectError("ghsa also down")

    async with httpx.AsyncClient() as http:
        osv = OsvClient(http=http, max_retries=2, retry_backoff=0.0)
        result = await lookup_with_fallback(BRACES, osv=osv, ghsa=_DownGhsa())

    assert result.unable_to_verify is True
    assert result.advisories == []


def test_advisory_lookup_protocol_is_importable() -> None:
    assert AdvisoryLookup is not None
    assert GhsaClient is not None


# ---------------------------------------------------------------------------
# CVSS fallback (review finding #6)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_osv_lookup_falls_back_to_cvss_band_when_severity_missing(
    httpx_mock: HTTPXMock,
) -> None:
    """OSV returns a vuln with no `database_specific.severity` but with a
    CVSS v3 vector carrying a HIGH availability impact -> severity=HIGH.
    """
    payload = {
        "vulns": [
            {
                "id": "GHSA-abcd-efgh-ijkl",
                "summary": "cvss-only",
                "severity": [
                    {
                        "type": "CVSS_V3",
                        "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
                    }
                ],
                "affected": [],
            }
        ]
    }
    httpx_mock.add_response(url=OSV_URL, method="POST", json=payload)

    async with httpx.AsyncClient() as http:
        client = OsvClient(http=http)
        advisories = await client.lookup(BRACES)

    assert len(advisories) == 1
    assert advisories[0].severity == "HIGH"


@pytest.mark.asyncio
async def test_osv_lookup_returns_unknown_when_no_severity_anywhere(
    httpx_mock: HTTPXMock,
) -> None:
    payload = {"vulns": [{"id": "GHSA-no-sev", "summary": "x", "affected": []}]}
    httpx_mock.add_response(url=OSV_URL, method="POST", json=payload)

    async with httpx.AsyncClient() as http:
        client = OsvClient(http=http)
        advisories = await client.lookup(BRACES)

    assert advisories[0].severity == "UNKNOWN"
