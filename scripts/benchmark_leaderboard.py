#!/usr/bin/env python3
"""DueCare Harness-Lift Benchmark -- leaderboard generator.

Turns the per-model component-0-100 results into a versioned, machine-readable **leaderboard** ranked
by the safety lift the DueCare harness adds to each model. The lift is pure prompt augmentation, so the
SAME benchmark wraps ANY model -- adding a model is one ``rich_harness_lift.py --models <model>`` run.

This is the presentation/aggregation layer that makes the evaluation an ongoing, comparable benchmark:
  * a FROZEN spec id + version + prompt set + judge panel (provenance on every row),
  * a STANDARD per-model schema (baseline, harnessed, lift, per-criterion gain, n, pairwise),
  * a machine-readable JSON (for the site + reuse) and a human leaderboard (markdown).

Reads the shared panel written by rich_harness_lift (``reports/rich_lift/panel.jsonl`` +
``pairwise.jsonl``) and emits:
  * ``docs/research/benchmark_leaderboard.md``                       (human leaderboard)
  * ``apps/duecare-ai.com/app/static/benchmark_leaderboard.json``    (machine-readable, served by the site)

Every leaderboard carries the spec id/version, the prompt set, the judge panel, the git SHA, and the
generation timestamp, so any row is reproducible from (git_sha, spec_version).

    python scripts/benchmark_leaderboard.py
    python scripts/benchmark_leaderboard.py --generated 2026-06-23T21:00:00Z   # pin the timestamp
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
import subprocess
import sys
from collections import Counter

_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))
for _src in glob.glob(str(_ROOT / "packages" / "*" / "src")):
    if _src not in sys.path:
        sys.path.insert(0, _src)

from rich_harness_lift import ARMS, COMPONENTS, PANEL, PAIRWISE, RESULTS  # noqa: E402,F401  (frozen surface defs)
from _atomic import write_json_atomic, write_text_atomic  # noqa: E402

# The frozen benchmark spec. Bump `version` only when the prompt set, rubric, protocol, or judge panel
# changes -- that is what makes scores comparable across models and over time.
BENCHMARK = {
    "id": "duecare-harness-lift",
    "name": "DueCare Harness-Lift Benchmark",
    "version": "1.3",
    "scale": "0-100 (component-based LLM-judge panel)",
    "prompt_set": "scheme_prompts.json v1.3 -- 3,700+ synthetic adversarial prompts across 170+ typologies "
                  "(and growing as the discovery-to-vetting flywheel folds in newly vetted prompts) "
                  "at easy/medium/hard/very_hard difficulty: a curated scheme core, the harness-lift "
                  "expansion set (jailbreaks, evasion probes, false-legitimacy, worker/employer queries), "
                  "casefile-derived worker-support scenarios, a 2,915-prompt stratified draw from the "
                  "74,640-prompt trafficking seed registry, and automation-discovered prompts vetted by the "
                  "quality gate; built reproducibly by build_benchmark_promptset.py (seed=13). The "
                  "engine additionally runs an exhaustive sweep of the full ~74,640-prompt trafficking "
                  "registry, so each model's n on the board climbs toward full-registry coverage as it runs.",
    "protocol": "paired baseline vs DueCare-harnessed (pure prompt augmentation: GREP indicator rules "
                "+ retrieved legal grounding + deterministic tools); both arms graded identically by a "
                "diverse frontier judge panel with self-family exclusion; the score is the lift "
                "(harnessed minus baseline), which cancels each judge's absolute scale.",
    "metric": "lift = harnessed - baseline on the 0-100 component rubric (A identifies indicator, "
              "B cites the specific law, C refuses, D concrete resources, E safety/privacy)",
}
DEFAULT_MD = _ROOT / "docs" / "research" / "benchmark_leaderboard.md"
DEFAULT_JSON = _ROOT / "apps" / "duecare-ai.com" / "app" / "static" / "benchmark_leaderboard.json"
_COMP_KEYS = [k for k, _l, _m in COMPONENTS]


def git_sha() -> str:
    """Short HEAD SHA for provenance (empty string if git is unavailable)."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(_ROOT),
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _score(row: dict, key: str = "score_0_100") -> float | None:
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return None


