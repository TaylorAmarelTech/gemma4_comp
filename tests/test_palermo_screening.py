"""Tests for scripts/palermo_screening.py -- Palermo Act-Means-Purpose triad + screening signals.

Pins the legal logic: the adult triad needs act+means+purpose; the child rule drops means; and the
operational screening signals are detected for use as contract enrichment / training-scenario ideation."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ps = _load("palermo_screening", _ROOT / "scripts" / "palermo_screening.py")


def test_full_triad_indicates_trafficking():
    text = ("She was recruited with false promises of a hotel job, then forced to work in a factory under "
            "threats; her passport was confiscated and her wages left unpaid.")
    a = ps.palermo_analysis(text)
    assert a["act_present"] and a["means_present"] and a["purpose_present"]
    assert a["triad_complete"] is True and a["trafficking_indicated"] is True
    assert "recruitment" in a["act"] and "fraud_deception" in a["means"] and "forced_labour" in a["purpose"]


def test_child_rule_drops_means_requirement():
    text = "The child was recruited and forced to work long hours in domestic servitude."
    adult = ps.palermo_analysis(text, minor=False)
    minor = ps.palermo_analysis(text, minor=True)
    assert adult["means_present"] is False            # no Palermo 'means' term present
    assert adult["trafficking_indicated"] is False     # adults need means
    assert minor["trafficking_indicated"] is True      # children do not (Art. 3(c))


def test_screening_signals_detected():
    text = "Her employer took her passport, left her wages unpaid, and threatened her if she complained."
    a = ps.palermo_analysis(text)
    assert {"document_retention", "wage_withholding", "threats_coercion"} <= set(a["screening_signals"])
    assert a["n_signals"] >= 3


def test_neutral_text_has_no_elements():
    a = ps.palermo_analysis("The weather report indicates mild temperatures and clear skies for the weekend.")
    assert not a["act_present"] and not a["means_present"] and not a["purpose_present"]
    assert a["trafficking_indicated"] is False and a["n_signals"] == 0


def test_coverage_aggregates_rates():
    full = ("She was recruited with false promises, forced to work under threats, her passport taken.")
    neutral = "A general note about office supplies and weekly schedules."
    cov = ps.coverage([full, neutral])
    assert cov["n"] == 2
    assert cov["act_rate"] == 0.5 and cov["purpose_rate"] == 0.5    # only the first text carries them
    assert "document_retention" in cov["screening_signal_rate"]
