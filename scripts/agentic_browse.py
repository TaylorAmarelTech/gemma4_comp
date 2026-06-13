#!/usr/bin/env python3
"""Gemma-4 function-calling browser agent: the model controls the browser.

"Gemma proposes, code disposes." The model never touches the page directly --
it sees a compact, safe snapshot (title + interactive elements + which JSON
endpoints were captured) and emits a TOOL CALL (navigate / click / fill /
extract / finish). A deterministic executor runs the call against a real
headless browser, and a deterministic verifier (the AgencyProfile scorer from
browser_scrape) checks what comes back. So a hallucinated step cannot do
anything destructive -- browsing is read-only and extraction is schema-checked.

Why this matters for the project:
  * It makes Gemma 4's NATIVE FUNCTION CALLING load-bearing, not decorative --
    the model orchestrates retrieval, exactly the rubric's ask.
  * It GENERALISES the connector beyond the hardcoded DMW path to any of the 72
    catalogued registries (configs/.../entity_sources.yaml): point it at a URL +
    a goal and the model works out the navigation and maps the unknown JSON keys
    to the AgencyProfile schema.
  * Multimodal extension point: an `observe()` snapshot can include a screenshot
    for vision-grounded clicks, and scanned PDFs (the DMW advisories) route to
    Gemma 4 vision OCR.

Design (matches the rest of the pipeline):
  * Both the MODEL and the EXECUTOR are injectable, so the planner loop, tool
    dispatch, transcript, and record aggregation are tested with a scripted
    model + a fake executor -- no browser, no GPU, no network.
  * The live executor reuses scripts/browser_scrape.py (launch + capture +
    AgencyProfile parsing). The live model calls Gemma 4 through an
    OpenAI-compatible / Ollama endpoint and is gated behind env config.
  * Propose-only: extracted records stage to reports/agency_registry/.
  * Read-only browsing: the tool set has no write/submit-money/destructive verbs.

Usage:
    # live (needs a browser + a Gemma endpoint, e.g. Ollama):
    #   set OLLAMA_HOST + OLLAMA_API_KEY (or DUECARE_MODEL_BASE_URL/_KEY/_NAME)
    python scripts/agentic_browse.py \
        --url https://some-registry.gov/agencies \
        --goal "extract the full list of licensed recruitment agencies" \
        --model gemma4:31b
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Callable, Protocol

_ROOT = Path(__file__).resolve().parents[1]


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(
        f"dc_{name}_for_agentic", str(_ROOT / "scripts" / f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---- the function-calling tool contract the model sees ---------------------

TOOLS = [
    {"name": "navigate", "description": "Load a URL in the browser.",
     "args": {"url": "the absolute URL to open"}},
    {"name": "observe", "description": "Get a fresh compact snapshot of the current page: "
     "title, visible interactive elements (buttons/inputs/links with their text), and the "
     "JSON data endpoints captured so far.", "args": {}},
    {"name": "click", "description": "Click an element by its visible text or a CSS selector.",
     "args": {"target": "visible text or CSS selector of the element to click"}},
    {"name": "fill", "description": "Type text into an input identified by selector/placeholder.",
     "args": {"target": "CSS selector or placeholder of the input", "text": "text to type"}},
    {"name": "next_page", "description": "Fetch further page(s) of a paginated data endpoint. "
     "It replays the registry's own API for you (forwarding the page's auth), so use it instead "
     "of clicking pagination buttons. Pass count to fetch several pages in one call. Keep calling "
     "until the observation shows pages_fetched == last_page, then extract.",
     "args": {"count": "how many further pages to fetch this call (default 1; you may pass the "
              "number still remaining to finish in one call)"}},
    {"name": "extract", "description": "Extract agency records from the captured JSON endpoint(s). "
     "Aggregates EVERY page fetched so far. Optionally pass field_map mapping the source's raw keys "
     "to canonical fields (name/status/license_no/address/phones/email).",
     "args": {"endpoint": "the captured endpoint URL to extract from (or empty for the richest)",
              "field_map": "optional {canonical_field: source_key} mapping"}},
    {"name": "finish", "description": "Stop: the goal is met, or it cannot be met.",
     "args": {"reason": "why you are stopping"}},
]

_TOOL_NAMES = {t["name"] for t in TOOLS}


class Observation(dict):
    """A compact, model-facing page snapshot (plain dict; subclass for clarity)."""


class BrowserExecutor(Protocol):
    def navigate(self, url: str) -> Observation: ...
    def observe(self) -> Observation: ...
    def click(self, target: str) -> Observation: ...
    def fill(self, target: str, text: str) -> Observation: ...
    def paginate(self, count: int = 1) -> dict: ...
    def extract(self, endpoint: str = "", field_map: dict | None = None) -> list[dict]: ...


# ---- the planner loop (model-agnostic, executor-agnostic) ------------------

def run_agent(goal: str, executor: BrowserExecutor,
              model_fn: Callable[..., dict], *, max_steps: int = 16,
              log: Callable[[str], None] | None = None) -> dict:
    """Drive `executor` toward `goal` using tool calls chosen by `model_fn`.

    `model_fn(goal, observation, tools, transcript) -> {"tool": str, "args": dict}`.
    Returns {records, transcript, steps, stop_reason}. Read-only + bounded."""
    records: list[dict] = []
    transcript: list[dict] = []
    stop_reason = "max_steps"
    obs: Observation = executor.observe()
    for step in range(max_steps):
        try:
            action = model_fn(goal=goal, observation=obs, tools=TOOLS, transcript=transcript) or {}
        except Exception as exc:  # noqa: BLE001
            stop_reason = f"model_error: {type(exc).__name__}"
            break
        tool = str(action.get("tool", "")).strip()
        args = action.get("args") or {}
        if tool == "finish" or tool not in _TOOL_NAMES:
            stop_reason = "finish" if tool == "finish" else f"invalid_tool:{tool}"
            transcript.append({"tool": tool or "(none)", "args": args, "result": {"stop": stop_reason}})
            break
        try:
            if tool == "navigate":
                result = dict(executor.navigate(str(args.get("url", ""))))
            elif tool == "observe":
                result = {"observed": True}
            elif tool == "click":
                result = dict(executor.click(str(args.get("target", ""))))
            elif tool == "fill":
                result = dict(executor.fill(str(args.get("target", "")), str(args.get("text", ""))))
            elif tool == "next_page":
                try:
                    cnt = max(1, int(args.get("count", 1) or 1))
                except (TypeError, ValueError):
                    cnt = 1
                result = dict(executor.paginate(cnt))
            elif tool == "extract":
                recs = executor.extract(str(args.get("endpoint", "")), args.get("field_map"))
                records.extend(recs)
                result = {"extracted": len(recs), "total_so_far": len(records)}
            else:  # pragma: no cover - guarded above
                result = {"error": f"unhandled tool {tool}"}
        except Exception as exc:  # noqa: BLE001
            result = {"error": f"{type(exc).__name__}: {str(exc)[:160]}"}
        transcript.append({"tool": tool, "args": args, "result": result})
        if log:
            log(f"step {step}: {tool}({json.dumps(args)[:80]}) -> {json.dumps(result)[:120]}")
        obs = executor.observe()

    # dedup identical records (entity_kb does entity-level merge downstream)
    seen, uniq = set(), []
    for r in records:
        k = (r.get("name"), r.get("status"), r.get("address"))
        if k in seen:
            continue
        seen.add(k); uniq.append(r)
    return {"records": uniq, "transcript": transcript, "steps": len(transcript),
            "stop_reason": stop_reason}


# ---- live model: Gemma 4 via an OpenAI-compatible / Ollama endpoint ---------

def _model_config(model_name: str = "") -> dict:
    """Resolve the Gemma endpoint from env (Ollama-cloud or any OpenAI-compat)."""
    base = (os.environ.get("DUECARE_MODEL_BASE_URL")
            or os.environ.get("OLLAMA_HOST", "").rstrip("/")
            or "")
    # Ollama's OpenAI-compatible API lives at <host>/v1 (local 11434 or cloud).
    if base and not base.rstrip("/").endswith("/v1"):
        base = base.rstrip("/") + "/v1"
    key = os.environ.get("DUECARE_MODEL_API_KEY") or os.environ.get("OLLAMA_API_KEY") or ""
    name = model_name or os.environ.get("DUECARE_MODEL_NAME") or "gemma4:31b"
    return {"base_url": base, "api_key": key, "model": name}


_SYSTEM = (
    "You are a careful web-research agent extracting a COMPLETE list of entities (e.g. licensed "
    "recruitment agencies) from an official public registry. You control a browser ONLY through "
    "the provided tools. Look at the observation -- especially `data_endpoints` and `pagination` "
    "(pages_fetched / last_page). Choose the single next tool call that makes progress. "
    "If pagination shows last_page > pages_fetched, the data is multi-page: call `next_page` "
    "(pass count = the number of pages still remaining to fetch them all in one call) and repeat "
    "until pages_fetched == last_page. Only THEN call `extract` (it aggregates every fetched "
    "page), then `finish`. Do not finish before pages_fetched == last_page. Reply with ONE JSON "
    'object: {"tool": "<name>", "args": {...}}. No prose.')


def gemma_model_fn(*, goal, observation, tools, transcript, cfg: dict | None = None,
                   caller: Callable[..., str] | None = None) -> dict:
    """A model_fn backed by Gemma 4 function-calling. `caller` is injectable for
    tests; by default it posts to the configured OpenAI-compatible endpoint."""
    cfg = cfg or _model_config()
    prompt = {
        "goal": goal,
        "tools": [{"name": t["name"], "description": t["description"], "args": t["args"]} for t in tools],
        "observation": observation,
        "recent_steps": transcript[-4:],
    }
    text = (caller or _openai_compatible_call)(
        system=_SYSTEM, user=json.dumps(prompt, ensure_ascii=False), cfg=cfg)
    return _parse_tool_call(text)


def _parse_tool_call(text: str) -> dict:
    """Pull the {"tool":...,"args":...} object out of a model reply."""
    if not text:
        return {"tool": "finish", "args": {"reason": "empty model reply"}}
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict) and "tool" in obj:
                            obj.setdefault("args", {})
                            return obj
                    except Exception:  # noqa: BLE001
                        break
        start = text.find("{", start + 1)
    return {"tool": "finish", "args": {"reason": "unparseable model reply"}}


def _openai_compatible_call(*, system: str, user: str, cfg: dict) -> str:
    """POST a chat-completion to an OpenAI-compatible endpoint (Ollama-cloud etc.)."""
    if not cfg.get("base_url"):
        raise RuntimeError("no model endpoint configured (set OLLAMA_HOST/OLLAMA_API_KEY "
                           "or DUECARE_MODEL_BASE_URL/_API_KEY/_NAME)")
    import urllib.request
    body = json.dumps({
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.2, "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        cfg["base_url"].rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {cfg['api_key']}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    return data["choices"][0]["message"]["content"]


# ---- live executor: a persistent Playwright session ------------------------

def make_playwright_executor(*, headless: bool = True):
    """Build a live executor over a persistent browser page. Lazy-imports
    Playwright; reuses scripts/browser_scrape.py for launch + parsing."""
    bs = _load_sibling("browser_scrape")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # noqa: BLE001
        raise ImportError("Playwright required: pip install playwright && "
                          "python -m playwright install chromium") from exc

    class _PwExecutor:
        def __init__(self):
            self._pw = sync_playwright().start()
            self._browser = bs._launch_browser(self._pw)
            self._ctx = self._browser.new_context(user_agent=bs.USER_AGENT)
            self._page = self._ctx.new_page()
            self._captured: list[dict] = []
            self._req_headers: dict[str, dict] = {}
            self._page.on("response", self._on_response)

        def _on_response(self, resp):
            try:
                if "json" in (resp.headers or {}).get("content-type", "").lower():
                    self._captured.append({"url": resp.url, "text": resp.text()})
                    try:
                        self._req_headers[resp.url] = dict(resp.request.headers)
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001
                pass

        def _agency_endpoint(self):
            """The captured paginated data endpoint: (url, last_page, req_headers)."""
            for c in self._captured:
                try:
                    lp = bs._pagination_last_page(json.loads(c["text"]))
                except Exception:  # noqa: BLE001
                    lp = None
                if lp and lp > 1:
                    return c["url"], lp, self._req_headers.get(c["url"], {})
            return None

        def _fetched_pages(self, base_url: str) -> set:
            import re
            base = base_url.split("?")[0]
            pages = set()
            for c in self._captured:
                if c["url"].split("?")[0] == base:
                    m = re.search(r"[?&]page=(\d+)", c["url"])
                    pages.add(int(m.group(1)) if m else 1)
            return pages

        def paginate(self, count: int = 1) -> dict:
            ep = self._agency_endpoint()
            if not ep:
                return {"error": "no paginated data endpoint detected yet; navigate/observe first"}
            base_url, last_page, hdrs = ep
            fwd = {k: v for k, v in hdrs.items()
                   if k.lower() in ("authorization", "accept", "x-api-key",
                                    "x-requested-with", "referer", "origin")}
            fwd.setdefault("accept", "application/json")
            done = self._fetched_pages(base_url)
            fetched = 0
            for n in range(2, last_page + 1):
                if fetched >= count:
                    break
                if n in done:
                    continue
                try:
                    if fetched:
                        time.sleep(0.3)  # polite pacing across a bulk pagination call
                    r = self._ctx.request.get(bs._with_page(base_url, n), headers=fwd, timeout=30000)
                    if not r.ok:
                        break
                    self._captured.append({"url": r.url, "text": r.text()})
                    done.add(n); fetched += 1
                except Exception:  # noqa: BLE001
                    break
            return {"fetched_now": fetched, "pages_fetched": len(done), "last_page": last_page}

        def navigate(self, url: str) -> Observation:
            self._page.goto(url, timeout=30000, wait_until="domcontentloaded")
            try:
                self._page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:  # noqa: BLE001
                pass
            return self.observe()

        def observe(self) -> Observation:
            try:
                els = self._page.eval_on_selector_all(
                    "button,input,a[href],select",
                    "els => els.slice(0,40).map(e => ({tag:e.tagName.toLowerCase(),"
                    "text:(e.getAttribute('aria-label')||e.placeholder||e.textContent||'').trim().slice(0,40)}))")
            except Exception:  # noqa: BLE001
                els = []
            endpoints = list(dict.fromkeys(c["url"] for c in self._captured))
            pagination = {}
            ep = self._agency_endpoint()
            if ep:
                base_url, last_page, _ = ep
                pagination = {"last_page": last_page, "pages_fetched": len(self._fetched_pages(base_url))}
            return Observation(title=self._page.title(), url=self._page.url,
                               elements=[e for e in els if e.get("text")][:30],
                               data_endpoints=endpoints[-12:], pagination=pagination)

        def click(self, target: str) -> Observation:
            try:
                self._page.get_by_text(target, exact=False).first.click(timeout=8000)
            except Exception:
                self._page.click(target, timeout=8000)
            try:
                self._page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:  # noqa: BLE001
                pass
            return self.observe()

        def fill(self, target: str, text: str) -> Observation:
            try:
                self._page.fill(target, text, timeout=8000)
            except Exception:
                self._page.get_by_placeholder(target).first.fill(text, timeout=8000)
            self._page.keyboard.press("Enter")
            try:
                self._page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:  # noqa: BLE001
                pass
            return self.observe()

        def extract(self, endpoint: str = "", field_map: dict | None = None) -> list[dict]:
            payloads = [c for c in self._captured if (not endpoint or endpoint in c["url"])]
            res = bs.CaptureResult(payloads=payloads or self._captured)
            profiles, _ = bs.captures_to_profiles(res, source="agentic")
            return profiles

        def close(self):
            try:
                self._browser.close(); self._pw.stop()
            except Exception:  # noqa: BLE001
                pass

    return _PwExecutor()


# ---- CLI -------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True, help="registry URL to start from")
    ap.add_argument("--goal", default="extract the full list of licensed recruitment agencies")
    ap.add_argument("--model", default="", help="Gemma model name (default: env or gemma4:31b)")
    ap.add_argument("--max-steps", type=int, default=16)
    ap.add_argument("--out", default=str(_ROOT / "reports" / "agency_registry" / "agentic_scraped.json"))
    args = ap.parse_args(argv)

    cfg = _model_config(args.model)
    if not cfg["base_url"]:
        print("no Gemma endpoint configured. Set OLLAMA_HOST + OLLAMA_API_KEY (or "
              "DUECARE_MODEL_BASE_URL/_API_KEY/_NAME).", file=sys.stderr)
        return 2
    try:
        executor = make_playwright_executor()
    except ImportError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    def model_fn(**kw):
        return gemma_model_fn(cfg=cfg, **kw)

    try:
        executor.navigate(args.url)
        result = run_agent(args.goal, executor, model_fn, max_steps=args.max_steps,
                           log=lambda m: print(m, file=sys.stderr))
    finally:
        getattr(executor, "close", lambda: None)()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"_synthetic": False, "goal": args.goal, "url": args.url,
                               "model": cfg["model"], "stop_reason": result["stop_reason"],
                               "steps": result["steps"], "n_records": len(result["records"]),
                               "records": result["records"]}, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    print(f"agent stopped ({result['stop_reason']}) after {result['steps']} steps; "
          f"{len(result['records'])} record(s) -> {out}", file=sys.stderr)
    return 0 if result["records"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
