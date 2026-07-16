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
import math
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
PROMPTSET = _ROOT / "reports" / "benchmark" / "full_promptset.json"
OUT = _ROOT / "docs" / "research" / "full_results.md"


def _sign_test_two_sided_p(wins: int, losses: int) -> float | None:
    """Two-sided sign test over non-tied paired deltas (ties excluded).

    Exact binomial for up to 200 informative pairs; the continuity-corrected
    normal approximation beyond that. Returns None when every pair ties.
    """
    informative = wins + losses
    if informative == 0:
        return None
    if informative <= 200:
        smaller_tail = sum(math.comb(informative, k) for k in range(min(wins, losses) + 1))
        return round(min(1.0, 2.0 * smaller_tail / (2.0 ** informative)), 6)
    z = max(0.0, (abs(wins - losses) - 1)) / math.sqrt(informative)
    return round(min(1.0, math.erfc(z / math.sqrt(2))), 6)


def _wilson_95(successes: int, n: int) -> list[float] | None:
    """Wilson 95% score interval for a binomial proportion."""
    if n == 0:
        return None
    z = 1.959963984540054
    phat = successes / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    margin = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)]


def _bootstrap_ci(deltas: list[float], seed: int = 20260716) -> list[float] | None:
    """Seeded percentile bootstrap 95% interval for the mean paired delta."""
    if len(deltas) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(
        statistics.fmean(rng.choices(deltas, k=len(deltas))) for _ in range(2000)
    )
    return [round(means[49], 2), round(means[1949], 2)]


