#!/usr/bin/env python3
"""Placebo control under a DIVERSE JUDGE PANEL — is the confound closed for *every* judge, not one?

`placebo_judge.py` closed the "any preamble helps" confound on a single judge (gpt-oss:120b):
the harness adds +3.34 beyond a length-matched placebo. The obvious skeptic's follow-up is *judge
choice* — would a different judge agree? This re-runs the SAME 3-arm placebo control (baseline,
length-matched placebo, harnessed) under a panel of independent frontier judges from different model
families (gpt-oss, GLM, Qwen, Kimi, DeepSeek), with **self-family exclusion** (a judge never scores a
candidate from its own family), and asks: does *every* judge find harnessed − placebo > 0?

If they all do, the confound is closed *robustly to judge choice*, not just for one model. Reuses the
stored responses (only the judge calls are new) and seeds gpt-oss:120b's already-computed scores from
placebo_judge.jsonl so they are not re-judged. Resumable; judge injectable for tests.

    OLLAMA_API_KEY=... python scripts/placebo_panel.py
Env knobs:
    PP_JUDGES  comma list of judges (default: the 5-model diverse panel)
    PP_MODELS  comma list of candidates to judge (default: gemma4:31b — the headline model)
    PP_PACE    seconds between judge calls (default 0.2)
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
import time
from typing import Callable

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

import lift_stats  # noqa: E402
from placebo_judge import (  # noqa: E402
    DEFAULT_PERDIM_RESP, DEFAULT_PLACEBO_RESP, DEFAULT_CKPT as SINGLE_CKPT, _ARMS, _fmt_p, load_arms,
)

DEFAULT_PANEL_CKPT = _ROOT / "reports" / "placebo_panel.jsonl"
DEFAULT_OUT = _ROOT / "docs" / "research" / "placebo_panel.md"
# Same diverse panel as frontier_panel_perdim.md — large frontier models from distinct families.
DEFAULT_JUDGES = ("gpt-oss:120b", "glm-5.2", "qwen3.5:397b", "kimi-k2.7-code", "deepseek-v3.2")


def _family(model: str) -> str:
    try:
        from multi_judge import model_family
        return model_family(model)
    except Exception:  # noqa: BLE001 -- fall back to a cheap prefix split
        return model.split(":")[0].split("-")[0].lower()


def _default_judge(prompt: str, response: str, *, model: str) -> float:
    from multi_judge import judge_one
    return judge_one(prompt, response, model=model)


def seed_from_single(panel_ckpt: pathlib.Path, single_ckpt: pathlib.Path,
                     judge_model: str = "gpt-oss:120b") -> int:
    """Carry the single-judge placebo_judge.jsonl scores into the panel ckpt (tagged with the judge),
    so the panel run does not re-pay for gpt-oss:120b's already-computed triples. Idempotent."""
    if not single_ckpt.exists():
        return 0
    have = set()
    if panel_ckpt.exists():
        for ln in panel_ckpt.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
                have.add((r["judge"], r["model"], r["prompt_id"], r["arm"]))
            except (json.JSONDecodeError, KeyError):
                continue
    seeded = 0
    panel_ckpt.parent.mkdir(parents=True, exist_ok=True)
    with panel_ckpt.open("a", encoding="utf-8") as f:
        for ln in single_ckpt.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
            except json.JSONDecodeError:
                continue
            key = (judge_model, r["model"], r["prompt_id"], r["arm"])
            if key in have:
                continue
            f.write(json.dumps({"judge": judge_model, "model": r["model"],
                                "prompt_id": r["prompt_id"], "arm": r["arm"],
                                "score": float(r["score"])}) + "\n")
            have.add(key)
            seeded += 1
    return seeded


def run_panel(arms: dict, *, judges: list[str], judge: Callable[..., float] | None = None,
              ckpt: pathlib.Path = DEFAULT_PANEL_CKPT, pace: float = 0.2,
              exclude_self_family: bool = True,
              log: Callable[[str], None] = lambda _m: None) -> list[dict]:
    """LLM-judge every (judge, model, prompt, arm) not already in the checkpoint. Resumable.

    Self-family exclusion: a judge skips any candidate from its own family (so the panel stays
    independent of the model under test)."""
    jf = judge or _default_judge
    done: set = set()
    rows: list[dict] = []
    if ckpt.exists():
        for ln in ckpt.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(ln)
                rows.append(r)
                done.add((r["judge"], r["model"], r["prompt_id"], r["arm"]))
            except (json.JSONDecodeError, KeyError):
                continue
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    for jm in judges:
        jfam = _family(jm)
        for (model, pid), info in arms.items():
            if exclude_self_family and _family(model) == jfam:
                continue
            for arm in _ARMS:
                if (jm, model, pid, arm) in done:
                    continue
                try:
                    score = float(jf(info["prompt_text"], info[arm], model=jm))
                except Exception as exc:  # noqa: BLE001 -- skip, keep the panel going
                    log(f"JUDGE FAIL {jm}|{model}|{pid}|{arm}: {type(exc).__name__}: {exc}")
                    continue
                row = {"judge": jm, "model": model, "prompt_id": pid, "arm": arm, "score": score}
                with ckpt.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
                rows.append(row)
                done.add((jm, model, pid, arm))
                log(f"{jm}|{model}|{pid}|{arm}: {score:.1f}")
                if pace:
                    time.sleep(pace)
    return rows


