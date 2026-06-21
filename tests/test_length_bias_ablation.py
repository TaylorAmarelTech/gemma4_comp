"""Tests for scripts/length_bias_ablation.py -- OLS length/arm decomposition on synthetic data."""
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


ab = _load("length_bias_ablation", _ROOT / "scripts" / "length_bias_ablation.py")


def _rows():
    # exact linear truth: score = 5 + 0.5*(length/1000) + 2.0*arm  (within-arm length varies so the
    # OLS can separate the length term from the arm term)
    lens_b = [1500, 2000, 2500, 1800, 2200, 2600]
    lens_h = [3500, 4000, 4500, 3800, 4200, 4600]
    out = []
    for i, (lb, lh) in enumerate(zip(lens_b, lens_h)):
        out.append({"model": "m", "prompt_id": f"p{i}", "arm": "baseline",
                    "score": 5 + 0.5 * lb / 1000, "length": lb})
        out.append({"model": "m", "prompt_id": f"p{i}", "arm": "harnessed",
                    "score": 5 + 0.5 * lh / 1000 + 2.0, "length": lh})
    return out


def test_pearson_known_values():
    assert abs(ab._pearson([1, 2, 3], [2, 4, 6]) - 1.0) < 1e-9     # perfectly correlated
    assert abs(ab._pearson([1, 2, 3], [6, 4, 2]) + 1.0) < 1e-9     # perfectly anti-correlated


def test_ols_separates_length_from_harness():
    o = ab.ols_decomposition(_rows())
    assert abs(o["b_len_per1k"] - 0.5) < 0.02      # recovers the length coefficient
    assert abs(o["b_arm"] - 2.0) < 0.02            # recovers the harness effect (length held constant)
    assert abs(o["harness_attrib"] - 2.0) < 0.02
    # raw lift decomposes into length + harness parts
    assert abs(o["raw_lift"] - (o["length_attrib"] + o["harness_attrib"])) < 0.05


def test_length_matched_bands_and_pair_corr():
    bands = ab.length_matched(_rows(), n_bins=2)
    assert bands and all("baseline" in b and "harnessed" in b for b in bands)
    pair = ab.pair_length_score_corr(_rows())
    assert pair["n_pairs"] == 6                    # six baseline/harnessed pairs


def test_build_report_states_decomposition(tmp_path):
    md = ab.build_report(_rows(), out_path=tmp_path / "r.md")
    assert "length-bias ablation" in md.lower()
    assert "holding length constant" in md.lower()
    assert "OLS decomposition" in md
