"""Tests for the paired harness-lift statistics module."""
from __future__ import annotations

import importlib
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

ls = importlib.import_module("lift_stats")


def _cell(pid: str, model: str, arm: str, dim: str, score: float) -> dict:
    return {"prompt_id": pid, "model": model, "arm": arm, "dim": dim, "score": score}


def test_per_prompt_pairs_collapses_means_and_requires_both_arms() -> None:
    cells = [
        _cell("p1", "m", "baseline", "g.a", 2.0),
        _cell("p1", "m", "baseline", "g.b", 4.0),
        _cell("p1", "m", "harnessed", "g.a", 8.0),
        _cell("p2", "m", "baseline", "g.a", 5.0),  # no harnessed arm -> dropped
        _cell("p3", "other", "harnessed", "g.a", 9.0),  # no baseline -> dropped
    ]
    pairs = ls.per_prompt_pairs(cells)
    assert pairs == {"m": [("p1", 3.0, 8.0)]}


def test_per_prompt_pairs_skips_malformed_cells() -> None:
    cells = [
        _cell("p1", "m", "baseline", "g.a", 2.0),
        _cell("p1", "m", "harnessed", "g.a", 6.0),
        {"prompt_id": "p1", "model": "m", "arm": "baseline", "score": None},
        {"model": "m", "arm": "harnessed", "score": 5.0},
    ]
    pairs = ls.per_prompt_pairs(cells)
    assert pairs["m"] == [("p1", 2.0, 6.0)]


def test_win_loss_tie_threshold_behaviour() -> None:
    wlt = ls.win_loss_tie([2.0, 0.05, -0.05, -2.0, 0.2], threshold=0.1)
    assert wlt["wins"] == 2
    assert wlt["losses"] == 1
    assert wlt["ties"] == 2
    assert abs(wlt["win_rate"] - 0.4) < 1e-9


def test_cohens_d_paired_known_value() -> None:
    # deltas mean=2, sample stdev=1 -> d=2
    assert abs(ls.cohens_d_paired([1.0, 2.0, 3.0]) - 2.0) < 1e-9
    assert ls.cohens_d_paired([5.0]) == 0.0
    assert ls.cohens_d_paired([2.0, 2.0, 2.0]) == 0.0  # zero variance guard


def test_bootstrap_ci_is_deterministic_and_brackets_mean() -> None:
    deltas = [1.0, 2.0, 3.0, 4.0, 5.0]
    lo1, hi1 = ls.bootstrap_mean_ci(deltas, n_resamples=2000, seed=13)
    lo2, hi2 = ls.bootstrap_mean_ci(deltas, n_resamples=2000, seed=13)
    assert (lo1, hi1) == (lo2, hi2)
    assert lo1 <= 3.0 <= hi1
    assert ls.bootstrap_mean_ci([]) == (0.0, 0.0)


def test_percentile_interpolates() -> None:
    xs = [0.0, 10.0]
    assert ls.percentile(xs, 50) == 5.0
    assert ls.percentile(xs, 0) == 0.0
    assert ls.percentile(xs, 100) == 10.0
    assert ls.percentile([], 50) == 0.0
    assert ls.percentile([7.0], 90) == 7.0


def test_model_stats_full_block() -> None:
    cells = []
    # model "up": deltas +2 on three prompts
    for pid, b in (("p1", 3.0), ("p2", 4.0), ("p3", 5.0)):
        cells.append(_cell(pid, "up", "baseline", "g.a", b))
        cells.append(_cell(pid, "up", "harnessed", "g.a", b + 2.0))
    # model "flat": no lift
    for pid in ("p1", "p2"):
        cells.append(_cell(pid, "flat", "baseline", "g.a", 5.0))
        cells.append(_cell(pid, "flat", "harnessed", "g.a", 5.0))
    stats = ls.model_stats(cells, seed=7)
    assert [s["model"] for s in stats] == ["up", "flat"]
    up = stats[0]
    assert up["n_prompts_paired"] == 3
    assert abs(up["lift"] - 2.0) < 1e-9
    assert up["wins"] == 3 and up["losses"] == 0
    assert up["win_rate"] == 1.0
    assert up["ci95_low"] <= up["lift"] <= up["ci95_high"]
    assert up["delta_percentiles"]["p50"] == 2.0
    flat = stats[1]
    assert flat["lift"] == 0.0
    assert flat["ties"] == 2
