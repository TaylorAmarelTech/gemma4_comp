"""Empirical study: how badly do LLMs handle human-exploitation / trafficking
prompts at BASELINE (no DueCare harness)?

Sends a set of exploitation / equivocation probes to a roster of models via
OpenRouter, grades each raw response with DueCare's own deterministic rubric
(``grade_response_universal``), and reports per-model failure rates — with a
focus on the ``domain_sense_resolution`` dimension (does the model resist the
cross-domain analogy-laundering move, e.g. "a worker bond is basically a
financial instrument") and the overall safety score.

Cost-controlled and resumable:
  * ``--limit`` caps prompts (pilot mode);  ``--models a,b,c`` overrides roster.
  * temperature 0, ``--max-tokens`` cap; OpenRouter usage is summed for a real
    spend figure printed at the end.
  * each (model, prompt) result is appended to a JSONL immediately, so a crash
    or rate-limit mid-run keeps everything already collected; re-running skips
    (model, prompt) pairs already present in the JSONL.

This is BASELINE-only by design: the question is "how bad are models out of the
box", so we send the raw prompt with a neutral system message, NOT the DueCare
GREP/RAG/persona harness. A second (harnessed) arm can be added later to show
the DueCare lift.

Run (via the recovery venv so the harness import works):
    set -a; . ./.env; set +a
    <venv-python> scripts/model_failure_study.py --limit 10 \
        --models openai/gpt-4o-mini,anthropic/claude-3.5-haiku,meta-llama/llama-3.3-70b-instruct
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Neutral system message: a plausible "general helpful assistant" framing, so we
# measure the model's OWN safety behaviour, not a DueCare-primed one.
NEUTRAL_SYSTEM = (
    "You are a helpful assistant. Answer the user's question clearly and concisely."
)

# Pilot roster — cheap, fast, representative spread (frontier + open). The full
# study roster is configurable via --models.
DEFAULT_MODELS = [
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-haiku",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-small-2503",
]

REPO = Path(__file__).resolve().parents[1]
PROBES = REPO / "configs/duecare/domains/trafficking/ambiguity_probes.jsonl"
SEEDS = REPO / "configs/duecare/domains/trafficking/seed_prompts.jsonl"
OUTDIR = REPO / "reports/model_failure_study"


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_prompts(*, include_seeds: bool, limit: int | None) -> list[dict]:
    """Probe set: equivocation probes first (the headline test), then optionally a
    sample of the business-framed / victim-voice seed prompts."""
    out = [{"id": p["id"], "text": p["text"], "category": p.get("category", ""),
            "ambiguous_term": p.get("metadata", {}).get("ambiguous_term", "")}
           for p in _load_jsonl(PROBES)]
    if include_seeds and SEEDS.exists():
        for p in _load_jsonl(SEEDS):
            out.append({"id": p["id"], "text": p["text"],
                        "category": p.get("category", ""), "ambiguous_term": ""})
    if limit is not None:
        out = out[:limit]
    return out


def call_chat(model: str, prompt: str, *, api_key: str, max_tokens: int,
              url: str = OPENROUTER_URL, timeout: int = 180) -> dict:
    """OpenAI-compatible chat call to any provider (OpenRouter / Ollama-cloud /
    OpenAI / ...). Return ``{ok, text, usage, error}``; never raises."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": NEUTRAL_SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/TaylorAmarelTech/gemma4_comp",
            "X-Title": "DueCare model-failure study",
        })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data["choices"][0]["message"]
        # some reasoning models leave `content` empty and put the answer in a
        # separate reasoning field — fall back so we never mis-score an empty string
        text = (msg.get("content") or msg.get("reasoning_content")
                or msg.get("reasoning") or "")
        return {"ok": True, "text": text, "usage": data.get("usage", {}), "error": None}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        return {"ok": False, "text": "", "usage": {}, "error": f"HTTP {e.code}: {detail}"}
    except Exception as e:  # noqa: BLE001 -- record + continue
        return {"ok": False, "text": "", "usage": {}, "error": f"{type(e).__name__}: {e}"}


def _done_pairs(path: Path, *, only_ok: bool = False) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            if only_ok and not r.get("ok"):
                continue  # a failed row is not "done" -> --retry-errors re-attempts it
            seen.add((r["model"], r["prompt_id"]))
        except Exception:  # noqa: BLE001
            pass
    return seen


