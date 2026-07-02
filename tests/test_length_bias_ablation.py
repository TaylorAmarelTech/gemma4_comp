"""Tests for scripts/length_bias_ablation.py -- OLS length/arm decomposition on synthetic data."""
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


ab = _load("length_bias_ablation", _ROOT / "scripts" / "length_bias_ablation.py")


def _rows():
    # exact linear truth: score = 5 + 0.5*(length/1000) + 2.0*arm  (within-arm length varies so the
    # OLS can separate the length term from the arm term). cite_density varies independently so the
    # citation-density covariate is identifiable.
    lens_b = [1500, 2000, 2500, 1800, 2200, 2600]
    lens_h = [3500, 4000, 4500, 3800, 4200, 4600]
    cd_b = [0.5, 1.0, 0.7, 1.2, 0.9, 0.6]
    cd_h = [2.0, 2.5, 2.2, 1.8, 2.4, 2.1]
    out = []
    for i, (lb, lh) in enumerate(zip(lens_b, lens_h)):
        out.append({"model": "m", "prompt_id": f"p{i}", "arm": "baseline",
                    "score": 5 + 0.5 * lb / 1000, "length": lb, "cite_density": cd_b[i]})
        out.append({"model": "m", "prompt_id": f"p{i}", "arm": "harnessed",
                    "score": 5 + 0.5 * lh / 1000 + 2.0, "length": lh, "cite_density": cd_h[i]})
    return out


def test_citation_density_counts_legal_markers():
    assert ab._citation_density("ILO C181 and the Palermo Protocol cover forced labour.") > 0
    assert ab._citation_density("Just pay the fee and don't worry about it.") == 0.0


def test_load_skips_malformed_non_object_and_non_string_response_rows(tmp_path):
    path = tmp_path / "results.jsonl"
    sensitive = "worker@example.com case-123456789"
    rows = [
        {"model": "m", "prompt_id": "p1", "arm": "baseline", "score": 4.0, "response": "safe reply"},
        [sensitive],
        sensitive,
        {"model": "m", "prompt_id": "p2", "arm": "harnessed", "score": 5.0, "response": [sensitive]},
        {"model": "m", "prompt_id": "p3", "arm": "other", "score": 5.0, "response": "wrong arm"},
        "{bad json",
    ]
    path.write_text("\n".join(json.dumps(r) if not isinstance(r, str) or r.startswith("worker") else r
                              for r in rows) + "\n", encoding="utf-8")

    out = ab.load([path])

    assert out == [{"model": "m", "prompt_id": "p1", "arm": "baseline", "score": 4.0,
                    "length": 10, "cite_density": 0.0}]
    assert sensitive not in json.dumps(out)


def test_load_cells_skips_malformed_and_non_object_rows(tmp_path):
    responses = tmp_path / "responses.jsonl"
    judge = tmp_path / "judge.jsonl"
    sensitive = "worker@example.com case-123456789"
    responses.write_text(
        "\n".join(json.dumps(r) for r in [
            {"prompt_id": "p1", "arm": "baseline", "response": "safe reply"},
            [sensitive],
            sensitive,
            {"prompt_id": "p2", "arm": "harnessed", "response": [sensitive]},
        ]) + "\n",
        encoding="utf-8",
    )
    judge.write_text(
        "\n".join(json.dumps(r) for r in [
            {"model": "m", "prompt_id": "p1", "arm": "baseline", "score": 4.0},
            [sensitive],
            sensitive,
            {"model": "m", "prompt_id": "p2", "arm": "harnessed", "score": "bad"},
        ]) + "\n",
        encoding="utf-8",
    )

    out = ab.load_cells(judge, responses)

    assert out == [{"model": "m", "prompt_id": "p1", "arm": "baseline", "score": 4.0,
                    "length": 10, "cite_density": 0.0}]
    assert sensitive not in json.dumps(out)


def test_ols_full_recovers_arm_with_citation_held_constant():
    o = ab.ols_full(_rows())
    # truth has no citation effect, so the arm coefficient should still recover ~2.0
    assert abs(o["b_arm"] - 2.0) < 0.1 and o["d_cite"] > 0


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


def test_analysis_helpers_skip_malformed_direct_rows_without_leaking():
    sensitive = "worker@example.com case-123456789"
    rows = _rows() + [
        sensitive,
        [sensitive],
        {"model": "m", "prompt_id": "p-bad", "arm": "baseline", "score": "bad",
         "length": 1000, "cite_density": 0.0},
        {"model": "m", "prompt_id": "p-bad2", "arm": "baseline", "score": 1.0,
         "length": -10, "cite_density": 0.0},
    ]

    o = ab.ols_decomposition(rows)
    pair = ab.pair_length_score_corr(rows)
    bands = ab.length_matched(rows, n_bins=2)

    assert abs(o["b_arm"] - 2.0) < 0.02
    assert pair["n_pairs"] == 6
    assert bands
    assert sensitive not in json.dumps({"ols": o, "pair": pair, "bands": bands})


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


def test_main_redacts_sensitive_output_name(tmp_path, capsys):
    sensitive = "worker@example.com-case-123456789"
    results = tmp_path / "results.jsonl"
    out = tmp_path / f"{sensitive}.md"
    rows = [
        {"model": r["model"], "prompt_id": r["prompt_id"], "arm": r["arm"], "score": r["score"],
         "response": "x" * r["length"]}
        for r in _rows()
    ]
    results.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    assert ab.main(["--frontier-only", "--results", str(results), "--out", str(out)]) == 0

    err = capsys.readouterr().err
    assert "report -> redacted" in err
    assert sensitive not in err
    assert out.exists()
