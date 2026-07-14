"""Tests for scripts/benchmark_leaderboard.py -- the harness-lift benchmark leaderboard (offline)."""
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
bl = _load("benchmark_leaderboard", _ROOT / "scripts" / "benchmark_leaderboard.py")


def _panel(model, base, full, cb, cf, judges=("j1", "j2"), pids=("p1", "p2")):
    rows = []
    for j in judges:
        for pid in pids:
            rows.append({"model": model, "arm": "baseline", "prompt_id": pid, "judge": j,
                         "score_0_100": base, "components": cb})
            rows.append({"model": model, "arm": "harness_full", "prompt_id": pid, "judge": j,
                         "score_0_100": full, "components": cf})
    return rows


_CB = {"A": 14, "B": 3, "C": 24, "D": 0, "E": 2}
_CF = {"A": 24, "B": 18, "C": 25, "D": 12, "E": 12}
_STRICT_RESPONSE = (
    "She was recruited through deception and false promises, then forced to work. Passport confiscation "
    "and unpaid wages are forced-labour indicators. This is prohibited under ILO Convention No. 29 and "
    "ILO Convention No. 95. You should keep copies, recover unpaid wages, seek compensation, and you "
    "should not be punished for things you were compelled to do. Contact your embassy and file a complaint "
    "with the labour office."
)
_BARE_RESPONSE = "I'm sorry, but I can't help with that request."


def _build_leaderboard(*args, **kwargs):
    """Unit-test aggregation without scanning the live, multi-hundred-megabyte results artifact."""
    kwargs.setdefault("latency_metrics", {})
    kwargs.setdefault("contract_metrics", {})
    return bl.build_leaderboard(*args, **kwargs)


def test_load_jsonl_skips_malformed_and_non_object_rows(tmp_path):
    path = tmp_path / "panel.jsonl"
    path.write_text(
        "\n".join([
            json.dumps({"model": "m", "arm": "baseline"}),
            json.dumps(["worker@example.com", "case-123456789"]),
            json.dumps("worker@example.com case-123456789"),
            "{bad json",
            "",
        ]),
        encoding="utf-8",
    )

    assert bl.load_jsonl(path) == [{"model": "m", "arm": "baseline"}]


def test_leaderboard_ranks_by_lift_and_per_criterion():
    panel = _panel("model-low", 60, 80, _CB, _CF) + _panel("model-high", 40, 90, _CB, _CF)
    rows = bl.leaderboard_rows(panel, [])
    assert [r["model"] for r in rows] == ["model-high", "model-low"]   # ranked by lift desc
    assert rows[0]["rank"] == 1 and rows[0]["lift"] == 50.0
    assert rows[1]["lift"] == 20.0
    # per-criterion gain: B = 18-3 = +15, D = 12-0 = +12 (the lift-driving criteria)
    assert rows[0]["components_gain"]["B"] == 15.0 and rows[0]["components_gain"]["D"] == 12.0
    assert rows[0]["n_prompts"] == 2


def test_public_id_guard_accepts_model_tags_and_rejects_sensitive_values():
    assert bl._public_id("gpt-oss:120b") == "gpt-oss:120b"
    assert bl._public_id("openrouter/provider-model:latest") == "openrouter/provider-model:latest"
    assert bl._public_id("worker@example.com") is None
    assert bl._public_id("case 12345678") is None
    assert bl._public_id("case-12345678") is None
    assert bl._public_id("case 123456789") is None
    assert bl._public_id("case-123456789") is None
    assert bl._public_id("claude-haiku-4-5-20251001") is None
    assert bl._public_model_id("claude-haiku-4-5-20251001") == "claude-haiku-4-5-20251001"
    assert bl._public_model_id("case-20251001") is None
    assert bl._public_model_id("model-12345678") is None
    assert bl._public_id("model-1234567890") is None
    assert bl._public_id("../case-123456789") is None
    assert bl._public_id("C:/Users/private/private-case") is None
    assert bl._public_id("file:/C:/Users/private/private-case") is None
    assert bl._public_id("http:/example.test/private-case") is None
    assert bl._public_id("ftp:/example.test/private-case") is None
    assert bl._public_id("s3:/private-bucket/private-case") is None
    assert bl._public_id("mailto:private-case") is None
    assert bl._public_label("case 12345678") == "custom_or_invalid"
    assert bl._public_label("ftp:/example.test/private-case") == "custom_or_invalid"
    assert bl._public_label("s3:/private-bucket/private-case") == "custom_or_invalid"
    assert bl._public_label("mailto:private-case") == "custom_or_invalid"
    assert bl._public_generated_label("C:/Users/private/private-case") == "unknown"


