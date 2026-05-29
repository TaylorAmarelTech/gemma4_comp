"""Tests for the model-agnostic harness-lift primitive."""
from __future__ import annotations

from duecare.chat.harness_lift import build_harness_preamble, lift_arms


def _fake_grep(text, **_kw):
    if "loan" in text.lower():
        return {"hits": [{
            "rule": "debt_bondage_loan_salary_deduction",
            "severity": "critical",
            "citation": "ILO C029 §1 + P029; ILO C095 Art. 8",
            "indicator": "worker-funded loan + salary deduction is debt bondage",
        }]}
    return {"hits": []}


def _fake_rag(text, top_k=4):
    return {"docs": [{
        "id": "ilo_c029_art1",
        "title": "ILO Convention 29, Article 1",
        "snippet": "forced or compulsory labour ... under the menace of any penalty",
    }]}


def test_preamble_includes_fired_rules_and_citations():
    g = build_harness_preamble(
        "the agency gave me a loan with a salary deduction",
        grep_call=_fake_grep, rag_call=_fake_rag,
    )
    assert "debt_bondage_loan_salary_deduction" in g["preamble"]
    assert "ILO C029" in g["preamble"]
    assert g["grep_fired"] == ["debt_bondage_loan_salary_deduction"]
    assert "ilo_c029_art1" in g["rag_doc_ids"]
    # the ILO-reasoning instruction is always appended
    assert "ILO forced-labour indicators" in g["preamble"]


def test_preamble_handles_no_hits():
    g = build_harness_preamble("good morning", grep_call=lambda t, **k: {"hits": []})
    assert "No indicator rules" in g["preamble"]
    assert g["grep_fired"] == []
    assert g["rag_doc_ids"] == []


def test_preamble_respects_max_chars():
    g = build_harness_preamble(
        "loan", grep_call=_fake_grep, rag_call=_fake_rag, max_chars=80,
    )
    assert len(g["preamble"]) <= 80 + len("\n...[grounding truncated]")
    assert g["preamble"].endswith("...[grounding truncated]")


def test_lift_arms_runs_baseline_raw_and_harnessed_with_preamble():
    seen: list[str] = []

    def model_call(prompt, **_kw):
        seen.append(prompt)
        return "RESPONSE"

    out = lift_arms(
        "the agency gave me a loan with a salary deduction",
        model_call=model_call, grep_call=_fake_grep, rag_call=_fake_rag,
    )
    assert out["baseline"] == "RESPONSE"
    assert out["harnessed"] == "RESPONSE"
    assert len(seen) == 2
    # baseline arm = raw prompt; harnessed arm = preamble prepended, prompt at end
    assert seen[0] == "the agency gave me a loan with a salary deduction"
    assert "SAFETY GROUNDING" in seen[1]
    assert seen[1].endswith("the agency gave me a loan with a salary deduction")
    assert "debt_bondage_loan_salary_deduction" in out["grep_fired"]


def test_lift_arms_passes_generation_kwargs_through():
    captured: list[dict] = []

    def model_call(prompt, **kw):
        captured.append(kw)
        return "ok"

    lift_arms(
        "hello", model_call=model_call, grep_call=lambda t, **k: {"hits": []},
        max_new_tokens=256, temperature=0.7,
    )
    assert captured[0] == {"max_new_tokens": 256, "temperature": 0.7}
