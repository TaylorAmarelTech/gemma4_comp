"""Tests for scripts/harvest.py -- the routine entity-intelligence orchestrator.

Offline: collectors are injected fakes, so the orchestration, FAULT ISOLATION
(one collector raising must not abort the harvest), dedup-merge across
collectors, and the manifest are tested with no browser/network/creds.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


hv = _load("harvest", _ROOT / "scripts" / "harvest.py")


def _collector(name, records, *, error=""):
    def c():
        return {"name": name, "n_records": len(records), "records": records, "note": "", "error": error}
    c.__name__ = name
    return c


def test_run_harvest_merges_and_writes_manifest(tmp_path):
    a = _collector("src_a", [{"entity_type": "recruitment_agency", "name": "Goldfield Mariners Inc",
                              "jurisdiction": "PH", "status": "valid"}])
    b = _collector("src_b", [{"entity_type": "recruitment_agency", "name": "Goldfield Mariners",  # same entity
                              "jurisdiction": "PH", "status": "cancelled"},
                             {"entity_type": "employer", "name": "Gulf Star LLC", "jurisdiction": "QA"}])
    man = hv.run_harvest([a, b], harvested_at="2026-06-13T10:00", out_dir=tmp_path)
    # the two Goldfield forms merged; employer kept -> 2 entities
    assert man["n_entities"] == 2
    assert man["by_type"] == {"recruitment_agency": 1, "employer": 1}
    assert {c["name"] for c in man["collectors"]} == {"src_a", "src_b"}
    assert (tmp_path / "combined.jsonl").exists()
    manifest_file = Path(man["manifest_path"])
    assert manifest_file.exists()
    saved = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert saved["harvested_at"] == "2026-06-13T10:00" and saved["n_entities"] == 2


def test_one_failing_collector_does_not_abort_harvest(tmp_path):
    good = _collector("good", [{"entity_type": "employer", "name": "Acme", "jurisdiction": "AE"}])

    def boom():
        raise RuntimeError("scraper exploded")
    boom.__name__ = "boom"

    man = hv.run_harvest([boom, good], harvested_at="t", out_dir=tmp_path)
    by_name = {c["name"]: c for c in man["collectors"]}
    assert "RuntimeError" in by_name["boom"]["error"]      # error captured
    assert man["n_entities"] == 1                            # good collector still merged
    assert by_name["good"]["n_records"] == 1


def test_collector_returning_error_dict_is_recorded(tmp_path):
    failing = _collector("flaky", [], error="HTTPError: 503")
    man = hv.run_harvest([failing], harvested_at="t", out_dir=tmp_path)
    assert man["collectors"][0]["error"] == "HTTPError: 503"
    assert man["n_entities"] == 0


def test_builtin_collectors_registered_and_filesystem_ones_are_fault_tolerant():
    assert set(hv.BUILTIN_COLLECTORS) == {"dmw_agencies", "dmw_issuances", "hk_eaa",
                                          "hk_money_lenders", "bd_oep", "kaggle", "staged"}
    # the filesystem-only built-ins must return a result dict and never raise
    # (network/browser ones are not invoked here to keep the test offline+fast)
    for name in ("kaggle", "staged"):
        r = hv.BUILTIN_COLLECTORS[name]()
        assert set(r) >= {"name", "n_records", "records", "error"} and r["name"] == name