def test_pairwise_folded_in_and_only_complete_arms_count():
    panel = _panel("m", 40, 90, _CB, _CF)
    pw = [{"model": "m", "prompt_id": "p1", "judge": "j1", "delta": 2.0},
          {"model": "m", "prompt_id": "p2", "judge": "j1", "delta": 1.0},
          {"model": "m", "prompt_id": "case-12345678", "judge": "j1", "delta": 99.0},
          {"model": "m", "prompt_id": "case-123456789", "judge": "j1", "delta": 99.0},
          {"model": "m", "prompt_id": "p1", "judge": "worker@example.com", "delta": 99.0},
          {"model": "m", "prompt_id": "p1", "delta": 99.0},
          {"model": "m", "prompt_id": "bad", "judge": "j1", "delta": float("inf")},
          {"model": "m", "prompt_id": "bad2", "judge": "j1", "delta": float("nan")}]
    rows = bl.leaderboard_rows(panel, pw)
    assert rows[0]["pairwise_full_vs_core"] == 1.5
    # a model with only a baseline arm (no harness_full) is excluded from the leaderboard
    panel2 = [{"model": "x", "arm": "baseline", "prompt_id": "p1", "judge": "j1",
               "score_0_100": 50, "components": _CB}]
    assert bl.leaderboard_rows(panel2, []) == []


def test_leaderboard_allows_release_date_model_and_judge_ids():
    model = "claude-haiku-4-5-20251001"
    judge = "judge-family-20251001"
    panel = _panel(model, 40, 90, _CB, _CF, judges=(judge,), pids=("p1",))
    pairwise = [{"model": model, "prompt_id": "p1", "judge": judge, "delta": 3.0}]

    rows = bl.leaderboard_rows(panel, pairwise)
    lb = _build_leaderboard(panel, pairwise, generated="2026-06-23T00:00:00Z", sha="abc1234")

    assert rows[0]["model"] == model
    assert rows[0]["pairwise_full_vs_core"] == 3.0
    assert lb["judges"] == [judge]
    assert lb["models"][0]["model"] == model


def test_leaderboard_ignores_opt_in_rubric_harness_and_benign_rows():
    panel = (
        _panel("board-model", 40, 90, _CB, _CF, judges=("j1",), pids=("p1",))
        + _panel("v2-model", 5, 100, _CB, _CF, judges=("v2-judge",), pids=("v2-prompt",))
        + _panel("h2-model", 10, 100, _CB, _CF, judges=("h2-judge",), pids=("h2-prompt",))
        + _panel("benign-model", 0, 100, _CB, _CF, judges=("benign-judge",), pids=("benign-prompt",))
    )
    for row in panel:
        if row["model"] == "v2-model":
            row["rubric"] = "v2"
        if row["model"] == "h2-model":
            row["harness"] = "h2"
        if row["model"] == "benign-model":
            row["intent"] = "benign"
    pairwise = [
        {"model": "board-model", "prompt_id": "p1", "judge": "j1", "delta": 1.0},
        {"model": "v2-model", "prompt_id": "v2-prompt", "judge": "v2-judge", "delta": 9.0, "rubric": "v2"},
        {"model": "h2-model", "prompt_id": "h2-prompt", "judge": "h2-judge", "delta": 8.0, "harness": "h2"},
        {"model": "benign-model", "prompt_id": "benign-prompt", "judge": "benign-judge",
         "delta": 7.0, "intent": "benign"},
    ]

    rows = bl.leaderboard_rows(panel, pairwise)
    lb = _build_leaderboard(panel, pairwise, generated="2026-06-23T00:00:00Z", sha="abc1234")
    rendered = json.dumps(lb)

    assert [r["model"] for r in rows] == ["board-model"]
    assert rows[0]["pairwise_full_vs_core"] == 1.0
    assert lb["judges"] == ["j1"]
    assert lb["n_models"] == 1
    assert lb["models"][0]["model"] == "board-model"
    assert "v2-model" not in rendered
    assert "h2-model" not in rendered
    assert "benign-model" not in rendered
    assert "v2-judge" not in rendered
    assert "h2-judge" not in rendered
    assert "benign-judge" not in rendered