def aggregate(rows: list[dict], registry_meta: dict | None = None) -> dict:
    """rows: [{model, arm, prompt_id, score_0_100, components, judge?}] -> per-model stats.

    Pure + testable. When registry_meta maps prompt_id -> {category, corridor,
    difficulty} from the real prompt registry, per-model breakdowns are added so
    lift is reported against the actual benchmark taxonomy instead of only one
    global mean.
    """
    sc: dict = collections.defaultdict(list)
    comp: dict = collections.defaultdict(list)
    judge_sc: dict = collections.defaultdict(list)
    for r in rows:
        m, a, pid = r.get("model"), r.get("arm"), r.get("prompt_id")
        if not (m and a and pid) or not isinstance(r.get("score_0_100"), (int, float)):
            continue
        sc[(m, pid, a)].append(r["score_0_100"])
        judge = r.get("judge")
        if judge:
            judge_sc[(m, pid, a, judge)].append(r["score_0_100"])
        for k, v in (r.get("components") or {}).items():
            if isinstance(v, (int, float)):
                comp[(m, pid, a, k)].append(v)
    mean = {k: statistics.mean(v) for k, v in sc.items()}
    comp_mean = {k: statistics.mean(v) for k, v in comp.items()}
    judge_mean = {k: statistics.mean(v) for k, v in judge_sc.items()}
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
        wins = sum(1 for x in d if x > 0)
        losses = len(hurt_d)
        stats_block = {
            "sign_test_two_sided_p": _sign_test_two_sided_p(wins, losses),
            "win_rate": round(wins / (wins + losses), 4) if wins + losses else None,
            "win_rate_wilson_95": _wilson_95(wins, wins + losses),
            "lift_bootstrap_95": _bootstrap_ci(d),
            "ties_excluded": sum(1 for x in d if x == 0),
        }
        per_judge = []
        for judge in sorted({k[3] for k in judge_mean if k[0] == mdl}):
            judge_pids = sorted(
                p for p in pids
                if (mdl, p, "baseline", judge) in judge_mean
                and (mdl, p, "harness_core", judge) in judge_mean
            )
            if not judge_pids:
                continue
            jd = [
                judge_mean[(mdl, p, "harness_core", judge)]
                - judge_mean[(mdl, p, "baseline", judge)]
                for p in judge_pids
            ]
            per_judge.append({
                "judge": judge,
                "n_pair": len(jd),
                "baseline": round(statistics.mean(
                    judge_mean[(mdl, p, "baseline", judge)] for p in judge_pids
                ), 1),
                "core": round(statistics.mean(
                    judge_mean[(mdl, p, "harness_core", judge)] for p in judge_pids
                ), 1),
                "lift": round(statistics.mean(jd), 1),
                "helps": sum(1 for x in jd if x > 0),
                "hurts": sum(1 for x in jd if x < 0),
            })
        breakdowns = None
        if registry_meta is not None:
            breakdowns = {}
            for dim in ("category", "corridor", "difficulty"):
                groups: dict = collections.defaultdict(list)
                for p in sorted(bc_pids):
                    value = str((registry_meta.get(p) or {}).get(dim) or "unknown")
                    groups[value].append(
                        (mean[(mdl, p, "baseline")], mean[(mdl, p, "harness_core")])
                    )
                entries = []
                for value, pairs in groups.items():
                    group_d = [c - b for b, c in pairs]
                    entries.append({
                        "value": value,
                        "n": len(group_d),
                        "baseline": round(statistics.mean(b for b, c in pairs), 1),
                        "core": round(statistics.mean(c for b, c in pairs), 1),
                        "lift": round(statistics.mean(group_d), 1),
                        "helps": sum(1 for x in group_d if x > 0),
                        "hurts": sum(1 for x in group_d if x < 0),
                    })
                entries.sort(key=lambda e: -e["n"])
                breakdowns[dim] = entries
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
            "statistics": stats_block,
            "per_judge": per_judge,
            "breakdowns": breakdowns,
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
    if head and head.get("statistics"):
        s = head["statistics"]
        parts = []
        if s.get("lift_bootstrap_95"):
            lo, hi = s["lift_bootstrap_95"]
            parts.append(f"seeded bootstrap 95% interval for the mean lift [{lo:+}, {hi:+}]")
        if s.get("sign_test_two_sided_p") is not None:
            parts.append(f"two-sided sign test p = {s['sign_test_two_sided_p']} "
                         f"({s['ties_excluded']:,} ties excluded)")
        if s.get("win_rate") is not None and s.get("win_rate_wilson_95"):
            wl, wh = s["win_rate_wilson_95"]
            parts.append(f"win rate {100 * s['win_rate']:.1f}% with Wilson 95% interval "
                         f"[{100 * wl:.1f}%, {100 * wh:.1f}%]")
        L += ["", "## Statistical strength (real-prompt panel)", "",
              f"For `{head['model']}` baseline->core over {head['n_pair']:,} paired registry "
              "prompts: " + "; ".join(parts)
              + ". These are inferential statements about the recorded panel, "
              "not real-world detection claims.", ""]
    if head and head.get("per_judge"):
        L += ["## Per-judge robustness", "",
              "The same paired lift computed independently inside each judge's own "
              f"verdicts (`{head['model']}`):",
              "",
              "| judge | n pairs | baseline | core | lift | helps | hurts |",
              "|---|---:|---:|---:|---:|---:|---:|"]
        for j in head["per_judge"]:
            L.append(f"| `{j['judge']}` | {j['n_pair']:,} | {j['baseline']} | {j['core']} | "
                     f"{j['lift']:+} | {j['helps']:,} | {j['hurts']:,} |")
        L.append("")
    if head and head.get("breakdowns"):
        sections = (
            ("category", "## Lift by prompt category", 20),
            ("corridor", "## Lift by corridor", 15),
            ("difficulty", "## Lift by difficulty", None),
        )
        for dim, title, cap in sections:
            entries = head["breakdowns"].get(dim) or []
            if not entries:
                continue
            shown = entries[:cap] if cap else entries
            L += [title, "",
                  "Registry-taxonomy view of the same paired prompts "
                  f"(`{head['model']}`, baseline->core):",
                  "",
                  f"| {dim} | n | baseline | core | lift | helps | hurts |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
            for e in shown:
                L.append(f"| `{e['value']}` | {e['n']:,} | {e['baseline']} | {e['core']} | "
                         f"{e['lift']:+} | {e['helps']:,} | {e['hurts']:,} |")
            if cap and len(entries) > cap:
                L.append(f"\nThe remaining {len(entries) - cap:,} smaller {dim} groups are in the "
                         "machine-readable JSON published beside this report; nothing is dropped.")
            L.append("")
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


def load_registry_meta(path: Path) -> dict | None:
    """prompt_id -> {category, corridor, difficulty} from the real prompt registry."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return {
        str(p["id"]): {
            "category": p.get("category"),
            "corridor": p.get("corridor"),
            "difficulty": p.get("difficulty"),
        }
        for p in data.get("prompts", [])
        if p.get("id")
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Full-results analysis over the accumulated benchmark panel.")
    ap.add_argument("--panel", type=Path, default=PANEL)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--promptset", type=Path, default=PROMPTSET)
    ap.add_argument("--registry", type=int, default=78719)  # the full_promptset.json registry the engine grades against
    ap.add_argument("--today", default=datetime.now(timezone.utc).date().isoformat())
    args = ap.parse_args(argv)
    agg = aggregate(load_panel(args.panel), registry_meta=load_registry_meta(args.promptset))
    if not agg["per_model"]:
        print("no graded rows found in panel")
        return 1
    args.out.write_text(render(agg, args.registry, args.today), encoding="utf-8")
    json_out = args.out.with_suffix(".json")
    json_out.write_text(
        json.dumps({"generated": args.today, "registry": args.registry, **agg},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    head = next((r for r in agg["per_model"] if r["model"] == "gemma4:31b"), agg["per_model"][0])
    print(f"paired {agg['fully_paired_prompt_ids']:,}/{args.registry:,} all-arm prompts "
          f"({agg['paired_prompt_ids']:,} baseline/core; {agg['graded_prompt_ids']:,} any arm); "
          f"headline {head['model']} "
          f"{head['baseline']}->{head['core']} ({head['lift_core']:+}); hurts {head['hurts']}. -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
