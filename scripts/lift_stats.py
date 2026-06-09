"""Paired statistics for harness-lift checkpoints (pure stdlib, deterministic).

The per-cell checkpoints produced by ``harness_lift_local.py`` /
``harness_lift_opus_judge.py`` hold one row per
``(prompt_id, model, arm, dimension)``. The honest unit of analysis for
"does the harness help?" is the PROMPT, not the cell: collapse each
``(prompt, model, arm)`` to its mean score, pair baseline vs harnessed on
the same prompt, then analyze the per-prompt deltas. This module provides
that collapse plus the defensibility layer the report needs: win/loss/tie
rates, paired Cohen's d, and a seeded bootstrap CI on the mean lift.

Used by ``scripts/build_lift_report.py``; tested in
``tests/test_lift_stats.py``.
"""
from __future__ import annotations

import collections
import math
import random
from typing import Any

WIN_THRESHOLD = 0.1  # |delta| below this counts as a tie, not a win/loss.


def per_prompt_pairs(cells: list[dict[str, Any]]) -> dict[str, list[tuple[str, float, float]]]:
    """Collapse cells to per-prompt paired means.

    Returns ``{model: [(prompt_id, baseline_mean, harnessed_mean), ...]}``
    including only prompts where BOTH arms were graded for that model.
    """
    sums: dict[tuple[str, str, str], list[float]] = collections.defaultdict(list)
    for c in cells:
        try:
            sums[(str(c["model"]), str(c["prompt_id"]), str(c["arm"]))].append(float(c["score"]))
        except (KeyError, TypeError, ValueError):
            continue
    out: dict[str, list[tuple[str, float, float]]] = collections.defaultdict(list)
    prompts_by_model: dict[str, set[str]] = collections.defaultdict(set)
    for (model, pid, _arm) in sums:
        prompts_by_model[model].add(pid)
    for model, pids in sorted(prompts_by_model.items()):
        for pid in sorted(pids):
            base = sums.get((model, pid, "baseline"))
            harn = sums.get((model, pid, "harnessed"))
            if not base or not harn:
                continue
            out[model].append((pid, sum(base) / len(base), sum(harn) / len(harn)))
    return dict(out)


def win_loss_tie(deltas: list[float], *, threshold: float = WIN_THRESHOLD) -> dict[str, Any]:
    """Count prompts the harness won/lost/tied at the given delta threshold."""
    wins = sum(1 for d in deltas if d > threshold)
    losses = sum(1 for d in deltas if d < -threshold)
    ties = len(deltas) - wins - losses
    n = len(deltas) or 1
    return {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / n,
        "loss_rate": losses / n,
        "threshold": threshold,
    }


def cohens_d_paired(deltas: list[float]) -> float:
    """Paired Cohen's d: mean(delta) / sample-stdev(delta). 0.0 when undefined."""
    if len(deltas) < 2:
        return 0.0
    m = sum(deltas) / len(deltas)
    var = sum((d - m) ** 2 for d in deltas) / (len(deltas) - 1)
    sd = math.sqrt(var)
    return m / sd if sd > 1e-12 else 0.0


def bootstrap_mean_ci(
    deltas: list[float], *, n_resamples: int = 10_000, alpha: float = 0.05, seed: int = 13
) -> tuple[float, float]:
    """Seeded percentile-bootstrap CI on the mean of ``deltas``."""
    if not deltas:
        return (0.0, 0.0)
    rng = random.Random(seed)
    n = len(deltas)
    means = sorted(
        sum(deltas[rng.randrange(n)] for _ in range(n)) / n for _ in range(n_resamples)
    )
    lo_idx = int((alpha / 2) * n_resamples)
    hi_idx = min(n_resamples - 1, int((1 - alpha / 2) * n_resamples))
    return (means[lo_idx], means[hi_idx])


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolated percentile (q in 0..100) of ``values``."""
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (q / 100) * (len(xs) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


def model_stats(
    cells: list[dict[str, Any]], *, threshold: float = WIN_THRESHOLD, seed: int = 13
) -> list[dict[str, Any]]:
    """Full per-model paired-stats block, sorted by lift descending."""
    pairs = per_prompt_pairs(cells)
    out: list[dict[str, Any]] = []
    for model, rows in pairs.items():
        deltas = [h - b for (_pid, b, h) in rows]
        base_means = [b for (_pid, b, _h) in rows]
        harn_means = [h for (_pid, _b, h) in rows]
        wlt = win_loss_tie(deltas, threshold=threshold)
        lo, hi = bootstrap_mean_ci(deltas, seed=seed)
        n = len(rows) or 1
        out.append({
            "model": model,
            "n_prompts_paired": len(rows),
            "baseline_mean": sum(base_means) / n,
            "harnessed_mean": sum(harn_means) / n,
            "lift": (sum(harn_means) - sum(base_means)) / n,
            **wlt,
            "cohens_d": cohens_d_paired(deltas),
            "ci95_low": lo,
            "ci95_high": hi,
            "delta_percentiles": {
                f"p{q}": percentile(deltas, q) for q in (10, 25, 50, 75, 90)
            },
        })
    out.sort(key=lambda r: r["lift"], reverse=True)
    return out
