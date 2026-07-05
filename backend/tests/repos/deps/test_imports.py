"""SP1 Task 6 — first-party import-site scan (the safety grep, collect_import_sites)."""

from __future__ import annotations

from cliff.repos.deps.imports import collect_import_sites


def test_npm_shipping_not_test_and_subpath(tmp_path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.ts").write_text("import { parse } from 'yaml'\nconst m = require('lodash/merge')\n")
    tests = tmp_path / "src" / "__tests__"
    tests.mkdir()
    (tests / "app.test.ts").write_text("import { parse } from 'yaml'\n")  # test → excluded
    got = collect_import_sites(tmp_path, "npm")
    assert got.get("yaml") == ["src/app.ts:1"]  # test file not counted
    assert got.get("lodash") == ["src/app.ts:2"]  # subpath → package


def test_npm_scoped_and_relative(tmp_path) -> None:
    (tmp_path / "b.js").write_text("const z = require('@xmldom/xmldom')\n")
    (tmp_path / "rel.ts").write_text("import './local'\n")  # relative — ignored
    got = collect_import_sites(tmp_path, "npm")
    assert got.get("@xmldom/xmldom") == ["b.js:1"]
    assert "." not in got and "./local" not in got


def test_npm_no_false_match_on_substring(tmp_path) -> None:
    # 'undici-types' must NOT be bucketed as 'undici'
    (tmp_path / "x.ts").write_text("import type { X } from 'undici-types'\n")
    got = collect_import_sites(tmp_path, "npm")
    assert "undici" not in got
    assert got.get("undici-types") == ["x.ts:1"]


def test_npm_barrel_reexport_counted(tmp_path) -> None:
    # `export … from 'pkg'` is a real shipping import — must be recorded (it has no
    # 'import'/'require' token, so the prefilter must also allow 'from').
    (tmp_path / "index.ts").write_text("export { Foo } from 'some-lib'\nexport * from 'other-lib'\n")
    got = collect_import_sites(tmp_path, "npm")
    assert got.get("some-lib") == ["index.ts:1"]
    assert got.get("other-lib") == ["index.ts:2"]


def test_py_import_forms_and_test_excluded(tmp_path) -> None:
    pkg = tmp_path / "instructor" / "cli"
    pkg.mkdir(parents=True)
    (pkg / "usage.py").write_text("import aiohttp\n")
    (tmp_path / "other.py").write_text("from aiohttp.client import ClientSession\n")
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_x.py").write_text("import aiohttp\n")  # test → excluded
    got = collect_import_sites(tmp_path, "pypi")
    assert set(got.get("aiohttp", [])) == {"instructor/cli/usage.py:1", "other.py:1"}


def test_py_dotted_import_bucketed_by_top_level(tmp_path) -> None:
    # protobuf's import name is 'google.protobuf'; the collector must bucket by the
    # TOP-LEVEL 'google' so build.py's top-level lookup matches.
    (tmp_path / "m.py").write_text("from google.protobuf import message\nimport google.cloud.storage\n")
    got = collect_import_sites(tmp_path, "pypi")
    assert got.get("google") == ["m.py:1", "m.py:2"]


def test_py_multi_import_all_captured(tmp_path) -> None:
    # `import json, vulnerable_pkg` must capture BOTH, not just the first.
    (tmp_path / "m.py").write_text("import json, vulnerable_pkg as vp\n")
    got = collect_import_sites(tmp_path, "pypi")
    assert got.get("vulnerable_pkg") == ["m.py:1"]
    assert got.get("json") == ["m.py:1"]


def test_py_not_imported(tmp_path) -> None:
    (tmp_path / "m.py").write_text("import requests\n")
    assert collect_import_sites(tmp_path, "pypi").get("urllib3") is None
