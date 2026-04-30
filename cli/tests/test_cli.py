"""Unit tests for the agent CLI.

These mock the OpenSec HTTP API via pytest-httpx and assert the JSON shape +
exit codes the skill depends on. The contract surface is tiny on purpose —
the skill cannot tolerate drift here without breaking for every user.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from opensec_cli.cli import main


@pytest.fixture(autouse=True)
def _set_base_url(monkeypatch):
    monkeypatch.setenv("OPENSEC_URL", "http://test-server")


@pytest.fixture
def cli():
    return CliRunner()


def _last_json(text: str) -> dict:
    """Extract the last JSON line from output (commands always emit one)."""
    lines = [line for line in text.strip().splitlines() if line.strip()]
    assert lines, f"expected JSON output, got: {text!r}"
    return json.loads(lines[-1])


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_status_ready(cli, httpx_mock):
    httpx_mock.add_response(
        url="http://test-server/health",
        json={
            "opensec": "ok",
            "opencode": "ok",
            "opencode_version": "1.3.2",
            "model": "openai/gpt-4.1",
        },
    )
    httpx_mock.add_response(
        url="http://test-server/api/version",
        json={
            "opensec": "0.1.1-alpha",
            "opencode": "1.3.2",
            "schema_version": "1",
            "min_cli": "0.1.0",
        },
    )
    res = cli.invoke(main, ["status"])
    assert res.exit_code == 0, res.stderr
    payload = _last_json(res.stdout)
    assert payload["ok"] is True
    assert payload["ready"] is True
    assert payload["opensec"] == "0.1.1-alpha"
    assert payload["blockers"] == []


def test_status_blockers_when_engine_down(cli, httpx_mock):
    httpx_mock.add_response(
        url="http://test-server/health",
        json={"opensec": "ok", "opencode": "unavailable", "opencode_version": "1.3.2", "model": ""},
    )
    httpx_mock.add_response(
        url="http://test-server/api/version",
        json={
            "opensec": "0.1.1-alpha",
            "opencode": "1.3.2",
            "schema_version": "1",
            "min_cli": "0.1.0",
        },
    )
    res = cli.invoke(main, ["status"])
    assert res.exit_code == 0
    payload = _last_json(res.stdout)
    assert payload["ready"] is False
    assert "opencode_engine_unavailable" in payload["blockers"]
    assert "no_llm_model_configured" in payload["blockers"]


def test_status_daemon_down(cli, httpx_mock):
    import httpx

    httpx_mock.add_exception(httpx.ConnectError("refused"))
    res = cli.invoke(main, ["status"])
    assert res.exit_code == 3
    payload = json.loads(res.stderr.strip().splitlines()[-1])
    assert payload["ok"] is False
    assert payload["error"]["code"] == "daemon_down"


def test_status_version_mismatch(cli, httpx_mock):
    httpx_mock.add_response(
        url="http://test-server/health",
        json={"opensec": "ok", "opencode": "ok", "opencode_version": "1.3.2", "model": "x"},
    )
    httpx_mock.add_response(
        url="http://test-server/api/version",
        json={
            "opensec": "9.9.9",
            "opencode": "1.3.2",
            "schema_version": "2",
            "min_cli": "9.9.9",
        },
    )
    res = cli.invoke(main, ["status"])
    assert res.exit_code == 4
    payload = json.loads(res.stderr.strip().splitlines()[-1])
    assert payload["error"]["code"] == "version_mismatch"
    assert payload["min_cli"] == "9.9.9"


# ---------------------------------------------------------------------------
# issues
# ---------------------------------------------------------------------------


def _stub_version(httpx_mock):
    httpx_mock.add_response(
        url="http://test-server/api/version",
        json={
            "opensec": "0.1.1-alpha",
            "opencode": "1.3.2",
            "schema_version": "1",
            "min_cli": "0.1.0",
        },
    )


def test_issues_filters_by_severity(cli, httpx_mock):
    _stub_version(httpx_mock)
    httpx_mock.add_response(
        url="http://test-server/api/findings?scope=current&limit=200&status=new",
        json=[
            {
                "id": "f1",
                "title": "log4j RCE",
                "type": "dependency",
                "status": "new",
                "normalized_priority": "critical",
                "derived": {"workspace_id": None},
            },
            {
                "id": "f2",
                "title": "minor lint",
                "type": "code",
                "status": "new",
                "normalized_priority": "low",
            },
        ],
    )
    res = cli.invoke(main, ["issues", "--severity", "critical,high"])
    assert res.exit_code == 0, res.stderr
    payload = _last_json(res.stdout)
    assert [i["id"] for i in payload["issues"]] == ["f1"]
    assert payload["next"] == "fix f1"


def test_issues_empty(cli, httpx_mock):
    _stub_version(httpx_mock)
    httpx_mock.add_response(
        url="http://test-server/api/findings?scope=current&limit=200&status=new",
        json=[],
    )
    res = cli.invoke(main, ["issues"])
    assert res.exit_code == 0
    payload = _last_json(res.stdout)
    assert payload["issues"] == []
    assert payload["next"] is None


# ---------------------------------------------------------------------------
# scan — exit 5 when no findings
# ---------------------------------------------------------------------------


def test_scan_exits_5_when_clean(cli, httpx_mock):
    _stub_version(httpx_mock)
    httpx_mock.add_response(
        url="http://test-server/api/assessment/run",
        method="POST",
        json={"assessment_id": "asm-1", "status": "pending"},
    )
    httpx_mock.add_response(
        url="http://test-server/api/assessment/status/asm-1",
        json={"assessment_id": "asm-1", "status": "complete", "progress_pct": 100},
    )
    httpx_mock.add_response(
        url="http://test-server/api/findings?scope=current&limit=1000",
        json=[],
    )
    res = cli.invoke(main, ["scan", "https://github.com/example/repo"])
    assert res.exit_code == 5
    payload = _last_json(res.stdout)
    assert payload["finding_count"] == 0
    assert payload["scan_id"] == "asm-1"


def test_scan_counts_by_severity(cli, httpx_mock):
    _stub_version(httpx_mock)
    httpx_mock.add_response(
        url="http://test-server/api/assessment/run",
        method="POST",
        json={"assessment_id": "asm-2", "status": "pending"},
    )
    httpx_mock.add_response(
        url="http://test-server/api/assessment/status/asm-2",
        json={"assessment_id": "asm-2", "status": "complete", "progress_pct": 100},
    )
    httpx_mock.add_response(
        url="http://test-server/api/findings?scope=current&limit=1000",
        json=[
            {"id": "a", "title": "x", "normalized_priority": "critical"},
            {"id": "b", "title": "y", "normalized_priority": "high"},
            {"id": "c", "title": "z", "normalized_priority": "high"},
        ],
    )
    res = cli.invoke(main, ["scan", "https://github.com/example/repo"])
    assert res.exit_code == 0
    payload = _last_json(res.stdout)
    assert payload["finding_count"] == 3
    assert payload["by_severity"] == {"critical": 1, "high": 2}


# ---------------------------------------------------------------------------
# fix — exits 2 awaiting plan approval
# ---------------------------------------------------------------------------


def test_fix_creates_workspace_and_pauses_at_plan(cli, httpx_mock):
    _stub_version(httpx_mock)
    httpx_mock.add_response(
        url="http://test-server/api/findings/f1",
        json={
            "id": "f1",
            "source_type": "scanner",
            "source_id": "s1",
            "title": "log4j",
            "status": "new",
            "type": "dependency",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "derived": {"workspace_id": None},
        },
    )
    httpx_mock.add_response(
        url="http://test-server/api/workspaces",
        method="POST",
        status_code=201,
        json={
            "id": "ws-1",
            "finding_id": "f1",
            "state": "open",
            "created_at": "x",
            "updated_at": "x",
        },
    )
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1/sessions",
        method="POST",
        json={"session_id": "sess-1"},
    )
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1/pipeline/run-all",
        method="POST",
        status_code=202,
        json={"status": "running", "message": "started"},
    )
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1/sidebar",
        json={
            "workspace_id": "ws-1",
            "plan": {
                "summary": "Bump log4j to 2.17.1",
                "steps": ["update pom.xml", "rebuild"],
                "definition_of_done": "tests pass",
                "approved": False,
            },
            "updated_at": "x",
        },
    )
    res = cli.invoke(main, ["fix", "f1"])
    assert res.exit_code == 2
    payload = _last_json(res.stdout)
    assert payload["workspace_id"] == "ws-1"
    assert payload["awaiting"] == "plan_approval"
    assert payload["plan"]["summary"].startswith("Bump")
    assert payload["next"] == "approve ws-1"


# ---------------------------------------------------------------------------
# approve — returns PR URL when validation passes
# ---------------------------------------------------------------------------


def test_approve_passes_validation(cli, httpx_mock):
    _stub_version(httpx_mock)
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1/plan/approve",
        method="POST",
        json={"workspace_id": "ws-1", "updated_at": "x"},
    )
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1/pipeline/run-all",
        method="POST",
        status_code=202,
        json={"status": "running", "message": "go"},
    )
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1/sidebar",
        json={
            "workspace_id": "ws-1",
            "validation": {"verdict": "ok", "reason": "tests pass"},
            "pull_request": {"url": "https://github.com/x/y/pull/1", "branch": "fix/log4j"},
            "updated_at": "x",
        },
    )
    res = cli.invoke(main, ["approve", "ws-1"])
    assert res.exit_code == 0, res.stderr
    payload = _last_json(res.stdout)
    assert payload["pr_url"] == "https://github.com/x/y/pull/1"
    assert payload["branch"] == "fix/log4j"
    assert payload["validation"]["verdict"] == "ok"
    assert payload["next"] == "close ws-1"


def test_approve_validation_failed_exits_2(cli, httpx_mock):
    _stub_version(httpx_mock)
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1/plan/approve",
        method="POST",
        json={"workspace_id": "ws-1", "updated_at": "x"},
    )
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1/pipeline/run-all",
        method="POST",
        status_code=202,
        json={"status": "running", "message": "go"},
    )
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1/sidebar",
        json={
            "workspace_id": "ws-1",
            "validation": {"verdict": "fail", "reason": "tests broke"},
            "pull_request": {},
            "updated_at": "x",
        },
    )
    res = cli.invoke(main, ["approve", "ws-1"])
    assert res.exit_code == 2
    payload = _last_json(res.stdout)
    assert payload["validation"]["verdict"] == "fail"
    assert payload["next"] is None


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


def test_close_marks_workspace(cli, httpx_mock):
    _stub_version(httpx_mock)
    httpx_mock.add_response(
        url="http://test-server/api/workspaces/ws-1",
        method="PATCH",
        json={
            "id": "ws-1",
            "finding_id": "f1",
            "state": "closed",
            "created_at": "x",
            "updated_at": "x",
        },
    )
    res = cli.invoke(main, ["close", "ws-1"])
    assert res.exit_code == 0
    payload = _last_json(res.stdout)
    assert payload["closed"] is True
    assert payload["finding_id"] == "f1"
