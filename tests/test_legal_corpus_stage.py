"""Gated legal-corpus staging: guardrails reject unsourced/overbroad/duplicate candidates, the convergence
vet needs a majority, and nothing is ever auto-promoted (staged for a human)."""
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


sys.path.insert(0, str(_ROOT / "scripts"))
st = _load("legal_corpus_stage", _ROOT / "scripts" / "legal_corpus_stage.py")


def _good_candidate():
    return {"id": "np_test", "claim_type": "rule", "text": "Nepal caps the worker service fee subject to "
            "exceptions where the employer declines.", "authority": "Gov Nepal directive",
            "authority_class": "administrative_rule", "source_url": "https://example.gov.np/x",
            "jurisdiction": "NP", "applies_to": "Nepali workers", "exceptions": ["agency fee if employer refuses"],
            "binding_status": "binding_domestic", "effective_from": "2015-07-01", "as_of": "2026-07-10",
            "volatility": "high", "recheck_after": "2026-10-01", "recheck_reason": "weak enforcement"}


def test_guardrails_pass_a_well_formed_sourced_candidate():
    ok, issues = st.guardrail_check(_good_candidate(), existing=[])
    assert ok and issues == []


def test_guardrails_reject_unsourced_exceptionless_overbroad_and_duplicate():
    c = _good_candidate(); c["source_url"] = ""; c["exceptions"] = []
    c["text"] = "This law prohibits ANY recruitment fee in every country with no exception."
    ok, issues = st.guardrail_check(c, existing=[{"id": "np_test"}])
    assert not ok
    j = " ".join(issues)
    assert "source_url" in j and "exceptions" in j and "OVERBROAD" in j and "duplicate" in j


def test_overbroad_guardrail_closes_the_three_known_evasions():
    # (a) reversed word order ("illegal ... all cases") -- the old single-direction regex missed this
    a = _good_candidate(); a["text"] = "Recruitment fees are illegal in all cases, no exceptions."
    assert st._looks_overbroad(a["text"]) is True
    # (b) an unrelated hedge word in a DIFFERENT sentence must NOT launder an unscoped absolutist sentence
    b = ("This convention generally represents international consensus. "
         "Any recruitment fee is banned for every worker with no exception.")
    assert st._looks_overbroad(b) is True
    # (c) the PLURAL "no exceptions"
    c = _good_candidate(); c["text"] = "The rule applies in every country with no exceptions."
    assert st._looks_overbroad(c["text"]) is True
    # a genuinely SCOPED absolute claim is still allowed (the hedge is in the same sentence)
    ok = "All recruitment fees are prohibited, subject to authorised exceptions under national law."
    assert st._looks_overbroad(ok) is False
    # and a plain, non-absolutist claim is not flagged
    assert st._looks_overbroad("Nepal caps the worker service fee where the employer declines to pay it.") is False


def test_convergence_needs_a_majority():
    def caller_accept(p, **kw):
        return '{"accurate": true}' if "ACCURACY" in p else '{"fatal": false}' if "objection" in p else '{"scoped": true}'
    ok, votes = st.convergence_vet(_good_candidate(), caller=caller_accept)
    assert ok and votes == [True, True, True]

    def caller_split(p, **kw):
        return '{"accurate": false}' if "ACCURACY" in p else '{"fatal": true}' if "objection" in p else '{"scoped": true}'
    ok2, votes2 = st.convergence_vet(_good_candidate(), caller=caller_split)
    assert ok2 is False and votes2 == [False, False, True]      # 1 of 3 -> no majority -> HOLD


def test_stage_never_auto_promotes(tmp_path):
    p = tmp_path / "staging.json"
    rec = st.stage(_good_candidate(), guardrails_ok=True, guardrail_issues=[], convergence_ok=True,
                   votes=[True, True, True], staging_path=p)
    assert rec["ready_for_review"] is True and rec["_not_auto_promoted"] is True and rec["status"] == "staged"
    # a gate failure stages as NOT ready
    rec2 = st.stage(_good_candidate(), guardrails_ok=True, guardrail_issues=[], convergence_ok=False,
                    votes=[False], staging_path=p)
    assert rec2["ready_for_review"] is False
    saved = json.loads(p.read_text(encoding="utf-8"))
    assert saved["_propose_only"] is True and len(saved["staged"]) == 1   # same id replaced, not duplicated
