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


def _fake_tools(text):
    """Stand-in for the harness function-calling layer -> [{name, args, result}, ...]."""
    return [
        {"name": "lookup_corridor_fee_cap", "args": {"origin": "Nepal", "destination": "Qatar"},
         "result": {"statute": "Nepal FEA 2007", "max_fee_worker": "NPR 10000", "currency": "NPR"}},
        {"name": "lookup_ilo_indicator", "args": {"scenario": "(msg)"},
         "result": {"matched_indicators": ["Debt bondage", "Document retention"]}},
    ]


def test_preamble_folds_in_tool_results_when_tool_call_given():
    plain = build_harness_preamble("loan + deduction", grep_call=_fake_grep, rag_call=_fake_rag)
    rich = build_harness_preamble("loan + deduction", grep_call=_fake_grep, rag_call=_fake_rag,
                                  tool_call=_fake_tools)
    # plain path is unchanged: no tool section, empty tools_fired
    assert plain.get("tools_fired") == []
    assert "Deterministic tool results" not in plain["preamble"]
    # rich path folds the grounded tool facts into the preamble
    assert rich["tools_fired"] == ["lookup_corridor_fee_cap", "lookup_ilo_indicator"]
    assert "Deterministic tool results" in rich["preamble"]
    assert "Nepal FEA 2007" in rich["preamble"]            # the statute the tool returned
    assert "Debt bondage" in rich["preamble"]              # the matched ILO indicator
    assert len(rich["preamble"]) > len(plain["preamble"])  # more context


def test_preamble_supports_builtin_messages_list_tool_signature():
    seen: list[list[dict]] = []

    def messages_tool(messages):
        # Mirror the real default_harness()["tools_call"] contract. A raw string
        # is not a valid messages collection and should trigger the adapter's
        # structured-message fallback.
        if not isinstance(messages, list):
            raise AttributeError("messages must be a list")
        seen.append(messages)
        return {"tool_calls": [{
            "name": "lookup_ilo_indicator",
            "args": {"scenario": "(message)"},
            "result": {"matched_indicators": ["Document retention"]},
        }]}

    out = build_harness_preamble(
        "The agency will keep my passport.",
        grep_call=lambda _text, **_kw: {"hits": []},
        tool_call=messages_tool,
    )

    assert seen[0][0]["role"] == "user"
    assert seen[0][0]["content"][0]["text"] == "The agency will keep my passport."
    assert out["tools_fired"] == ["lookup_ilo_indicator"]
    assert "Document retention" in out["preamble"]


def test_preamble_knobs_widen_grep_and_rag():
    def many_grep(text, **_kw):
        return {"hits": [{"rule": f"rule_{i}", "severity": "high", "citation": f"C{i}"} for i in range(20)]}

    narrow = build_harness_preamble("x", grep_call=many_grep, grep_top=10)
    wide = build_harness_preamble("x", grep_call=many_grep, grep_top=15)
    assert len(narrow["grep_fired"]) == 10 and len(wide["grep_fired"]) == 15


def test_tool_call_failure_is_non_fatal():
    def boom(_text):
        raise RuntimeError("tool layer down")

    g = build_harness_preamble("loan", grep_call=_fake_grep, rag_call=_fake_rag, tool_call=boom)
    assert g["tools_fired"] == []                          # swallowed; preamble still built
    assert "SAFETY GROUNDING" in g["preamble"]


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