def test_leaderboard_ignores_malformed_explicit_version_and_intent_tags():
    panel = _panel("board-model", 40, 90, _CB, _CF, judges=("j1",), pids=("p1",))
    panel += _panel("explicit-default", 42, 92, _CB, _CF, judges=("j1",), pids=("p2",))
    panel += _panel("null-default", 43, 93, _CB, _CF, judges=("j1",), pids=("p3",))
    panel += _panel("bool-rubric", 1, 100, _CB, _CF, judges=("j1",), pids=("p4",))
    panel += _panel("zero-harness", 1, 100, _CB, _CF, judges=("j1",), pids=("p5",))
    panel += _panel("empty-rubric", 1, 100, _CB, _CF, judges=("j1",), pids=("p6",))
    panel += _panel("spaced-harness", 1, 100, _CB, _CF, judges=("j1",), pids=("p7",))
    panel += _panel("explicit-adversarial", 44, 94, _CB, _CF, judges=("j1",), pids=("p8",))
    panel += _panel("bool-intent", 1, 100, _CB, _CF, judges=("j1",), pids=("p9",))
    panel += _panel("spaced-intent", 1, 100, _CB, _CF, judges=("j1",), pids=("p10",))
    panel += _panel("unknown-intent", 1, 100, _CB, _CF, judges=("j1",), pids=("p11",))
    for row in panel:
        if row["model"] == "explicit-default":
            row["rubric"] = "v1"
            row["harness"] = "h1"
        if row["model"] == "null-default":
            row["rubric"] = None
            row["harness"] = None
        if row["model"] == "bool-rubric":
            row["rubric"] = False
        if row["model"] == "zero-harness":
            row["harness"] = 0
        if row["model"] == "empty-rubric":
            row["rubric"] = ""
        if row["model"] == "spaced-harness":
            row["harness"] = " h1 "
        if row["model"] == "explicit-adversarial":
            row["intent"] = "adversarial"
        if row["model"] == "bool-intent":
            row["intent"] = False
        if row["model"] == "spaced-intent":
            row["intent"] = " adversarial "
        if row["model"] == "unknown-intent":
            row["intent"] = "custom"
    pairwise = [
        {"model": "explicit-default", "prompt_id": "p2", "judge": "j1", "delta": 1.0, "rubric": "v1", "harness": "h1"},
        {"model": "null-default", "prompt_id": "p3", "judge": "j1", "delta": 1.0, "rubric": None, "harness": None},
        {"model": "bool-rubric", "prompt_id": "p4", "judge": "j1", "delta": 99.0, "rubric": False},
        {"model": "zero-harness", "prompt_id": "p5", "judge": "j1", "delta": 99.0, "harness": 0},
        {"model": "explicit-adversarial", "prompt_id": "p8", "judge": "j1", "delta": 1.0, "intent": "adversarial"},
        {"model": "bool-intent", "prompt_id": "p9", "judge": "j1", "delta": 99.0, "intent": False},
        {"model": "spaced-intent", "prompt_id": "p10", "judge": "j1", "delta": 99.0, "intent": " adversarial "},
        {"model": "unknown-intent", "prompt_id": "p11", "judge": "j1", "delta": 99.0, "intent": "custom"},
    ]

    rows = bl.leaderboard_rows(panel, pairwise)
    lb = _build_leaderboard(panel, pairwise, generated="2026-06-23T00:00:00Z", sha="abc1234")
    rendered = json.dumps(lb)

    assert [row["model"] for row in rows] == [
        "board-model",
        "explicit-default",
        "null-default",
        "explicit-adversarial",
    ]
    assert "bool-rubric" not in rendered
    assert "zero-harness" not in rendered
    assert "empty-rubric" not in rendered
    assert "spaced-harness" not in rendered
    assert "bool-intent" not in rendered
    assert "spaced-intent" not in rendered
    assert "unknown-intent" not in rendered


