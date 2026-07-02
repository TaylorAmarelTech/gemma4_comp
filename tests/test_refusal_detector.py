"""Tests for scripts/refusal_detector.py -- non-useful response classification + rates."""
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


rd = _load("refusal_detector", _ROOT / "scripts" / "refusal_detector.py")

_GOOD = "No, this is not normal — it is illegal forced labour under ILO C181. " * 6  # long, useful


def test_classify_distinguishes_non_answers():
    assert rd.classify("")[1] == "empty"
    assert rd.classify("(empty)")[1] == "empty"
    assert rd.classify("We need to answer the user. The user asks about passport retention…")[1] == "reasoning_trace"
    assert rd.classify("I can't help with that request.")[1] == "refusal"
    assert rd.classify("Maybe.")[1] == "too_short"
    assert rd.classify(_GOOD) == (True, "useful")


def test_analyze_separates_format_failures_from_refusals():
    rows = [{"model": "m", "arm": "baseline", "response": ""},                 # format failure (empty)
            {"model": "m", "arm": "harnessed", "response": _GOOD},             # useful answer
            {"model": "m", "arm": "baseline", "response": "I can't help with that."}]  # refusal (separate)
    a = rd.analyze(rows)
    assert a["n"] == 3 and a["n_format_failure"] == 1 and a["n_refusal"] == 1
    # the refusal is NOT counted as a format failure
    assert a["format_by_arm"]["baseline"]["rate"] == 0.5            # 1 of 2 baseline is a format-fail
    assert a["format_by_arm"]["harnessed"]["rate"] == 0.0
    assert a["refusal_by_arm"]["baseline"]["hit"] == 1             # the refusal shows here, separately


def test_load_skips_malformed_and_non_string_response_fields(tmp_path):
    p = tmp_path / "responses.jsonl"
    p.write_text(
        "\n".join([
            json.dumps({"model": "m", "arm": "baseline", "response": ""}),
            json.dumps({"model": "m", "arm": "harnessed", "response": _GOOD}),
            json.dumps({"model": {"private": "worker@example.com"}, "arm": "baseline", "response": _GOOD}),
            json.dumps({"model": "m", "arm": ["baseline"], "response": _GOOD}),
            json.dumps({"model": "m", "arm": "baseline", "response": {"private": "worker@example.com"}}),
            json.dumps({"model": "m", "arm": "placebo", "response": _GOOD}),
            json.dumps(["not", "an", "object"]),
            "{not-json",
        ]) + "\n",
        encoding="utf-8",
    )

    rows = rd.load([p])

    assert rows == [
        {"model": "m", "arm": "baseline", "response": ""},
        {"model": "m", "arm": "harnessed", "response": _GOOD},
    ]


def test_analyze_filters_malformed_rows_but_keeps_empty_response():
    rows = [
        {"model": "m", "arm": "baseline", "response": ""},
        {"model": "m", "arm": "harnessed", "response": _GOOD},
        {"model": {"private": "worker@example.com"}, "arm": "baseline", "response": _GOOD},
        {"model": "m", "arm": "baseline", "response": {"private": "worker@example.com"}},
    ]

    a = rd.analyze(rows)

    assert a["n"] == 2
    assert a["n_format_failure"] == 1
    assert a["format_by_model"] == {"m": {"n": 2, "hit": 1, "rate": 0.5}}


def test_build_report_flags_and_explains(tmp_path):
    rows = [{"model": "m", "arm": "baseline", "response": "We need to answer the user…"},
            {"model": "m", "arm": "harnessed", "response": _GOOD}]
    md = rd.build_report(rows, out_path=tmp_path / "r.md")
    assert "non-useful" in md.lower()
    assert "reasoning_trace" in md and "excluded from the quality" in md.lower()


def test_build_report_redacts_sensitive_model_labels(tmp_path):
    sensitive = "worker@example.com-case-123456789"
    rows = [
        {"model": sensitive, "arm": "baseline", "response": ""},
        {"model": "safe-model", "arm": "harnessed", "response": _GOOD},
    ]

    md = rd.build_report(rows, out_path=tmp_path / "r.md")

    assert "worker@example.com" not in md
    assert "case-123456789" not in md
    assert "`redacted`" in md
