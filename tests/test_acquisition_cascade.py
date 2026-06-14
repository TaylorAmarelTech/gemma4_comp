"""Tests for scripts/acquisition_cascade.py -- the multi-layer escalation core.

Offline: acquirers and the archive function are injected fakes, so the escalation
(stop at the first layer that succeeds), cheapest-wins, fault isolation, and the
archive sweep of all outbound URLs are tested with no browser/model/network.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


cas = _load("acquisition_cascade", _ROOT / "scripts" / "acquisition_cascade.py")


def _acq(tier, name, records, *, discovered=None, calls=None):
    def a(target):
        if calls is not None:
            calls.append(name)
        return {"tier": tier, "name": name, "records": records, "n": len(records),
                "confidence": 0.5, "cost": "none", "discovered_urls": discovered or [],
                "note": "", "error": ""}
    a.__name__ = name
    return a


def test_cascade_stops_at_first_layer_that_succeeds():
    calls = []
    acquirers = [_acq(1, "deterministic", [], calls=calls),
                 _acq(2, "llm_assisted", [{"name": "A"}], calls=calls),
                 _acq(3, "agentic", [{"name": "B"}], calls=calls)]
    res = cas.run_cascade({"url": "https://x"}, acquirers)
    assert calls == ["deterministic", "llm_assisted"]   # agentic NOT run -- escalation stopped
    assert res["won_by"] == "llm_assisted" and res["tier"] == 2 and res["n_records"] == 1


def test_cascade_cheapest_layer_wins():
    res = cas.run_cascade({"url": "u"}, [_acq(1, "deterministic", [{"name": "A"}]),
                                         _acq(2, "llm_assisted", [{"name": "B"}])])
    assert res["won_by"] == "deterministic" and res["tier"] == 1


def test_cascade_fault_isolation_continues_after_error():
    def boom(_t):
        raise RuntimeError("scraper exploded")
    boom.__name__ = "boom"
    res = cas.run_cascade({"url": "u"}, [boom, _acq(2, "llm_assisted", [{"name": "A"}])])
    assert res["attempts"][0]["error"].startswith("RuntimeError")
    assert res["won_by"] == "llm_assisted"               # a failing layer never aborts the cascade


def test_cascade_archives_target_plus_discovered_urls_deduped():
    archived = []
    res = cas.run_cascade(
        {"url": "https://x"},
        [_acq(1, "deterministic", [{"name": "A"}], discovered=["https://x", "https://api/data"])],
        archive_fn=lambda u: (archived.append(u) or {"url": u, "status": "saved"}))
    # the target + the discovered endpoint, deduped (target appeared in both)
    assert set(archived) == {"https://x", "https://api/data"}
    assert set(res["archived_urls"]) == {"https://x", "https://api/data"}
    assert all(a["status"] == "saved" for a in res["archived"])


def test_cascade_no_escalate_runs_every_layer():
    calls = []
    acquirers = [_acq(1, "a", [], calls=calls), _acq(2, "b", [], calls=calls), _acq(3, "c", [], calls=calls)]
    cas.run_cascade({"url": "u"}, acquirers, escalate=False)
    assert calls == ["a", "b", "c"]


def test_cascade_archival_never_breaks_acquisition():
    def boom_archive(u):
        raise ConnectionError("wayback down")
    res = cas.run_cascade({"url": "https://x"}, [_acq(1, "deterministic", [{"name": "A"}])],
                          archive_fn=boom_archive)
    assert res["n_records"] == 1                          # acquisition still succeeded
    assert res["archived"][0]["status"].startswith("error_")


def test_ladder_is_cheap_to_powerful():
    assert [a.__name__ for a in cas.LADDER] == ["acq_deterministic", "acq_llm_assisted", "acq_agentic", "acq_vision"]