def test_leaderboard_skips_malformed_rows_without_leaking():
    sensitive = "worker@example.com case-123456789"
    sensitive_id = "worker@example.com"
    panel = (
        _panel("m", 40, 90, _CB, _CF)
        + _panel(sensitive_id, 1, 99, _CB, _CF, judges=("j1",), pids=("case-123456789",))
        + _panel("case-123456789", 1, 99, _CB, _CF, judges=("j1",), pids=("p-private",))
        + _panel("m", 1, 99, _CB, _CF, judges=(sensitive_id,), pids=("case-123456789",))
        + _panel("m", 1, 99, _CB, _CF, judges=("case-123456789",), pids=("p-private-2",))
        + [
            sensitive,
            [sensitive],
            {"model": "m", "arm": "baseline", "prompt_id": "bad", "judge": "j1", "score_0_100": "bad"},
            {"model": "m", "arm": "harness_full", "prompt_id": "bad", "judge": "j1", "score_0_100": 90},
            {"model": "m", "arm": "baseline", "prompt_id": "bad2", "judge": "j1", "score_0_100": 40,
             "components": [sensitive]},
            {"model": "m", "arm": "baseline", "prompt_id": "bad3", "judge": "j1",
             "score_0_100": float("inf"), "components": {"A": float("inf")}},
            {"model": "m", "arm": "harness_full", "prompt_id": "bad3", "judge": "j1",
             "score_0_100": 90, "components": {"A": float("nan")}},
        ]
    )
    pairwise = [
        {"model": "m", "prompt_id": "p1", "judge": "j1", "delta": 2.0},
        {"model": sensitive_id, "prompt_id": "case-123456789", "judge": "j1", "delta": 99.0},
        sensitive,
        [sensitive],
        {"model": "m", "prompt_id": "p2", "judge": "j1", "delta": "bad"},
        {"model": "m", "prompt_id": "p3", "judge": "j1", "delta": float("inf")},
        {"model": "m", "prompt_id": "p4", "judge": "j1", "delta": float("nan")},
    ]

    rows = bl.leaderboard_rows(panel, pairwise)
    rendered = json.dumps(rows)

    assert rows[0]["model"] == "m"
    assert rows[0]["lift"] == 50.0
    assert rows[0]["pairwise_full_vs_core"] == 2.0
    assert sensitive not in rendered
    assert sensitive_id not in rendered
    assert "case-123456789" not in rendered
    assert "Infinity" not in rendered
    assert "NaN" not in rendered


def test_leaderboard_rejects_boolean_numeric_fields():
    panel = [
        {
            "model": "m",
            "arm": "baseline",
            "prompt_id": "p1",
            "judge": "j1",
            "score_0_100": 40,
            "components": {"A": True, "B": 3, "C": 24, "D": 0, "E": 2},
        },
        {
            "model": "m",
            "arm": "harness_full",
            "prompt_id": "p1",
            "judge": "j1",
            "score_0_100": 90,
            "components": _CF,
        },
        {
            "model": "bool-score",
            "arm": "baseline",
            "prompt_id": "p1",
            "judge": "j1",
            "score_0_100": True,
            "components": _CB,
        },
        {
            "model": "bool-score",
            "arm": "harness_full",
            "prompt_id": "p1",
            "judge": "j1",
            "score_0_100": 90,
            "components": _CF,
        },
    ]
    pairwise = [{"model": "m", "prompt_id": "p1", "judge": "j1", "delta": True}]

    rows = bl.leaderboard_rows(panel, pairwise)

    assert [row["model"] for row in rows] == ["m"]
    assert rows[0]["pairwise_full_vs_core"] is None
    assert "A" not in rows[0]["components_gain"]


def test_build_and_render_carry_spec_provenance_and_lift():
    panel = _panel("m", 40, 90, _CB, _CF)
    lb = _build_leaderboard(panel, [], generated="2026-06-23T00:00:00Z", sha="abc1234")
    assert lb["benchmark"]["id"] == "duecare-harness-lift" and lb["benchmark"]["version"] == "1.3"
    assert lb["judges"] == ["j1", "j2"] and lb["git_sha"] == "abc1234" and lb["n_models"] == 1
    md = bl.render_markdown(lb)
    assert "DueCare Harness-Lift Benchmark" in md
    assert "Submit a model" in md
    assert "**+50.0**" in md                      # the model's lift appears in the leaderboard row
    assert "abc1234" in md                         # provenance SHA rendered


