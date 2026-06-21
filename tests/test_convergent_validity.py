"""Tests for scripts/convergent_validity.py -- deterministic vs LLM-judge agreement."""
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


cv = _load("convergent_validity", _ROOT / "scripts" / "convergent_validity.py")


def _means():
    """6 prompts; det lift = i*0.1, llm lift = i*0.5 (positively correlated by construction)."""
    detm, judm = {}, {}
    for i in range(6):
        pid = f"p{i}"
        detm[(pid, "baseline")] = 5.0
        detm[(pid, "harnessed")] = 5.0 + i * 0.1
        judm[(pid, "baseline")] = 4.0
        judm[(pid, "harnessed")] = 4.0 + i * 0.5
    return detm, judm


def test_pearson_and_spearman():
    assert abs(cv._pearson([1, 2, 3], [2, 4, 6]) - 1.0) < 1e-9
    assert abs(cv._spearman([1, 2, 3], [10, 20, 30]) - 1.0) < 1e-9   # monotone -> rho 1
    assert abs(cv._spearman([1, 2, 3], [30, 20, 10]) + 1.0) < 1e-9   # anti-monotone -> -1


def test_pair_means_averages_dims():
    cells = [{"prompt_id": "p", "arm": "baseline", "dim": "d1", "score": 4.0},
             {"prompt_id": "p", "arm": "baseline", "dim": "d2", "score": 6.0}]
    assert cv.pair_means(cells)[("p", "baseline")] == 5.0


def test_aligned_lift_pairs_arms():
    detm, judm = _means()
    dl, ll = cv.aligned_lift(detm, judm)
    assert len(dl) == 6
    assert dl[0] == 0.0 and round(dl[5], 1) == 0.5 and round(ll[5], 1) == 2.5


def test_sign_agreement():
    assert cv.sign_agreement([1.0, -1.0, 0.0], [1.0, -1.0, 0.0]) == 1.0
    assert cv.sign_agreement([1.0, 1.0], [-1.0, -1.0]) == 0.0


def test_analyze_reports_directional_convergence():
    detm, judm = _means()
    a = cv.analyze(detm, judm)
    assert a["n_lift"] == 6
    assert a["det_lift_mean"] > 0 and a["llm_lift_mean"] > 0 and a["both_positive"]
    assert a["lift_pearson"] > 0.9                 # correlated by construction
    assert a["bins_monotone"]                      # judge-lift rises across det-lift bins


def test_build_report_is_honest(tmp_path):
    detm, judm = _means()
    a = cv.analyze(detm, judm)
    md = cv.build_report(a, det_label="run", judge_label="judge", out_path=tmp_path / "r.md")
    assert "Convergent validity" in md and "Spearman" in md
    # the honest framing -- direction converges, graders are not interchangeable
    assert "direction" in md.lower() and "proxy" in md.lower()
