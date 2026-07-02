#!/usr/bin/env python3
"""Phase 3 four-arm evaluator -- does training internalise the harness lift, and do they stack?

The benchmark already grades the STOCK model in two arms: A = baseline (harness off) and B =
harness_full (harness on). This evaluator adds the TRAINED model (the LoRA from train_lift_distill.py)
in the same two arms -- C = trained baseline, D = trained harness_full -- on the SAME prompts, then
reports:

  internalisation     = C - A           (how much training alone raised the unharnessed model)
  internalised_frac   = (C-A)/(B-A)      (fraction of the harness's lift that training captured)
  harness_lift_stock  = B - A
  harness_lift_trained= D - C            (does the harness still help after training?)
  total               = D - A            (trained + harness vs stock baseline)
  stacks_vs_stock_harness = D >= B       (trained + harness beats stock + harness?)

Two paths:
  --analyze  CPU-safe: read panel.jsonl (the board's stock A/B + this tool's trained C/D) and print
             + write the four-arm table. Runs anywhere; this is the testable core.
  --run      GPU (Kaggle): load the trained adapter, generate C/D on the stock model's already-graded
             prompts (reusing rich_harness_lift's generation + the component-judge panel), then analyze.

    python scripts/four_arm_eval.py --analyze --stock-model gemma4:31b --trained-label duecare-trained
    python scripts/four_arm_eval.py --run --adapter reports/training/adapter --stock-model gemma4:31b

Design: docs/phase3_training_framework.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
BOARD_PANEL = _ROOT / "reports" / "rich_lift" / "panel.jsonl"
BOARD_RESULTS = _ROOT / "reports" / "rich_lift" / "results.jsonl"
OUT_DIR = _ROOT / "reports" / "four_arm"
FOUR_ARM_PANEL = OUT_DIR / "panel.jsonl"
FOUR_ARM_RESULTS = OUT_DIR / "results.jsonl"
REPORT = _ROOT / "docs" / "research" / "four_arm_eval.md"
ARM_OFF = "baseline"
ARM_ON = "harness_full"
DEFAULT_BASE = "unsloth/gemma-4-E2B-it"
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_MODEL_LABEL = re.compile(r"^[A-Za-z0-9._:/\-]+$")


def _contains_sensitive_text(value: str) -> bool:
    return bool(_EMAIL.search(value) or _PHONE.search(value) or re.search(r"\b\d{9,}\b", value))


def _safe_relative_report_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _contains_sensitive_text(display):
        return "redacted"
    if not _SAFE_RELATIVE_PATH.fullmatch(display):
        return "redacted"
    return display


def _display_report_path(raw_path: Any) -> str:
    if not raw_path:
        return "n/a"
    raw = str(raw_path)
    try:
        path = pathlib.Path(raw)
        if path.is_absolute():
            try:
                return _safe_relative_report_path(path.relative_to(_ROOT))
            except ValueError:
                return "external"
        return _safe_relative_report_path(pathlib.PurePosixPath(pathlib.PureWindowsPath(raw).as_posix()))
    except (OSError, RuntimeError, ValueError):
        return "redacted"


def _display_model_label(label: Any) -> str:
    text = str(label or "")
    if _SAFE_MODEL_LABEL.fullmatch(text) and not _contains_sensitive_text(text):
        return text
    return "redacted"


def _display_table_for_output(table: dict[str, Any]) -> dict[str, Any]:
    out = dict(table)
    if "stock_model" in out:
        out["stock_model"] = _display_model_label(out["stock_model"])
    if "trained_model" in out:
        out["trained_model"] = _display_model_label(out["trained_model"])
    return out


def generated_timestamp() -> str:
    """UTC timestamp for report provenance."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_sha() -> str:
    """Short git SHA for report provenance, or empty when git is unavailable."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(_ROOT),
                             text=True, capture_output=True, check=False)
    except OSError:
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def _coerce_nonnegative_int(value: Any) -> int:
    try:
        n = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, n)


def _nonnegative_int_arg(value: str) -> int:
    try:
        n = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from exc
    if n < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return n


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def mean_by_arm(panel: list[dict], model: str) -> dict[tuple[str, str], float]:
    """{(prompt_id, arm): mean 0-100 score over judges} for one model."""
    by: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in panel:
        if not isinstance(r, dict):
            continue
        if str(r.get("model")) != model:
            continue
        try:
            by[(str(r["prompt_id"]), str(r["arm"]))].append(float(r["score_0_100"]))
        except (KeyError, TypeError, ValueError):
            continue
    return {k: round(statistics.mean(v), 1) for k, v in by.items() if v}


def four_arm_table(panel: list[dict], stock_model: str, trained_model: str) -> dict[str, Any]:
    """A/B/C/D on prompts graded for BOTH models in both off/on arms, plus internalisation + stacking."""
    stock = mean_by_arm(panel, stock_model)
    trained = mean_by_arm(panel, trained_model)
    common = {p for (p, _a) in stock} & {p for (p, _a) in trained}
    rows = []
    for pid in sorted(common):
        a, b = stock.get((pid, ARM_OFF)), stock.get((pid, ARM_ON))
        c, d = trained.get((pid, ARM_OFF)), trained.get((pid, ARM_ON))
        if None in (a, b, c, d):
            continue
        rows.append({"prompt_id": pid, "A": a, "B": b, "C": c, "D": d})
    if not rows:
        return {"n": 0, "stock_model": stock_model, "trained_model": trained_model, "rows": [],
                "issues": ["no prompts graded for BOTH models in both off/on arms "
                           "(run --run after training, or check the model labels)"]}

    def m(k: str) -> float:
        return round(statistics.mean(r[k] for r in rows), 1)

    a, b, c, d = m("A"), m("B"), m("C"), m("D")
    harness_lift_stock = round(b - a, 1)
    return {
        "n": len(rows), "stock_model": stock_model, "trained_model": trained_model,
        "arms": {"A_stock_off": a, "B_stock_on": b, "C_trained_off": c, "D_trained_on": d},
        "internalisation": round(c - a, 1),
        "internalised_frac": (round((c - a) / harness_lift_stock, 2) if harness_lift_stock > 0 else None),
        "harness_lift_stock": harness_lift_stock,
        "harness_lift_trained": round(d - c, 1),
        "total": round(d - a, 1),
        "stacks_vs_stock_harness": d >= b,
        "harness_still_helps_trained": d > c,
        "rows": rows,
        "issues": [],
    }


def input_coverage(
    panel: list[dict],
    board_results: list[dict],
    stock_model: str,
    trained_model: str,
    *,
    requested_n: int = 0,
) -> dict[str, Any]:
    """Privacy-safe preflight counts for the four-arm inputs.

    This deliberately reports aggregate prompt counts only: no prompt IDs, prompt text, responses, or judge
    content. It is meant to make a pending status report actionable without turning it into a case log.
    """
    prompts_by_model_arm: dict[tuple[str, str], set[str]] = defaultdict(set)
    panel_row_count = 0
    for row in panel:
        if not isinstance(row, dict):
            continue
        model = str(row.get("model", ""))
        arm = str(row.get("arm", ""))
        prompt_id = row.get("prompt_id")
        if model not in {stock_model, trained_model} or arm not in {ARM_OFF, ARM_ON} or prompt_id is None:
            continue
        prompts_by_model_arm[(model, arm)].add(str(prompt_id))
        panel_row_count += 1

    stock_off = prompts_by_model_arm[(stock_model, ARM_OFF)]
    stock_on = prompts_by_model_arm[(stock_model, ARM_ON)]
    trained_off = prompts_by_model_arm[(trained_model, ARM_OFF)]
    trained_on = prompts_by_model_arm[(trained_model, ARM_ON)]
    stock_both = stock_off & stock_on
    trained_both = trained_off & trained_on

    stock_text_prompts: set[str] = set()
    for row in board_results:
        if not isinstance(row, dict):
            continue
        if str(row.get("model")) == stock_model and row.get("prompt_text"):
            prompt_id = row.get("prompt_id")
            if prompt_id is not None:
                stock_text_prompts.add(str(prompt_id))
    run_ready = stock_both & stock_text_prompts

    issues: list[str] = []
    if not stock_off:
        issues.append("stock_baseline_missing")
    if not stock_on:
        issues.append("stock_harness_full_missing")
    if not stock_both:
        issues.append("stock_paired_prompts_missing")
    if stock_both and not run_ready:
        issues.append("stock_prompt_text_missing_for_run")
    if not trained_off:
        issues.append("trained_baseline_missing")
    if not trained_on:
        issues.append("trained_harness_full_missing")
    if not trained_both:
        issues.append("trained_paired_prompts_missing")
    requested = _coerce_nonnegative_int(requested_n)

    return {
        "panel_row_count": panel_row_count,
        "stock_baseline_prompts": len(stock_off),
        "stock_harness_full_prompts": len(stock_on),
        "stock_paired_prompts": len(stock_both),
        "stock_prompt_text_prompts": len(stock_text_prompts),
        "stock_run_ready_prompts": len(run_ready),
        "requested_run_prompts": requested,
        "runnable_now_prompts": min(len(run_ready), requested) if requested else len(run_ready),
        "trained_baseline_prompts": len(trained_off),
        "trained_harness_full_prompts": len(trained_on),
        "trained_paired_prompts": len(trained_both),
        "four_arm_paired_prompts": len(stock_both & trained_both),
        "blocking_issues": issues,
    }


def load_heldout_categories(path: pathlib.Path | None = None) -> set[str] | None:
    """Held-out typologies from organize_training_data.py's manifest (the generalisation split), or None
    if no manifest exists yet (run scripts/organize_training_data.py first)."""
    p = path or (_ROOT / "reports" / "training" / "organize_manifest.json")
    if not p.exists():
        return None
    try:
        manifest = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(manifest, dict):
        return None
    cats = manifest.get("heldout_categories")
    return set(map(str, cats)) if isinstance(cats, list) else None


def split_by_typology(rows: list[dict], pid2cat: dict[str, str],
                      heldout_cats: set[str]) -> dict[str, Any]:
    """Internalisation (C-A) for trained-on vs held-out typologies, plus the generalisation gap.

    Held-out typologies were never in the training data, so they isolate understanding from memorisation:
    a SMALL or negative gap means training carried the behaviour to typologies it never saw (understanding);
    a LARGE positive gap means it only helped the typologies it trained on (memorisation / shortcut).
    """
    def _internal(rs: list[dict]) -> dict[str, Any] | None:
        valid = []
        for r in rs:
            if not isinstance(r, dict):
                continue
            try:
                valid.append({"A": float(r["A"]), "C": float(r["C"])})
            except (KeyError, TypeError, ValueError):
                continue
        if not valid:
            return None
        a = statistics.mean(r["A"] for r in valid)
        c = statistics.mean(r["C"] for r in valid)
        return {"n": len(valid), "C_minus_A": round(c - a, 1),
                "A_stock_off": round(a, 1), "C_trained_off": round(c, 1)}

    held = []
    seen = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            category = pid2cat.get(str(r["prompt_id"]), "unknown")
        except KeyError:
            continue
        if category in heldout_cats:
            held.append(r)
        else:
            seen.append(r)
    seen_m, held_m = _internal(seen), _internal(held)
    gap = (round(seen_m["C_minus_A"] - held_m["C_minus_A"], 1) if seen_m and held_m else None)
    return {
        "heldout_categories": sorted(heldout_cats),
        "trained_typologies": seen_m, "heldout_typologies": held_m,
        "generalisation_gap": gap,
        "reading": ("gap = internalisation(trained typologies) - internalisation(held-out typologies); "
                    "small/negative = training generalises to unseen typologies (understanding), large "
                    "positive = it only helped the typologies it trained on (memorisation)"),
    }


def _split_section(table: dict[str, Any]) -> str:
    """Markdown for the held-out-typology generalisation diagnostic, or '' when absent."""
    sp = table.get("typology_split")
    if not sp:
        return ""
    if sp.get("issue"):
        return f"\n## Generalisation by typology\n\n_{sp['issue']}_\n"
    tr, ho, gap = sp["trained_typologies"], sp["heldout_typologies"], sp["generalisation_gap"]
    held = ", ".join("`" + c + "`" for c in sp["heldout_categories"])
    lines = ["\n## Generalisation by typology (held-out diagnostic)\n",
             f"Whole typologies held out of training, then scored: {held}.\n",
             "| typology set | n | internalisation (C-A) |", "|---|---:|---:|"]
    if tr:
        lines.append(f"| trained-on | {tr['n']} | {tr['C_minus_A']:+.1f} |")
    if ho:
        lines.append(f"| held-out | {ho['n']} | {ho['C_minus_A']:+.1f} |")
    if gap is not None:
        lines.append(f"\n**Generalisation gap = {gap:+.1f}.** " + sp["reading"] + "\n")
    else:
        lines.append("\n_(need both trained-on and held-out rows to compute the gap)_\n")
    return "\n".join(lines)


def _coverage_section(table: dict[str, Any]) -> str:
    """Markdown for the aggregate input coverage preflight, or '' when absent."""
    cov = table.get("input_coverage")
    if not isinstance(cov, dict):
        return ""
    lines = [
        "\n## Input preflight coverage\n",
        "| input arm | unique prompts |",
        "|---|---:|",
        f"| stock baseline (A) | {cov.get('stock_baseline_prompts', 0)} |",
        f"| stock harness_full (B) | {cov.get('stock_harness_full_prompts', 0)} |",
        f"| trained baseline (C) | {cov.get('trained_baseline_prompts', 0)} |",
        f"| trained harness_full (D) | {cov.get('trained_harness_full_prompts', 0)} |",
        "",
        f"Stock prompts ready for `--run` (both stock arms plus prompt text): "
        f"**{cov.get('stock_run_ready_prompts', 0)}**.",
    ]
    requested = cov.get("requested_run_prompts", 0)
    if requested:
        lines.append(f"Requested `--n={requested}` would run **{cov.get('runnable_now_prompts', 0)}** prompts.")
    lines.append(f"Four-arm paired prompts currently analyzable: **{cov.get('four_arm_paired_prompts', 0)}**.")
    issues = cov.get("blocking_issues") or []
    if issues:
        safe_issues = [str(issue) for issue in issues if re.fullmatch(r"[a-z0-9_]+", str(issue))]
        if safe_issues:
            lines.append("Blocking inputs: " + ", ".join(f"`{issue}`" for issue in safe_issues) + ".")
    lines.append("No prompt IDs, prompt text, responses, or judge content are copied into this status report.\n")
    return "\n".join(lines)


def render_report(table: dict[str, Any], *, generated: str, sha: str) -> str:
    """Markdown four-arm report."""
    if table.get("n", 0) == 0:
        return ("# Four-arm evaluation (stock vs trained x harness off/on)\n\n"
                f"_generated {generated} - git {sha}_\n\n"
                "This is a status report, not an evaluation result.\n\n"
                "No paired data yet: " + "; ".join(table.get("issues") or ["pending the first trained run"])
                + ".\n\n"
                "Inputs checked: `reports/rich_lift/panel.jsonl` for stock arms A/B and "
                "`reports/four_arm/panel.jsonl` for trained arms C/D.\n\n"
                "Run `python scripts/four_arm_eval.py --run --adapter reports/training/adapter` "
                "on a GPU after training to populate arms C/D, then rerun "
                "`python scripts/four_arm_eval.py --analyze` on CPU to refresh this report.\n"
                + _coverage_section(table)
                + _split_section(table))
    arms = table["arms"]
    frac = table["internalised_frac"]
    frac_s = f"{int(round(frac * 100))}%" if frac is not None else "n/a"
    return (
        "# Four-arm evaluation (stock vs trained x harness off/on)\n\n"
        f"_generated {generated} - git {sha} - n={table['n']} paired prompts - "
        f"stock `{_display_model_label(table['stock_model'])}` vs trained "
        f"`{_display_model_label(table['trained_model'])}`_\n\n"
        "Does training internalise the harness lift, and do training + harness stack? Each prompt is "
        "scored by the same 0-100 component-judge panel in four arms on the same prompts.\n\n"
        "| arm | model | harness | mean 0-100 |\n|---|---|---|---:|\n"
        f"| A | stock | off | {arms['A_stock_off']} |\n"
        f"| B | stock | on | {arms['B_stock_on']} |\n"
        f"| C | trained | off | {arms['C_trained_off']} |\n"
        f"| D | trained | on | {arms['D_trained_on']} |\n\n"
        "| metric | value | reading |\n|---|---:|---|\n"
        f"| internalisation (C-A) | {table['internalisation']:+.1f} | training alone, harness off |\n"
        f"| internalised fraction | {frac_s} | share of the harness lift (B-A) captured by training |\n"
        f"| harness lift, stock (B-A) | {table['harness_lift_stock']:+.1f} | the original inference-time lift |\n"
        f"| harness lift, trained (D-C) | {table['harness_lift_trained']:+.1f} | does the harness still help after training |\n"
        f"| total (D-A) | {table['total']:+.1f} | trained + harness vs stock baseline |\n"
        f"| stacks vs stock+harness (D>=B) | {table['stacks_vs_stock_harness']} | training + harness beats harness alone |\n\n"
        "**Honest reading.** A high internalised fraction means training carried the harness's stable "
        "behaviours into the weights; a positive harness-lift-trained (D-C) means the harness still adds "
        "value on top (the volatile facts it supplies that weights can't memorise). We do not claim the "
        "gap closes -- we report it. Numbers regenerate from `panel.jsonl`; the judge panel is "
        "self-family-excluded.\n"
        + _coverage_section(table)
        + _split_section(table)
    )


def _stock_prompts(board_panel: list[dict], board_results: list[dict], stock_model: str, n: int) -> list[dict]:
    """Prompts the board already graded for the stock model in BOTH arms, with their text (for re-gen)."""
    requested = _coerce_nonnegative_int(n)
    arms_by_pid: dict[str, set] = defaultdict(set)
    for r in board_panel:
        if not isinstance(r, dict):
            continue
        if str(r.get("model")) == stock_model:
            arms_by_pid[str(r.get("prompt_id"))].add(str(r.get("arm")))
    text_by_pid = {}
    for r in board_results:
        if not isinstance(r, dict):
            continue
        if str(r.get("model")) == stock_model and r.get("prompt_text"):
            text_by_pid[str(r.get("prompt_id"))] = str(r["prompt_text"])
    out = []
    for pid in sorted(p for p, arms in arms_by_pid.items() if {ARM_OFF, ARM_ON} <= arms):
        if pid in text_by_pid:
            out.append({"id": pid, "text": text_by_pid[pid]})
    return out[:requested] if requested else out


def run(*, adapter: str, base: str, stock_model: str, trained_label: str, n: int,
        judges: list[str], max_seq: int, max_new_tokens: int) -> dict[str, Any]:
    """GPU path: generate the trained model's A/B (=C/D) on the stock prompts, judge, then analyze."""
    import sys as _sys
    _sys.path.insert(0, str(_ROOT / "scripts"))
    import rich_harness_lift as rl  # noqa: E402  (heavy: pulls llm_generate; lazy on purpose)

    board_panel = load_jsonl(BOARD_PANEL)
    prompts = _stock_prompts(board_panel, load_jsonl(BOARD_RESULTS), stock_model, n)
    if not prompts:
        raise SystemExit(
            f"no board-graded prompts for stock model {_display_model_label(stock_model)!r}; grade it first."
        )
    print(
        f"[four-arm] {len(prompts)} stock-graded prompts -> generating trained arms with adapter "
        f"{_display_report_path(adapter)}"
    )

    try:
        from unsloth import FastModel
        from unsloth.chat_templates import get_chat_template
        import torch  # noqa: F401
    except ImportError as exc:
        raise SystemExit(f"Unsloth/torch unavailable ({exc}); the --run step needs a CUDA GPU. "
                         "Use --analyze on CPU once a trained run has populated reports/four_arm/.")

    model, tokenizer = FastModel.from_pretrained(model_name=adapter, max_seq_length=max_seq,
                                                 dtype=None, load_in_4bit=True)
    tokenizer = get_chat_template(tokenizer, chat_template="gemma-4-thinking")
    if hasattr(FastModel, "for_inference"):
        FastModel.for_inference(model)

    def gen(_model_id: str, prompt_in: str) -> str:
        msgs = [{"role": "user", "content": [{"type": "text", "text": prompt_in}]}]
        ids = tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                            return_tensors="pt").to(model.device)
        out = model.generate(input_ids=ids, max_new_tokens=max_new_tokens, temperature=1.0,
                             top_p=0.95, top_k=64, do_sample=True)
        return tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rl.generate_responses(prompts, [trained_label], reuse={}, results_path=FOUR_ARM_RESULTS,
                          generate=gen, pace=0.0, max_tokens=max_new_tokens,
                          log=lambda m: print("  " + m, flush=True))
    four_results = load_jsonl(FOUR_ARM_RESULTS)
    rl.judge_panel(four_results, judges, panel_path=FOUR_ARM_PANEL, judge_caller=None, pace=0.6,
                   log=lambda m: print("  " + m, flush=True))
    combined = board_panel + load_jsonl(FOUR_ARM_PANEL)
    return four_arm_table(combined, stock_model, trained_label)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analyze", action="store_true", help="CPU-safe: read panels + print/write the table")
    ap.add_argument("--run", action="store_true", help="GPU: generate trained C/D then analyze")
    ap.add_argument("--adapter", default=str(_ROOT / "reports" / "training" / "adapter"))
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--stock-model", default="gemma4:31b")
    ap.add_argument("--trained-label", default="duecare-trained")
    ap.add_argument("--n", type=_nonnegative_int_arg, default=100)
    ap.add_argument("--judges", default="gpt-oss:120b,glm-5.2,deepseek-v4-pro")
    ap.add_argument("--max-seq", type=int, default=2048)
    ap.add_argument("--max-new-tokens", type=int, default=1024)
    ap.add_argument("--generated", default="", help="ISO timestamp for the report header (optional)")
    ap.add_argument("--sha", default="", help="git sha for the report header (optional)")
    ap.add_argument("--split-by-typology", action="store_true",
                    help="add the held-out-typology generalisation gap (internalisation C-A: trained vs held-out)")
    args = ap.parse_args(argv)

    if args.run:
        table = run(adapter=args.adapter, base=args.base, stock_model=args.stock_model,
                    trained_label=args.trained_label, n=args.n,
                    judges=[j.strip() for j in args.judges.split(",") if j.strip()],
                    max_seq=args.max_seq, max_new_tokens=args.max_new_tokens)
    else:
        board_panel = load_jsonl(BOARD_PANEL)
        four_panel = load_jsonl(FOUR_ARM_PANEL)
        combined = board_panel + four_panel
        table = four_arm_table(combined, args.stock_model, args.trained_label)
    board_panel = load_jsonl(BOARD_PANEL)
    four_panel = load_jsonl(FOUR_ARM_PANEL)
    table["input_coverage"] = input_coverage(
        board_panel + four_panel,
        load_jsonl(BOARD_RESULTS),
        args.stock_model,
        args.trained_label,
        requested_n=args.n,
    )

    if args.split_by_typology:
        heldout = load_heldout_categories()
        if heldout is None:
            table["typology_split"] = {"issue": "no reports/training/organize_manifest.json yet -- run "
                                                "scripts/organize_training_data.py first"}
        elif table.get("n", 0) == 0:
            table["typology_split"] = {"issue": "no four-arm rows yet -- run --run after training to "
                                                "populate the trained arms (C/D)"}
        else:
            import sys as _sys
            _sys.path.insert(0, str(_ROOT / "scripts"))
            import organize_training_data as _otd  # reuse load_pid2cat (DRY)
            pid2cat = _otd.load_pid2cat(_otd.FULL_SET, _otd.CURATED_SET)
            table["typology_split"] = split_by_typology(table["rows"], pid2cat, heldout)

    print("[four-arm]", json.dumps({k: v for k, v in _display_table_for_output(table).items() if k != "rows"},
                                  indent=2))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    generated = args.generated.strip() or generated_timestamp()
    sha = args.sha.strip() or git_sha() or "unknown"
    REPORT.write_text(render_report(table, generated=generated, sha=sha), encoding="utf-8")
    print(f"[four-arm] report -> {_display_report_path(REPORT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
