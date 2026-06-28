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


def test_citation_coherence_matches_governing_law():
    # passport retention is a forced-labour indicator -> governed by C29; citing C29 is coherent
    coh = ps.citation_coherence("Her passport was confiscated; this is prohibited under ILO Convention No. 29.")
    assert coh["coherent"] is True and 29 in coh["matched"]


def test_citation_coherence_flags_irrelevant_citation():
    # citing C138 (child labour minimum age) for passport retention is real-but-irrelevant -> incoherent
    coh = ps.citation_coherence("Her passport was confiscated; see ILO Convention No. 138.")
    assert coh["coherent"] is False and coh["matched"] == [] and 138 in coh["cited_conventions"]


def test_citation_coherence_lenient_without_citation():
    # naming an indicator without citing any law is not 'incoherent' (no false citation to flag)
    coh = ps.citation_coherence("Her passport was confiscated; keep copies of your documents.")
    assert coh["coherent"] is True and coh["cited_conventions"] == []


def test_citation_coherence_recruitment_fee_maps_to_c181():
    coh = ps.citation_coherence("He paid a large recruitment fee, contrary to ILO Convention No. 181.")
    assert coh["coherent"] is True and 181 in coh["matched"]


def test_citation_coherence_enriched_from_verified_map():
    # wage withholding is governed by C095 (Protection of Wages) -- added from the verified statute map
    wages = ps.citation_coherence("There was withholding of wages, contrary to ILO Convention No. 95.")
    assert wages["coherent"] is True and 95 in wages["matched"]
    # passport retention is governed by C189 (Domestic Workers, keep-own-documents) -- the biggest sector
    docs = ps.citation_coherence("Her passport was confiscated, contrary to ILO Convention No. 189.")
    assert docs["coherent"] is True and 189 in docs["matched"]


def test_coverage_aggregates_rates():
    full = ("She was recruited with false promises, forced to work under threats, her passport taken.")
    neutral = "A general note about office supplies and weekly schedules."
    cov = ps.coverage([full, neutral])
    assert cov["n"] == 2
    assert cov["act_rate"] == 0.5 and cov["purpose_rate"] == 0.5    # only the first text carries them
    assert "document_retention" in cov["screening_signal_rate"]