def _components(row: dict) -> dict:
    value = row.get("components", {})
    return value if isinstance(value, dict) else {}


def leaderboard_rows(panel: list[dict], pairwise: list[dict]) -> list[dict]:
    """One standardized row per candidate model, ranked by harness lift (harnessed - baseline).

    The lift is measured on the harness_full arm vs baseline, paired per (judge, prompt); each row also
    carries the per-criterion gain (where the harness helps) and the ceiling-free pairwise preference of
    the full harness over the core harness.
    """
    # (model, judge, prompt) -> {arm: cell}
    cube: dict[tuple, dict[str, dict]] = {}
    for p in panel:
        if not isinstance(p, dict) or _score(p) is None:
            continue
        try:
            cube.setdefault((p["model"], p["judge"], p["prompt_id"]), {})[p["arm"]] = p
        except KeyError:
            continue
    by_model: dict[str, list[tuple[dict, dict]]] = {}
    prompts_by_model: dict[str, set] = {}
    core_by_model: dict[str, list[float]] = {}
    for (m, _j, pid), arms in cube.items():
        if "baseline" in arms and "harness_full" in arms:
            by_model.setdefault(m, []).append((arms["baseline"], arms["harness_full"]))
            prompts_by_model.setdefault(m, set()).add(pid)
            if "harness_core" in arms:
                core_score = _score(arms["harness_core"])
                if core_score is not None:
                    core_by_model.setdefault(m, []).append(core_score)

    pw_by_model: dict[str, list[float]] = {}
    for r in pairwise:
        if not isinstance(r, dict):
            continue
        try:
            delta = float(r["delta"])
            model = str(r["model"])
        except (KeyError, TypeError, ValueError):
            continue
        pw_by_model.setdefault(model, []).append(delta)

    rows = []
    for m, pairs in by_model.items():
        base = float(statistics.mean(_score(b) for b, _f in pairs if _score(b) is not None))
        harn = float(statistics.mean(_score(f) for _b, f in pairs if _score(f) is not None))
        core_scores = core_by_model.get(m, [])
        core = float(statistics.mean(core_scores)) if core_scores else None
        comp_gain: dict[str, float] = {}
        comp_baseline: dict[str, float] = {}
        comp_full: dict[str, float] = {}
        for k in _COMP_KEYS:
            bvals = [_components(b).get(k) for b, _f in pairs]
            fvals = [_components(f).get(k) for _b, f in pairs]
            bvals = [x for x in bvals if isinstance(x, (int, float))]
            fvals = [x for x in fvals if isinstance(x, (int, float))]
            if bvals and fvals:
                comp_baseline[k] = round(float(statistics.mean(bvals)), 1)
                comp_full[k] = round(float(statistics.mean(fvals)), 1)
                comp_gain[k] = round(comp_full[k] - comp_baseline[k], 1)
        pw = pw_by_model.get(m, [])
        rows.append({
            "model": m,
            "n_prompts": len(prompts_by_model.get(m, set())),
            "n_observations": len(pairs),
            "baseline": round(base, 1),
            "harness_core": round(core, 1) if core is not None else None,
            "harnessed": round(harn, 1),
            "lift": round(harn - base, 1),
            "lift_core": round(core - base, 1) if core is not None else None,
            "components_gain": comp_gain,
            "components_baseline": comp_baseline,
            "components_full": comp_full,
            "pairwise_full_vs_core": round(statistics.mean(pw), 2) if pw else None,
        })
    rows.sort(key=lambda r: -r["lift"])
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def krippendorff_alpha_safe(panel: list[dict]) -> float | None:
    """Inter-judge agreement on the absolute 0-100 scores (reuses multi_judge's implementation)."""
    from multi_judge import krippendorff_alpha
    by_resp: dict[str, list[float]] = {}
    for p in panel:
        if not isinstance(p, dict):
            continue
        score = _score(p)
        if score is None:
            continue
        try:
            by_resp.setdefault(f"{p['model']}|{p['prompt_id']}|{p['arm']}", []).append(score)
        except KeyError:
            continue
    return krippendorff_alpha(by_resp)


