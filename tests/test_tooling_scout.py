"""Tests for scripts/tooling_scout.py -- GitHub tooling-discovery scorer.

Offline: scoring/classification are pure; gh search is exercised through an
injected runner that returns canned JSON (no network, no gh).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ts = _load("tooling_scout", _ROOT / "scripts" / "tooling_scout.py")
_NOW = datetime(2026, 6, 18, tzinfo=timezone.utc)


def _repo(**over):
    base = {"fullName": "owner/repo", "stargazersCount": 5000, "language": "Python",
            "license": {"key": "mit"}, "pushedAt": "2026-06-01T00:00:00Z",
            "description": "x", "isArchived": False}
    base.update(over)
    return base


# ---- scoring --------------------------------------------------------------

def test_popular_python_permissive_maintained_is_adopt():
    r = ts.evaluate(_repo(), now=_NOW)
    assert r["verdict"] == "ADOPT" and r["score"] >= 9 and r["flags"] == []


def test_agpl_is_avoided_however_popular():
    r = ts.evaluate(_repo(stargazersCount=50000, license={"key": "agpl-3.0"}), now=_NOW)
    assert r["verdict"] == "AVOID" and any(f.startswith("copyleft:") for f in r["flags"])


def test_archived_is_avoided():
    assert ts.evaluate(_repo(isArchived=True), now=_NOW)["verdict"] == "AVOID"


def test_node_repo_is_demoted_to_consider():
    r = ts.evaluate(_repo(language="TypeScript"), now=_NOW)
    assert "node" in r["flags"] and r["verdict"] == "CONSIDER"


def test_no_license_flag_caps_at_consider():
    r = ts.evaluate(_repo(license={}), now=_NOW)
    assert "no-license" in r["flags"] and r["verdict"] == "CONSIDER"


def test_stale_repo_is_flagged_and_penalized():
    fresh = ts.score_repo(_repo(), now=_NOW)[0]
    stale = ts.evaluate(_repo(pushedAt="2023-01-01T00:00:00Z"), now=_NOW)
    assert any(f.startswith("stale:") for f in stale["flags"]) and stale["score"] < fresh


def test_low_stars_unknown_is_avoid():
    assert ts.evaluate(_repo(stargazersCount=1, license={}), now=_NOW)["verdict"] == "AVOID"


# ---- gh search (injected runner) ------------------------------------------

def test_gh_search_repos_parses_runner_json():
    payload = json.dumps([_repo(fullName="a/b"), _repo(fullName="c/d")])
    seen = {}

    def run(cmd):
        seen["cmd"] = cmd
        return payload
    repos = ts.gh_search_repos("cloudflare bypass", limit=5, run=run)
    assert [r["fullName"] for r in repos] == ["a/b", "c/d"]
    assert seen["cmd"][:3] == ["gh", "search", "repos"] and "--json" in seen["cmd"]


def test_gh_search_failure_returns_empty():
    def boom(cmd):
        raise RuntimeError("gh not found")
    assert ts.gh_search_repos("x", run=boom) == []


def test_scout_dedups_across_queries_and_ranks():
    big = json.dumps([_repo(fullName="top/repo", stargazersCount=90000)])
    small = json.dumps([_repo(fullName="low/repo", stargazersCount=10),
                        _repo(fullName="top/repo", stargazersCount=90000)])  # dup of top

    def run(cmd):
        return big if "queryA" in cmd else small
    rows = ts.scout(["queryA", "queryB"], run=run, now=_NOW)
    names = [r["fullName"] for r in rows]
    assert names.count("top/repo") == 1                 # deduped
    assert names[0] == "top/repo"                        # ranked by score desc
