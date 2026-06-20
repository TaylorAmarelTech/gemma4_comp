#!/usr/bin/env python3
"""Reusable LLM generation engine -> propose-only staging.

The one place DueCare generates content with the Ollama-cloud LLM (glm-5.2 / kimi-k2.7-code
/ gpt-oss / gemma4:31b). It bakes in two hard-won facts:

  * REASONING-MODEL HANDLING. glm-5.2 / gpt-oss / kimi put thinking in ``message.reasoning``
    and the answer in ``message.content``; with a low ``max_tokens`` the thinking eats the
    budget and ``content`` comes back EMPTY. So we default ``max_tokens`` high and read
    ``content`` with a ``reasoning`` fallback.
  * PROPOSE-ONLY. Everything generated is a DRAFT. It is staged to gitignored
    ``reports/llm_proposals/`` with ``_synthetic`` / ``_propose_only`` markers and is NEVER
    auto-merged into the live knowledge/safety layer. A human reviews + promotes. (Real, not
    faked: an LLM may draft test inputs, but "facts" must be source-verified before merge.)

Key comes from the gitignored ``.env`` (``OLLAMA_API_KEY``) -- never embedded. The model
call is injectable so the engine is unit-tested offline with no network.

Usage:
    python scripts/llm_generate.py --task triage-tests --n 5 --model glm-5.2
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parents[1]
PROPOSALS_DIR = _ROOT / "reports" / "llm_proposals"
OLLAMA_CLOUD_BASE = "https://ollama.com/v1"   # NOT OLLAMA_HOST (that's the down local daemon)
DEFAULT_MODEL = "glm-5.2"
DEFAULT_MAX_TOKENS = 2000   # high enough that a reasoning model still emits an answer


def _load_key() -> str:
    """OLLAMA_API_KEY from the gitignored repo .env (never embedded in source)."""
    env = _ROOT / ".env"
    if env.exists():
        for ln in env.read_text(encoding="utf-8").splitlines():
            if ln.startswith("OLLAMA_API_KEY=") and not ln.lstrip().startswith("#"):
                return ln.split("=", 1)[1].strip()
    import os
    key = os.environ.get("OLLAMA_API_KEY", "")
    if not key:
        raise RuntimeError("no OLLAMA_API_KEY in .env or environment")
    return key


def ollama_chat(prompt: str, *, model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS,
                temperature: float = 0.6, key: str | None = None, system: str | None = None,
                timeout: float = 180.0) -> str:
    """One Ollama-cloud chat completion -> the answer text (content, reasoning fallback)."""
    key = key or _load_key()
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens,
                       "temperature": temperature, "stream": False}).encode("utf-8")
    req = urllib.request.Request(f"{OLLAMA_CLOUD_BASE}/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.loads(resp.read().decode("utf-8", "replace"))
    msg = (out.get("choices") or [{}])[0].get("message") or {}
    # reasoning-model aware: prefer the answer, fall back to the thinking text if content empty
    return str(msg.get("content") or "").strip() or str(msg.get("reasoning") or "").strip()


def complete(prompt: str, *, model: str = DEFAULT_MODEL, max_tokens: int = DEFAULT_MAX_TOKENS,
             temperature: float = 0.6, system: str | None = None,
             caller: Callable[..., str] | None = None) -> str:
    """Model-agnostic completion; ``caller`` is injectable for offline tests."""
    if caller is None:
        key = _load_key()
        def caller(p, **kw):  # noqa: E306 -- default real backend
            return ollama_chat(p, key=key, system=system, **kw)
    return caller(prompt, model=model, max_tokens=max_tokens, temperature=temperature)


def extract_json(text: str) -> Any | None:
    """Pull the first JSON object/array out of model text (handles ``` fences)."""
    cleaned = re.sub(r"```(?:json)?", "", str(text or "")).strip()
    m = re.search(r"[\[{].*[\]}]", cleaned, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def stage_proposal(items: list, *, task: str, model: str, name: str | None = None,
                   at: str | None = None) -> Path:
    """Write a propose-only proposal to gitignored reports/llm_proposals/. NEVER the live layer."""
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    out = PROPOSALS_DIR / (name or f"{task}.json")
    payload = {
        "_synthetic": True,
        "_propose_only": True,
        "_note": "LLM-generated DRAFT -- review + (for facts) source-verify before any merge",
        "task": task,
        "model": model,
        "generated_at": at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n": len(items),
        "items": items,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


_TRIAGE_TESTS_PROMPT = (
    "Generate {n} SYNTHETIC job-advertisement test cases for a migrant-worker recruitment-fraud "
    "screen. Each embeds ONE subtle exploitation signal (illegal placement fee / passport "
    "retention / contract substitution / debt bondage / wage withholding) phrased the way a real "
    "recruiter would -- NOT obvious. Composite/fictional ONLY: no real names, companies, or numbers. "
    'Reply with ONLY compact JSON, no prose: {{"cases":[{{"text":"...","hidden_signal":"...",'
    '"why_subtle":"..."}}]}}'
)


def generate_triage_test_cases(n: int = 5, *, model: str = DEFAULT_MODEL,
                               caller: Callable[..., str] | None = None) -> list[dict]:
    """Generate synthetic red-team test cases for the triage screen (test inputs, not facts)."""
    text = complete(_TRIAGE_TESTS_PROMPT.format(n=n), model=model, caller=caller)
    data = extract_json(text) or {}
    cases = data.get("cases") if isinstance(data, dict) else (data if isinstance(data, list) else [])
    return [c for c in (cases or []) if isinstance(c, dict) and c.get("text")]


_TASKS = {"triage-tests": generate_triage_test_cases}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", default="triage-tests", choices=sorted(_TASKS),
                    help="what to generate")
    ap.add_argument("--n", type=int, default=5, help="how many items")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="ollama-cloud model id")
    ap.add_argument("--out", default="", help="proposal filename (under reports/llm_proposals/)")
    args = ap.parse_args(argv)

    items = _TASKS[args.task](args.n, model=args.model)
    path = stage_proposal(items, task=args.task, model=args.model, name=args.out or None)
    print(f"{args.model}: generated {len(items)} item(s) for '{args.task}'", file=sys.stderr)
    print(f"staged PROPOSE-ONLY -> {path.relative_to(_ROOT)} (gitignored; review before use)",
          file=sys.stderr)
    for i, it in enumerate(items[:8], 1):
        label = it.get("hidden_signal") or it.get("label") or ""
        print(f"  [{i}] {label}: {str(it.get('text', ''))[:120]}", file=sys.stderr)
    return 0 if items else 1


if __name__ == "__main__":
    raise SystemExit(main())
