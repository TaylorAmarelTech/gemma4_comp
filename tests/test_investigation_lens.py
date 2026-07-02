"""Tests for scripts/investigation_lens.py -- actors, connections (network + money), crime-script stage."""
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


il = _load("investigation_lens", _ROOT / "scripts" / "investigation_lens.py")


def test_actors_network_and_money_detected():
    text = ("The same recruiter placed multiple workers, and deductions were sent as remittances into a "
            "shell company whose beneficial owner profits.")
    a = il.investigation_analysis(text)
    assert "recruiter" in a["actors"]                     # actor role mapped
    assert a["considers_network"] is True                 # same recruiter / multiple workers / shell company
    assert a["considers_financial"] is True               # remittances / who profits
    assert "financial_flow" in a["connections"]


def test_isolated_case_has_no_network_or_money():
    a = il.investigation_analysis("A worker's passport was confiscated and wages withheld at the factory.")
    assert a["considers_network"] is False and a["considers_financial"] is False
    assert "control" in a["stages"]                        # passport / withheld wages -> control stage


def test_crime_stage_recruitment_detected():
    a = il.investigation_analysis("She was recruited in the village with a job offer before departure.")
    assert "recruitment" in a["stages"]


def test_institutional_review_recognizes_good_response():
    a = il.institutional_review("The labour inspector treated her with a victim-centered, trauma-informed "
                               "approach and used the national referral mechanism.")
    assert "labour_inspector" in a["response_actors"]
    assert "victim_centered" in a["good_behaviors"] and a["flags_institutional_failure"] is False


def test_institutional_review_flags_regulator_corruption():
    a = il.institutional_review("The police were complicit and turned a blind eye, and the regulator left "
                               "the agency unlicensed.")
    assert {"police", "regulator"} <= set(a["response_actors"])
    assert a["flags_institutional_failure"] is True
    assert "corruption_complicity" in a["failure_behaviors"] and "non_enforcement" in a["failure_behaviors"]


def test_institutional_review_flags_ngo_bad_advice():
    # the user's key point: NGOs can contribute harm, often unknowingly (bad advice / wrong stance)
    a = il.institutional_review("A well-intentioned but misguided NGO gave bad advice and the worker was "
                               "re-traumatized.")
    assert "ngo" in a["response_actors"] and "bad_advice_wrong_stance" in a["failure_behaviors"]


def test_institutional_review_flags_victim_criminalization():
    a = il.institutional_review("The immigration officer detained the worker and threatened deportation.")
    assert "immigration" in a["response_actors"] and "victim_criminalization" in a["failure_behaviors"]


def test_coverage_aggregates_rates():
    networked = ("The same recruiter placed multiple workers; remittances flowed to a shell company.")
    isolated = "A general note about office supplies and weekly schedules."
    cov = il.coverage([networked, isolated])
    assert cov["n"] == 2
    assert cov["considers_network_rate"] == 0.5           # only the first reasons about the network
    assert "financial_flow" in cov["connection_rate"]


def test_coverage_includes_institutional_rates():
    corrupt = "The police were complicit and turned a blind eye to the agency."
    neutral = "A general note about office supplies."
    cov = il.coverage([corrupt, neutral])
    assert cov["reviews_institutions_rate"] == 0.5 and cov["flags_institutional_failure_rate"] == 0.5
    assert "corruption_complicity" in cov["institutional_failure_rate"]


def test_main_text_output_includes_institutional_review(capsys):
    rc = il.main(["--text", "A well-intentioned NGO gave bad advice and made it worse."])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert "institutional_review" in out
    assert "ngo" in out["institutional_review"]["response_actors"]
    assert "bad_advice_wrong_stance" in out["institutional_review"]["failure_behaviors"]


def test_load_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "reasoning_sft.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps({"messages": [{"role": "assistant", "content": "The recruiter controlled the debt."}]}),
                json.dumps(["not", "an", "object"]),
                json.dumps("worker@example.com should not become an eval row"),
                "{not json",
                json.dumps({"messages": "not a list"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = il._load_jsonl(path)

    assert len(rows) == 2
    assert all(isinstance(row, dict) for row in rows)


def test_assistant_text_ignores_malformed_messages_and_non_string_content():
    row = {
        "messages": [
            "not a dict",
            {"role": "assistant", "content": {"text": "do not stringify"}},
            {"role": "user", "content": "ignore"},
            {"role": "assistant", "content": "The same recruiter used a shell company."},
        ]
    }

    assert il._assistant_text(row) == "The same recruiter used a shell company."
    assert il._assistant_text({"messages": "not a list"}) == ""
    assert il._assistant_text(["not", "a", "dict"]) == ""


def test_missing_input_console_redacts_sensitive_path(tmp_path, capsys):
    sensitive_dir = tmp_path / "worker@example.com-case-123456789"

    result = il.main(["--sft", str(sensitive_dir / "reasoning_sft.jsonl")])
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
    out = sensitive_dir / "investigation_lens.json"
    sft.write_text(
        json.dumps({"messages": [{"role": "assistant", "content": "The recruiter controlled the debt."}]}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(il, "OUT", out)

    result = il.main(["--sft", str(sft)])
    printed = capsys.readouterr().out

    assert result == 0
    assert "-> external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
    assert out.exists()
