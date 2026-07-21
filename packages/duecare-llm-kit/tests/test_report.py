"""Tests for the DueCare HTML report generator."""
from __future__ import annotations

import json

import pandas as pd

from duecare.kit.report import aggregate, generate_report, report_from_jsonl


def _panel_records():
    """Two models, two prompts, three judges, three arms -- a small hand-checkable panel."""
    records = []
    plan = {
        "gemma4:31b": {"P1": (40, 90), "P2": (50, 88)},
        "glm-5.2": {"P1": (60, 70), "P2": (55, 65)},
    }
    for model, prompts in plan.items():
        for pid, (base, core) in prompts.items():
            for judge in ("j1", "j2", "j3"):
                for arm, score in (("baseline", base), ("harness_core", core), ("harness_full", core - 1)):
                    records.append({
                        "model": model, "arm": arm, "prompt_id": pid, "judge": judge,
                        "score_0_100": float(score),
                        "components": {"A": score / 5, "B": score / 10, "C": score / 4,
                                       "D": score / 8, "E": score / 6},
                    })
    return records


def test_aggregate_computes_paired_lift():
    agg = aggregate(_panel_records())
    head = next(r for r in agg["per_model"] if r["model"] == "gemma4:31b")
    # baseline mean (40,50)=45, core mean (90,88)=89, lift=44, both prompts help -> win rate 1.0
    assert head["baseline"] == 45.0
    assert head["core"] == 89.0
    assert head["lift_core"] == 44.0
    assert head["win_rate"] == 1.0
    assert head["n_pair"] == 2


def test_generate_report_from_dataframe(tmp_path):
    df = pd.DataFrame(_panel_records())
    out = generate_report(df, tmp_path / "report.html", model="gemma4:31b")
    assert out.exists()
    doc = out.read_text(encoding="utf-8")
    assert out.stat().st_size > 5000
    assert "<!doctype html>" in doc
    assert 'src="data:image/png;base64,' in doc      # embedded, offline charts
    assert "gemma4:31b" in doc                        # headline model named
    assert "+44.0" in doc                             # headline lift rendered
    assert "Honest boundary" in doc                   # honest-boundary footer


def test_report_from_jsonl(tmp_path):
    panel = tmp_path / "panel.jsonl"
    with panel.open("w", encoding="utf-8") as fh:
        for rec in _panel_records():
            fh.write(json.dumps(rec) + "\n")
    out = report_from_jsonl(panel, tmp_path / "from_jsonl.html")
    assert out.exists() and out.stat().st_size > 0
    assert "<img" in out.read_text(encoding="utf-8")


def test_generate_report_falls_back_to_top_model_when_missing(tmp_path):
    df = pd.DataFrame(_panel_records())
    out = generate_report(df, tmp_path / "fallback.html", model="does-not-exist")
    # falls back to the most-covered model rather than raising
    assert out.exists()
