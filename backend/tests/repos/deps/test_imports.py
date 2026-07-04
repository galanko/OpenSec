"""SP1 Task 6 — first-party import-site scan (the safety grep)."""

from __future__ import annotations

from cliff.repos.deps.imports import collect_import_sites, find_import_sites


def test_npm_import_found_in_shipping_not_test(tmp_path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.ts").write_text("import { parse } from 'yaml'\nconst x = 1\n")
    tests = tmp_path / "src" / "__tests__"
    tests.mkdir()
    (tests / "app.test.ts").write_text("import { parse } from 'yaml'\n")

    sites = find_import_sites(tmp_path, "yaml", "npm")
    assert sites == ["src/app.ts:1"]  # test file excluded


def test_npm_subpath_and_require(tmp_path) -> None:
    (tmp_path / "a.js").write_text("const merge = require('lodash/merge')\n")
    (tmp_path / "b.mjs").write_text("import debounce from 'lodash/debounce'\n")
    sites = find_import_sites(tmp_path, "lodash", "npm")
    assert set(sites) == {"a.js:1", "b.mjs:1"}


def test_npm_scoped_package(tmp_path) -> None:
    (tmp_path / "x.ts").write_text("import { DOMParser } from '@xmldom/xmldom'\n")
    sites = find_import_sites(tmp_path, "@xmldom/xmldom", "npm")
    assert sites == ["x.ts:1"]


def test_npm_no_false_match_on_substring(tmp_path) -> None:
    # 'undici-types' must NOT match a search for 'undici'
    (tmp_path / "x.ts").write_text("import type { X } from 'undici-types'\n")
    assert find_import_sites(tmp_path, "undici", "npm") == []


def test_py_import_forms(tmp_path) -> None:
    pkg = tmp_path / "instructor" / "cli"
    pkg.mkdir(parents=True)
    (pkg / "usage.py").write_text("import aiohttp\nasync def f():\n    pass\n")
    (tmp_path / "other.py").write_text("from aiohttp.client import ClientSession\n")
    # test file excluded
    t = tmp_path / "tests"
    t.mkdir()
    (t / "test_x.py").write_text("import aiohttp\n")
    sites = find_import_sites(tmp_path, "aiohttp", "pypi")
    assert set(sites) == {"instructor/cli/usage.py:1", "other.py:1"}


def test_py_not_imported(tmp_path) -> None:
    (tmp_path / "m.py").write_text("import requests\n")
    assert find_import_sites(tmp_path, "urllib3", "pypi") == []


def test_collect_npm_one_pass(tmp_path) -> None:
    (tmp_path / "a.ts").write_text("import x from 'yaml'\nimport y from 'lodash/merge'\n")
    (tmp_path / "b.js").write_text("const z = require('@xmldom/xmldom')\n")
    (tmp_path / "rel.ts").write_text("import './local'\n")  # relative — ignored
    t = tmp_path / "__tests__"
    t.mkdir()
    (t / "c.ts").write_text("import q from 'yaml'\n")  # test — excluded
    got = collect_import_sites(tmp_path, "npm")
    assert got.get("yaml") == ["a.ts:1"]
    assert got.get("lodash") == ["a.ts:2"]
    assert got.get("@xmldom/xmldom") == ["b.js:1"]
    assert "." not in got and "./local" not in got


def test_collect_py_one_pass(tmp_path) -> None:
    (tmp_path / "m.py").write_text("import aiohttp\nfrom yaml.loader import SafeLoader\n")
    got = collect_import_sites(tmp_path, "pypi")
    assert got.get("aiohttp") == ["m.py:1"]
    assert got.get("yaml") == ["m.py:2"]
