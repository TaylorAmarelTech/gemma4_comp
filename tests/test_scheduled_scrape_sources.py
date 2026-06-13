"""Guard for the scheduled-scrape source registry + monitor run.

The scheduled-scrape GitHub Actions workflow runs the research monitor over
configs/duecare/research_monitor/sources.yaml forever. This test pins that the
recruitment-agency licensing registries are present and well-formed, and that
the monitor runs over the whole registry offline (propose-only, needs_review).
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _src in glob.glob(str(_ROOT / "packages" / "*" / "src")):
    if _src not in sys.path:
        sys.path.insert(0, _src)

SOURCES = _ROOT / "configs" / "duecare" / "research_monitor" / "sources.yaml"

# the recruitment-agency licensing feed added for the scheduled scraper
_REQUIRED_AGENCY_SOURCES = {
    "ph_dmw_licensed_agencies",
    "hk_eaa_licensed",
    "sg_mom_ea_directory",
    "ph_dmw_advisories",
}
_VALID_KINDS = {"law", "agency", "complaint_form", "contact", "guidance", "scam_watch"}


def _load():
    from duecare.research_tools.monitor import load_sources
    return load_sources(SOURCES)


def test_recruitment_agency_sources_present_and_valid():
    sources = _load()
    by_id = {s.id: s for s in sources}
    missing = _REQUIRED_AGENCY_SOURCES - set(by_id)
    assert not missing, f"scheduled-scrape registry missing agency sources: {missing}"
    for sid in _REQUIRED_AGENCY_SOURCES:
        s = by_id[sid]
        assert s.url.startswith("https://"), f"{sid} must be https"
        assert s.kind in _VALID_KINDS
        assert s.label
    # the DMW licensed-agency inquiry (the verification feed) points at the
    # inquiry path, not just the homepage
    assert "licensed-recruitment-agencies" in by_id["ph_dmw_licensed_agencies"].url


def test_monitor_runs_offline_over_registry_propose_only():
    from duecare.research_tools.monitor import (
        FetchResult, build_report, check_sources,
    )
    sources = _load()
    assert len(sources) >= 22

    def offline_fetch(_url):
        return FetchResult(ok=False, status=0, error="offline")

    findings, new_state, proposals = check_sources(sources, offline_fetch, {})
    report = build_report(findings, proposals)
    assert report.n_sources == len(sources)
    assert report.n_unreachable == len(sources)  # offline -> all unreachable
    # every proposal is a review item, never auto-applied
    assert proposals and all(p.needs_review for p in proposals)


def test_change_detection_flags_only_changed_sources():
    """A second run with a changed page flags exactly that source (the
    'continue forever' diff behavior)."""
    from duecare.research_tools.monitor import FetchResult, check_sources

    src = _load()[:1]  # one source is enough to prove the diff logic

    def fetch_v1(_url):
        return FetchResult(ok=True, status=200, text="version one content")

    _, state1, _ = check_sources(src, fetch_v1, {})
    # unchanged run -> no proposals
    _, state2, props_same = check_sources(src, fetch_v1, state1)
    assert state2 == state1 and props_same == []

    def fetch_v2(_url):
        return FetchResult(ok=True, status=200, text="version TWO different content")

    _, _, props_changed = check_sources(src, fetch_v2, state1)
    assert len(props_changed) == 1 and props_changed[0].change == "changed"