def _paired_cells(panel: list[dict]) -> list[dict]:
    """rich-lift panel rows -> lift_stats cells (baseline + harness_full mapped to 'harnessed')."""
    cells = []
    for p in panel:
        if not isinstance(p, dict):
            continue
        arm = p.get("arm")
        a = "baseline" if arm == "baseline" else "harnessed" if arm == "harness_full" else None
        if a is None:
            continue
        score = _score(p)
        if score is None:
            continue
        try:
            cells.append({"model": p["model"], "prompt_id": p["prompt_id"], "arm": a,
                          "score": score})
        except KeyError:
            continue
    return cells


def paired_stats_by_model(panel: list[dict]) -> dict[str, dict]:
    """Per-model paired statistics on the full-harness lift: bootstrap 95% CI, paired Cohen's d,
    win-rate, and a two-sided paired-t (z-approx) p-value -- the defensibility layer a reviewer needs."""
    import lift_stats
    cells = _paired_cells(panel)
    stats = {s["model"]: s for s in lift_stats.model_stats(cells)}
    pairs = lift_stats.per_prompt_pairs(cells)
    out: dict[str, dict] = {}
    for m, s in stats.items():
        deltas = [h - b for (_pid, b, h) in pairs.get(m, [])]
        pt = lift_stats.paired_test(deltas)
        out[m] = {
            "n_pairs": s["n_prompts_paired"],
            "ci95_low": round(s["ci95_low"], 1),
            "ci95_high": round(s["ci95_high"], 1),
            "cohens_d": round(s["cohens_d"], 2),
            "win_rate": round(100 * s["win_rate"], 1),
            "loss_rate": round(100 * s["loss_rate"], 1),
            "p_value": pt["p"],
        }
    return out


