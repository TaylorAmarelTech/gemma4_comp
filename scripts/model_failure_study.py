"""Empirical study: how badly do LLMs handle human-exploitation / trafficking
prompts at BASELINE (no DueCare harness)?

Sends a set of exploitation / equivocation probes to a roster of models via
OpenRouter, grades each raw response with DueCare's own deterministic rubric
(``grade_response_universal``), and reports per-model failure rates — with a
focus on the ``domain_sense_resolution`` dimension (does the model resist the
cross-domain analogy-laundering move, e.g. "a worker bond is basically a
financial instrument") and the overall safety score.

Cost-controlled and resumable:
  * ``--plan`` computes the exact call/token plan without credentials or writes;
    ``--max-planned-model-calls`` refuses oversized execution before transport.
  * ``--limit`` caps prompts (pilot mode); ``--selection-mode
    category-balanced`` prevents a dominant category from swallowing a
    directional sample; ``--models a,b,c`` overrides the roster.
  * temperature 0, ``--max-tokens`` cap; OpenRouter usage is summed for a real
    spend figure printed at the end.
  * each (model, prompt) result is appended to a JSONL immediately, so a crash
    or rate-limit mid-run keeps everything already collected; re-running skips
    (model, prompt) pairs already present in the JSONL.
  * every OpenAI-compatible transport attempt reserves against the shared
    provider attempt/input/output/cash ledger when budget settings are active.

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
import hashlib
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any

try:
    import provider_budget
except ModuleNotFoundError:  # imported from the repository root in tests
    from scripts import provider_budget

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
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/\-]+$")
_SAFE_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _nonempty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _string_or_empty(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _has_sensitive_display_text(text: str) -> bool:
    return bool(
        _EMAIL.search(text)
        or _PHONE.search(text)
        or _LOCAL_PATH_HINT.search(text)
        or re.search(r"\b\d{9,}\b", text)
    )


def _safe_relative_report_path(path: PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _has_sensitive_display_text(display):
        return "redacted"
    if not _SAFE_RELATIVE_PATH.fullmatch(display):
        return "redacted"
    return display


def _display_report_path(raw_path: Any) -> str:
    if not raw_path:
        return "n/a"
    raw = str(raw_path)
    try:
        path = Path(raw)
        if path.is_absolute():
            try:
                return _safe_relative_report_path(path.relative_to(REPO))
            except ValueError:
                return "external"
        return _safe_relative_report_path(PurePosixPath(PureWindowsPath(raw).as_posix()))
    except (OSError, RuntimeError, ValueError):
        return "redacted"


def _display_identifier(value: Any) -> str:
    text = str(value or "")
    if _SAFE_IDENTIFIER.fullmatch(text) and not _has_sensitive_display_text(text):
        return text
    return "redacted"


def _display_env_name(value: Any) -> str:
    text = str(value or "")
    if _SAFE_ENV_NAME.fullmatch(text) and not _has_sensitive_display_text(text):
        return text
    return "redacted"


def _display_error(value: Any) -> str:
    text = str(value or "")
    if _has_sensitive_display_text(text):
        return "details redacted"
    return text[:120]


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _select_prompts(
    prompts: list[dict],
    *,
    limit: int | None,
    mode: str,
    seed: int,
) -> list[dict]:
    if limit is None or limit >= len(prompts):
        return prompts
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if mode == "prefix":
        return prompts[:limit]
    if mode != "category-balanced":
        raise ValueError(f"unsupported selection mode: {mode}")

    grouped: dict[str, list[dict]] = defaultdict(list)
    for prompt in prompts:
        grouped[str(prompt.get("category") or "uncategorized")].append(prompt)
    rng = random.Random(seed)
    categories = sorted(grouped)
    rng.shuffle(categories)
    for category in categories:
        rng.shuffle(grouped[category])

    selected: list[dict] = []
    offset = 0
    while len(selected) < limit:
        made_progress = False
        for category in categories:
            bucket = grouped[category]
            if offset < len(bucket):
                selected.append(bucket[offset])
                made_progress = True
                if len(selected) == limit:
                    break
        if not made_progress:
            break
        offset += 1
    return selected


def load_prompts(
    *,
    include_seeds: bool,
    limit: int | None,
    selection_mode: str = "prefix",
    selection_seed: int = 0,
) -> list[dict]:
    """Probe set: equivocation probes first (the headline test), then optionally a
    sample of the business-framed / victim-voice seed prompts."""
    out = []
    for p in _load_jsonl(PROBES):
        prompt_id = _nonempty_string(p.get("id"))
        text = _nonempty_string(p.get("text"))
        if not prompt_id or not text:
            continue
        metadata = p.get("metadata") if isinstance(p.get("metadata"), dict) else {}
        out.append({
            "id": prompt_id,
            "text": text,
            "category": _string_or_empty(p.get("category")),
            "ambiguous_term": _string_or_empty(metadata.get("ambiguous_term")),
        })
    if include_seeds and SEEDS.exists():
        for p in _load_jsonl(SEEDS):
            prompt_id = _nonempty_string(p.get("id"))
            text = _nonempty_string(p.get("text"))
            if not prompt_id or not text:
                continue
            out.append({"id": prompt_id, "text": text,
                        "category": _string_or_empty(p.get("category")), "ambiguous_term": ""})
    return _select_prompts(
        out,
        limit=limit,
        mode=selection_mode,
        seed=selection_seed,
    )


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
    provider = (
        "ollama_cloud" if "ollama.com" in url.lower()
        else "openrouter" if "openrouter.ai" in url.lower()
        else "openai_compatible"
    )
    try:
        with provider_budget.environment_ledger().attempt(
            provider=provider,
            model=model,
            prompt=prompt,
            system=NEUTRAL_SYSTEM,
            max_output_tokens=max_tokens,
        ) as budget_attempt:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            msg = data["choices"][0]["message"]
            # Some reasoning models leave `content` empty and put the answer in
            # a separate reasoning field — fall back so we never mis-score an empty string.
            raw_text = (msg.get("content") or msg.get("reasoning_content")
                        or msg.get("reasoning") or "")
            text = raw_text if isinstance(raw_text, str) else ""
            budget_attempt.settle(response=data, output_text=text)
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
            model = _nonempty_string(r.get("model"))
            prompt_id = _nonempty_string(r.get("prompt_id"))
            if model and prompt_id:
                seen.add((model, prompt_id))
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS),
                    help="comma-separated OpenRouter model slugs")
    ap.add_argument("--limit", type=int, default=None, help="cap number of prompts")
    ap.add_argument("--include-seeds", action="store_true",
                    help="also include seed_prompts.jsonl (large)")
    ap.add_argument("--selection-mode", choices=("prefix", "category-balanced"),
                    default="prefix",
                    help="selection used with --limit; category-balanced is deterministic")
    ap.add_argument("--selection-seed", type=int, default=0,
                    help="fixed seed for category-balanced selection")
    ap.add_argument("--max-tokens", type=int, default=500)
    ap.add_argument("--workers", type=int, default=8, help="concurrent generation calls")
    ap.add_argument("--out", default=str(OUTDIR / "results.jsonl"))
    ap.add_argument("--base-url", default=OPENROUTER_URL,
                    help="OpenAI-compatible chat endpoint (e.g. https://ollama.com/v1/chat/completions)")
    ap.add_argument("--key-env", default="OPENROUTER_API_KEY",
                    help="env var holding the bearer key for --base-url")
    ap.add_argument("--retry-errors", action="store_true",
                    help="re-attempt (model, prompt) pairs whose prior row failed (ok=False)")
    ap.add_argument("--plan", action="store_true",
                    help="print the exact offline call/token plan and exit without credentials, writes, or calls")
    ap.add_argument("--max-planned-model-calls", type=int, default=None,
                    help="refuse before writes/calls when planned calls exceed this ceiling; environment fallback supported")
    args = ap.parse_args(argv)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    prompts = load_prompts(
        include_seeds=args.include_seeds,
        limit=args.limit,
        selection_mode=args.selection_mode,
        selection_seed=args.selection_seed,
    )
    out_path = Path(args.out)
    done = _done_pairs(out_path, only_ok=args.retry_errors)

    tasks = [(model, p) for model in models for p in prompts if (model, p["id"]) not in done]
    selection_sha256 = hashlib.sha256(
        json.dumps(
            [
                {
                    "id": prompt["id"],
                    "text_sha256": hashlib.sha256(prompt["text"].encode("utf-8")).hexdigest(),
                }
                for prompt in prompts
            ],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    plan = {
        "schema": "duecare.model-failure-plan.v1",
        "model_count": len(models),
        "selected_prompt_count": len(prompts),
        "selected_category_count": len({p["category"] or "uncategorized" for p in prompts}),
        "selection_mode": args.selection_mode,
        "selection_seed": args.selection_seed,
        "selection_sha256": selection_sha256,
        "already_done_pairs": len(done),
        "planned_calls": len(tasks),
        "reserved_input_tokens": sum(
            provider_budget.estimate_tokens(NEUTRAL_SYSTEM + "\n" + prompt["text"])
            for _model, prompt in tasks
        ),
        "reserved_output_tokens": len(tasks) * args.max_tokens,
        "max_output_tokens_per_call": args.max_tokens,
    }
    if args.plan:
        print(json.dumps(plan, indent=2))
        return 0

    ceiling = args.max_planned_model_calls
    if ceiling is None and "DUECARE_MAX_PLANNED_MODEL_CALLS" in os.environ:
        try:
            ceiling = int(os.environ["DUECARE_MAX_PLANNED_MODEL_CALLS"])
        except ValueError:
            print("ERROR: DUECARE_MAX_PLANNED_MODEL_CALLS must be an integer", file=sys.stderr)
            return 2
    if ceiling is not None and (ceiling < 0 or len(tasks) > ceiling):
        print(
            f"ERROR: planned calls ({len(tasks)}) exceed the authorized ceiling ({ceiling}); "
            "no writes or calls made",
            file=sys.stderr,
        )
        return 2

    api_key = os.environ.get(args.key_env)
    if not api_key:
        print(f"ERROR: {_display_env_name(args.key_env)} not set", file=sys.stderr)
        return 2

    try:
        from duecare.chat.harness import grade_response_universal as grader
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: cannot import DueCare grader ({_display_error(e)}). Run with the recovery venv python.",
              file=sys.stderr)
        return 2

    out_path.parent.mkdir(parents=True, exist_ok=True)
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
            text = _nonempty_string(res.get("text"))
            usage = res.get("usage") if isinstance(res.get("usage"), dict) else {}
            if res["ok"] and not text:
                res = {"ok": False, "text": "", "usage": usage,
                       "error": "empty_response"}
            rec: dict = {"model": model, "prompt_id": p["id"], "category": p["category"],
                         "ambiguous_term": p["ambiguous_term"], "ok": res["ok"]}
            if res["ok"]:
                rec["response"] = text
                rec["usage"] = usage
                rec["grade"] = grade(grader, text, p["text"])  # serial, main thread
                spend_tokens["prompt"] += int(usage.get("prompt_tokens", 0) or 0)
                spend_tokens["completion"] += int(usage.get("completion_tokens", 0) or 0)
                dsr = rec["grade"]["domain_sense_resolution"]
                print(f"  {_display_identifier(model):30s} {_display_identifier(p['id']):22s} "
                      f"pct={rec['grade']['pct_score']!s:>5} "
                      f"dsr={dsr['status']}")
            else:
                rec["error"] = res["error"]
                n_err += 1
                print(f"  {_display_identifier(model):30s} {_display_identifier(p['id']):22s} "
                      f"ERROR {_display_error(res['error'])}")
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            n_called += 1

    print(f"\nDONE: {n_called} new calls ({n_err} errors). "
          f"Tokens: prompt={spend_tokens['prompt']:,} completion={spend_tokens['completion']:,}")
    print(f"Results appended to {_display_report_path(out_path)}")
    print("Next: scripts/model_failure_report.py to aggregate + render the report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