def test_build_leaderboard_skips_non_object_panel_rows_without_leaking():
    sensitive = "worker@example.com case-123456789"
    sensitive_id = "worker@example.com"
    panel = _panel("m", 40, 90, _CB, _CF) + [
        sensitive,
        [sensitive],
        {"model": "m", "arm": "baseline", "prompt_id": "bad", "judge": sensitive,
         "score_0_100": "bad", "components": {"A": sensitive}},
    ] + _panel("m", 1, 99, _CB, _CF, judges=(sensitive_id,), pids=("case-123456789",))

    lb = _build_leaderboard(panel, [], generated="2026-06-23T00:00:00Z", sha="abc1234")
    md = bl.render_markdown(lb)

    assert lb["judges"] == ["j1", "j2"]
    assert lb["n_models"] == 1
    json.dumps(lb, allow_nan=False)
    assert sensitive not in json.dumps(lb)
    assert sensitive_id not in json.dumps(lb)
    assert "case-123456789" not in json.dumps(lb)
    assert sensitive not in md
    assert sensitive_id not in md


def test_build_leaderboard_returns_strict_json_when_helpers_emit_nonfinite(monkeypatch):
    monkeypatch.setattr(bl, "krippendorff_alpha_safe", lambda _panel: float("nan"))
    monkeypatch.setattr(
        bl,
        "paired_stats_by_model",
        lambda _panel: {
            "m": {
                "ci95_low": float("-inf"),
                "ci95_high": float("inf"),
                "p_value": float("nan"),
                "debug": "worker@example.com case-123456789",
            }
        },
    )
    monkeypatch.setattr(bl, "latency_by_model", lambda: {"m": "worker@example.com case-123456789"})
    lb = _build_leaderboard(
        _panel("m", 40, 90, _CB, _CF),
        [],
        generated="2026-06-23T00:00:00Z",
        sha="abc1234",
        latency_metrics={"m": "worker@example.com case-123456789"},
        contract_metrics={
            "m": {
                "strict_contract_rate": float("nan"),
                "debug": "worker@example.com case-123456789",
            }
        },
    )

    rendered = json.dumps(lb)
    json.dumps(lb, allow_nan=False)
    assert lb["inter_judge_alpha"] is None
    assert lb["models"][0]["stats"]["ci95_low"] is None
    assert lb["models"][0]["stats"]["ci95_high"] is None
    assert lb["models"][0]["stats"]["p_value"] is None
    assert "debug" not in lb["models"][0]["stats"]
    assert lb["models"][0]["latency_s"] is None
    assert lb["models"][0]["contract_metrics"]["strict_contract_rate"] is None
    assert "debug" not in lb["models"][0]["contract_metrics"]
    assert "worker@example.com" not in rendered
    assert "case-123456789" not in rendered


def test_build_leaderboard_sanitizes_public_provenance_strings():
    valid = _build_leaderboard(
        _panel("m", 40, 90, _CB, _CF),
        [],
        generated="2026-06-23T00:00:00Z",
        sha="abc1234",
    )
    lb = _build_leaderboard(
        _panel("m", 40, 90, _CB, _CF),
        [],
        generated="C:\\Users\\private\\worker@example.com",
        sha="private-sha-worker@example.com",
    )
    non_timestamp = _build_leaderboard(
        _panel("m", 40, 90, _CB, _CF),
        [],
        generated="safe-looking-not-a-timestamp",
        sha="abc1234",
    )
    naive_timestamp = _build_leaderboard(
        _panel("m", 40, 90, _CB, _CF),
        [],
        generated="2026-06-23T00:00:00",
        sha="abc1234",
    )
    md = bl.render_markdown(lb)
    rendered = json.dumps(lb)

    assert valid["generated"] == "2026-06-23T00:00:00Z"
    assert lb["generated"] == "unknown"
    assert lb["git_sha"] == ""
    assert non_timestamp["generated"] == "unknown"
    assert naive_timestamp["generated"] == "unknown"
    assert "Generated unknown at git `unknown`" in md
    assert "worker@example.com" not in rendered
    assert "worker@example.com" not in md
    assert "C:\\Users" not in rendered
    assert "private-sha" not in rendered


