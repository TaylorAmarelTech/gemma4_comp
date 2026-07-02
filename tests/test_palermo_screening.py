"""Tests for scripts/palermo_screening.py -- Palermo Act-Means-Purpose triad + screening signals.

Pins the legal logic: the adult triad needs act+means+purpose; the child rule drops means; and the
operational screening signals are detected for use as contract enrichment / training-scenario ideation."""
from __future__ import annotations

import importlib.util
import json
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


def test_citation_coherence_rejects_c105_negative_cite():
    # C105 addresses state-imposed forced labour categories, not private economic-coercion indicators.
    coh = ps.citation_coherence("Her passport was confiscated; see ILO Convention No. 105.")
    assert coh["coherent"] is False
    assert 105 in coh["cited_conventions"] and 105 not in coh["expected_conventions"]


def test_citation_coherence_lenient_without_citation():
    # naming an indicator without citing any law is not 'incoherent' (no false citation to flag)
    coh = ps.citation_coherence("Her passport was confiscated; keep copies of your documents.")
    assert coh["coherent"] is True and coh["cited_conventions"] == []


def test_citation_coherence_ignores_non_ilo_treaty_years():
    coh = ps.citation_coherence(
        "Her passport was confiscated; the UN Migrant Workers Convention 1990 and Palermo Convention 2000 "
        "are relevant legal frameworks."
    )
    assert coh["coherent"] is True
    assert coh["cited_conventions"] == []


def test_citation_coherence_recruitment_fee_maps_to_c181():
    coh = ps.citation_coherence("He paid a large recruitment fee, contrary to ILO Convention No. 181.")
    assert coh["coherent"] is True and 181 in coh["matched"]


def test_citation_coherence_enriched_from_verified_map():
    # wage withholding is governed by C095 (Protection of Wages) -- added from the verified statute map
    wages = ps.citation_coherence("There was withholding of wages, contrary to ILO Convention No. 95.")
    assert wages["coherent"] is True and 95 in wages["matched"]
    # passport retention is governed by C189 when the scenario is domestic work
    docs = ps.citation_coherence("A domestic worker's passport was confiscated, contrary to ILO Convention No. 189.")
    assert docs["coherent"] is True and 189 in docs["matched"]


def test_citation_coherence_enriched_map_covers_deception_wages_and_domestic_indicators():
    deception = ps.citation_coherence(
        "The recruiter misled her about the promised job, contrary to ILO Convention No. 181."
    )
    assert "deception_about_work" in deception["mapped_signals"]
    assert deception["coherent"] is True and 181 in deception["matched"]

    wages = ps.citation_coherence("The employer made wage deductions and left salary unpaid under ILO C95.")
    assert "wage_withholding" in wages["mapped_signals"]
    assert wages["coherent"] is True and 95 in wages["matched"]

    domestic = ps.citation_coherence(
        "A domestic worker was not allowed to leave and had no day off, contrary to ILO Convention No. 189."
    )
    assert {"movement_restriction", "excessive_hours"} <= set(domestic["mapped_signals"])
    assert domestic["coherent"] is True and 189 in domestic["matched"]


def test_citation_coherence_c189_requires_domestic_work_context():
    coh = ps.citation_coherence(
        "A farm employer confiscated passports from agricultural workers; see ILO Convention No. 189."
    )
    assert coh["coherent"] is False
    assert 189 in coh["cited_conventions"] and 189 not in coh["expected_conventions"]


def test_citation_coherence_c95_requires_wage_or_deduction_context():
    coh = ps.citation_coherence("She worked excessive hours with no rest day; see ILO Convention No. 95.")
    assert coh["coherent"] is False
    assert 95 in coh["cited_conventions"] and 95 not in coh["expected_conventions"]

    wages = ps.citation_coherence("She worked excessive hours and was not paid; see ILO Convention No. 95.")
    assert wages["coherent"] is True and 95 in wages["matched"]

    withheld = ps.citation_coherence("The employer withheld wages; see ILO Convention No. 95.")
    assert withheld["coherent"] is True and 95 in withheld["matched"]


def test_citation_coherence_c95_maps_deduction_only_wage_language():
    deductions = ps.citation_coherence(
        "The employer imposed deductions from wages; see ILO Convention No. 95."
    )
    assert "wage_withholding" in deductions["mapped_signals"]
    assert deductions["coherent"] is True and 95 in deductions["matched"]

    plural = ps.citation_coherence("The payslip showed unlawful deductions under ILO C95.")
    assert plural["mapped_signals"] == ["wage_withholding"]
    assert plural["coherent"] is True and 95 in plural["matched"]


def test_debt_bondage_does_not_match_owe_inside_showed():
    analysis = ps.palermo_analysis("The payslip showed unlawful deductions under ILO C95.")
    assert "wage_withholding" in analysis["screening_signals"]
    assert "debt_bondage" not in analysis["screening_signals"]


