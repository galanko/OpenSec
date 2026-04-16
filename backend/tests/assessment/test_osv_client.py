"""Tests for the OSV client + GHSA fallback (IMPL-0002 B4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest

from opensec.assessment.ghsa_client import GhsaClient

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock
from opensec.assessment.osv_client import (
    OSV_URL,
    AdvisoryLookup,
    OsvClient,
    lookup_with_fallback,
)
from opensec.assessment.parsers.base import ParsedDependency

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
    # Three attempts total (2 failures + 1 success).
    assert len(httpx_mock.get_requests(url=OSV_URL)) == 3


@pytest.mark.asyncio
async def test_osv_lookup_caches_within_one_assessment(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=OSV_URL, method="POST", json=_osv_braces_payload())

    async with httpx.AsyncClient() as http:
        client = OsvClient(http=http)
        first = await client.lookup(BRACES)
        second = await client.lookup(BRACES)

    assert first == second
    assert len(httpx_mock.get_requests(url=OSV_URL)) == 1


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
    # OSV always 503 — 2 attempts (max_retries=2).
    for _ in range(2):
        httpx_mock.add_response(url=OSV_URL, method="POST", status_code=503)

    ghsa_result = [
        type(
            "A",
            (),
            {
                "id": "GHSA-grv7-fg5c-xmjg",
                "summary": "from ghsa",
                "severity": "HIGH",
                "fixed_version": "3.0.3",
                "raw": {},
            },
        )()
    ]

    class _StubGhsa:
        async def lookup(self, dep):  # type: ignore[no-untyped-def]
            return list(ghsa_result)

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
        async def lookup(self, dep):  # type: ignore[no-untyped-def]
            raise httpx.ConnectError("ghsa also down")

    async with httpx.AsyncClient() as http:
        osv = OsvClient(http=http, max_retries=2, retry_backoff=0.0)
        result = await lookup_with_fallback(BRACES, osv=osv, ghsa=_DownGhsa())

    assert result.unable_to_verify is True
    assert result.advisories == []


def test_advisory_lookup_protocol_is_importable() -> None:
    # Guards against future renames — B6 injects via protocol.
    assert AdvisoryLookup is not None
    assert GhsaClient is not None
