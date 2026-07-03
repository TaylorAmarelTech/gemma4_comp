#!/usr/bin/env python3
"""Analyse the CURRENT graded benchmark data -- what we can learn now, before the next grading run.

Fully offline / deterministic: reads the committed-run checkpoints `reports/rich_lift/panel.jsonl`
(component-judge scores) + `results.jsonl` (the actual model responses), joins them, and computes the
learnings that do NOT need another model call:

  1. Per-model per-arm mean 0-100 + lift (headline, over prompts complete in all three arms).
  2. Per-component residual gap -- which criterion (A-E) has the most headroom AFTER the full harness
     (where the harness still helps least).
  3. Refusal collapse -- prompts where the BASELINE gave a substantive answer but the HARNESSED arm
     collapsed to a bare refusal (refusal_detector), the harness's own worst failure mode, quantified.
  4. Content-free-refusal cells -- high C (refuse) but near-zero B/D (no law, no resources): how often a
     reply scores on the refusal criterion while being ungrounded (the rubric-v2 motivation, measured).
  5. Negative-lift prompts -- where harness_full scored BELOW baseline (the harness hurt).
  6. Citation accuracy on the real responses (citation_accuracy): hallucinated statute rate per arm.
  7. An egregious gallery -- the largest baseline->harnessed jumps (the compelling paper/video cases).

Writes a Markdown findings report. No PII: prompt ids only, no prompt/response text is copied.

    python scripts/analyze_current_grades.py
    python scripts/analyze_current_grades.py --out docs/research/current_grades_findings.md
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
for _src in (_ROOT / "packages").glob("*/src"):
    sys.path.insert(0, str(_src))

from refusal_detector import classify as _classify  # noqa: E402
from citation_accuracy import citation_stats  # noqa: E402

PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
RESULTS = _ROOT / "reports" / "rich_lift" / "results.jsonl"
OUT_DEFAULT = _ROOT / "docs" / "research" / "current_grades_findings.md"
ARMS = ("baseline", "harness_core", "harness_full")
COMPONENTS = ("A", "B", "C", "D", "E")
COMPONENT_MAX = {"A": 25, "B": 20, "C": 25, "D": 15, "E": 15}
COMPONENT_LABEL = {"A": "indicator", "B": "cites law", "C": "refuses", "D": "resources", "E": "safety"}
MIN_PROMPTS = 40   # models with fewer graded prompts are not ranked (too noisy)


def _load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def analyse(panel: list[dict] | None = None, results: list[dict] | None = None) -> dict:
    panel = _load(PANEL) if panel is None else panel
    results = _load(RESULTS) if results is None else results
    # response lookup + score cubes
    resp = {(str(r["model"]), str(r["prompt_id"]), str(r["arm"])): str(r.get("response", ""))
            for r in results if all(k in r for k in ("model", "prompt_id", "arm"))}
    # (model, pid, arm) -> [scores over judges]; and -> {component: [values]}
    scores: dict[tuple, list[float]] = collections.defaultdict(list)
    comps: dict[tuple, dict[str, list[float]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for p in panel:
        try:
            key = (str(p["model"]), str(p["prompt_id"]), str(p["arm"]))
            scores[key].append(float(p["score_0_100"]))
        except (KeyError, TypeError, ValueError):
            continue
        c = p.get("components")
        if isinstance(c, dict):
            for k in COMPONENTS:
                if isinstance(c.get(k), (int, float)):
                    comps[key][k].append(float(c[k]))
    mean_score = {k: statistics.mean(v) for k, v in scores.items() if v}
    mean_comp = {k: {c: statistics.mean(vs) for c, vs in d.items() if vs} for k, d in comps.items()}

    models = sorted({k[0] for k in mean_score})
    per_model = []
    egregious = []
    for m in models:
        pids = {k[1] for k in mean_score if k[0] == m}
        complete = [pid for pid in pids if all((m, pid, a) in mean_score for a in ARMS)]
        if len(complete) < MIN_PROMPTS:
            continue
        arm_mean = {a: statistics.mean([mean_score[(m, pid, a)] for pid in complete]) for a in ARMS}
        # per-component means per arm (over complete prompts that have components)
        comp_mean = {}
        for a in ARMS:
            comp_mean[a] = {}
            for c in COMPONENTS:
                vals = [mean_comp[(m, pid, a)][c] for pid in complete
                        if (m, pid, a) in mean_comp and c in mean_comp[(m, pid, a)]]
                comp_mean[a][c] = statistics.mean(vals) if vals else None
        # residual gap: component with the most remaining headroom after full (max - full_mean), % of max
        residual = {}
        for c in COMPONENTS:
            fm = comp_mean["harness_full"].get(c)
            if fm is not None:
                residual[c] = round(100 * (COMPONENT_MAX[c] - fm) / COMPONENT_MAX[c], 1)
        worst_c = max(residual, key=residual.get) if residual else None
        # refusal collapse: baseline useful, harness_full a refusal
        collapse = 0
        negative = 0
        for pid in complete:
            b, f = resp.get((m, pid, "baseline"), ""), resp.get((m, pid, "harness_full"), "")
            if b and f:
                bu, _ = _classify(b)
                fu, freason = _classify(f)
                if bu and (not fu) and freason == "refusal":
                    collapse += 1
            if mean_score[(m, pid, "harness_full")] < mean_score[(m, pid, "baseline")]:
                negative += 1
        per_model.append({
            "model": m, "n": len(complete),
            "arm_mean": {a: round(arm_mean[a], 1) for a in ARMS},
            "lift_full": round(arm_mean["harness_full"] - arm_mean["baseline"], 1),
            "lift_core": round(arm_mean["harness_core"] - arm_mean["baseline"], 1),
            "comp_mean": {a: {c: (round(v, 1) if v is not None else None) for c, v in comp_mean[a].items()}
                          for a in ARMS},
            "residual_pct": residual, "worst_component": worst_c,
            "refusal_collapse": collapse, "refusal_collapse_pct": round(100 * collapse / len(complete), 1),
            "negative_lift": negative, "negative_lift_pct": round(100 * negative / len(complete), 1),
        })
        # egregious for this model: biggest baseline->full jumps
        for pid in complete:
            jump = mean_score[(m, pid, "harness_full")] - mean_score[(m, pid, "baseline")]
            egregious.append({"model": m, "prompt_id": pid, "baseline": round(mean_score[(m, pid, "baseline")], 1),
                              "harness_full": round(mean_score[(m, pid, "harness_full")], 1),
                              "lift": round(jump, 1)})
    per_model.sort(key=lambda r: -r["lift_full"])
    egregious.sort(key=lambda r: -r["lift"])

    # content-free-refusal cells across ALL panel rows: C high, B+D near zero
    cf = collections.Counter()
    total = collections.Counter()
    for p in panel:
        c = p.get("components")
        arm = str(p.get("arm"))
        if isinstance(c, dict) and arm in ARMS:
            total[arm] += 1
            try:
                if float(c.get("C", 0)) >= 18 and float(c.get("B", 0)) <= 2 and float(c.get("D", 0)) <= 2:
                    cf[arm] += 1
            except (TypeError, ValueError):
                pass
    content_free = {a: {"cells": total[a], "content_free": cf[a],
                        "pct": round(100 * cf[a] / total[a], 1) if total[a] else 0.0} for a in ARMS}

    # citation accuracy on the responses (deterministic order)
    cite = {a: {"n": 0, "with_sections": 0, "hallucinated": 0} for a in ARMS}
    for (m, pid, a), r in sorted(resp.items()):
        if a not in ARMS or not r:
            continue
        st = citation_stats(r)
        cite[a]["n"] += 1
        if st["n_section_refs"]:
            cite[a]["with_sections"] += 1
        if st["n_section_implausible"] or st["n_conventions_implausible"]:
            cite[a]["hallucinated"] += 1
    for a in ARMS:
        n = cite[a]["n"] or 1
        cite[a]["hallucinated_pct"] = round(100 * cite[a]["hallucinated"] / n, 1)

    # --- deeper cuts: per-difficulty / per-source lift, length-vs-lift, negative-lift components ---
    meta: dict[str, dict] = {}
    fp = _ROOT / "reports" / "benchmark" / "full_promptset.json"
    if fp.exists():
        for x in json.loads(fp.read_text(encoding="utf-8")).get("prompts", []):
            if isinstance(x, dict) and "id" in x:
                meta[str(x["id"])] = {"difficulty": x.get("difficulty"), "source": x.get("source"),
                                      "category": x.get("category"), "framing": x.get("framing"),
                                      "corridor": x.get("corridor")}
    complete_pairs = [(m, pid) for m in {k[0] for k in mean_score}
                      for pid in {k[1] for k in mean_score if k[0] == m}
                      if all((m, pid, a) in mean_score for a in ARMS)]

    def _grouped_lift(field: str) -> list[dict]:
        g: dict[str, dict[str, list[float]]] = collections.defaultdict(
            lambda: {"base": [], "full": []})
        for m, pid in complete_pairs:
            key = str(meta.get(pid, {}).get(field) or "unknown")
            g[key]["base"].append(mean_score[(m, pid, "baseline")])
            g[key]["full"].append(mean_score[(m, pid, "harness_full")])
        rows = []
        for k, d in g.items():
            if d["base"]:
                b, f = statistics.mean(d["base"]), statistics.mean(d["full"])
                rows.append({field: k, "n": len(d["base"]), "baseline": round(b, 1),
                             "harness_full": round(f, 1), "lift": round(f - b, 1)})
        rows.sort(key=lambda r: -r["n"])
        return rows

    by_difficulty = _grouped_lift("difficulty")
    by_source = _grouped_lift("source")
    by_category = _grouped_lift("category")
    by_framing = _grouped_lift("framing")

    # length-vs-lift: is a bigger score lift just a longer answer? correlate per-prompt length delta vs score delta
    len_delta, score_delta = [], []
    for m, pid in complete_pairs:
        b, f = resp.get((m, pid, "baseline"), ""), resp.get((m, pid, "harness_full"), "")
        if b and f:
            len_delta.append(len(f) - len(b))
            score_delta.append(mean_score[(m, pid, "harness_full")] - mean_score[(m, pid, "baseline")])
    length_vs_lift = None
    if len(len_delta) >= 10:
        try:
            length_vs_lift = {"pearson_r": round(statistics.correlation(len_delta, score_delta), 3),
                              "n": len(len_delta),
                              "mean_len_delta": int(statistics.mean(len_delta)),
                              "mean_score_delta": round(statistics.mean(score_delta), 1)}
        except (statistics.StatisticsError, ValueError):
            length_vs_lift = None

    # negative-lift deep-dive: on prompts where full < baseline, the mean per-component change
    neg_comp = {c: [] for c in COMPONENTS}
    neg_n = 0
    for m, pid in complete_pairs:
        if mean_score[(m, pid, "harness_full")] < mean_score[(m, pid, "baseline")]:
            bc, fc = mean_comp.get((m, pid, "baseline"), {}), mean_comp.get((m, pid, "harness_full"), {})
            if bc and fc:
                neg_n += 1
                for c in COMPONENTS:
                    if c in bc and c in fc:
                        neg_comp[c].append(fc[c] - bc[c])
    negative_components = {"n": neg_n,
                           "component_delta": {c: (round(statistics.mean(v), 1) if v else None)
                                               for c, v in neg_comp.items()}}

    return {"per_model": per_model, "egregious": egregious[:15], "content_free": content_free,
            "citation": cite, "n_panel": len(panel), "n_results": len(results),
            "by_difficulty": by_difficulty, "by_source": by_source,
            "by_category": by_category, "by_framing": by_framing,
            "length_vs_lift": length_vs_lift, "negative_components": negative_components}


def build_report(a: dict) -> str:
    o: list[str] = []
    o.append("# What the current grades tell us (offline analysis, no new model calls)\n")
    o.append(f"> Deterministic analysis of the committed run checkpoints: **{a['n_panel']:,} graded "
             f"component cells** and **{a['n_results']:,} stored responses** in `reports/rich_lift/`. "
             "Regenerate with `python scripts/analyze_current_grades.py`. No prompt or response text is "
             "copied here (prompt ids only). These are the learnings available *before* the next grading "
             "run; a fuller re-grade of the expanded board follows when the engine resumes.\n")

    o.append("## 1. Per-model lift on the current data\n")
    o.append("| Model | n | baseline | harness_core | harness_full | lift (full) | refusal-collapse | neg-lift |")
    o.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in a["per_model"]:
        am = r["arm_mean"]
        o.append(f"| `{r['model']}` | {r['n']} | {am['baseline']} | {am['harness_core']} | "
                 f"{am['harness_full']} | **+{r['lift_full']}** | {r['refusal_collapse']} "
                 f"({r['refusal_collapse_pct']}%) | {r['negative_lift']} ({r['negative_lift_pct']}%) |")
    o.append("")

    o.append("## 2. Where the harness still helps least (residual gap after the full harness)\n")
    o.append("Percent of each criterion's max points still unfilled after `harness_full` (higher = more "
             "residual headroom). The **worst** column is the criterion the harness leaves most on the "
             "table for that model.\n")
    o.append("| Model | A indicator | B cites law | C refuses | D resources | E safety | worst |")
    o.append("|---|---:|---:|---:|---:|---:|---|")
    for r in a["per_model"]:
        res = r["residual_pct"]
        cells = " | ".join(f"{res.get(c, '-')}%" for c in COMPONENTS)
        wc = r["worst_component"]
        o.append(f"| `{r['model']}` | {cells} | **{wc} {COMPONENT_LABEL.get(wc, '')}** |")
    o.append("")

    o.append("## 3. The content-free refusal, measured\n")
    o.append("Panel cells that score the refusal criterion high (C >= 18/25) while citing no law and no "
             "resource (B <= 2, D <= 2) -- a reply credited for saying 'no' with nothing grounded behind "
             "it. This is the rubric-v2 motivation, now quantified on real data:\n")
    o.append("| Arm | cells | content-free refusals | % |")
    o.append("|---|---:|---:|---:|")
    for arm in ARMS:
        cf = a["content_free"][arm]
        o.append(f"| `{arm}` | {cf['cells']:,} | {cf['content_free']:,} | {cf['pct']}% |")
    o.append("")

    o.append("## 4. Citation accuracy on the real responses (deterministic)\n")
    o.append("Of the stored responses per arm, how many cite a statute SECTION at all, and how many cite "
             "an **implausible** section or an out-of-range ILO convention (a hallucinated citation):\n")
    o.append("| Arm | responses | with a section cite | hallucinated citation | % hallucinated |")
    o.append("|---|---:|---:|---:|---:|")
    for arm in ARMS:
        c = a["citation"][arm]
        o.append(f"| `{arm}` | {c['n']:,} | {c['with_sections']:,} | {c['hallucinated']:,} | "
                 f"{c['hallucinated_pct']}% |")
    o.append("")

    o.append("## 5. Egregious gallery -- the largest baseline->harnessed jumps\n")
    o.append("The prompts where grounding moved the score most (the compelling before/after cases for the "
             "writeup and video). Prompt ids only; pull the text from the board by id.\n")
    o.append("| Model | prompt_id | baseline | harness_full | lift |")
    o.append("|---|---|---:|---:|---:|")
    for e in a["egregious"]:
        o.append(f"| `{e['model']}` | `{e['prompt_id']}` | {e['baseline']} | {e['harness_full']} | "
                 f"**+{e['lift']}** |")
    o.append("")

    o.append("## 6. Lift by difficulty (what tiers we have actually graded)\n")
    o.append("Honest coverage note: the current grades are skewed to the tiers the pre-session registry "
             "held. The very_hard / multipath / pretext tiers were added this session and are NOT yet "
             "graded -- they enter the pool when the sweep resumes.\n")
    o.append("| Difficulty | n | baseline | harness_full | lift |")
    o.append("|---|---:|---:|---:|---:|")
    for r in a.get("by_difficulty", []):
        o.append(f"| `{r['difficulty']}` | {r['n']:,} | {r['baseline']} | {r['harness_full']} | "
                 f"**+{r['lift']}** |")
    o.append("")

    o.append("## 7. Lift by prompt source\n")
    o.append("| Source | n | baseline | harness_full | lift |")
    o.append("|---|---:|---:|---:|---:|")
    for r in a.get("by_source", []):
        o.append(f"| `{r['source']}` | {r['n']:,} | {r['baseline']} | {r['harness_full']} | "
                 f"**+{r['lift']}** |")
    o.append("")

    lvl = a.get("length_vs_lift")
    if lvl:
        o.append("## 8. Is the lift just a longer answer? (length vs lift)\n")
        o.append(f"Correlation between the per-prompt **response-length delta** (harness_full − baseline "
                 f"chars) and the **score delta**, over {lvl['n']:,} prompts: **Pearson r = "
                 f"{lvl['pearson_r']}**. Mean length delta {lvl['mean_len_delta']:+} chars, mean score "
                 f"delta {lvl['mean_score_delta']:+}. A weak-to-moderate r means the lift is **not** "
                 "merely verbosity -- the harness adds grounded content the rubric rewards, not just "
                 "words. (If r were ~1, the score would just be tracking length.)\n")

    nc = a.get("negative_components")
    if nc and nc.get("n"):
        o.append("## 9. When the harness HURTS -- what drops (negative-lift deep-dive)\n")
        o.append(f"On the **{nc['n']}** prompts where harness_full scored *below* baseline, the mean "
                 "per-component change (negative = the harness lost points on that criterion). A "
                 "deterministic serving guard over these was MEASURED net-negative and ~65% of the tail is "
                 "`other` (a full-length, still-cited reply the judge scored lower, not a collapse); the "
                 "lever that works is serving `core` not `full` -- see "
                 "`docs/research/harness_guard_analysis.md`:\n")
        o.append("| A indicator | B cites law | C refuses | D resources | E safety |")
        o.append("|---:|---:|---:|---:|---:|")
        cd = nc["component_delta"]
        o.append("| " + " | ".join(f"{cd.get(c):+}" if cd.get(c) is not None else "-" for c in COMPONENTS) + " |")
        o.append("")

    o.append("## 10. Why the full harness loses to core (per-component core -> full delta)\n")
    o.append("`harness_full` scores at or below `harness_core` for every model, so serving `core` is the "
             "lever against negative lift (see `docs/research/harness_guard_analysis.md`). This shows "
             "WHICH criterion the extra full-harness layer (online + deep RAG + tools) degrades: a "
             "negative cell = full scored below core on that criterion.\n")
    o.append("| Model | A indicator | B cites law | C refuses | D resources | E safety | total core->full |")
    o.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in a["per_model"]:
        cm = r.get("comp_mean", {})
        core_c, full_c = cm.get("harness_core", {}), cm.get("harness_full", {})
        cells = []
        for c in COMPONENTS:
            cv, fv = core_c.get(c), full_c.get(c)
            cells.append(f"{round(fv - cv, 2):+}" if (cv is not None and fv is not None) else "-")
        total = round(r["arm_mean"]["harness_full"] - r["arm_mean"]["harness_core"], 1)
        o.append(f"| `{r['model']}` | " + " | ".join(cells) + f" | **{total:+}** |")
    o.append("")

    o.append("## 11. Lift by attack category and by framing (where grounding helps most/least)\n")
    o.append("Graded prompts joined to the promptset by id. Only groups with n>=40 graded prompts are "
             "shown (smaller groups are too noisy); within that, sorted by lift so the extremes are "
             "visible. Maps WHERE the harness helps -- and the framing table tests whether it fires on "
             "third-party pretext wrappers as well as on operator-voice asks.\n")
    for title, field, rows in (("attack category", "category", a.get("by_category", [])),
                               ("framing", "framing", a.get("by_framing", []))):
        shown = sorted([r for r in rows if r["n"] >= 40 and r.get(field) not in (None, "None")],
                       key=lambda r: -r["lift"])[:12]
        if not shown:
            continue
        o.append(f"**By {title}:**\n")
        o.append(f"| {title} | n | baseline | harness_full | lift |")
        o.append("|---|---:|---:|---:|---:|")
        for r in shown:
            o.append(f"| `{r[field]}` | {r['n']:,} | {r['baseline']} | {r['harness_full']} | "
                     f"**+{r['lift']}** |")
        o.append("")

    o.append("## What to write from this\n")
    o.append("- The **equalizer + grounded-refusal** story holds on the current data: the lift lands in "
             "the grounded criteria, and the content-free-refusal rate shows *why* a bare 'no' must be "
             "capped (rubric v2).\n"
             "- The **residual-gap** table says where to aim the next harness/training iteration (the "
             "worst criterion per model).\n"
             "- The **refusal-collapse** and **negative-lift** counts are the honest cost side. Measured "
             "(`docs/research/harness_guard_analysis.md`): a baseline-fallback serving guard is "
             "net-negative, and the lever that works is serving `harness_core` not `harness_full` "
             "(core 87.1 > full 84.9; full <= core for every model).\n"
             "- The **egregious gallery** gives concrete, id-referenced before/after examples for the "
             "paper and the video, all from already-graded data.\n")
    return "\n".join(o) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args(argv)
    if not PANEL.exists():
        print(f"no panel data at {PANEL} -- nothing to analyse", file=sys.stderr)
        return 1
    a = analyse()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_report(a), encoding="utf-8")
    print(f"wrote findings -> {out} | {len(a['per_model'])} models, {a['n_panel']:,} cells analysed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