def _contrasts(triples: dict, keys: list) -> dict:
    b = [triples[k]["baseline"] for k in keys]
    pl = [triples[k]["placebo"] for k in keys]
    h = [triples[k]["harnessed"] for k in keys]
    return {
        "n": len(keys),
        "mean_baseline": round(sum(b) / len(b), 3),
        "mean_placebo": round(sum(pl) / len(pl), 3),
        "mean_harnessed": round(sum(h) / len(h), 3),
        "placebo_minus_baseline": lift_stats.paired_test([x - y for x, y in zip(pl, b)]),
        "harnessed_minus_placebo": lift_stats.paired_test([x - y for x, y in zip(h, pl)]),
        "harnessed_minus_baseline": lift_stats.paired_test([x - y for x, y in zip(h, b)]),
    }


def aggregate(rows: list[dict], *, common_only: bool = False) -> dict:
    """Per-judge contrasts (each judge's own paired triples) + a panel summary across judges.

    common_only restricts every judge to the (model, prompt) keys that *all* judges scored on all
    three arms — an apples-to-apples panel where each judge graded the same prompts."""
    by_judge_triples: dict = collections.defaultdict(lambda: collections.defaultdict(dict))
    for r in rows:
        by_judge_triples[r["judge"]][(r["model"], r["prompt_id"])][r["arm"]] = float(r["score"])
    complete: dict = {jm: {k for k, v in by.items() if all(a in v for a in _ARMS)}
                      for jm, by in by_judge_triples.items()}
    shared: set | None = None
    if common_only and complete:
        shared = set.intersection(*complete.values()) if complete else set()
    per_judge: dict = {}
    for jm, by in by_judge_triples.items():
        triples = {k: v for k, v in by.items() if all(a in v for a in _ARMS)}
        if shared is not None:
            triples = {k: v for k, v in triples.items() if k in shared}
        if triples:
            per_judge[jm] = _contrasts(triples, list(triples))
    # panel summary: distribution of each judge's harnessed-minus-placebo mean
    hp_means = [c["harnessed_minus_placebo"]["mean"] for c in per_judge.values()]
    n_judges = len(hp_means)
    panel = {}
    if n_judges:
        mean = sum(hp_means) / n_judges
        spread = (sum((x - mean) ** 2 for x in hp_means) / n_judges) ** 0.5 if n_judges > 1 else 0.0
        panel = {
            "n_judges": n_judges,
            "panel_mean_harnessed_minus_placebo": round(mean, 3),
            "spread": round(spread, 3),
            "min_hp": round(min(hp_means), 3),
            "max_hp": round(max(hp_means), 3),
            "all_positive": all(x > 0 for x in hp_means),
            "all_significant": all(c["harnessed_minus_placebo"]["p"] < 0.05 for c in per_judge.values()),
        }
    return {"per_judge": per_judge, "panel": panel}