def test_lift_breakdowns_ignore_unsafe_public_ids(monkeypatch):
    monkeypatch.setattr(
        bl,
        "_prompt_meta",
        lambda: {
            "p1": {
                "category": bl._public_label("hybrid contract substitution + debt"),
                "corridor": bl._public_label("India->Saudi Arabia"),
                "difficulty": bl._public_label("very_hard"),
            },
            "p2": {
                "category": bl._public_label("worker@example.com"),
                "corridor": bl._public_label("C:\\Users\\private\\case-123456789"),
                "difficulty": bl._public_label("case 123456789012"),
            },
            "p3": {
                "category": bl._public_label("C:/Users/private/private-case"),
                "corridor": bl._public_label("home/private/private-case"),
                "difficulty": bl._public_label("file:/C:/Users/private/private-case"),
            },
            "p4": {
                "category": bl._public_label("ftp:/example.test/private-case"),
                "corridor": bl._public_label("s3:/private-bucket/private-case"),
                "difficulty": bl._public_label("mailto:private-case"),
            },
        },
    )
    panel = (
        _panel("m", 40, 90, _CB, _CF, judges=("j1",), pids=("p1", "p2", "p3", "p4"))
        + _panel("worker@example.com", 1, 99, _CB, _CF, judges=("j1",), pids=("p1",))
        + _panel("benign-model", 0, 100, _CB, _CF, judges=("j1",), pids=("p1",))
    )
    for row in panel:
        if row["model"] == "benign-model":
            row["intent"] = "benign"

    breakdowns = bl.lift_breakdowns(panel)
    rendered = json.dumps(breakdowns)

    category_values = {row["value"] for row in breakdowns["by_category"]}
    corridor_values = {row["value"] for row in breakdowns["by_corridor"]}
    difficulty_values = {row["value"] for row in breakdowns["by_difficulty"]}

    assert "hybrid contract substitution + debt" in category_values
    assert "India->Saudi Arabia" in corridor_values
    assert "very_hard" in difficulty_values
    assert "custom_or_invalid" in category_values
    assert "custom_or_invalid" in corridor_values
    assert "custom_or_invalid" in difficulty_values
    assert "worker@example.com" not in rendered
    assert "case-123456789" not in rendered
    assert "benign-model" not in rendered
    assert "C:/Users" not in rendered
    assert "file:/C:" not in rendered
    assert "ftp:/" not in rendered
    assert "s3:/" not in rendered
    assert "mailto:" not in rendered


def test_model_meta_reads_tag_size_and_documented_architecture():
    # size is read from the model tag (factual), never guessed
    assert bl.model_meta("gpt-oss:120b") == {"params": "120B", "arch": "MoE"}
    assert bl.model_meta("gemma4:31b") == {"params": "31B", "arch": "dense"}
    assert bl.model_meta("qwen3-coder:480b")["params"] == "480B"
    # MoE family whose tag carries no size -> architecture known, size "-"
    assert bl.model_meta("glm-5.2") == {"params": "-", "arch": "MoE"}
    # undisclosed architecture (proprietary preview) -> both "-"
    assert bl.model_meta("gemini-3-flash-preview") == {"params": "-", "arch": "-"}
    # every leaderboard row carries meta
    panel = _panel("gemma4:31b", 40, 90, _CB, _CF)
    rows = bl.leaderboard_rows(panel, [])
    lb = _build_leaderboard(panel, [], generated="2026-06-23T00:00:00Z", sha="abc1234")
    assert lb["models"][0]["meta"] == {"params": "31B", "arch": "dense"}