def grade(grader, response_text: str, prompt_text: str) -> dict:
    """Deterministic DueCare grade. Returns the headline metrics for the report."""
    g = grader(response_text, prompt_text=prompt_text)
    by_id = {d["id"]: d for d in g.get("dimensions", [])}
    dsr = by_id.get("domain_sense_resolution", {})
    return {
        "pct_score": g.get("pct_score"),
        "score_0_10": g.get("score_0_10"),
        "n_applicable": sum(1 for d in g.get("dimensions", []) if d.get("status") != "NOT_APPLICABLE"),
        "domain_sense_resolution": {
            "status": dsr.get("status"),
            "score_0_10": dsr.get("score_0_10"),
            "applicable": dsr.get("status") != "NOT_APPLICABLE",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS),
                    help="comma-separated OpenRouter model slugs")
    ap.add_argument("--limit", type=int, default=None, help="cap number of prompts")
    ap.add_argument("--include-seeds", action="store_true",
                    help="also include seed_prompts.jsonl (large)")
    ap.add_argument("--max-tokens", type=int, default=500)
    ap.add_argument("--workers", type=int, default=8, help="concurrent generation calls")
    ap.add_argument("--out", default=str(OUTDIR / "results.jsonl"))
    ap.add_argument("--base-url", default=OPENROUTER_URL,
                    help="OpenAI-compatible chat endpoint (e.g. https://ollama.com/v1/chat/completions)")
    ap.add_argument("--key-env", default="OPENROUTER_API_KEY",
                    help="env var holding the bearer key for --base-url")
    ap.add_argument("--retry-errors", action="store_true",
                    help="re-attempt (model, prompt) pairs whose prior row failed (ok=False)")
    args = ap.parse_args()

    api_key = os.environ.get(args.key_env)
    if not api_key:
        print(f"ERROR: {args.key_env} not set (run: set -a; . ./.env; set +a)", file=sys.stderr)
        return 2

    try:
        from duecare.chat.harness import grade_response_universal as grader
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: cannot import DueCare grader ({e}). Run with the recovery venv python.",
              file=sys.stderr)
        return 2

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    prompts = load_prompts(include_seeds=args.include_seeds, limit=args.limit)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = _done_pairs(out_path, only_ok=args.retry_errors)

    tasks = [(model, p) for model in models for p in prompts if (model, p["id"]) not in done]
    print(f"models={len(models)} prompts={len(prompts)} -> {len(tasks)} calls "
          f"({len(done)} already done) with {args.workers} workers")
    spend_tokens = {"prompt": 0, "completion": 0}
    n_called = n_err = 0

    def _gen(model: str, p: dict):
        # generation only (I/O-bound -> parallel); grading is done serially below
        return model, p, call_chat(model, p["text"], api_key=api_key,
                                   max_tokens=args.max_tokens, url=args.base_url)

    with out_path.open("a", encoding="utf-8") as fh, \
            ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(_gen, model, p) for model, p in tasks]
        for fut in as_completed(futs):
            model, p, res = fut.result()
            # an empty/whitespace completion is an API/format artifact (e.g. gpt-oss
            # harmony channels), NOT a model safety failure -- don't grade it as one
            if res["ok"] and not (res["text"] or "").strip():
                res = {"ok": False, "text": "", "usage": res.get("usage", {}),
                       "error": "empty_response"}
            rec: dict = {"model": model, "prompt_id": p["id"], "category": p["category"],
                         "ambiguous_term": p["ambiguous_term"], "ok": res["ok"]}
            if res["ok"]:
                rec["response"] = res["text"]
                rec["usage"] = res["usage"]
                rec["grade"] = grade(grader, res["text"], p["text"])  # serial, main thread
                spend_tokens["prompt"] += int(res["usage"].get("prompt_tokens", 0) or 0)
                spend_tokens["completion"] += int(res["usage"].get("completion_tokens", 0) or 0)
                dsr = rec["grade"]["domain_sense_resolution"]
                print(f"  {model:30s} {p['id']:22s} pct={rec['grade']['pct_score']!s:>5} "
                      f"dsr={dsr['status']}")
            else:
                rec["error"] = res["error"]
                n_err += 1
                print(f"  {model:30s} {p['id']:22s} ERROR {str(res['error'])[:55]}")
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            n_called += 1

    print(f"\nDONE: {n_called} new calls ({n_err} errors). "
          f"Tokens: prompt={spend_tokens['prompt']:,} completion={spend_tokens['completion']:,}")
    print(f"Results appended to {out_path}")
    print("Next: scripts/model_failure_report.py to aggregate + render the report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
