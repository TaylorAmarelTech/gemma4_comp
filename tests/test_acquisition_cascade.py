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


# ---- registry presets -----------------------------------------------------

def test_proven_registries_and_resolvers_registered():
    assert set(cas.PROVEN_REGISTRIES) >= {"dmw_lra", "hk_eaa"}
    assert "hk_eaa" in cas.REGISTRY_RESOLVERS   # HK EAA has a special deterministic resolver


def test_resolve_registry_proven_presets():
    assert cas.resolve_registry("dmw_lra")["preset"] == "dmw_lra"
    assert cas.resolve_registry("hk_eaa")["preset"] == "hk_eaa"


def test_resolve_registry_catalogued_source_by_id():
    # a catalogued id that is NOT a proven registry resolves to its source URL
    srcs = {"sg_mom_directory": "https://mom.example/ea", "wafid": "https://wafid.example/centres"}
    assert cas.resolve_registry("sg_mom_directory", sources=srcs)["url"] == "https://mom.example/ea"
    assert cas.resolve_registry("not_a_registry", sources=srcs) == {}


def test_resolve_registry_proven_beats_catalogued():
    # a proven registry wins even if the same id is in the catalogued sources
    assert cas.resolve_registry("ofac_sdn", sources={"ofac_sdn": "https://x"}).get("preset") == "ofac_sdn"


def test_acq_deterministic_dispatches_registry_resolver(monkeypatch):
    monkeypatch.setitem(cas.REGISTRY_RESOLVERS, "hk_eaa",
                        lambda t: {"tier": 1, "name": "deterministic", "records": [{"name": "ADECCO"}],
                                   "n": 1, "confidence": 0.95, "cost": "none",
                                   "discovered_urls": ["u"], "note": "", "error": ""})
    r = cas.acq_deterministic({"preset": "hk_eaa"})
    assert r["records"] == [{"name": "ADECCO"}] and r["tier"] == 1 and r["cost"] == "none"


def test_config_specs_are_registered_as_registries():
    # every registry_specs.yaml id is addressable via --registry through the cascade
    assert "bd_oep_cfg" in cas.PROVEN_REGISTRIES and "bd_oep_cfg" in cas.REGISTRY_RESOLVERS
    assert cas.resolve_registry("cn_mara_cfg").get("preset") == "cn_mara_cfg"


def test_load_known_sources_reads_catalog():
    # the real catalogue should yield the catalogued source ids (incl. sweep endpoints)
    known = cas.load_known_sources()
    assert isinstance(known, dict) and len(known) > 10
    assert all(v.startswith("http") for v in known.values())
