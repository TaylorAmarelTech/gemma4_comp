"""Batch promote: passing candidates are APPENDED with an auto-vetted verification_weight; duplicates are
HELD (append-only, never overwrite); guardrail/convergence failures are held. Nothing existing is deleted."""
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


sys.path.insert(0, str(_ROOT / "scripts"))
pr = _load("legal_corpus_promote", _ROOT / "scripts" / "legal_corpus_promote.py")


def _cand(cid="x_new"):
    return {"id": cid, "claim_type": "rule", "text": "A caps worker fees subject to exceptions.",
            "authority": "Gov X", "authority_class": "domestic_law", "source_url": "https://gov.x/a",
            "jurisdiction": "XX", "applies_to": "workers", "exceptions": ["fee if employer refuses"],
            "binding_status": "binding_domestic", "effective_from": "2020-01-01", "as_of": "2026-07-10",
            "volatility": "high", "recheck_after": "2026-10-01", "recheck_reason": "changes"}


def _accept(p, **kw):
    return '{"accurate": true}' if "ACCURACY" in p else '{"fatal": false}' if "objection" in p else '{"scoped": true}'


def test_passing_candidate_is_appended_with_auto_vetted_weight():
    corpus = {"claims": [{"id": "existing"}]}
    out = pr.promote([_cand()], corpus, caller=_accept)
    appended = [c for c in out["corpus"]["claims"] if c["id"] == "x_new"][0]
    assert appended["verification_weight"] == pr.AUTO_WEIGHT   # below the human-verified core (0.9)
    assert appended["provenance"] == pr.PROVENANCE
    assert {"existing", "x_new"} <= {c["id"] for c in out["corpus"]["claims"]}   # existing untouched


def test_duplicate_is_held_never_overwrites():
    corpus = {"claims": [{"id": "x_new", "text": "ORIGINAL"}]}
    out = pr.promote([_cand()], corpus, caller=_accept)
    ids = [c["id"] for c in out["corpus"]["claims"]]
    assert ids.count("x_new") == 1                             # not duplicated
    assert out["corpus"]["claims"][0]["text"] == "ORIGINAL"    # existing record NOT overwritten
    assert out["report"][0]["action"] == "held"


def test_convergence_hold_is_not_appended():
    def split(p, **kw):
        return '{"accurate": false}' if "ACCURACY" in p else '{"fatal": true}' if "objection" in p else '{"scoped": true}'
    corpus = {"claims": []}
    out = pr.promote([_cand()], corpus, caller=split)
    assert out["corpus"]["claims"] == [] and out["report"][0]["action"] == "held"


def test_guardrail_failure_is_held():
    bad = _cand(); bad["source_url"] = ""; bad["exceptions"] = []
    out = pr.promote([bad], {"claims": []}, caller=_accept)
    assert out["corpus"]["claims"] == [] and out["report"][0]["action"] == "held"