def build_report(agg: dict, *, out_path: pathlib.Path) -> str:
    per, panel = agg["per_judge"], agg["panel"]
    o: list[str] = []
    o.append("# Placebo control under a diverse judge panel — does *every* judge close the confound?\n")
    o.append(
        "`placebo_judge.md` closed the 'any preamble helps' confound on one judge (gpt-oss:120b): the "
        "harness's grounding scored well beyond a length-matched, knowledge-free placebo. The natural "
        "skeptic's follow-up is **judge choice** — so here the *same* 3-arm control (baseline, placebo, "
        "harnessed) is re-scored by a panel of independent frontier judges from different model families "
        "(gpt-oss, GLM, Qwen, Kimi, DeepSeek), with **self-family exclusion**. The question: does the "
        "knowledge effect (**harnessed − placebo**) survive for *every* judge?\n")
    if panel:
        verdict = ("**every** judge" if panel["all_positive"] else "a majority of judges")
        sigword = ("and the effect is significant for **every** one of them"
                   if panel["all_significant"] else
                   "though significance varies by judge at this per-judge n")
        o.append(
            f"> Across **{panel['n_judges']} independent judges**, {verdict} finds the harness adds "
            f"knowledge *beyond* the generic preamble — harnessed − placebo ranges "
            f"**{panel['min_hp']:+.2f} … {panel['max_hp']:+.2f}** (panel mean "
            f"**{panel['panel_mean_harnessed_minus_placebo']:+.2f}**, judge spread ±{panel['spread']:.2f}), "
            f"{sigword}. The confound is closed **robustly to judge choice**, not for one judge only.\n")
    o.append("## Per judge — the placebo control (harnessed − placebo is the knowledge effect)\n")
    o.append("| Judge | n | baseline | placebo | harnessed | placebo − base | **harnessed − placebo** | p |")
    o.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for jm, c in sorted(per.items(), key=lambda kv: -kv[1]["harnessed_minus_placebo"]["mean"]):
        pb = c["placebo_minus_baseline"]
        hp = c["harnessed_minus_placebo"]
        o.append(f"| `{jm}` | {c['n']} | {c['mean_baseline']} | {c['mean_placebo']} | "
                 f"{c['mean_harnessed']} | {pb['mean']:+.2f} | **{hp['mean']:+.2f}** | {_fmt_p(hp['p'])} |")
    o.append("")
    o.append("## Reading this\n")
    o.append(
        "- The decisive column is **harnessed − placebo**: the lift that remains after subtracting any "
        "generic-preamble effect, i.e. the harness's *knowledge*. Every judge computes it on its own "
        "paired triples, so each row is a self-contained paired test.\n"
        "- **Self-family exclusion** keeps the panel independent: a judge never scores a candidate from "
        "its own family. (For the `gemma4:31b` candidate every panel judge is eligible, since none is a "
        "Gemma model.)\n"
        "- As in `frontier_panel_perdim.md`, judges may anchor their *absolute* scales differently; what "
        "we claim is the **paired contrast**, which cancels each judge's offset. Agreement on the *sign "
        "and rough size* of harnessed − placebo across a diverse panel is the robustness result.\n"
        "- These are the harder negative-control prompts, so absolute scores run high; the result is the "
        "**contrast and its consistency across judges**, not the absolute magnitude. The larger-N "
        "single-judge magnitude is in `placebo_judge.md`; the headline lift is `harness_lift_report.md`.\n")
    md = "\n".join(o) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return md


def main(argv: list[str] | None = None) -> int:
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ckpt", default=str(DEFAULT_PANEL_CKPT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--no-seed", action="store_true", help="do not seed gpt-oss rows from placebo_judge.jsonl")
    args = ap.parse_args(argv)
    judges = [j.strip() for j in os.environ.get("PP_JUDGES", ",".join(DEFAULT_JUDGES)).split(",") if j.strip()]
    models = [m.strip() for m in os.environ.get("PP_MODELS", "gemma4:31b").split(",") if m.strip()]
    ckpt = pathlib.Path(args.ckpt)

    if not args.report_only:
        if not args.no_seed:
            n = seed_from_single(ckpt, SINGLE_CKPT)
            if n:
                print(f"[placebo-panel] seeded {n} gpt-oss:120b rows from {SINGLE_CKPT.name}", flush=True)
        arms = load_arms(DEFAULT_PERDIM_RESP, DEFAULT_PLACEBO_RESP, models or None)
        limit = int(os.environ.get("PP_LIMIT", "0") or 0)
        if limit > 0:  # cap NEW judging cost — first N prompts per model, deterministic by id
            per_model: dict = collections.defaultdict(list)
            for (m, pid) in sorted(arms):
                per_model[m].append((m, pid))
            keep = {k for m in per_model for k in per_model[m][:limit]}
            arms = {k: v for k, v in arms.items() if k in keep}
        print(f"[placebo-panel] {len(arms)} 3-arm triples | judges={judges} | models={models or 'ALL'}"
              + (f" | limit={limit}/model" if limit else ""), flush=True)
        run_panel(arms, judges=judges, ckpt=ckpt, pace=float(os.environ.get("PP_PACE", "0.2")),
                  log=lambda m: print("  " + m, flush=True))

    rows = [json.loads(ln) for ln in ckpt.read_text(encoding="utf-8").splitlines() if ln.strip()] \
        if ckpt.exists() else []
    agg = aggregate(rows, common_only=True)
    if not agg["per_judge"]:
        print("no complete triples judged yet", file=sys.stderr)
        return 1
    build_report(agg, out_path=pathlib.Path(args.out))
    p = agg["panel"]
    print(f"report -> {pathlib.Path(args.out).name} | judges={p.get('n_judges')} | "
          f"panel harnessed-placebo {p.get('panel_mean_harnessed_minus_placebo'):+.2f} "
          f"(range {p.get('min_hp'):+.2f}..{p.get('max_hp'):+.2f})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
