"""Tests for scripts/remedy_taxonomy.py -- the remedy space + missed-remedy detection."""
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


rt = _load("remedy_taxonomy", _ROOT / "scripts" / "remedy_taxonomy.py")


def test_remedies_present_detects_multiple():
    text = ("You can recover your unpaid wages, seek compensation, and you have a right to free legal aid; "
            "you should also report to the labour office.")
    present = set(rt.remedies_present(text))
    assert {"unpaid_wage_recovery", "compensation_damages", "legal_aid", "labour_inspection"} <= present


def test_remedy_gap_lists_missing():
    gap = rt.remedy_gap("You should consult a lawyer for legal assistance.")   # only legal_aid
    assert "legal_aid" in gap["present"]
    assert "visa_immigration_remedy" in gap["missing"] and "repatriation" in gap["missing"]
    assert gap["n_present"] == 1 and 0 < gap["coverage"] < 1


def test_remedies_present_does_not_count_bare_money_harm_as_remedy():
    present = rt.remedies_present(
        "The worker reports unpaid wages, illegal deductions, and a recruitment fee debt."
    )

    assert "unpaid_wage_recovery" not in present
    assert "fee_refund" not in present


def test_core_remedy_gap_flags_missing_mandatory_money_and_non_punishment():
    gap = rt.core_remedy_gap(
        "The worker reports unpaid wages, illegal deductions, a recruitment fee debt, and exploitation."
    )

    assert {"wage_harm", "recruitment_fee_debt", "exploitation_or_forced_labour"} <= set(gap["triggers"])
    assert {"compensation_damages", "non_punishment", "unpaid_wage_recovery", "fee_refund"} <= set(
        gap["required"]
    )
    assert gap["complete"] is False
    assert {"compensation_damages", "non_punishment", "unpaid_wage_recovery", "fee_refund"} <= set(
        gap["missing"]
    )


def test_core_remedy_gap_passes_when_required_remedies_are_named():
    gap = rt.core_remedy_gap(
        "Because this forced labour case includes unpaid wages and recruitment fees, you can recover your "
        "unpaid wages, seek fee reimbursement, seek compensation, and you should not be punished for "
        "things you were compelled to do."
    )

    assert gap["triggers"]
    assert gap["missing"] == []
    assert gap["complete"] is True


def test_neutral_text_offers_no_remedy():
    gap = rt.remedy_gap("The weather is mild and the office reopens on Monday.")
    assert gap["present"] == [] and gap["n_present"] == 0
    assert gap["core_required"] == [] and gap["core_complete"] is True


def test_coverage_aggregates_and_finds_least_offered():
    rich = ("Recover your unpaid wages, claim compensation, get free legal aid, seek a residence permit, "
            "and you should not be prosecuted as you are a victim.")
    thin = "Contact a support organisation."
    cov = rt.coverage([rich, thin])
    assert cov["n"] == 2 and cov["mean_remedies_per_reply"] >= 2
    assert cov["remedy_rate"]["unpaid_wage_recovery"] == 0.5    # only the rich reply offers it


def test_coverage_reports_core_remedy_completeness():
    complete = (
        "Forced labour with unpaid wages: recover your unpaid wages, seek compensation, and you should "
        "not be punished."
    )
    incomplete = "The worker reports unpaid wages and exploitation. Contact a support organisation."

    cov = rt.coverage([complete, incomplete])

    assert cov["core_triggered_n"] == 2
    assert cov["core_complete_rate"] == 0.5
    assert cov["core_missing_rate"]["compensation_damages"] == 0.5
    assert cov["core_missing_rate"]["non_punishment"] == 0.5
    assert cov["core_missing_rate"]["unpaid_wage_recovery"] == 0.5


def test_load_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "reasoning_sft.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"messages": [{"role": "assistant", "content": "Contact your embassy for legal aid."}]}),
                json.dumps(["not", "an", "object"]),
                json.dumps("worker@example.com should not become an eval row"),
                "{not json",
                json.dumps({"messages": "not a list"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = rt._load_jsonl(path)

    assert len(rows) == 2
    assert all(isinstance(row, dict) for row in rows)


def test_assistant_text_ignores_malformed_messages_and_non_string_content():
    row = {
        "messages": [
            "not a dict",
            {"role": "assistant", "content": {"text": "do not stringify"}},
            {"role": "user", "content": "ignore"},
            {"role": "assistant", "content": "Contact your embassy for legal aid."},
        ]
    }

    assert rt._assistant_text(row) == "Contact your embassy for legal aid."
    assert rt._assistant_text({"messages": "not a list"}) == ""
    assert rt._assistant_text(["not", "a", "dict"]) == ""


def test_missing_input_console_redacts_sensitive_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"

    result = rt.main(["--sft", str(sensitive_dir / "reasoning_sft.jsonl")])
    printed = capsys.readouterr().out

    assert result == 1
    assert "no reasoning set at external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_success_console_redacts_sensitive_output_path(tmp_path, monkeypatch, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"
    sensitive_dir.mkdir()
    sft = sensitive_dir / "reasoning_sft.jsonl"
    out = sensitive_dir / "remedy_coverage.json"
    sft.write_text(
        json.dumps({"messages": [{"role": "assistant", "content": "Contact your embassy for legal aid."}]}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(rt, "OUT", out)

    result = rt.main(["--sft", str(sft)])
    printed = capsys.readouterr().out

    assert result == 0
    assert "-> external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert out.exists()
