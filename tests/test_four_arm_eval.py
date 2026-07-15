"""Tests for scripts/four_arm_eval.py -- the Phase 3 four-arm evaluator (CPU-safe core only).

The GPU run() path (load adapter, generate trained C/D) is not exercised; these cover the
panel aggregation, the four-arm table (internalisation + stacking), the report, and prompt pairing.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fa = _load("four_arm_eval", _ROOT / "scripts" / "four_arm_eval.py")


def test_default_base_matches_the_canonical_training_model() -> None:
    assert fa.DEFAULT_BASE == "google/gemma-4-E4B-it"
    assert len(fa.DEFAULT_BASE_REVISION) == 40


def test_adapter_base_verification_requires_exact_model_and_revision(tmp_path) -> None:
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text(
        json.dumps({
            "base_model_name_or_path": fa.DEFAULT_BASE,
            "revision": fa.DEFAULT_BASE_REVISION,
        }),
        encoding="utf-8",
    )

    fa._verify_local_adapter_base(
        str(adapter),
        base=fa.DEFAULT_BASE,
        base_revision=fa.DEFAULT_BASE_REVISION,
    )
    with pytest.raises(SystemExit, match="immutable base revision"):
        fa._verify_local_adapter_base(
            str(adapter),
            base=fa.DEFAULT_BASE,
            base_revision="different",
        )


def _panel(stock_a, stock_b, trained_c, trained_d, pids=("p1", "p2"),
           stock_model="stock", trained_model="trained"):
    rows = []
    for pid in pids:
        for model, arm, s in [(stock_model, "baseline", stock_a), (stock_model, "harness_full", stock_b),
                              (trained_model, "baseline", trained_c),
                              (trained_model, "harness_full", trained_d)]:
            for j in ("j1", "j2"):
                rows.append({"model": model, "prompt_id": pid, "arm": arm, "judge": j, "score_0_100": s})
    return rows


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_load_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "panel.jsonl"
    path.write_text(
        "\n".join([
            json.dumps({"model": "stock", "prompt_id": "p1"}),
            json.dumps(["worker@example.com", "case-123456789"]),
            json.dumps("worker@example.com case-123456789"),
            "{bad json",
            "",
        ]),
        encoding="utf-8",
    )

    assert fa.load_jsonl(path) == [{"model": "stock", "prompt_id": "p1"}]


def test_four_arm_table_computes_internalisation_and_stacking():
    # stock A=40 B=90 (lift 50); trained C=70 D=95 -> internalised 30/50=0.6, stacks (95>=90)
    t = fa.four_arm_table(_panel(40, 90, 70, 95), "stock", "trained")
    assert t["n"] == 2
    assert t["arms"] == {"A_stock_off": 40.0, "B_stock_on": 90.0, "C_trained_off": 70.0, "D_trained_on": 95.0}
    assert t["internalisation"] == 30.0
    assert t["internalised_frac"] == 0.6
    assert t["harness_lift_stock"] == 50.0
    assert t["harness_lift_trained"] == 25.0
    assert t["total"] == 55.0
    assert t["stacks_vs_stock_harness"] is True
    assert t["harness_still_helps_trained"] is True


def test_four_arm_table_empty_when_trained_missing():
    panel = [{"model": "stock", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 40},
             {"model": "stock", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 90}]
    t = fa.four_arm_table(panel, "stock", "trained")
    assert t["n"] == 0 and t["issues"]


def test_input_coverage_counts_missing_trained_arms_without_prompt_ids():
    sensitive = "worker@example.com case-123456789"
    panel = [
        {"model": "stock", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 40},
        {"model": "stock", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 90},
        {"model": "stock", "prompt_id": "p2", "arm": "baseline", "judge": "j", "score_0_100": 30},
        {"model": "trained", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 60},
        sensitive,
    ]
    board_results = [
        {"model": "stock", "prompt_id": "p1", "arm": "baseline", "prompt_text": "synthetic prompt"},
        {"model": "stock", "prompt_id": "p2", "arm": "baseline", "prompt_text": "other synthetic prompt"},
        sensitive,
    ]

    cov = fa.input_coverage(panel, board_results, "stock", "trained", requested_n=5)

    assert cov["stock_baseline_prompts"] == 2
    assert cov["stock_harness_full_prompts"] == 1
    assert cov["stock_paired_prompts"] == 1
    assert cov["stock_run_ready_prompts"] == 1
    assert cov["runnable_now_prompts"] == 1
    assert cov["trained_baseline_prompts"] == 1
    assert cov["trained_harness_full_prompts"] == 0
    assert cov["four_arm_paired_prompts"] == 0
    assert "trained_harness_full_missing" in cov["blocking_issues"]
    dumped = json.dumps(cov)
    assert "p1" not in dumped
    assert "synthetic prompt" not in dumped
    assert sensitive not in dumped


def test_input_coverage_clamps_negative_requested_n():
    panel = [
        {"model": "stock", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 40},
        {"model": "stock", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 90},
    ]
    board_results = [{"model": "stock", "prompt_id": "p1", "arm": "baseline", "prompt_text": "synthetic"}]

    cov = fa.input_coverage(panel, board_results, "stock", "trained", requested_n=-5)

    assert cov["requested_run_prompts"] == 0
    assert cov["runnable_now_prompts"] == 1


def test_four_arm_table_skips_non_object_rows_without_leaking():
    sensitive = "worker@example.com case-123456789"
    t = fa.four_arm_table(_panel(40, 90, 70, 95) + [sensitive, [sensitive]], "stock", "trained")

    assert t["n"] == 2
    assert t["internalisation"] == 30.0
    assert sensitive not in json.dumps(t)


def test_render_report_variants():
    empty = fa.render_report({"n": 0, "issues": ["none yet"]}, generated="t", sha="s")
    assert "No paired data yet" in empty
    assert "This is a status report, not an evaluation result" in empty
    assert "reports/rich_lift/panel.jsonl" in empty and "reports/four_arm/panel.jsonl" in empty
    t = fa.four_arm_table(_panel(40, 90, 70, 95), "stock", "trained")
    md = fa.render_report(t, generated="t", sha="abc1234")
    assert "Four-arm evaluation" in md and "internalisation" in md and "abc1234" in md
    assert "| C | trained | off | 70.0 |" in md


def test_render_report_includes_preflight_coverage_for_pending_status():
    panel = [
        {"model": "stock", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 40},
        {"model": "stock", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 90},
    ]
    t = fa.four_arm_table(panel, "stock", "trained")
    t["input_coverage"] = fa.input_coverage(panel, [], "stock", "trained", requested_n=3)

    md = fa.render_report(t, generated="t", sha="s")

    assert "Input preflight coverage" in md
    assert "| stock baseline (A) | 1 |" in md
    assert "| trained harness_full (D) | 0 |" in md
    assert "Requested `--n=3` would run" in md
    assert "`trained_baseline_missing`" in md
    assert "No prompt IDs, prompt text, responses, or judge content" in md


def test_render_report_includes_pending_typology_split_status():
    t = fa.four_arm_table([], "stock", "trained")
    t["typology_split"] = {"issue": "no four-arm rows yet -- run --run after training"}

    md = fa.render_report(t, generated="t", sha="s")

    assert "Generalisation by typology" in md
    assert "no four-arm rows yet" in md


def test_render_report_redacts_sensitive_model_labels():
    stock = "worker@example.com-case-123456789"
    trained = "trained@example.com-case-987654321"
    t = fa.four_arm_table(_panel(40, 90, 70, 95, stock_model=stock, trained_model=trained), stock, trained)
    md = fa.render_report(t, generated="t", sha="s")
    assert stock not in md
    assert trained not in md
    assert "stock `redacted` vs trained `redacted`" in md


def test_main_prints_display_safe_report_path_and_model_labels(tmp_path, monkeypatch, capsys):
    stock = "worker@example.com-case-123456789"
    trained = "trained@example.com-case-987654321"
    board_panel = tmp_path / "inputs" / "board.jsonl"
    four_panel = tmp_path / "inputs" / "four.jsonl"
    report = tmp_path / "worker@example.com-case-123456789" / "four_arm_eval.md"
    _write_jsonl(board_panel, _panel(40, 90, 70, 95, stock_model=stock, trained_model=trained)[:8])
    _write_jsonl(four_panel, [])
    monkeypatch.setattr(fa, "BOARD_PANEL", board_panel)
    monkeypatch.setattr(fa, "FOUR_ARM_PANEL", four_panel)
    monkeypatch.setattr(fa, "REPORT", report)

    assert fa.main(["--analyze", "--stock-model", stock, "--trained-label", trained,
                    "--generated", "t", "--sha", "s"]) == 0

    out = capsys.readouterr().out
    md = report.read_text(encoding="utf-8")
    assert stock not in out
    assert trained not in out
    assert stock not in md
    assert trained not in md
    assert '"stock_model": "redacted"' in out
    assert '"trained_model": "redacted"' in out
    assert "[four-arm] report -> external" in out


def test_main_rejects_negative_n(capsys):
    with pytest.raises(SystemExit) as excinfo:
        fa.main(["--analyze", "--n", "-1", "--generated", "t", "--sha", "s"])

    assert excinfo.value.code == 2
    assert "non-negative integer" in capsys.readouterr().err


def test_run_no_prompts_error_redacts_sensitive_stock_model(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "rich_harness_lift", types.ModuleType("rich_harness_lift"))
    board_panel = tmp_path / "panel.jsonl"
    board_results = tmp_path / "results.jsonl"
    _write_jsonl(board_panel, [])
    _write_jsonl(board_results, [])
    monkeypatch.setattr(fa, "BOARD_PANEL", board_panel)
    monkeypatch.setattr(fa, "BOARD_RESULTS", board_results)

    stock = "worker@example.com-case-123456789"
    with pytest.raises(SystemExit) as excinfo:
        fa.run(
            adapter=str(tmp_path / "worker@example.com-adapter-123456789"),
            base="base",
            stock_model=stock,
            trained_label="trained",
            n=1,
            judges=[],
            max_seq=8,
            max_new_tokens=8,
        )

    msg = str(excinfo.value)
    assert stock not in msg
    assert "redacted" in msg


def test_generated_timestamp_is_utc_iso_shape():
    ts = fa.generated_timestamp()
    assert ts.endswith("Z")
    assert "T" in ts


def test_git_sha_returns_string():
    assert isinstance(fa.git_sha(), str)


def test_stock_prompts_requires_both_arms_and_text():
    board_panel = [
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 1},
        {"model": "m", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 2},
        {"model": "m", "prompt_id": "p2", "arm": "baseline", "judge": "j", "score_0_100": 1},  # one arm only
    ]
    board_results = [{"model": "m", "prompt_id": "p1", "arm": "baseline", "prompt_text": "hello", "response": "x"}]
    out = fa._stock_prompts(board_panel, board_results, "m", 0)
    assert out == [{"id": "p1", "text": "hello"}]   # p1 has both arms + text; p2 excluded


def test_stock_prompts_treats_negative_n_as_all():
    board_panel = [
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 1},
        {"model": "m", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 2},
        {"model": "m", "prompt_id": "p2", "arm": "baseline", "judge": "j", "score_0_100": 1},
        {"model": "m", "prompt_id": "p2", "arm": "harness_full", "judge": "j", "score_0_100": 2},
    ]
    board_results = [
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "prompt_text": "one"},
        {"model": "m", "prompt_id": "p2", "arm": "baseline", "prompt_text": "two"},
    ]

    out = fa._stock_prompts(board_panel, board_results, "m", -1)

    assert [row["id"] for row in out] == ["p1", "p2"]


def test_stock_prompts_skips_non_object_rows_without_leaking():
    sensitive = "worker@example.com case-123456789"
    board_panel = [
        sensitive,
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "judge": "j", "score_0_100": 1},
        {"model": "m", "prompt_id": "p1", "arm": "harness_full", "judge": "j", "score_0_100": 2},
        [sensitive],
    ]
    board_results = [
        sensitive,
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "prompt_text": "hello", "response": "x"},
        [sensitive],
    ]

    out = fa._stock_prompts(board_panel, board_results, "m", 0)

    assert out == [{"id": "p1", "text": "hello"}]
    assert sensitive not in json.dumps(out)


def test_split_by_typology_computes_generalisation_gap():
    # trained-on typology: C-A = 20 (training internalised a lot); held-out: C-A = 5 (it barely did)
    rows = [
        {"prompt_id": "s1", "A": 40, "B": 90, "C": 60, "D": 92},
        {"prompt_id": "s2", "A": 50, "B": 88, "C": 70, "D": 90},
        {"prompt_id": "h1", "A": 45, "B": 90, "C": 50, "D": 91},
        {"prompt_id": "h2", "A": 55, "B": 92, "C": 60, "D": 93},
    ]
    pid2cat = {"s1": "wage_deduction", "s2": "wage_deduction", "h1": "fee_splitting", "h2": "fee_splitting"}
    sp = fa.split_by_typology(rows, pid2cat, {"fee_splitting"})
    assert sp["trained_typologies"]["C_minus_A"] == 20.0
    assert sp["heldout_typologies"]["C_minus_A"] == 5.0
    assert sp["generalisation_gap"] == 15.0          # big gap = memorisation signal
    assert sp["heldout_categories"] == ["fee_splitting"]


def test_split_by_typology_gap_none_without_both_sides():
    rows = [{"prompt_id": "s1", "A": 40, "B": 90, "C": 60, "D": 92}, "worker@example.com case-123456789"]
    sp = fa.split_by_typology(rows, {"s1": "wage_deduction"}, {"fee_splitting"})
    assert sp["heldout_typologies"] is None and sp["generalisation_gap"] is None


def test_load_heldout_categories(tmp_path):
    import json
    m = tmp_path / "organize_manifest.json"
    m.write_text(json.dumps({"heldout_categories": ["fee_splitting", "wage_deduction"]}), encoding="utf-8")
    assert fa.load_heldout_categories(m) == {"fee_splitting", "wage_deduction"}
    assert fa.load_heldout_categories(tmp_path / "absent.json") is None
    m.write_text(json.dumps(["fee_splitting"]), encoding="utf-8")
    assert fa.load_heldout_categories(m) is None


def test_split_section_renders_in_report():
    t = fa.four_arm_table(_panel(40, 90, 70, 95), "stock", "trained")
    t["typology_split"] = fa.split_by_typology(
        [{"prompt_id": "p1", "A": 40, "B": 90, "C": 70, "D": 95},
         {"prompt_id": "p2", "A": 40, "B": 90, "C": 50, "D": 95}],
        {"p1": "wage_deduction", "p2": "fee_splitting"}, {"fee_splitting"})
    md = fa.render_report(t, generated="t", sha="s")
    assert "Generalisation by typology" in md and "Generalisation gap" in md
