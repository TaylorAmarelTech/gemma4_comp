"""The vetted legal-claim library must be schema-valid, and the recheck flagger must catch stale/volatile
claims (recheck_after passed, high volatility, or a reform whose effective date has arrived)."""
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(_ROOT / "scripts"))
lc = _load("legal_claims", _ROOT / "scripts" / "legal_claims.py")


def test_shipped_library_is_schema_valid():
    claims = lc.load_claims()
    assert len(claims) >= 12                                   # the shipped library is non-trivial
    assert lc.validate_schema(claims) == []                    # no schema errors


def test_every_claim_has_source_exceptions_and_recheck():
    for c in lc.load_claims():
        assert c["source_url"].startswith("http")             # a real source, not a bare convention name
        assert "exceptions" in c and isinstance(c["exceptions"], list)
        assert c["recheck_reason"] and c["recheck_after"]      # every claim says WHEN + WHY to re-verify


def test_validate_schema_catches_bad_records():
    bad = [{"id": "x", "claim_type": "rule", "text": "t", "authority": "a", "source_url": "u",
            "jurisdiction": "j", "binding_status": "b", "as_of": "2026-07-10", "volatility": "MASSIVE",
            "recheck_after": "not-a-date", "recheck_reason": "r"}]
    errs = lc.validate_schema(bad)
    assert any("volatility" in e for e in errs) and any("recheck_after" in e for e in errs)


def test_recheck_flags_high_volatility_and_passed_dates():
    claims = [
        {"id": "stable", "claim_type": "definition", "volatility": "low", "recheck_after": "2030-01-01"},
        {"id": "volatile", "claim_type": "rule", "volatility": "high", "recheck_after": "2030-01-01"},
        {"id": "stale", "claim_type": "rule", "volatility": "low", "recheck_after": "2026-01-01"},
    ]
    due = {c["id"]: c["_reasons"] for c in lc.due_for_recheck(claims, date(2026, 7, 10))}
    assert "stable" not in due                                  # low volatility + future recheck -> ok
    assert "volatile" in due and any("high volatility" in r for r in due["volatile"])
    assert "stale" in due and any("has passed" in r for r in due["stale"])


def test_reform_becoming_effective_is_flagged():
    claims = [{"id": "eu_flr", "claim_type": "reform", "volatility": "high",
               "recheck_after": "2030-01-01", "effective_from": "2027-12-14"}]
    # before the effective date: flagged for volatility but NOT for "now in the past"
    before = lc.due_for_recheck(claims, date(2026, 7, 10))[0]["_reasons"]
    assert not any("now in the past" in r for r in before)
    # after the effective date: the 'forthcoming' framing is stale
    after = lc.due_for_recheck(claims, date(2028, 1, 1))[0]["_reasons"]
    assert any("now in the past" in r for r in after)


def test_shipped_library_flags_the_expected_volatile_claims():
    claims = lc.load_claims()
    due = {c["id"] for c in lc.due_for_recheck(claims, date(2026, 7, 10))}
    # the young/expanding + brand-new-reform claims must be flagged; a stable definition must not
    assert {"ph_placement_fee", "sa_kafala_reform_2025", "eu_forced_labour_regulation"} <= due
    assert "c029_definition" not in due


def test_library_includes_court_precedents_workers_can_search():
    by = {c["id"]: c for c in lc.load_claims()}
    for cid in ("rantsev_2010", "siliadin_2005", "kozminski_1988"):
        assert by[cid]["claim_type"] == "precedent"           # landmark cases are enriched in
        assert by[cid]["authority_class"] == "court_precedent"


def test_append_only_principle_supersede_not_delete():
    # Kozminski is retained (not deleted) as historical context and marked superseded_by the TVPA -- the
    # 'build upon, do not replace' principle. It must NOT be presented as current law.
    koz = {c["id"]: c for c in lc.load_claims()}["kozminski_1988"]
    assert koz["superseded_by"]                                 # points forward to the current standard
    assert "do NOT cite Kozminski as the current" in " ".join(koz["caveats"])
    assert koz["binding_status"] == "historical_superseded_by_statute"