def _prompt_meta() -> dict[str, dict]:
    """prompt_id -> {category, corridor, difficulty} from the frozen scheme prompt set (empty if absent)."""
    from rich_harness_lift import SCHEME_PROMPTS
    try:
        d = json.loads(SCHEME_PROMPTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(d, dict):
        ps = d.get("prompts", d)
    elif isinstance(d, list):
        ps = d
    else:
        return {}
    return {p["id"]: {"category": p.get("category", "?"), "corridor": p.get("corridor", "?"),
                      "difficulty": p.get("difficulty", "?")}
            for p in ps if isinstance(p, dict) and "id" in p}


def lift_breakdowns(panel: list[dict]) -> dict[str, list[dict]]:
    """Pooled baseline/harnessed/lift by prompt category, corridor, and difficulty -- construct-validity
    evidence that the lift holds across typologies and corridors, not just one slice."""
    meta = _prompt_meta()

    def agg(field: str) -> list[dict]:
        acc: dict[str, dict[str, list[float]]] = {}
        for p in panel:
            if not isinstance(p, dict):
                continue
            arm = p.get("arm")
            a = "baseline" if arm == "baseline" else "harnessed" if arm == "harness_full" else None
            if a is None:
                continue
            score = _score(p)
            if score is None:
                continue
            v = meta.get(str(p.get("prompt_id")), {}).get(field, "?")
            acc.setdefault(v, {"baseline": [], "harnessed": []})[a].append(score)
        out = []
        for v, arms in acc.items():
            if arms["baseline"] and arms["harnessed"]:
                b = statistics.mean(arms["baseline"])
                h = statistics.mean(arms["harnessed"])
                out.append({"value": v, "n_obs": len(arms["baseline"]),
                            "baseline": round(b, 1), "harnessed": round(h, 1), "lift": round(h - b, 1)})
        out.sort(key=lambda r: -r["lift"])
        return out

    return {"by_category": agg("category"), "by_corridor": agg("corridor"),
            "by_difficulty": agg("difficulty")}


# Architecture from each model family's published design (mixture-of-experts vs dense); "-" when
# undisclosed (e.g. proprietary previews). Substring (MoE) / prefix (dense) match keeps version tags robust.
_MOE_FAMILIES = ("gpt-oss", "glm-", "deepseek", "kimi", "qwen3", "minimax")
_DENSE_FAMILIES = ("gemma", "devstral", "ministral", "nemotron")
_PARAMS_RE = re.compile(r":(\d+(?:\.\d+)?)\s*([bt])\b")


def model_meta(model_id: str) -> dict[str, str]:
    """Parameter size (read from the model tag) + architecture (documented family) for a model.

    Size comes from the ``:<N>b``/``:<N>t`` suffix in the Ollama tag (e.g. ``gpt-oss:120b`` -> ``120B``)
    and is ``-`` when the tag carries none. Architecture is the family's published design (MoE/dense),
    ``-`` when undisclosed. Metadata only -- never inferred from scores -- so a reader can weigh each
    model's harness lift against its scale and architecture.
    """
    low = model_id.lower()
    m = _PARAMS_RE.search(low)
    params = f"{m.group(1)}{m.group(2).upper()}" if m else "-"
    if any(f in low for f in _MOE_FAMILIES):
        arch = "MoE"
    elif any(low.startswith(f) for f in _DENSE_FAMILIES):
        arch = "dense"
    else:
        arch = "-"
    return {"params": params, "arch": arch}


def latency_by_model(results_path: pathlib.Path = RESULTS) -> dict[str, float]:
    """Median end-to-end generation latency (seconds per response) per model, from the raw response log.

    Each value is the wall-clock around a model call on Ollama cloud (queue + network included), so it
    is an indicative responsiveness signal, not a controlled throughput benchmark; the median is robust
    to cloud queue spikes. Models generated before latency capture have no rows and render as '-'."""
    by: dict[str, list[float]] = {}
    if not results_path.exists():
        return {}
    for line in results_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(r, dict):
            continue
        lat = r.get("latency_s")
        if isinstance(lat, (int, float)) and lat > 0:
            by.setdefault(str(r.get("model")), []).append(float(lat))
    return {m: round(statistics.median(v), 1) for m, v in by.items() if v}


def _rate(count: int, total: int) -> float | None:
    return round(count / total, 3) if total else None


def _pct(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return f"{100 * float(value):.0f}%"


def contract_metrics_by_model(results_path: pathlib.Path = RESULTS) -> dict[str, dict]:
    """Judge-independent reasoning-contract metrics from raw harness_full responses.

    These are deterministic counts over model text, not LLM-judge scores. They attach the Claude workflow
    outputs (Palermo triad, citation relevance, core remedies, referral-safety review) to the public board
    without changing the lift rubric.
    """
    from reasoning_contract import verify_reasoning  # noqa: PLC0415
    from investigation_lens import institutional_review  # noqa: PLC0415

    counts: dict[str, Counter] = {}
    for row in load_jsonl(results_path):
        if not isinstance(row, dict) or row.get("arm") != "harness_full":
            continue
        model = str(row.get("model") or "")
        response = row.get("response")
        if not model or not isinstance(response, str) or not response.strip():
            continue
        verdict = verify_reasoning(response, min_steps=4, require_triad=True, require_core_remedies=True)
        inst = institutional_review(response)
        c = counts.setdefault(model, Counter())
        c["n"] += 1
        c["strict_contract"] += int(verdict.satisfied)
        c["citation_valid"] += int(verdict.citation_valid)
        c["palermo_triad"] += int(bool(verdict.palermo.get("triad_complete")))
        if verdict.core_remedies.get("required"):
            c["core_required"] += 1
            c["core_complete"] += int(bool(verdict.core_remedies.get("complete")))
        c["institutional_review"] += int(bool(inst.get("reviews_institutions")))
        c["institutional_failure_flag"] += int(bool(inst.get("flags_institutional_failure")))

    out: dict[str, dict] = {}
    for model, c in counts.items():
        n = int(c["n"])
        out[model] = {
            "n": n,
            "strict_contract_rate": _rate(int(c["strict_contract"]), n),
            "citation_valid_rate": _rate(int(c["citation_valid"]), n),
            "palermo_triad_rate": _rate(int(c["palermo_triad"]), n),
            "core_remedy_required_n": int(c["core_required"]),
            "core_remedy_complete_rate": _rate(int(c["core_complete"]), int(c["core_required"])),
            "institutional_review_rate": _rate(int(c["institutional_review"]), n),
            "institutional_failure_flag_rate": _rate(int(c["institutional_failure_flag"]), n),
        }
    return out


# A model needs at least this many paired prompts to be RANKED on the public board. Smaller runs (e.g.
# a rate-limited sweep that only judged a handful of prompts) are listed separately as "preliminary" so
# an incomplete row can never show a misleading lift or regression next to the n=100 rows.
MIN_N = 10


def build_leaderboard(panel: list[dict], pairwise: list[dict], *, generated: str, sha: str,
                      min_n: int = 1, contract_metrics: dict[str, dict] | None = None) -> dict:
    rows = leaderboard_rows(panel, pairwise)
    pstats = paired_stats_by_model(panel)
    lat = latency_by_model()
    cm = contract_metrics if contract_metrics is not None else contract_metrics_by_model()
    for r in rows:
        r["stats"] = pstats.get(r["model"], {})
        r["meta"] = model_meta(r["model"])
        r["latency_s"] = lat.get(r["model"])
        r["contract_metrics"] = cm.get(r["model"], {})
    # Rank only models with enough prompts; the rest are preliminary (shown, not ranked).
    ranked = [r for r in rows if r["n_prompts"] >= min_n]
    preliminary = [r for r in rows if r["n_prompts"] < min_n]
    ranked.sort(key=lambda r: -r["lift"])
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    preliminary.sort(key=lambda r: -r["n_prompts"])
    judges = sorted({p["judge"] for p in panel if isinstance(p, dict) and "judge" in p})
    return {
        "benchmark": BENCHMARK,
        "generated": generated,
        "git_sha": sha,
        "judges": judges,
        "inter_judge_alpha": krippendorff_alpha_safe(panel),
        "min_n": min_n,
        "n_models": len(ranked),
        "models": ranked,
        "n_preliminary": len(preliminary),
        "preliminary": preliminary,
        "breakdowns": lift_breakdowns(panel),
    }


def render_markdown(lb: dict) -> str:
    b = lb["benchmark"]
    o: list[str] = []
    o.append(f"# {b['name']} -- leaderboard (v{b['version']})\n")
    o.append(f"> Ranked by the safety **lift** the DueCare harness adds to each model on the 0-100 "
             f"component rubric. The harness is pure prompt augmentation, so the same benchmark wraps "
             f"any model; adding a model is one `rich_harness_lift.py --models <model>` run. "
             f"Generated {lb['generated']} at git `{lb['git_sha'] or 'unknown'}`.\n")
    o.append(f"- **Prompt set:** {b['prompt_set']}\n"
             f"- **Protocol:** {b['protocol']}\n"
             f"- **Judges (self-family excluded):** {', '.join('`' + j + '`' for j in lb['judges']) or 'none yet'}"
             f" &middot; inter-judge Krippendorff alpha = {lb['inter_judge_alpha']}\n")
    o.append("## Leaderboard (harness lift on 0-100)\n")
    o.append("| Rank | Model | n | baseline | harnessed | **lift** | B: cites law | D: resources | "
             "contract | triad | core remedies | referral review | pairwise full-vs-core |")
    o.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in lb["models"]:
        cg = r["components_gain"]
        pw = r["pairwise_full_vs_core"]
        pw_cell = (("+" if isinstance(pw, (int, float)) and pw >= 0 else "") + str(pw)) if pw is not None else "-"
        cm = r.get("contract_metrics") or {}
        contract = _pct(cm.get("strict_contract_rate"))
        triad = _pct(cm.get("palermo_triad_rate"))
        remedies = _pct(cm.get("core_remedy_complete_rate"))
        referral = _pct(cm.get("institutional_review_rate"))
        o.append(f"| {r['rank']} | `{r['model']}` | {r['n_prompts']} | {r['baseline']:.1f} | "
                 f"{r['harnessed']:.1f} | **+{r['lift']:.1f}** | +{cg.get('B', 0):.1f} | "
                 f"+{cg.get('D', 0):.1f} | {contract} | {triad} | {remedies} | {referral} | {pw_cell} |")
    o.append("")
    if lb.get("preliminary"):
        names = ", ".join(f"`{r['model']}` (n={r['n_prompts']})" for r in lb["preliminary"])
        o.append(f"*Preliminary (n &lt; {lb.get('min_n', MIN_N)}, not ranked - the run is incomplete and "
                 f"would be misleading next to the larger runs): {names}. Rerun to add enough prompts.*\n")
    o.append("## Per-criterion gain (mean points, baseline to harnessed)\n")
    o.append("| Model | " + " | ".join(f"{k}. {label} ({mx})" for k, label, mx in COMPONENTS) + " |")
    o.append("|---" * (len(COMPONENTS) + 1) + "|")
    for r in lb["models"]:
        cg = r["components_gain"]
        o.append(f"| `{r['model']}` | " + " | ".join(f"+{cg.get(k, 0):.1f}" for k, _l, _m in COMPONENTS) + " |")
    o.append("")
    o.append("## Submit a model\n")
    o.append("Run any chat model through the same benchmark and regenerate the leaderboard:\n")
    o.append("```bash\n"
             "python scripts/rich_harness_lift.py --models <your-model> "
             "--judges gpt-oss:120b,glm-5.2,deepseek-v4-pro --pairwise\n"
             "python scripts/benchmark_leaderboard.py\n```\n")
    o.append(f"The model is any chat endpoint the runner can call. Spec id `{b['id']}` v{b['version']}; "
             f"method catalog: `benchmark_methods.md`; full methodology: `evaluation_methodology.md`.\n")
    return "\n".join(o) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--panel", default=str(PANEL))
    ap.add_argument("--pairwise", default=str(PAIRWISE))
    ap.add_argument("--md", default=str(DEFAULT_MD))
    ap.add_argument("--json", default=str(DEFAULT_JSON))
    ap.add_argument("--generated", default="", help="ISO timestamp to stamp (default: git HEAD commit date)")
    args = ap.parse_args(argv)

    panel = load_jsonl(pathlib.Path(args.panel))
    pairwise = load_jsonl(pathlib.Path(args.pairwise))
    if not panel:
        print(f"no panel data in {args.panel}; run rich_harness_lift.py first", file=sys.stderr)
        return 1
    sha = git_sha()
    generated = args.generated.strip()
    if not generated:
        try:  # tie the default timestamp to the code state, not wall-clock, for reproducibility
            out = subprocess.run(["git", "show", "-s", "--format=%cI", "HEAD"], cwd=str(_ROOT),
                                 capture_output=True, text=True, timeout=10)
            generated = out.stdout.strip() if out.returncode == 0 else "unknown"
        except Exception:  # noqa: BLE001
            generated = "unknown"

    lb = build_leaderboard(panel, pairwise, generated=generated, sha=sha, min_n=MIN_N)
    md_path, json_path = pathlib.Path(args.md), pathlib.Path(args.json)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(md_path, render_markdown(lb))
    write_json_atomic(json_path, lb)
    print(f"leaderboard -> {md_path.name} + {json_path.name} | {lb['n_models']} models | "
          f"judges={len(lb['judges'])} alpha={lb['inter_judge_alpha']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