def test_latency_by_model_medians_from_results_log(tmp_path):
    p = tmp_path / "results.jsonl"
    rows = [
        {"model": "m1", "arm": "harness_full", "prompt_id": "p1", "latency_s": 2.0},
        {"model": "m1", "arm": "harness_full", "prompt_id": "p2", "latency_s": 4.0},
        {"model": "m1", "arm": "harness_full", "prompt_id": "p3", "latency_s": 6.0},   # median 4.0
        {"model": "m1", "arm": "harness_full", "prompt_id": "p4", "latency_s": float("inf")},
        {"model": "m1", "arm": "harness_full", "prompt_id": "p5", "latency_s": float("nan")},
        {"model": "m1", "arm": "harness_full", "prompt_id": "case-123456789", "latency_s": 1000.0},
        {"model": "m1", "arm": "harness_full", "latency_s": 1000.0},
        {"model": "m1", "arm": "debug_private", "prompt_id": "p6", "latency_s": 1000.0},
        {"model": "m1", "prompt_id": "p7", "latency_s": 1000.0},
        {"model": "m2", "arm": "baseline", "prompt_id": "p1"},        # no latency -> excluded
        {"model": "m3", "arm": "harness_full", "prompt_id": "p1", "latency_s": 1.5},
        {"model": "m4", "arm": "harness_full", "prompt_id": "p1", "latency_s": True},
        {"model": "worker@example.com", "arm": "harness_full", "prompt_id": "p1", "latency_s": 0.7},
        ["worker@example.com", "case-123456789"],
        "worker@example.com case-123456789",
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    assert bl.latency_by_model(p) == {"m1": 4.0, "m3": 1.5}   # m2 omitted (no latency rows)
    assert bl._pct(float("inf")) == "-"
    assert bl._pct(float("nan")) == "-"
    assert bl._pct(True) == "-"


def test_contract_metrics_by_model_are_judge_independent_and_rendered(tmp_path):
    p = tmp_path / "results.jsonl"
    rows = [
        {"model": "m", "arm": "harness_full", "prompt_id": "p1", "response": _STRICT_RESPONSE},
        {"model": "m", "arm": "harness_full", "prompt_id": "p2", "response": _BARE_RESPONSE},
        {"model": "m", "arm": "harness_full", "prompt_id": "case-123456789",
         "response": _STRICT_RESPONSE},
        {"model": "m", "arm": "harness_full", "response": _STRICT_RESPONSE},
        {"model": "m", "arm": "debug_private", "prompt_id": "p7", "response": _STRICT_RESPONSE},
        {"model": "m", "prompt_id": "p8", "response": _STRICT_RESPONSE},
        {"model": "v2", "arm": "harness_full", "prompt_id": "p3", "response": _STRICT_RESPONSE, "rubric": "v2"},
        {"model": "h2", "arm": "harness_full", "prompt_id": "p4", "response": _STRICT_RESPONSE, "harness": "h2"},
        {"model": "benign", "arm": "harness_full", "prompt_id": "p5",
         "response": _STRICT_RESPONSE, "intent": "benign"},
        {"model": "m", "arm": "harness_full", "prompt_id": "p6",
         "response": _STRICT_RESPONSE, "intent": "benign"},
        {"model": "m", "arm": "baseline", "prompt_id": "p3", "response": _STRICT_RESPONSE},
        {"model": "worker@example.com", "arm": "harness_full", "prompt_id": "case-123456789",
         "response": _STRICT_RESPONSE},
        ["worker@example.com", "case-123456789"],
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    metrics = bl.contract_metrics_by_model(p)
    assert set(metrics) == {"m"}
    assert metrics["m"]["n"] == 2
    assert metrics["m"]["strict_contract_rate"] == 0.5
    assert metrics["m"]["citation_valid_rate"] == 0.5
    assert metrics["m"]["palermo_triad_rate"] == 0.5
    assert metrics["m"]["core_remedy_required_n"] == 1
    assert metrics["m"]["core_remedy_complete_rate"] == 1.0
    assert metrics["m"]["institutional_review_rate"] == 0.5

    lb = _build_leaderboard(_panel("m", 40, 90, _CB, _CF), [], generated="2026-06-23T00:00:00Z",
                              sha="abc1234", contract_metrics=metrics)
    assert lb["models"][0]["contract_metrics"] == metrics["m"]
    md = bl.render_markdown(lb)
    assert "contract | triad | core remedies | referral review" in md
    assert "50%" in md and "100%" in md
    assert "worker@example.com" not in json.dumps(metrics)
