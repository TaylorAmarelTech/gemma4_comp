"""Kit-vs-production coverage: quantifies how much of the 456-rule production GREP layer the
compact kit engine reproduces, so "representative subset" is a measured number and not prose."""
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


k = _load("kit_coverage_vs_production", _ROOT / "scripts" / "kit_coverage_vs_production.py")


# Stub layers: `grep_call` mirrors the production return shape, `scan` the compact hit shape.
def _grep(hits):
    return lambda _t: {"hits": hits}


def _rule(name, severity="high"):
    return {"rule": name, "severity": severity, "citation": "ILO C029", "indicator": "x"}


def test_measure_counts_the_four_agreement_cells():
    texts = ["a", "b", "c", "d"]
    # a -> both, b -> production only, c -> compact only, d -> neither
    prod = {"a": [_rule("r1")], "b": [_rule("r2")], "c": [], "d": []}
    comp = {"a": [{"indicator": "i"}], "b": [], "c": [{"indicator": "i"}], "d": []}
    m = k.measure(texts, lambda t: {"hits": prod[t]}, lambda t: comp[t])
    assert (m["both"], m["production_only"], m["compact_only"], m["neither"]) == (1, 1, 1, 1)
    assert m["n_texts"] == 4
    assert m["production_fired"] == 2 and m["compact_fired"] == 2


def test_recall_is_measured_against_production_fires_only():
    # 3 production fires, compact agrees on 2 -> 66.7%, NOT 2/4 of all texts.
    texts = ["a", "b", "c", "d"]
    prod = {"a": [_rule("r")], "b": [_rule("r")], "c": [_rule("r")], "d": []}
    comp = {"a": [{"indicator": "i"}], "b": [{"indicator": "i"}], "c": [], "d": []}
    m = k.measure(texts, lambda t: {"hits": prod[t]}, lambda t: comp[t])
    assert m["compact_recall_vs_production_pct"] == 66.7


def test_recall_is_none_rather_than_zero_when_production_never_fires():
    m = k.measure(["a"], _grep([]), lambda _t: [])
    assert m["compact_recall_vs_production_pct"] is None


def test_missed_rules_are_ranked_by_how_often_they_fire_on_missed_texts():
    texts = ["a", "b", "c"]
    prod = {"a": [_rule("common"), _rule("rare")], "b": [_rule("common")], "c": [_rule("common")]}
    m = k.measure(texts, lambda t: {"hits": prod[t]}, lambda _t: [])  # compact always silent
    top = m["top_missed_rules"]
    assert top[0]["rule"] == "common" and top[0]["missed_texts"] == 3
    assert {r["rule"] for r in top} == {"common", "rare"}


def test_every_observed_severity_is_reported_including_critical_and_info():
    # A fixed high/medium/low bucket list would silently drop critical and info misses.
    prod = [_rule("a", "critical"), _rule("b", "info"), _rule("c", "high")]
    m = k.measure(["t"], _grep(prod), lambda _t: [])
    assert m["missed_severity"] == {"critical": 1, "high": 1, "info": 1}
    # critical must sort ahead of high; info last
    assert list(m["missed_severity"]) == ["critical", "high", "info"]


def test_collect_texts_reads_both_corpora_and_honours_the_limit(tmp_path):
    show = tmp_path / "showcase.jsonl"
    show.write_text(json.dumps({"prompt_id": "p1", "prompt_text": "P", "baseline_response": "B",
                                "harness_core_response": "H"}) + "\n", encoding="utf-8")
    res = tmp_path / "results.jsonl"
    res.write_text("".join(json.dumps({"model": "example:1b", "arm": "baseline",
                                       "prompt_id": f"p{i}", "response": f"R{i}"}) + "\n"
                           for i in range(10)), encoding="utf-8")
    texts = k.collect_texts(3, results=res, showcase=show)
    assert texts[:3] == ["P", "B", "H"]          # all three showcase fields
    assert texts[3:] == ["R0", "R1", "R2"]       # limit applies to streamed responses


def test_collect_texts_tolerates_missing_files_and_bad_lines(tmp_path):
    res = tmp_path / "results.jsonl"
    res.write_text('{"response": "ok"}\nnot json\n\n{"response": "   "}\n', encoding="utf-8")
    texts = k.collect_texts(10, results=res, showcase=tmp_path / "absent.jsonl")
    assert texts == ["ok"]                       # bad line skipped, blank response dropped


def test_render_states_the_recall_number_and_the_port_backlog():
    m = k.measure(["a", "b"], lambda t: {"hits": [_rule("passport_rule", "critical")]},
                  lambda t: [{"indicator": "i"}] if t == "a" else [])
    out = k.render(m, today="2026-07-26", limit=100)
    assert "Compact recall vs production: 50.0%" in out
    assert "`passport_rule`" in out
    assert "calls no model" in out


def test_render_handles_an_empty_corpus_without_claiming_a_result():
    out = k.render(k.measure([], _grep([]), lambda _t: []), today="2026-07-26", limit=100)
    assert "No texts available" in out
    assert "Compact recall" not in out


def test_label_never_leaks_an_out_of_repo_absolute_path():
    label = k._label(Path("C:/Users/someone/AppData/Local/Temp/results.jsonl").resolve())
    assert label == "results.jsonl"
    assert "Users" not in label and "AppData" not in label
    assert k._has_windows_drive_marker(("C:", "Users", "someone"))
