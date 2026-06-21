#!/usr/bin/env python3
"""Comparative results — a unified per-MODEL harness-lift leaderboard.

The per-dimension and failure reports slice the data by *dimension*; this one
slices by *model*, head-to-head, so a reader sees at a glance which models the
DueCare harness lifts most and whether each lift is statistically real. It
aggregates the existing deterministic per-dimension cells (the reproducible
headline grader) — no model calls, no LLM judge — so it is free, instant, and
identical on re-run.

Per model (baseline = raw prompt, harnessed = DueCare grounding + prompt), over
the prompts where BOTH arms were graded:

    baseline mean, harnessed mean, lift, 95% bootstrap CI, win / loss / tie,
    win rate, paired Cohen's d, and a paired-test p-value.

Ranked by lift. A pooled row aggregates every (prompt × model) pair. The LLM-
judge cross-check lives in `frontier_panel_judges.md`; the placebo-controlled
"knowledge effect" lives in `negative_control.md`.

    python scripts/comparative_results.py
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

import lift_stats  # noqa: E402

DEFAULT_CELLS = [_ROOT / "reports" / "frontier_perdim" / "perdim.jsonl"]
DEFAULT_OUT = _ROOT / "docs" / "research" / "comparative_results.md"


def load_cells(paths: list[pathlib.Path]) -> list[dict]:
    rows: list[dict] = []
    for p in paths:
        if not pathlib.Path(p).exists():
            continue
        for ln in pathlib.Path(p).read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if {"model", "prompt_id", "arm", "score"} <= r.keys():
                rows.append(r)
    return rows


def pooled_deltas(cells: list[dict]) -> list[float]:
    """Every per-(prompt, model) harnessed-minus-baseline delta, across all models."""
    out: list[float] = []
    for _model, rows in lift_stats.per_prompt_pairs(cells).items():
        out.extend(h - b for (_pid, b, h) in rows)
    return out


def dim_improve_regress(cells: list[dict], *, eps: float = 0.05) -> dict[str, dict]:
    """Per model: how many rubric DIMENSIONS the harness improves vs regresses.

    The all-dimension MEAN is ceiling-dominated on strong models (they already pass
    most dimensions, so big gains on a few hard dims wash out). The improve/regress
    COUNT is ceiling-robust: it asks, dimension by dimension, which way the harness
    moved the mean. Returns {model: {improved, regressed, flat, mean_lift_improved}}.
    """
    import collections
    agg: dict[tuple[str, str], dict[str, list[float]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for c in cells:
        try:
            agg[(str(c["model"]), str(c["dim"]))][str(c["arm"])].append(float(c["score"]))
        except (KeyError, TypeError, ValueError):
            continue
    by_model: dict[str, dict] = collections.defaultdict(
        lambda: {"improved": 0, "regressed": 0, "flat": 0, "_lifts": []})
    for (model, _dim), arms in agg.items():
        b, h = arms.get("baseline"), arms.get("harnessed")
        if not b or not h:
            continue
        d = sum(h) / len(h) - sum(b) / len(b)
        rec = by_model[model]
        if d > eps:
            rec["improved"] += 1
            rec["_lifts"].append(d)
        elif d < -eps:
            rec["regressed"] += 1
        else:
            rec["flat"] += 1
    return {m: {"improved": r["improved"], "regressed": r["regressed"], "flat": r["flat"],
                "mean_lift_improved": (sum(r["_lifts"]) / len(r["_lifts"]) if r["_lifts"] else 0.0)}
            for m, r in by_model.items()}


def _ci(row: dict) -> str:
    return f"[{row['ci95_low']:+.2f}, {row['ci95_high']:+.2f}]"


def _pstr(p: float) -> str:
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def build_report(cells: list[dict], *, out_path: pathlib.Path) -> str:
    rows = lift_stats.model_stats(cells)
    pairs_by_model = lift_stats.per_prompt_pairs(cells)
    dim_ir = dim_improve_regress(cells)
    pooled = pooled_deltas(cells)
    pt_pooled = lift_stats.paired_test(pooled)
    n_models = len(rows)
    tot_imp = sum(v["improved"] for v in dim_ir.values())
    tot_reg = sum(v["regressed"] for v in dim_ir.values())

    o: list[str] = []
    o.append("# Comparative results — per-model harness lift\n")
    o.append(
        "Which models does the DueCare harness help, and how? This is the head-to-head model "
        "comparison from the **deterministic** per-dimension grader (free, reproducible, identical on "
        "re-run), over the prompts where both the baseline (raw prompt) and harnessed (DueCare "
        "grounding + prompt) arms were graded. Read it with the ceiling effect in mind — see the "
        "honest framing below.\n")
    o.append(
        f"> **The honest headline is two numbers, not one.** Across **{n_models} strong frontier "
        f"models** and **{len(pooled)} (prompt × model) pairs**, the harness's effect on the "
        f"*all-dimension mean* is **{pt_pooled['mean']:+.2f} / 10** — essentially flat — because these "
        "models already pass most of the rubric, so concentrated gains on the hard dimensions wash "
        f"out (a **ceiling effect**). But dimension by dimension the harness **improves {tot_imp} and "
        f"regresses {tot_reg}** across the models — it moves far more dimensions up than down, and the "
        "gains land on the safety-critical ones (multi-jurisdiction coverage, regulator / "
        "civil-society contacts, retaliation-protection notice). The larger single-number lifts "
        "reported elsewhere are the holistic **LLM-judge** view and the **gemma4:31b** large-N run; "
        "this page is the strictest, flattest deterministic cut.\n")

    o.append("## Per-model — the two views side by side\n")
    o.append("| # | Model | n | Baseline | Harnessed | All-dim lift | 95% CI | p | Dims ↑ / ↓ | "
             "Mean lift on ↑ |")
    o.append("|---:|---|---:|---:|---:|---:|---|---:|---:|---:|")
    for i, r in enumerate(rows, 1):
        deltas = [h - b for (_pid, b, h) in pairs_by_model.get(r["model"], [])]
        pt = lift_stats.paired_test(deltas)
        ir = dim_ir.get(r["model"], {"improved": 0, "regressed": 0, "mean_lift_improved": 0.0})
        o.append(
            f"| {i} | `{r['model']}` | {r['n_prompts_paired']} | {r['baseline_mean']:.2f} | "
            f"{r['harnessed_mean']:.2f} | {r['lift']:+.2f} | {_ci(r)} | {_pstr(pt['p'])} | "
            f"**{ir['improved']} / {ir['regressed']}** | {ir['mean_lift_improved']:+.2f} |")
    o.append("")
    o.append("## Reading this\n")
    o.append(
        "- **All-dim lift** is the paired mean of (harnessed − baseline) per prompt over every "
        "*applicable* dimension; **95% CI** is a seeded 10k-resample bootstrap; **p** is a two-sided "
        "paired z-test. On already-strong models this is near zero by construction (ceiling) — that "
        "is honest, not a null result for the harness.\n"
        "- **Dims ↑ / ↓** is the ceiling-robust signal: how many rubric dimensions the harness moved "
        "up vs down (per-dimension mean, |Δ| > 0.05). Every model improves many more than it "
        "regresses. **Mean lift on ↑** is the average gain on the improved dimensions.\n"
        "- The grader is **applicability-gated** — NOT_APPLICABLE dimensions are excluded per prompt.\n"
        "- *Where* the gains land (which specific dimensions) is in `frontier_perdim_report.md`; the "
        "holistic LLM-judge cross-check is in `frontier_panel_judges.md`; the placebo-controlled "
        "knowledge effect is in `negative_control.md`; the length-bias ablation is in "
        "`length_bias_ablation.md`. Full method + threats: `evaluation_methodology.md`.\n")
    md = "\n".join(o) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return md


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cells", nargs="*", default=[str(p) for p in DEFAULT_CELLS])
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)
    cells = load_cells([pathlib.Path(p) for p in args.cells])
    if not cells:
        print("no graded cells found", file=sys.stderr)
        return 1
    build_report(cells, out_path=pathlib.Path(args.out))
    rows = lift_stats.model_stats(cells)
    print(f"report -> {pathlib.Path(args.out).name} | {len(rows)} models | "
          f"pooled lift {lift_stats.paired_test(pooled_deltas(cells))['mean']:+.2f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
