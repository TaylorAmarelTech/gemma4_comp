"""Tests for scripts/benchmark_db.py -- SQLite ingest + integrity audit of the benchmark checkpoints.

Uses an in-memory database and synthetic rows with deliberately seeded defects, so the audit's
issue-detection is pinned without touching the real (gitignored) checkpoints.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

import benchmark_db as bdb  # noqa: E402


def _panel(model, pid, arm, judge, score, comp=None):
    return {"model": model, "prompt_id": pid, "arm": arm, "judge": judge,
            "score_0_100": score, "components": comp or {}}


def _res(model, pid, arm, resp):
    return {"model": model, "prompt_id": pid, "arm": arm, "response": resp}


def _seeded_conn():
    conn = bdb.connect(":memory:")
    panel = [
        _panel("m", "p1", "baseline", "j1", 40, {"A": 10, "B": 5, "C": 10, "D": 5, "E": 5}),
        _panel("m", "p1", "baseline", "j1", 41),          # duplicate judge row (same key)
        _panel("m", "porphan", "baseline", "j1", 50),     # scored, no response -> orphan panel
        _panel("m", "p2", "baseline", "j1", 150),         # score out of 0-100 range
        _panel("m", "p1", "harness_full", "j2", 88, {"A": 30}),  # A=30 > max 25 -> component OOR
        {"model": "m", "prompt_id": "bad"},               # malformed (no arm/score) -> skipped
    ]
    results = [
        _res("m", "p1", "baseline", "a substantive grounded response"),
        _res("m", "p2", "baseline", ""),                  # empty response
        _res("m", "pND", "baseline", "never scored"),     # orphan result (no panel)
        _res("m", "p1", "harness_full", "the harnessed reply"),
    ]
    stats = bdb.ingest(conn, panel=panel, results=results)
    return conn, stats


def test_ingest_counts_and_skips_malformed():
    conn, stats = _seeded_conn()
    assert stats["panel"] == 5 and stats["panel_skipped"] == 1   # the malformed row is dropped
    assert stats["results"] == 4 and stats["results_skipped"] == 0


def test_audit_flags_each_seeded_defect():
    conn, _ = _seeded_conn()
    a = bdb.audit(conn)
    assert a["dup_panel"] == 1
    assert a["empty_responses"] == 1
    assert a["orphan_panel"] == 1        # porphan/baseline has no response
    assert a["orphan_results"] == 1      # pND/baseline has no score
    assert a["score_out_of_range"] == 1
    assert a["component_out_of_range"] == 1
    assert a["n_results"] == 4


def test_clean_data_has_no_issues():
    conn = bdb.connect(":memory:")
    panel = [_panel("m", "p1", a, "j1", 80, {"A": 10, "B": 5, "C": 10, "D": 5, "E": 5})
             for a in ("baseline", "harness_core", "harness_full")]
    results = [_res("m", "p1", a, "ok response") for a in ("baseline", "harness_core", "harness_full")]
    bdb.ingest(conn, panel=panel, results=results)
    a = bdb.audit(conn)
    assert a["dup_panel"] == 0 and a["orphan_panel"] == 0 and a["orphan_results"] == 0
    assert a["empty_responses"] == 0 and a["score_out_of_range"] == 0
    assert a["complete_prompts"] == 1


def test_report_renders():
    conn, _ = _seeded_conn()
    md = bdb.build_audit_report(bdb.audit(conn))
    assert "Integrity checks" in md and "Responses per model" in md


def test_neg_lift_instances_ranks_worst_first():
    conn = bdb.connect(":memory:")
    panel = []
    for pid, base, full in [("p_neg", 60, 30), ("p_pos", 40, 90), ("p_worse", 70, 20)]:
        panel.append(_panel("m", pid, "baseline", "j1", base))
        panel.append(_panel("m", pid, "harness_full", "j1", full))
    bdb.ingest(conn, panel=panel, results=[])
    rows = bdb.neg_lift_instances(conn, limit=10)
    assert len(rows) == 2                        # only the two negative-lift prompts (p_pos excluded)
    assert rows[0]["prompt_id"] == "p_worse"     # worst (most negative) first
    assert rows[0]["lift"] == -50.0
    assert all(r["lift"] < 0 for r in rows)
