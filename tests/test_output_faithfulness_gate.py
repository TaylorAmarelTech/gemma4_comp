"""Output-faithfulness gate: flag a generated answer that states an absolute legal rule without its
exception (the overbroad-no-exception failure the reasoning contract cannot catch, now guarded at output)."""
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
g = _load("output_faithfulness_gate", _ROOT / "scripts" / "output_faithfulness_gate.py")


def test_absolute_no_exception_fails():
    r = g.check("ILO Convention No. 181 absolutely prohibits ANY recruitment fee in every country with no "
                "exceptions, so this is illegal everywhere.")
    assert r["verdict"] == "fail"
    assert r["overbroad_sentences"] and r["mentions_exception"] is False


def test_scoped_answer_passes():
    r = g.check("Recruitment fees are prohibited under ILO Convention No. 181, but this is subject to "
                "authorised national exceptions and depends on ratification.")
    assert r["verdict"] == "pass"
    assert not r["overbroad_sentences"]     # clean because it is scoped -- NOT a "No. 181" false positive


def test_convention_number_is_not_a_false_quantifier():
    # "Convention No. 29 ... prohibited" must NOT trip overbroad just because "No." looks like "no"
    r = g.check("Under ILO Convention No. 29 forced labour is prohibited.")
    assert r["verdict"] == "pass" and not r["overbroad_sentences"]


def test_absolute_with_exception_stated_passes():
    r = g.check("Under Convention No. 29 forced labour is prohibited; note that C29 has defined lawful "
                "exceptions such as military service and supervised prison labour.")
    assert r["verdict"] == "pass"                                  # 'exceptions' surfaced -> not a fail


def test_warn_when_named_exception_bearing_claim_is_stated_absolutely():
    claims = [{"id": "c181", "authority": "ILO Convention No. 181", "text": "recruitment fees No. 181",
               "exceptions": ["authorised national-law exceptions"]}]
    # overbroad sentence + a hedge word ('varies') elsewhere -> not a hard fail, but names an exception-bearing law
    r = g.check("Convention No. 181 bans every recruitment fee everywhere, though it varies by country.",
                claims=claims)
    assert r["verdict"] == "warn"
    assert "c181" in r["cited_claims_with_exceptions"]


def test_benign_answer_passes():
    r = g.check("Keep copies of your contract and payslips, and contact your embassy or a migrant-worker NGO "
                "if you need help; the specific rule depends on your destination and occupation.")
    assert r["verdict"] == "pass" and not r["overbroad_sentences"]