def test_debt_bondage_still_detects_explicit_debt_phrasing():
    analysis = ps.palermo_analysis("She owed money to the recruiter and had to pay off the debt.")
    assert "debt_bondage" in analysis["screening_signals"]


def test_citation_coherence_c95_does_not_treat_document_withholding_as_wage_context():
    coh = ps.citation_coherence(
        "She worked excessive hours and the employer was withholding her passport; see ILO Convention No. 95."
    )
    assert {"document_retention", "excessive_hours"} <= set(coh["mapped_signals"])
    assert coh["coherent"] is False
    assert 95 in coh["cited_conventions"] and 95 not in coh["expected_conventions"]


def test_citation_coherence_c181_requires_recruitment_or_agency_context():
    employer = ps.citation_coherence(
        "The employer says the contract was changed after arrival; see ILO Convention No. 181."
    )
    assert employer["coherent"] is False
    assert 181 in employer["cited_conventions"] and 181 not in employer["expected_conventions"]

    recruiter = ps.citation_coherence(
        "The recruiter said the contract was changed after arrival; see ILO Convention No. 181."
    )
    assert recruiter["coherent"] is True and 181 in recruiter["matched"]


def test_coverage_aggregates_rates():
    full = ("She was recruited with false promises, forced to work under threats, her passport taken.")
    neutral = "A general note about office supplies and weekly schedules."
    cov = ps.coverage([full, neutral])
    assert cov["n"] == 2
    assert cov["act_rate"] == 0.5 and cov["purpose_rate"] == 0.5    # only the first text carries them
    assert "document_retention" in cov["screening_signal_rate"]


def test_coverage_ignores_non_string_inputs():
    full = "She was recruited with false promises and forced to work."

    cov = ps.coverage([full, "", None, {"content": "forced to work"}, ["not text"]])

    assert cov["n"] == 1
    assert cov["act_rate"] == 1.0
    assert cov["purpose_rate"] == 1.0


def test_assistant_text_ignores_malformed_messages_and_non_string_content():
    row = {
        "messages": [
            "not a dict",
            {"role": "assistant", "content": {"text": "forced to work should not stringify"}},
            {"role": "user", "content": "ignore"},
            {"role": "assistant", "content": "She was recruited by deception and forced to work."},
        ]
    }

    assert ps._assistant_text(row) == "She was recruited by deception and forced to work."
    assert ps._assistant_text({"messages": "not a list"}) == ""
    assert ps._assistant_text(["not", "a", "dict"]) == ""


def test_non_string_inputs_are_empty_safe():
    analysis = ps.palermo_analysis({"text": "forced to work"})
    coherence = ps.citation_coherence(["ILO Convention No. 29"])

    assert analysis["n_signals"] == 0
    assert analysis["trafficking_indicated"] is False
    assert coherence == {
        "mapped_signals": [],
        "cited_conventions": [],
        "expected_conventions": [],
        "matched": [],
        "coherent": True,
    }


def test_main_text_output_includes_citation_coherence(capsys):
    rc = ps.main(["--text", "A domestic worker's passport was confiscated under ILO Convention No. 189."])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "citation_coherence" in out
    assert out["citation_coherence"]["coherent"] is True
    assert 189 in out["citation_coherence"]["matched"]


def test_main_missing_sft_redacts_sensitive_path(tmp_path, capsys):
    sensitive = tmp_path / "worker@example.com-case-123456789" / "reasoning_sft.jsonl"
    rc = ps.main(["--sft", str(sensitive)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "worker@example.com-case-123456789" not in out
    assert "no reasoning set at external" in out


def test_main_success_prints_display_safe_output_path(tmp_path, monkeypatch, capsys):
    sft = tmp_path / "reasoning_sft.jsonl"
    row = {
        "messages": [
            {"role": "assistant", "content": "She was recruited by deception and forced to work with unpaid wages."}
        ]
    }
    sft.write_text(
        "\n".join([
            "{not-json",
            json.dumps(["not", "an", "object"]),
            json.dumps({"messages": "not-a-list"}),
            json.dumps({"messages": [["not", "a", "message"]]}),
            json.dumps({"messages": [{"role": "assistant", "content": {"text": "forced to work"}}]}),
            json.dumps(row),
        ]) + "\n",
        encoding="utf-8",
    )
    out_path = tmp_path / "worker@example.com-case-123456789" / "palermo_analysis.json"
    monkeypatch.setattr(ps, "OUT", out_path)

    rc = ps.main(["--sft", str(sft)])

    out = capsys.readouterr().out
    assert rc == 0
    assert out_path.exists()
    assert json.loads(out_path.read_text(encoding="utf-8"))["n"] == 1
    assert "worker@example.com-case-123456789" not in out
    assert "-> external" in out
