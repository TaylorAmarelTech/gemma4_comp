"""Tests for scripts/citation_accuracy.py -- deterministic, judge-independent citation check (offline)."""
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
for _s in _ROOT.glob("packages/*/src"):
    sys.path.insert(0, str(_s))
ca = _load("citation_accuracy", _ROOT / "scripts" / "citation_accuracy.py")


def test_convention_numbers_extracts_and_dedupes():
    assert ca.convention_numbers("ILO C181 and Convention No. 29 and C181 again") == [29, 181]
    assert ca.convention_numbers("no conventions here, just RA 8042") == []


def test_convention_numbers_ignore_non_ilo_treaty_years():
    text = (
        "The 1990 UN Migrant Workers Convention and Palermo Convention 2000 are relevant. "
        "ILO Convention No. 29 is the ILO citation."
    )
    assert ca.convention_numbers(text) == [29]
    stats = ca.citation_stats("Passport retention also implicates the Migrant Workers Convention 1990.")
    assert stats["n_conventions"] == 0 and stats["n_conventions_implausible"] == 0


def test_citation_stats_flags_out_of_range_convention():
    # a real convention in range is not flagged
    s = ca.citation_stats("ILO C181 Article 7 prohibits worker-paid fees")
    assert s["n_conventions"] == 1 and s["n_conventions_implausible"] == 0
    # an out-of-range convention number is a fabrication
    s2 = ca.citation_stats("as set out in ILO C999 (does not exist)")
    assert s2["n_conventions"] == 1 and s2["n_conventions_implausible"] == 1
    # no citations -> nothing to verify, no fake 100
    s3 = ca.citation_stats("just help me restructure the fee, please")
    assert s3["n_conventions"] == 0 and s3["section_verified_pct"] is None


def test_load_results_skips_malformed_and_non_object_rows(tmp_path):
    results = tmp_path / "results.jsonl"
    results.write_text(
        "\n".join([
            json.dumps({"model": "m", "arm": "baseline", "response": "No citations."}),
            "[1, 2, 3]",
            '"worker@example.com case-123456789 raw row"',
            "{bad json",
        ]) + "\n",
        encoding="utf-8",
    )

    rows = ca.load_results(results)

    assert rows == [{"model": "m", "arm": "baseline", "response": "No citations."}]


def test_aggregate_per_arm_counts_and_hallucination_rate():
    results = [
        {"model": "m", "arm": "baseline", "response": "I can help you structure that fee."},
        {"model": "m", "arm": "baseline", "response": "Here is the documentation matrix."},
        {"model": "m", "arm": "harness_full", "response": "ILO C181 Art. 7 and ILO C029 prohibit this."},
        {"model": "m", "arm": "harness_full", "response": "ILO C189 protects domestic workers."},
    ]
    agg = ca.aggregate(results)
    assert agg["baseline"]["n_responses"] == 2 and agg["baseline"]["mean_conventions"] == 0
    assert agg["harness_full"]["n_responses"] == 2
    assert agg["harness_full"]["mean_conventions"] == 1.5          # (2 + 1) / 2
    # real citations -> no hallucinations flagged in either arm
    assert agg["baseline"]["pct_responses_with_a_hallucinated_citation"] == 0.0
    assert agg["harness_full"]["pct_responses_with_a_hallucinated_citation"] == 0.0


def test_aggregate_skips_non_object_rows_without_copying_values():
    results = [
        "worker@example.com case-123456789 raw row",
        ["worker@example.com case-123456789 raw list"],
        {"model": "m", "arm": "harness_full", "response": "per ILO C181 this is illegal"},
    ]

    agg = ca.aggregate(results)
    agg_json = json.dumps(agg)

    assert agg["harness_full"]["n_responses"] == 1
    assert "worker@example.com" not in agg_json
    assert "case-123456789" not in agg_json


def test_aggregate_skips_non_string_response_fields_without_copying_values():
    results = [
        {"model": "m", "arm": "harness_full", "response": "per ILO C181 this is illegal"},
        {"model": "m", "arm": "harness_full", "response": {"raw": "worker@example.com ILO C777"}},
        {"model": "m", "arm": {"raw": "harness_full"}, "response": "case-123456789 ILO C777"},
    ]

    agg = ca.aggregate(results)
    agg_json = json.dumps(agg)

    assert agg["harness_full"]["n_responses"] == 1
    assert agg["harness_full"]["mean_conventions"] == 1
    assert "worker@example.com" not in agg_json
    assert "case-123456789" not in agg_json


def test_aggregate_flags_a_fabricated_convention():
    results = [
        {"model": "m", "arm": "harness_full", "response": "per ILO C181 this is illegal"},
        {"model": "m", "arm": "harness_full", "response": "per ILO C777 (made up) this is illegal"},
    ]
    agg = ca.aggregate(results)
    # one of two harnessed replies has a fabricated convention -> 50%
    assert agg["harness_full"]["pct_responses_with_a_hallucinated_citation"] == 50.0


def test_main_missing_results_redacts_sensitive_path(tmp_path, capsys):
    sensitive = tmp_path / "worker@example.com-case-123456789" / "results.jsonl"
    assert ca.main(["--results", str(sensitive), "--out", str(tmp_path / "out.md")]) == 1
    err = capsys.readouterr().err
    assert "worker@example.com-case-123456789" not in err
    assert "no stored responses in external" in err


def test_main_success_redacts_sensitive_output_path(tmp_path, capsys):
    results = tmp_path / "results.jsonl"
    rows = [
        {"model": "m", "arm": "baseline", "response": "No citations here."},
        {"model": "m", "arm": "harness_full", "response": "ILO C181 Art. 7 applies."},
    ]
    results.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    out_path = tmp_path / "worker@example.com-case-123456789" / "citation_accuracy.md"

    assert ca.main(["--results", str(results), "--out", str(out_path)]) == 0

    out = capsys.readouterr().out
    assert out_path.exists()
    assert "worker@example.com-case-123456789" not in out
    assert "citation-accuracy -> external" in out
