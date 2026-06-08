"""model_failure_loop.py -- one-command, goal-guided, self-healing driver for the
model-failure study.

Pipeline (each stage is a checkpoint with validation):

    preflight -> [generate] -> validate-gen -> judge -> validate-judge -> report

run as a BOUNDED loop that re-attempts gaps until the goals are met or no further
progress is made (loop-until-dry). Goals:

  * generation: every model has >= ``--gen-quota`` non-error responses
  * judge:      every (ok response x dimension) has a FINAL verdict (no ERROR/UNPARSED)
  * report:     a two-layer (deterministic screen + LLM-judge) markdown report renders

It does NOT re-implement generation/judging/aggregation -- it orchestrates the three
existing scripts (``model_failure_study.py``, ``model_failure_judge.py``,
``model_failure_report.py``) so resumability/concurrency live in one place each.

Provider-agnostic: ``--provider auto`` probes OpenRouter then Ollama-cloud and uses
whichever is live; ``--provider ollama|openrouter`` forces one. Switching to "more
advanced LLMs" once an OpenRouter key is funded is a single flag -- nothing else
changes.

Examples
--------
Prove the machine end-to-end on the free Ollama-cloud provider, judging an existing
response set (no new generation), rendering the full report::

    set -a; . ./.env; set +a
    PY="$LOCALAPPDATA/gemma4-testenv/venv/Scripts/python.exe"
    "$PY" scripts/model_failure_loop.py --provider ollama --run-tag v1 \
        --skip-generation --responses reports/model_failure_study/study_v1.jsonl

Plan only, no API calls (validate wiring + show what would run)::

    "$PY" scripts/model_failure_loop.py --provider auto --dry-run

Full frontier run once OPENROUTER_API_KEY is funded::

    "$PY" scripts/model_failure_loop.py --provider openrouter --run-tag frontier \
        --include-seeds --limit 160 --gen-quota 160
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
PROBES = REPO / "configs/duecare/domains/trafficking/ambiguity_probes.jsonl"
SEEDS = REPO / "configs/duecare/domains/trafficking/seed_prompts.jsonl"
OUTDIR = REPO / "reports/model_failure_study"

JUDGE_DIMS = ["sense_resolution", "legal_grounding", "harm_safety", "actionability"]

# --- Provider registry ------------------------------------------------------
# gen_models: roster sent the probes. judge_model: must emit a parseable verdict
# in the OpenAI `content` field. On Ollama-cloud only deepseek-v3.2 / gemma4:31b
# return usable content (qwen3-next / glm-4.6 / gemini-3-flash-preview leave
# `content` empty and put text in `reasoning`, which is a poor judge channel).
PROVIDERS: dict[str, dict] = {
    "ollama": {
        "base_url": "https://ollama.com/v1/chat/completions",
        "key_env": "OLLAMA_API_KEY",
        "gen_models": [
            "deepseek-v3.2", "deepseek-v4-flash", "qwen3-next:80b", "glm-4.6",
            "glm-5", "kimi-k2.5", "minimax-m2", "mistral-large-3:675b",
            "nemotron-3-super", "cogito-2.1:671b", "gemini-3-flash-preview", "gemma4:31b",
        ],
        "judge_model": "deepseek-v3.2",
        "probe_model": "deepseek-v3.2",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
        "gen_models": [
            "openai/gpt-4o", "openai/gpt-4.1", "anthropic/claude-3.7-sonnet",
            "anthropic/claude-3.5-sonnet", "google/gemini-2.5-pro",
            "openai/gpt-4o-mini", "anthropic/claude-3.5-haiku",
        ],
        "judge_model": "anthropic/claude-3.7-sonnet",
        "probe_model": "openai/gpt-4o-mini",
    },
}


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                              capture_output=True, text=True, timeout=10).stdout.strip() or "?"
    except Exception:  # noqa: BLE001
        return "?"


# --- Preflight: provider liveness -------------------------------------------
def probe_provider(name: str) -> tuple[bool, str]:
    """Send one tiny chat to the provider; return (live, detail). Never raises."""
    cfg = PROVIDERS[name]
    api_key = os.environ.get(cfg["key_env"])
    if not api_key:
        return False, f"{cfg['key_env']} not set"
    body = json.dumps({
        "model": cfg["probe_model"],
        "messages": [{"role": "user", "content": "reply with the single word OK"}],
        "max_tokens": 16, "temperature": 0,
    }).encode("utf-8")
    req = urllib.request.Request(cfg["base_url"], data=body, method="POST", headers={
        "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("choices"):
            return True, f"live ({cfg['probe_model']})"
        return False, f"no choices in response: {str(data)[:120]}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:160]}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def resolve_provider(requested: str) -> tuple[str, str]:
    """auto -> prefer openrouter (frontier) if live, else ollama. Returns
    (provider_name, detail) or raises SystemExit if none live."""
    order = ["openrouter", "ollama"] if requested == "auto" else [requested]
    last = ""
    for name in order:
        live, detail = probe_provider(name)
        print(f"  probe {name:11s}: {'LIVE' if live else 'dead'} -- {detail}")
        if live:
            return name, detail
        last = detail
    raise SystemExit(f"ERROR: no live provider (last: {last}). "
                     "Fund/refresh a key in .env, then re-run.")


# --- Subprocess plumbing ----------------------------------------------------
def _venv_python() -> str:
    """The recovery venv python (so the DueCare grader imports in generation);
    falls back to the current interpreter."""
    la = os.environ.get("LOCALAPPDATA", "")
    cand = Path(la) / "gemma4-testenv" / "venv" / "Scripts" / "python.exe"
    return str(cand) if cand.exists() else sys.executable


def _child_env() -> dict:
    env = dict(os.environ)
    srcs = sorted((REPO / "packages").glob("*/src"))
    pp = os.pathsep.join(str(s) for s in srcs)
    if pp:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = pp + (os.pathsep + existing if existing else "")
    return env


def run_script(script: str, argv: list[str]) -> int:
    py = _venv_python()
    cmd = [py, str(SCRIPTS / script), *argv]
    print(f"  $ {script} {' '.join(argv)}")
    proc = subprocess.run(cmd, cwd=REPO, env=_child_env())
    return proc.returncode


# --- Validation / goal checks -----------------------------------------------
def count_responses(path: Path) -> dict[str, dict]:
    by: dict[str, dict] = defaultdict(lambda: {"ok": 0, "err": 0})
    for r in _load_jsonl(path):
        if r.get("ok") and (r.get("response") or "").strip():
            by[r["model"]]["ok"] += 1
        else:
            by[r["model"]]["err"] += 1
    return dict(by)


def gen_gaps(path: Path, models: list[str], quota: int) -> list[str]:
    counts = count_responses(path)
    return [m for m in models if counts.get(m, {}).get("ok", 0) < quota]


def judge_coverage(responses_path: Path, judge_path: Path, dims: list[str]) -> dict:
    """How many (ok response x dimension) pairs have a FINAL verdict."""
    responses = [r for r in _load_jsonl(responses_path)
                 if r.get("ok") and (r.get("response") or "").strip()]
    total = len(responses) * len(dims)
    done = set()
    errors = 0
    for r in _load_jsonl(judge_path):
        v = r.get("verdict")
        if v in ("PASS", "PARTIAL", "FAIL"):
            done.add((r.get("model"), r.get("prompt_id"), r.get("dimension")))
        elif v in ("ERROR", "UNPARSED"):
            errors += 1
    return {"done": len(done), "total": total, "errors": errors,
            "complete": total > 0 and len(done) >= total,
            "pct": (len(done) / total) if total else 0.0}


def write_checkpoint(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  checkpoint -> {path}")


# --- Main loop --------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=["auto", "ollama", "openrouter"], default="auto")
    ap.add_argument("--run-tag", default="v1", help="suffix for result/checkpoint files")
    ap.add_argument("--out-dir", default=str(OUTDIR))
    ap.add_argument("--report-out", default="docs/research/model_failure_on_human_exploitation.md")
    ap.add_argument("--gen-models", default=None, help="override roster (comma-sep)")
    ap.add_argument("--judge-model", default=None, help="override judge model")
    ap.add_argument("--include-seeds", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="cap prompts/model in generation")
    ap.add_argument("--gen-quota", type=int, default=None,
                    help="min ok responses/model (default: #probes, or --limit)")
    ap.add_argument("--judge-limit", type=int, default=None,
                    help="cap responses judged (pilot); default all")
    ap.add_argument("--judge-dims", default=",".join(JUDGE_DIMS))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument("--skip-generation", action="store_true",
                    help="judge/report an existing response set; do not call any model for generation")
    ap.add_argument("--responses", default=None,
                    help="response JSONL to judge (default <out-dir>/study_<tag>.jsonl)")
    ap.add_argument("--dry-run", action="store_true",
                    help="preflight + plan + counts only; no generation/judge API calls")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    responses_path = Path(args.responses) if args.responses else out_dir / f"study_{args.run_tag}.jsonl"
    judge_path = out_dir / f"judge_{args.run_tag}.jsonl"
    state_path = out_dir / f"loop_state_{args.run_tag}.json"
    report_out = Path(args.report_out)
    dims = [d.strip() for d in args.judge_dims.split(",") if d.strip() in JUDGE_DIMS]

    n_probes = len(_load_jsonl(PROBES))
    n_prompts = n_probes + (len(_load_jsonl(SEEDS)) if args.include_seeds else 0)
    if args.limit is not None:
        n_prompts = min(n_prompts, args.limit)
    gen_quota = args.gen_quota if args.gen_quota is not None else n_prompts

    print("=" * 72)
    print("MODEL-FAILURE STUDY LOOP")
    print(f"  git_sha={_git_sha()}  run_tag={args.run_tag}  rounds<= {args.max_rounds}")
    print("-" * 72)

    # ---- PREFLIGHT ----
    print("PREFLIGHT: resolving provider")
    provider, _pdetail = resolve_provider(args.provider)
    cfg = PROVIDERS[provider]
    gen_models = ([m.strip() for m in args.gen_models.split(",") if m.strip()]
                  if args.gen_models else list(cfg["gen_models"]))
    judge_model = args.judge_model or cfg["judge_model"]
    print(f"  provider={provider}  base_url={cfg['base_url']}")
    print(f"  gen_models={len(gen_models)}  judge_model={judge_model}")
    print(f"  prompts/model={n_prompts} (probes={n_probes}{' + seeds' if args.include_seeds else ''}"
          f"{f', limit={args.limit}' if args.limit else ''})  gen_quota={gen_quota}")
    print(f"  responses={responses_path.name}  judge={judge_path.name}  report={report_out}")
    print(f"  venv_python={_venv_python()}")

    base = {"provider": provider, "base_url": cfg["base_url"], "git_sha": _git_sha(),
            "run_tag": args.run_tag, "gen_models": gen_models, "judge_model": judge_model,
            "gen_quota": gen_quota, "judge_dims": dims, "started_at": time.time()}

    if args.dry_run:
        counts = count_responses(responses_path)
        cov = judge_coverage(responses_path, judge_path, dims)
        gaps = gen_gaps(responses_path, gen_models, gen_quota) if responses_path.exists() else gen_models
        print("-" * 72)
        print("DRY RUN -- no API calls. Current on-disk state:")
        print(f"  existing responses: {sum(c['ok'] for c in counts.values())} ok across {len(counts)} models")
        print(f"  generation gaps (models < quota): {len(gaps)}")
        print(f"  judge coverage: {cov['done']}/{cov['total']} ({cov['pct']*100:.0f}%), errors={cov['errors']}")
        write_checkpoint(state_path, {**base, "mode": "dry_run", "gen_counts": counts,
                                      "judge_coverage": cov, "gen_gaps": gaps})
        print("Pipeline wiring OK. Re-run without --dry-run to execute.")
        return 0

    # ---- self-healing rounds ----
    prev_signature = None
    goals_met = False
    rnd = 0
    for rnd in range(1, args.max_rounds + 1):
        print("=" * 72)
        print(f"ROUND {rnd}/{args.max_rounds}  (provider={provider})")

        # STAGE 1: generation (unless skipped) ------------------------------
        if not args.skip_generation:
            print("STAGE generate")
            gen_argv = ["--models", ",".join(gen_models),
                        "--base-url", cfg["base_url"], "--key-env", cfg["key_env"],
                        "--out", str(responses_path), "--workers", str(args.workers),
                        "--max-tokens", "800"]
            if args.include_seeds:
                gen_argv.append("--include-seeds")
            if args.limit is not None:
                gen_argv += ["--limit", str(args.limit)]
            if rnd > 1:
                gen_argv.append("--retry-errors")  # self-heal transient failures
            rc = run_script("model_failure_study.py", gen_argv)
            if rc != 0:
                print(f"  WARN: generation exited {rc} (continuing with what was collected)")
        else:
            print("STAGE generate: SKIPPED (--skip-generation)")

        # STAGE 2: validate generation --------------------------------------
        print("STAGE validate-gen")
        counts = count_responses(responses_path)
        gaps = gen_gaps(responses_path, gen_models, gen_quota)
        n_ok = sum(c["ok"] for c in counts.values())
        print(f"  responses: {n_ok} ok across {len(counts)} models; {len(gaps)} below quota={gen_quota}")
        if gaps:
            print(f"  below-quota: {', '.join(gaps[:8])}{' ...' if len(gaps) > 8 else ''}")
        if n_ok == 0:
            print("  FATAL: zero usable responses -- aborting (check provider/models).")
            write_checkpoint(state_path, {**base, "round": rnd, "gen_counts": counts,
                                          "gen_gaps": gaps, "fatal": "no_responses"})
            return 1
        write_checkpoint(state_path, {**base, "round": rnd, "stage": "post-generate",
                                      "gen_counts": counts, "gen_gaps": gaps})

        # STAGE 3: judge (one dimension per call) ---------------------------
        print("STAGE judge")
        judge_argv = ["--in", str(responses_path), "--out", str(judge_path),
                      "--base-url", cfg["base_url"], "--key-env", cfg["key_env"],
                      "--judge-model", judge_model, "--dimensions", ",".join(dims),
                      "--workers", str(args.workers)]
        if args.judge_limit is not None:
            judge_argv += ["--limit", str(args.judge_limit)]
        rc = run_script("model_failure_judge.py", judge_argv)
        if rc != 0:
            print(f"  WARN: judge exited {rc} (continuing)")

        # STAGE 4: validate judge -------------------------------------------
        print("STAGE validate-judge")
        cov = judge_coverage(responses_path, judge_path, dims)
        print(f"  judge coverage: {cov['done']}/{cov['total']} ({cov['pct']*100:.0f}%), "
              f"unresolved(ERROR/UNPARSED)={cov['errors']}")

        # STAGE 5: render report (checkpoint artifact) ----------------------
        print("STAGE report")
        rc = run_script("model_failure_report.py",
                        ["--in", str(responses_path), "--judge", str(judge_path),
                         "--out", str(report_out)])
        if rc != 0:
            print(f"  WARN: report exited {rc}")

        write_checkpoint(state_path, {**base, "round": rnd, "stage": "post-report",
                                      "gen_counts": counts, "gen_gaps": gaps,
                                      "judge_coverage": cov, "report": str(report_out),
                                      "updated_at": time.time()})

        # ---- goal check + loop-until-dry ----
        gen_ok = args.skip_generation or not gaps
        goals_met = gen_ok and cov["complete"] and cov["errors"] == 0
        signature = (len(gaps), cov["done"], cov["errors"])
        print("-" * 72)
        print(f"  goals: generation={'OK' if gen_ok else f'{len(gaps)} short'}  "
              f"judge={'OK' if cov['complete'] and not cov['errors'] else 'incomplete'}")
        if goals_met:
            print(f"  ALL GOALS MET after round {rnd}.")
            break
        if signature == prev_signature:
            print("  No progress this round (loop-until-dry) -- stopping; gaps likely "
                  "need a different model/provider or a funded key.")
            break
        prev_signature = signature

    # ---- final summary ----
    print("=" * 72)
    cov = judge_coverage(responses_path, judge_path, dims)
    counts = count_responses(responses_path)
    print("SUMMARY")
    print(f"  provider={provider}  rounds_run={rnd}  goals_met={goals_met}")
    print(f"  responses: {sum(c['ok'] for c in counts.values())} ok / "
          f"{sum(c['err'] for c in counts.values())} err across {len(counts)} models")
    print(f"  judge: {cov['done']}/{cov['total']} verdicts ({cov['pct']*100:.0f}%), errors={cov['errors']}")
    print(f"  report: {report_out}")
    print(f"  checkpoint: {state_path}")
    return 0 if goals_met else 2


if __name__ == "__main__":
    raise SystemExit(main())
