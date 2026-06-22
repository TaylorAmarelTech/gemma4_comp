"""Tests for scripts/robustness_checks.py -- applicability / clustering / circularity rebuttals."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


rc = _load("robustness_checks", _ROOT / "scripts" / "robustness_checks.py")


def _perdim_cells():
    # one (model, prompt): baseline scored on d1,d2; harnessed on d1,d2,d3 (response-driven extra dim)
    return [
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "dim": "d1", "score": 4.0},
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "dim": "d2", "score": 4.0},
        {"model": "m", "prompt_id": "p1", "arm": "harnessed", "dim": "d1", "score": 7.0},
        {"model": "m", "prompt_id": "p1", "arm": "harnessed", "dim": "d2", "score": 7.0},
        {"model": "m", "prompt_id": "p1", "arm": "harnessed", "dim": "d3", "score": 1.0},  # extra, low
    ]


def test_applicability_intersection_vs_per_arm():
    a = rc.applicability_check(_perdim_cells())
    # intersection (d1,d2): harnessed 7 - baseline 4 = +3.0
    assert a["lift_intersection_only"] == 3.0
    # per-arm: harnessed mean (7+7+1)/3=5.0 - baseline 4.0 = +1.0  (the extra low dim under-credits)
    assert a["lift_per_arm_applicable"] == 1.0
    assert a["mean_dims_differing"] == 1.0


def test_icc_deff_zero_when_no_between_cluster_variance():
    # identical deltas across clusters -> ICC 0, design effect 1
    groups = {"A": [1.0, 1.0, 1.0], "B": [1.0, 1.0, 1.0]}
    r = rc._icc_deff(groups)
    assert r["icc"] == 0.0 and r["deff"] == 1.0
    # strong between-cluster separation -> ICC > 0, deff > 1
    r2 = rc._icc_deff({"A": [0.0, 0.0, 0.0], "B": [5.0, 5.0, 5.0]})
    assert r2["icc"] > 0.5 and r2["deff"] > 1.5


def test_circularity_splits_injected_vs_incidental():
    cells = []
    # injected dim 'ilo_indicator_naming' improves +2; incidental 'response_quality.empathy' improves +1
    for i in range(12):
        pid = f"p{i}"
        cells += [
            {"model": "m", "prompt_id": pid, "arm": "baseline", "dim": "ilo_indicator_naming", "score": 4.0},
            {"model": "m", "prompt_id": pid, "arm": "harnessed", "dim": "ilo_indicator_naming", "score": 6.0},
            {"model": "m", "prompt_id": pid, "arm": "baseline", "dim": "response_quality.empathy", "score": 4.0},
            {"model": "m", "prompt_id": pid, "arm": "harnessed", "dim": "response_quality.empathy", "score": 5.0},
        ]
    c = rc.circularity_check(cells, min_obs=10)
    assert c["injected_n"] == 1 and c["incidental_n"] == 1
    assert c["injected_mean_lift"] == 2.0 and c["incidental_mean_lift"] == 1.0
    assert c["incidental_improving"] == 1   # the incidental dim improves -> anti-circularity evidence


def test_build_report_renders(tmp_path):
    applic = rc.applicability_check(_perdim_cells())
    cluster = {"headline_by_template": {"icc": 0.0, "deff": 1.05, "n": 100, "k": 5, "mbar": 20.0,
                                        "lift": 1.73, "ci_naive": 0.17, "ci_cluster_adj": 0.18},
               "pooled_by_model": {"icc": 0.1, "deff": 1.6, "n": 455, "k": 5, "mbar": 91.0}}
    circ = {"n_dims": 2, "injected_n": 1, "injected_mean_lift": 2.0, "incidental_n": 1,
            "incidental_mean_lift": 1.0, "incidental_improving": 1,
            "incidental_top": [("response_quality.empathy", 1.0)]}
    md = rc.build_report(applic, cluster, circ, out_path=tmp_path / "r.md")
    assert "Robustness checks" in md and "Circularity" in md and "intersection" in md.lower()
    assert "exploratory" in md.lower()   # the honest FDR caveat
