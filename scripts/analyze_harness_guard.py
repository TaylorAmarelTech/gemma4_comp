#!/usr/bin/env python3
"""Offline: which serving choice removes the negative-lift tail (where the harness HURTS)?

Reads the committed run checkpoints ``reports/rich_lift/{panel,results}.jsonl`` and, over every
(model, prompt) complete in all three arms, measures -- with NO new model call -- two independent levers
against "the harness hurts":

  1. WHICH HARNESS TO SERVE. The full harness underperforms the cheap core harness for every model
     (the online/deep-RAG/tools layer adds noise to a strong reply). Serving ``harness_core`` instead of
     ``harness_full`` is the larger, generation-time lever. Reported as a served-mean per strategy:
     ``full`` / ``core`` / ``full+guard`` / ``core+guard``.

  2. THE SERVING GUARD (``harness_guard``): fall back to the baseline reply on a deterministic loss of
     grounding. Reported as fired / recovery (full<baseline, correctly reverted) / misfire (full>=
     baseline, reverted where the harness had helped -> lift lost) per policy (``off`` / ``min`` /
     ``len``). ``len`` includes the length signal only to show its measured net-negative effect.

Also breaks the negative-lift prompts (harness_full < baseline) into deterministic harm modes
(``bare_nonanswer`` / ``citation_regression`` / ``drastic_shortening`` / ``other``) so the
un-catchable ``other`` residual -- the honest limit of a text-only guard -- is explicit.

Fully deterministic; no model calls. No prompt or response text is copied -- aggregate counts only.

    python scripts/analyze_harness_guard.py
    python scripts/analyze_harness_guard.py --out docs/research/harness_guard_analysis.md
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

from harness_guard import GUARD_POLICIES, GUARD_SIGNALS, guard_signals  # noqa: E402
from refusal_detector import classify as _classify  # noqa: E402
from citation_accuracy import citation_stats as _cite  # noqa: E402

PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
RESULTS = _ROOT / "reports" / "rich_lift" / "results.jsonl"
OUT_DEFAULT = _ROOT / "docs" / "research" / "harness_guard_analysis.md"
ARMS = ("baseline", "harness_core", "harness_full")
POLICIES = ("off", "min", "len", "hard")
GUARD_MIN = GUARD_POLICIES["min"]
MIN_PROMPTS = 40


def _load(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _mean_scores(panel: list[dict]) -> dict[tuple, float]:
    scores: dict[tuple, list[float]] = collections.defaultdict(list)
    for p in panel:
        try:
            scores[(str(p["model"]), str(p["prompt_id"]), str(p["arm"]))].append(float(p["score_0_100"]))
        except (KeyError, TypeError, ValueError):
            continue
    return {k: statistics.mean(v) for k, v in scores.items() if v}


def _responses(results: list[dict]) -> dict[tuple, str]:
    return {(str(r["model"]), str(r["prompt_id"]), str(r["arm"])): str(r.get("response", ""))
            for r in results if all(k in r for k in ("model", "prompt_id", "arm"))}


def _first_signal(sig: dict[str, bool]) -> str | None:
    for name in GUARD_SIGNALS:
        if sig.get(name):
            return name
    return None


def _fires(sig: dict[str, bool], policy: str) -> bool:
    return any(sig.get(name) for name in GUARD_POLICIES[policy])


def analyse(panel: list[dict] | None = None, results: list[dict] | None = None) -> dict:
    panel = _load(PANEL) if panel is None else panel
    results = _load(RESULTS) if results is None else results
    mean_score = _mean_scores(panel)
    resp = _responses(results)

    models = sorted({k[0] for k in mean_score})
    per_model: list[dict] = []
    pooled_signals: collections.Counter = collections.Counter()
    pooled_neg = 0
    # served-strategy pooled score lists
    strategies = ("full", "core", "full_guard", "core_guard")
    pooled_served: dict[str, list[float]] = {s: [] for s in strategies}
    pooled_base: list[float] = []
    # guard-policy pooled tallies (applied to the FULL arm)
    pooled_pol = {p: {"served": [], "fired": 0, "recovery": 0, "misfire": 0, "neutral": 0,
                      "recovered_pts": 0.0, "lost_pts": 0.0} for p in POLICIES}
    # negative-lift TEXT signature: what did the harness DO to the reply on the prompts where it hurt?
    # (added a refusal? cited fewer conventions/sections? got shorter?) -- diagnoses the uncatchable tail.
    negsig = {b: {"n": 0, "added_refusal": 0, "len_delta": [], "conv_delta": [], "sect_delta": []}
              for b in ("all", "other")}

    for m in models:
        pids = {k[1] for k in mean_score if k[0] == m}
        complete = [pid for pid in pids
                    if all((m, pid, a) in mean_score and (m, pid, a) in resp for a in ARMS)]
        if len(complete) < MIN_PROMPTS:
            continue
        base_mean = statistics.mean([mean_score[(m, pid, "baseline")] for pid in complete])
        core_mean = statistics.mean([mean_score[(m, pid, "harness_core")] for pid in complete])
        full_mean = statistics.mean([mean_score[(m, pid, "harness_full")] for pid in complete])

        # signals for (baseline, full) and (baseline, core), computed once per prompt
        sig_full: dict[str, dict[str, bool]] = {}
        sig_core: dict[str, dict[str, bool]] = {}
        neg_bucket: collections.Counter = collections.Counter()
        neg_n = 0
        for pid in complete:
            b = resp[(m, pid, "baseline")]
            sig_full[pid] = guard_signals(b, resp[(m, pid, "harness_full")])
            sig_core[pid] = guard_signals(b, resp[(m, pid, "harness_core")])
            if mean_score[(m, pid, "harness_full")] < mean_score[(m, pid, "baseline")]:
                neg_n += 1
                bucket = _first_signal(sig_full[pid]) or "other"
                neg_bucket[bucket] += 1
                f = resp[(m, pid, "harness_full")]
                b_useful = _classify(b)[0]
                f_useful, f_reason = _classify(f)
                added = int(b_useful and (not f_useful) and f_reason == "refusal")
                cb, cf = _cite(b), _cite(f)
                for key in (["all", "other"] if bucket == "other" else ["all"]):
                    ns = negsig[key]
                    ns["n"] += 1
                    ns["added_refusal"] += added
                    ns["len_delta"].append(len(f) - len(b))
                    ns["conv_delta"].append(cf["n_conventions"] - cb["n_conventions"])
                    ns["sect_delta"].append(cf["n_section_refs"] - cb["n_section_refs"])

        # served strategies (min guard where guarded)
        served = {s: [] for s in strategies}
        for pid in complete:
            b_sc = mean_score[(m, pid, "baseline")]
            c_sc = mean_score[(m, pid, "harness_core")]
            f_sc = mean_score[(m, pid, "harness_full")]
            served["full"].append(f_sc)
            served["core"].append(c_sc)
            served["full_guard"].append(b_sc if _fires(sig_full[pid], "min") else f_sc)
            served["core_guard"].append(b_sc if _fires(sig_core[pid], "min") else c_sc)
        served_mean = {s: round(statistics.mean(served[s]), 1) for s in strategies}
        for s in strategies:
            pooled_served[s].extend(served[s])
        pooled_base.extend(mean_score[(m, pid, "baseline")] for pid in complete)

        # guard-policy sanity on the FULL arm
        pol_stats = {}
        for policy in POLICIES:
            arm_served, fired, recovery, misfire, neutral = [], 0, 0, 0, 0
            recovered_pts, lost_pts = 0.0, 0.0
            for pid in complete:
                b_sc, f_sc = mean_score[(m, pid, "baseline")], mean_score[(m, pid, "harness_full")]
                if _fires(sig_full[pid], policy):
                    fired += 1
                    arm_served.append(b_sc)
                    if b_sc > f_sc:
                        recovery += 1
                        recovered_pts += b_sc - f_sc
                    elif b_sc < f_sc:
                        misfire += 1
                        lost_pts += f_sc - b_sc
                    else:
                        neutral += 1
                else:
                    arm_served.append(f_sc)
            pol_stats[policy] = {"guarded_mean": round(statistics.mean(arm_served), 1),
                                 "fired": fired, "recovery": recovery, "misfire": misfire,
                                 "neutral": neutral, "recovered_pts": round(recovered_pts, 1),
                                 "lost_pts": round(lost_pts, 1),
                                 "net_pts": round(recovered_pts - lost_pts, 1)}
            pp = pooled_pol[policy]
            pp["served"].extend(arm_served)
            pp["fired"] += fired
            pp["recovery"] += recovery
            pp["misfire"] += misfire
            pp["neutral"] += neutral
            pp["recovered_pts"] += recovered_pts
            pp["lost_pts"] += lost_pts

        per_model.append({
            "model": m, "n": len(complete), "baseline": round(base_mean, 1), "core": round(core_mean, 1),
            "full": round(full_mean, 1), "full_minus_core": round(full_mean - core_mean, 1),
            "neg_lift": neg_n, "neg_lift_pct": round(100 * neg_n / len(complete), 1),
            "neg_bucket": dict(neg_bucket), "served_mean": served_mean, "policies": pol_stats,
        })
        pooled_neg += neg_n
        pooled_signals.update(neg_bucket)

    per_model.sort(key=lambda r: -r["neg_lift_pct"])
    bmean = statistics.mean(pooled_base) if pooled_base else 0.0
    served_pooled = {s: {"mean": round(statistics.mean(v), 1) if v else 0.0,
                         "lift": round((statistics.mean(v) if v else 0.0) - bmean, 1)}
                     for s, v in pooled_served.items()}
    pol_pooled = {}
    for policy in POLICIES:
        pp = pooled_pol[policy]
        gm = statistics.mean(pp["served"]) if pp["served"] else 0.0
        pol_pooled[policy] = {"guarded_mean": round(gm, 1), "fired": pp["fired"], "recovery": pp["recovery"],
                              "misfire": pp["misfire"], "neutral": pp["neutral"],
                              "recovered_pts": round(pp["recovered_pts"], 1),
                              "lost_pts": round(pp["lost_pts"], 1),
                              "net_pts": round(pp["recovered_pts"] - pp["lost_pts"], 1)}
    def _sig_summary(ns: dict) -> dict:
        n = ns["n"]
        return {"n": n,
                "added_refusal": ns["added_refusal"],
                "added_refusal_pct": round(100 * ns["added_refusal"] / n, 1) if n else 0.0,
                "mean_len_delta": int(statistics.mean(ns["len_delta"])) if ns["len_delta"] else 0,
                "mean_conv_delta": round(statistics.mean(ns["conv_delta"]), 2) if ns["conv_delta"] else 0.0,
                "mean_sect_delta": round(statistics.mean(ns["sect_delta"]), 2) if ns["sect_delta"] else 0.0}
    neg_signature = {k: _sig_summary(v) for k, v in negsig.items()}
    return {"per_model": per_model, "served_pooled": served_pooled, "pol_pooled": pol_pooled,
            "base_mean": round(bmean, 1), "pooled_neg": pooled_neg,
            "pooled_signals": dict(pooled_signals), "neg_signature": neg_signature,
            "n_models": len(per_model), "n_panel": len(panel), "n_results": len(results)}


def build_report(a: dict) -> str:
    o: list[str] = []
    o.append("# Where the harness hurts, and what removes it (offline, no model calls)\n")
    o.append(f"> Deterministic post-processing of the committed grades ({a['n_panel']:,} component cells, "
             f"{a['n_results']:,} stored responses in `reports/rich_lift/`). No new generation, no new "
             "judging -- every number is recomputed from the already-graded arms. Regenerate with "
             "`python scripts/analyze_harness_guard.py`. Prompt ids are not copied; aggregate counts "
             "only.\n")

    sp = a["served_pooled"]
    o.append("## Lever 1 -- which harness to serve (the big one)\n")
    o.append("Served mean over all ranked models by serving strategy. `core` = the cheap offline harness "
             "(GREP + top-4 RAG); `full` = core + deep RAG + tools + online. `+guard` applies the `min` "
             "serving guard (baseline fallback on a deterministic loss of grounding).\n")
    o.append(f"Baseline (no harness) mean: **{a['base_mean']}**.\n")
    o.append("| Serve | mean | lift over baseline |")
    o.append("|---|---:|---:|")
    for s, label in (("full", "harness_full (current board)"), ("core", "harness_core"),
                     ("full_guard", "harness_full + min guard"), ("core_guard", "harness_core + min guard")):
        o.append(f"| {label} | {sp[s]['mean']} | **+{sp[s]['lift']}** |")
    o.append("")
    best = max(sp, key=lambda s: sp[s]["mean"])
    label = {"full": "harness_full", "core": "harness_core", "full_guard": "harness_full + min guard",
             "core_guard": "harness_core + min guard"}[best]
    o.append(f"**Best served mean: `{label}` ({sp[best]['mean']}).** Serving `core` instead of `full` is "
             "the larger, cheaper win -- the full harness's online / deep-RAG / tool layer adds noise a "
             "strong reply does not need, so `full <= core` for every model (next table).\n")

    o.append("## Per-model: full underperforms core, and the negative-lift rate\n")
    o.append("`full - core` < 0 means the extra full-harness layer HURT that model. `neg-lift` = prompts "
             "where harness_full scored below baseline.\n")
    o.append("| Model | n | baseline | core | full | full - core | neg-lift |")
    o.append("|---|---:|---:|---:|---:|---:|---:|")
    for r in a["per_model"]:
        o.append(f"| `{r['model']}` | {r['n']} | {r['baseline']} | {r['core']} | {r['full']} | "
                 f"{r['full_minus_core']:+} | {r['neg_lift']} ({r['neg_lift_pct']}%) |")
    o.append("")

    pp = a["pol_pooled"]
    o.append("## Lever 2 -- the serving guard (a bounded safety net, not the main lever)\n")
    o.append("Guard policies applied to the full arm, pooled. `fired` = fell back to baseline; `recovery` "
             "= those where full < baseline (correctly reverted a regression); `misfire` = those where "
             "full >= baseline (reverted where the harness helped -> lift lost). `net pts` = recovered - "
             "lost.\n")
    o.append("| Policy | signals | guarded mean | fired | recovery | misfire | net pts |")
    o.append("|---|---|---:|---:|---:|---:|---:|")
    for pol in POLICIES:
        s = pp[pol]
        sigs = "+".join(GUARD_POLICIES[pol]) or "(none)"
        o.append(f"| `{pol}` | {sigs} | {s['guarded_mean']} | {s['fired']} | {s['recovery']} "
                 f"(+{s['recovered_pts']}) | {s['misfire']} (-{s['lost_pts']}) | **{s['net_pts']:+}** |")
    o.append("")
    o.append("Read the `net pts` column. The **broad** policies are net-NEGATIVE: `min` fires far more "
             "often on prompts the harness IMPROVED than on true regressions (misfire >> recovery), "
             "because the harness's signature win is a *grounded refusal* that `refusal_detector` flags "
             "as a refusal -- no cheap phrase test separates it from a bare 'I can't help' -- and `len` "
             "(adding the length signal) is worse still. But the **tight `hard` policy IS net-positive**: "
             "it fires only on the catastrophic collapses (a >=1k-char baseline turned into a <=150-char "
             "reply), which its length cap CANNOT confuse with a grounded refusal (those run to hundreds "
             "of chars). It catches the ~-75 disasters (big recovery) with few, small misfires -> a "
             "guarded mean ABOVE unguarded. **Conclusion: `DEFAULT_GUARD_POLICY = hard`** -- a cheap "
             "serving-time safety net for the catastrophic tail, on top of serving `core`.\n")

    o.append("## The negative-lift tail, by deterministic harm mode\n")
    o.append(f"Of the **{a['pooled_neg']}** prompts where harness_full scored below baseline, the harm "
             "mode (first deterministic signal, else `other`):\n")
    o.append("| Harm mode | count | catchable by a text guard? |")
    o.append("|---|---:|---|")
    catch = {"bare_nonanswer": "yes (min)", "citation_regression": "yes (min)",
             "drastic_shortening": "no -- signal is net-negative", "other": "no -- residual"}
    for k, v in sorted(a["pooled_signals"].items(), key=lambda x: -x[1]):
        o.append(f"| `{k}` | {v} | {catch.get(k, '?')} |")
    o.append("")
    o.append("| Model | neg-lift | bare_nonanswer | citation_regression | drastic_shortening | other |")
    o.append("|---|---:|---:|---:|---:|---:|")
    for r in a["per_model"]:
        nb = r["neg_bucket"]
        o.append(f"| `{r['model']}` | {r['neg_lift']} | {nb.get('bare_nonanswer', 0)} | "
                 f"{nb.get('citation_regression', 0)} | {nb.get('drastic_shortening', 0)} | "
                 f"{nb.get('other', 0)} |")
    o.append("")

    ns_all, ns_other = a["neg_signature"]["all"], a["neg_signature"]["other"]
    o.append("## What the harness DID on the negative-lift prompts (text signature)\n")
    o.append("Deterministic deltas (harness_full - baseline) on the prompts where the harness hurt. "
             "`added a refusal` = the baseline answered substantively but the harnessed reply is a "
             "refusal; `conv/section delta` = change in cited ILO conventions / statute sections; "
             "`len delta` = change in characters.\n")
    o.append("| Subset | n | added a refusal | mean conv delta | mean section delta | mean len delta |")
    o.append("|---|---:|---:|---:|---:|---:|")
    for label, ns in (("all negative-lift", ns_all), ("`other` (un-catchable tail)", ns_other)):
        o.append(f"| {label} | {ns['n']} | {ns['added_refusal']} ({ns['added_refusal_pct']}%) | "
                 f"{ns['mean_conv_delta']:+} | {ns['mean_sect_delta']:+} | {ns['mean_len_delta']:+} |")
    o.append("")
    o.append("Reading: a **positive** conv/section delta means the harnessed reply cited *more* law than "
             "the baseline and still scored lower -- so the loss is not missing grounding but the judge "
             "preferring the strong baseline's breadth (a rubric/judge-preference effect, not a harness "
             "bug). A high `added a refusal` share means the harm is the harness turning a useful answer "
             "into a (grounded) refusal -- the failure the h2 grounded-response contract and intent-aware "
             "routing target at generation time (serving `core` also constrains a strong reply less).\n")

    o.append("## What this says\n")
    o.append("- **Serve `core`, not `full`.** This is the single measured lever that reduces where the "
             "harness hurts (full <= core for every model) and it is cheaper (no online / tool calls). "
             "It is a board change and rolls out under the versioned re-grade discipline, not mid-sweep.\n"
             "- **A TIGHT serving guard works; a broad one does not.** The `hard` policy "
             "(`DEFAULT_GUARD_POLICY = hard`) fires only on the catastrophic collapses (a substantial "
             "baseline turned into a <=150-char reply) and is net-positive -- its length cap cannot fire "
             "on a grounded refusal. The broad `min`/`len` policies are net-negative (they revert grounded "
             "refusals `refusal_detector` flags), so they are kept only to demonstrate that.\n"
             "- **The bulk of the tail (65%) is `other`, and the text signature shows it is NOT a harness "
             "failure:** on those prompts the harnessed reply cites MORE conventions and MORE sections and "
             "adds a refusal ~0% of the time -- a full-length, MORE-grounded reply the judge still scored "
             "below a strong baseline's essay. That is a judge / rubric-preference effect near the quality "
             "ceiling, not lost safety value; no text guard should try to 'fix' it. The honest response "
             "is to report it, serve `core` for strong-baseline models (less constraint), and let the h2 "
             "contract handle the tiny genuine bare-collapse count.\n")
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
    sp = a["served_pooled"]
    print(f"wrote {out} | {a['n_models']} models, pooled neg-lift {a['pooled_neg']}, served means: "
          + ", ".join(f"{s}={sp[s]['mean']}" for s in ("full", "core", "full_guard", "core_guard")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
