"""Full-results analysis over the accumulated benchmark panel -- the honest current read of every graded
prompt, regenerable as the sweep grows toward the 78,719-prompt registry.

It joins the panel's per-judge grades into a mean per (model, prompt_id, arm) and reports, per model: the
paired coverage, baseline / harness_core / harness_full means, the three lifts, WHERE the harness helps vs
HURTS (the negative-lift tail -- the north star), the full-vs-core comparison (the 'serve core, not full'
evidence), and the per-component lift. Coverage is stated against the full registry so the report never
implies the sweep is complete. Deterministic, offline; regenerate whenever panel.jsonl grows.

Run:
    python scripts/analyze_full_results.py                      # -> docs/research/full_results.md
    python scripts/analyze_full_results.py --registry 78719
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
OUT = _ROOT / "docs" / "research" / "full_results.md"


def aggregate(rows: list[dict]) -> dict:
    """rows: [{model, arm, prompt_id, score_0_100, components}] -> per-model stats. Pure + testable."""
    sc: dict = collections.defaultdict(list)
    comp: dict = collections.defaultdict(list)
    for r in rows:
        m, a, pid = r.get("model"), r.get("arm"), r.get("prompt_id")
        if not (m and a and pid) or not isinstance(r.get("score_0_100"), (int, float)):
            continue
        sc[(m, pid, a)].append(r["score_0_100"])
        for k, v in (r.get("components") or {}).items():
            if isinstance(v, (int, float)):
                comp[(m, pid, a, k)].append(v)
    mean = {k: statistics.mean(v) for k, v in sc.items()}
    comp_mean = {k: statistics.mean(v) for k, v in comp.items()}
    paired_prompt_ids: set[str] = set()
    fully_paired_prompt_ids: set[str] = set()
    per_model = []
    for mdl in sorted({k[0] for k in mean}):
        pids = {k[1] for k in mean if k[0] == mdl}
        bc_pids = {p for p in pids
                   if (mdl, p, "baseline") in mean and (mdl, p, "harness_core") in mean}
        bf_pids = {p for p in pids
                   if (mdl, p, "baseline") in mean and (mdl, p, "harness_full") in mean}
        cf_pids = {p for p in pids
                   if (mdl, p, "harness_core") in mean and (mdl, p, "harness_full") in mean}
        all_arm_pids = bc_pids & bf_pids & cf_pids
        paired_prompt_ids.update(bc_pids)
        fully_paired_prompt_ids.update(all_arm_pids)
        bc = [(mean[(mdl, p, "baseline")], mean[(mdl, p, "harness_core")])
              for p in sorted(bc_pids)]
        bf = [(mean[(mdl, p, "baseline")], mean[(mdl, p, "harness_full")])
              for p in sorted(bf_pids)]
        cf = [(mean[(mdl, p, "harness_core")], mean[(mdl, p, "harness_full")])
              for p in sorted(cf_pids)]
        if not bc:
            continue
        d = [c - b for b, c in bc]
        hurt_d = [x for x in d if x < 0]
        full_core_d = [f - c for c, f in cf]
        full_core_mean = statistics.mean(full_core_d) if full_core_d else None
        component_lift = {}
        component_n = {}
        component_keys = {k[3] for k in comp_mean if k[0] == mdl}
        for key in sorted(component_keys):
            component_pids = {
                p for p in bc_pids
                if (mdl, p, "baseline", key) in comp_mean
                and (mdl, p, "harness_core", key) in comp_mean
            }
            if component_pids:
                component_lift[key] = round(statistics.mean(
                    comp_mean[(mdl, p, "harness_core", key)]
                    - comp_mean[(mdl, p, "baseline", key)]
                    for p in sorted(component_pids)
                ), 2)
                component_n[key] = len(component_pids)
        per_model.append({
            "model": mdl, "n_pair": len(bc), "n_full_pair": len(bf),
            "n_core_full_pair": len(cf), "n_all_arms": len(all_arm_pids),
            "baseline": round(statistics.mean(b for b, c in bc), 1),
            "core": round(statistics.mean(c for b, c in bc), 1),
            "full": round(statistics.mean(f for b, f in bf), 1) if bf else None,
            "lift_core": round(statistics.mean(d), 1),
            "lift_full": round(statistics.mean(f - b for b, f in bf), 1) if bf else None,
            "full_minus_core": round(full_core_mean, 2) if full_core_mean is not None else None,
            "full_core_winner": ("full" if full_core_mean is not None and full_core_mean > 0
                                 else "core" if full_core_mean is not None and full_core_mean < 0
                                 else "tie" if full_core_mean is not None else None),
            "full_better": sum(1 for x in full_core_d if x > 0),
            "core_better": sum(1 for x in full_core_d if x < 0),
            "full_core_ties": sum(1 for x in full_core_d if x == 0),
            "helps": sum(1 for x in d if x > 0), "hurts": sum(1 for x in d if x < 0),
            "hurt_worst": round(min(hurt_d), 1) if hurt_d else None,
            "components": component_lift,
            "component_n": component_n,
        })
    per_model.sort(key=lambda r: -r["n_pair"])
    return {
        "per_model": per_model,
        "graded_prompt_ids": len({k[1] for k in mean}),
        "paired_prompt_ids": len(paired_prompt_ids),
        "fully_paired_prompt_ids": len(fully_paired_prompt_ids),
        "n_panel_rows": len(rows),
    }


def _full_core_conclusion(row: dict) -> str:
    """Describe the observed full-vs-core direction without assuming which arm won."""
    delta = row.get("full_minus_core")
    winner = row.get("full_core_winner")
    n_pair = row.get("n_core_full_pair", 0)
    if delta is None:
        return "harness_core and harness_full are not yet paired"
    if winner == "core" or (winner is None and delta < 0):
        return (f"full - core = {delta:+} across {n_pair:,} pairs "
                "(core outperforms full on average -- serve core, not full)")
    if winner == "full" or (winner is None and delta > 0):
        return (f"full - core = {delta:+} across {n_pair:,} pairs "
                "(full outperforms core on average; core >= full does not hold)")
    return f"full - core = {delta:+} across {n_pair:,} pairs (core and full tie on average)"


def render(agg: dict, registry: int, today: str) -> str:
    pm = agg["per_model"]
    graded = agg["graded_prompt_ids"]
    paired = agg.get("paired_prompt_ids", graded)
    fully_paired = agg.get("fully_paired_prompt_ids", 0)
    head = next((r for r in pm if r["model"] == "gemma4:31b"), pm[0] if pm else None)
    L = [f"# Full benchmark results -- current read ({today})", "",
         f"Regenerated by `scripts/analyze_full_results.py` from `reports/rich_lift/panel.jsonl`. "
         f"**Complete paired coverage: {fully_paired:,} of the {registry:,}-prompt registry have all three "
         f"arms ({100*fully_paired/registry:.1f}%)**; {paired:,} have baseline/core pairs, while {graded:,} "
         "have at least one scored arm. The sweep is accumulating; the remaining prompts need the Gemma-4-31b "
         "generation + the configured large-model judge panel on Ollama-cloud, which is credit-gated. These are "
         "the paired results available so far.", ""]
    if head:
        full_disp = (f"harness_full {head['full']} ({head['lift_full']:+}); "
                     f"{_full_core_conclusion(head)}"
                     if head["full"] is not None else "harness_full not yet graded for this model")
        hurt_disp = f" (worst {head['hurt_worst']})" if head["hurt_worst"] is not None else ""
        L += [f"**Headline (`{head['model']}`, n={head['n_pair']:,}):** baseline {head['baseline']} -> "
              f"harness_core {head['core']} (**{head['lift_core']:+}**), {full_disp}. The harness helps on "
              f"{head['helps']:,} prompts and HURTS on {head['hurts']}{hurt_disp}.", ""]
    L += ["## Per-model paired lift (0-100)", "",
          "| model | n base/core | n base/full | n core/full | n all-arm | baseline | core | full | core-base | full-base | full-core | hurts |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in pm:
        lf = f"{r['lift_full']:+}" if r["lift_full"] is not None else "n/a"
        L.append(f"| `{r['model']}` | {r['n_pair']:,} | {r['n_full_pair']:,} | "
                 f"{r['n_core_full_pair']:,} | {r['n_all_arms']:,} | {r['baseline']} | {r['core']} | "
                 f"{r['full']} | {r['lift_core']:+} | {lf} | "
                 f"{r['full_minus_core']} | {r['hurts']} |")
    if head and head["components"]:
        L += ["", f"## Per-component lift (`{head['model']}`, core - baseline)", "",
              "| A indicator | B law | C refuses | D resources | E privacy/safety |",
              "|---:|---:|---:|---:|---:|",
              "| " + " | ".join(f"{head['components'].get(k, 0):+}" for k in ("A", "B", "C", "D", "E")) + " |"]
    L += ["", "## Where it hurts (the north star)", ""]
    if head:
        help_rate = 100 * head["helps"] / head["n_pair"] if head["n_pair"] else 0.0
        L += [f"On `{head['model']}` the core harness helps {head['helps']:,} of "
              f"{head['n_pair']:,} paired prompts ({help_rate:.1f}%) and hurts {head['hurts']:,}. Among "
              f"{head['n_core_full_pair']:,} core/full pairs, core scores higher on "
              f"{head['core_better']:,}, full scores higher on {head['full_better']:,}, and "
              f"{head['full_core_ties']:,} tie. {_full_core_conclusion(head).capitalize()}."]
    L += ["Honesty caveats (rubric-scored proxy, deterministic-null-over-placebo, diverse-lens ~+12-14, "
          "English-only) are in `findings_synthesis_2026_07_10.md`; this file is the paired-coverage + "
          "raw-lift view.", ""]
    return "\n".join(L)


def load_panel(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Full-results analysis over the accumulated benchmark panel.")
    ap.add_argument("--panel", type=Path, default=PANEL)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--registry", type=int, default=78719)  # the full_promptset.json registry the engine grades against
    ap.add_argument("--today", default=datetime.now(timezone.utc).date().isoformat())
    args = ap.parse_args(argv)
    agg = aggregate(load_panel(args.panel))
    if not agg["per_model"]:
        print("no graded rows found in panel")
        return 1
    args.out.write_text(render(agg, args.registry, args.today), encoding="utf-8")
    head = next((r for r in agg["per_model"] if r["model"] == "gemma4:31b"), agg["per_model"][0])
    print(f"paired {agg['fully_paired_prompt_ids']:,}/{args.registry:,} all-arm prompts "
          f"({agg['paired_prompt_ids']:,} baseline/core; {agg['graded_prompt_ids']:,} any arm); "
          f"headline {head['model']} "
          f"{head['baseline']}->{head['core']} ({head['lift_core']:+}); hurts {head['hurts']}. -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
