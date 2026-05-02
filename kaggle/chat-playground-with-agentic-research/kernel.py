"""
============================================================================
  DUECARE CHAT PLAYGROUND with AGENTIC RESEARCH -- Kaggle notebook
============================================================================

  APPENDIX A4. Proof-of-concept: agentic web research as a FIFTH harness
  layer alongside Persona / GREP / RAG / Tools.

  Same chat UI conceptually as chat-playground-with-grep-rag-tools, but
  with FIVE toggle tiles instead of four. The new tile:

      Agentic   Gemma 4 multi-step web research loop. When ON, before
                 Gemma generates the chat response, an inner loop runs:
                   step 1 -- Gemma decides whether the query needs the web
                   step 2 -- if yes, picks a tool: web_search, web_fetch,
                              wikipedia
                   step 3 -- Gemma reads the result, decides next action
                              or "done"
                   loop until done OR step-limit (default 5)
                 The findings are appended to the pre-context Gemma sees
                 alongside GREP hits + RAG docs + Tool results.

  The three open-source tools (no API keys required):

      web_search   DuckDuckGo HTML scrape
      web_fetch    httpx + trafilatura (Markdown extraction)
      wikipedia    Wikipedia REST API (free, no key)

  All three live in duecare-llm-research-tools. All three pass through
  the existing PIIFilter before any network call -- the same hard gate
  that protects the in-house tools.

  Why this is APPENDIX:
    - Adds ~10 sec latency per agentic turn
    - Requires Internet ON (the other notebooks are happy offline)
    - Demonstrates the *concept* of "agentic research" before judges
      see it integrated into the live-demo
    - Standalone proof; not required for end-user deployment

  Requires:
    - GPU T4 x2 (default e4b-it; works on single T4 too)
    - Internet ON (mandatory for agentic loop)
    - Datasets attached:
        taylorsamarel/duecare-chat-playground-with-agentic-research-wheels
        google/gemma-4 (any IT variant)
    - HF_TOKEN OPTIONAL

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms
  of Use (https://ai.google.dev/gemma/terms).
============================================================================
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
DATASET_SLUG = "duecare-chat-playground-with-agentic-research-wheels"

GEMMA_MODEL_VARIANT = "e4b-it"          # "e2b-it" | "e4b-it" | "26b-a4b-it" | "31b-it"
GEMMA_LOAD_IN_4BIT  = True
GEMMA_DEVICE_MAP    = "auto"
GEMMA_MAX_SEQ_LEN   = 8192

PORT   = 8080
TUNNEL = "cloudflared"

# Agentic loop config
AGENT_MAX_STEPS    = 5      # max tool calls per agentic turn
AGENT_STEP_TIMEOUT = 30     # seconds per Gemma decision
AGENT_FETCH_CHARS  = 6000   # chars to keep per fetched page

# Trafilatura is optional (better extraction). Falls back to regex strip.
INSTALL_TRAFILATURA = True

# Playwright for the real-browser path (no API keys for major search
# engines). Adds ~400 MB of Chromium download but lets the agent
# actually navigate brave.com / duckduckgo.com / ecosia.org via real
# browser UIs instead of paid APIs. Set to False if you prefer the
# DDG HTML scrape fallback only.
INSTALL_PLAYWRIGHT = True

GEMMA_HF_REPO_VARIANT = (
    GEMMA_MODEL_VARIANT
    .replace("e2b-it", "E2B-it").replace("e4b-it", "E4B-it")
    .replace("26b-a4b-it", "26B-A4B-it").replace("31b-it", "31B-it"))


# ===========================================================================
# Inline persona (mirror of duecare.chat.app.DEFAULT_PERSONA)
# ===========================================================================
DUECARE_PERSONA = (
    "You are an international anti-trafficking in persons and modern-day "
    "slavery expert with 40 years of dedicated experience combating human "
    "exploitation, illicit recruitment, debt bondage, and labour abuses. "
    "You hold deep, current knowledge of ILO conventions (C029/C181/C189), "
    "national recruitment statutes (POEA MCs, BP2MI Reg, Nepal FEA, HK "
    "Employment Ord., HK Money Lenders Ord.), corridor fee caps, fee "
    "camouflage tactics, and NGO partner organisations (POEA, BP2MI, "
    "Polaris, IJM, ECPAT, Mission for Migrant Workers HK). When the user "
    "describes a scenario: identify red flags, cite ILO + national "
    "statutes by section, name the controlling fee cap if a corridor is "
    "involved, refer the user to the appropriate NGO/regulator hotline. "
    "DO NOT provide operational optimization advice for any scheme "
    "containing trafficking indicators."
)


# ===========================================================================
# PHASE 0 -- Hanchen's Unsloth stack (only for big variants)
# ===========================================================================
_UNSLOTH_MARKER = Path("/tmp/.duecare_agentic_unsloth_v1_done")


def _need_unsloth() -> bool:
    return GEMMA_MODEL_VARIANT in ("31b-it", "26b-a4b-it")


def _install_unsloth() -> bool:
    print("=" * 76)
    print("[phase 0] installing Hanchen's Unsloth Gemma 4 stack")
    print("=" * 76)
    try:
        import numpy as _np_v, PIL as _pil_v
        np_pin = f"numpy=={_np_v.__version__}"
        pil_pin = f"pillow=={_pil_v.__version__}"
    except Exception:
        np_pin, pil_pin = "numpy", "pillow"
    if subprocess.run(["uv", "--version"], capture_output=True).returncode == 0:
        installer = ["uv", "pip", "install", "-qqq", "--system"]
    else:
        installer = [sys.executable, "-m", "pip", "install",
                     "-q", "--no-input", "--disable-pip-version-check"]
    cmd = installer + [
        "torch>=2.8.0", "triton>=3.4.0", np_pin, pil_pin,
        "torchvision", "bitsandbytes",
        "unsloth", "unsloth_zoo>=2026.4.6",
        "transformers==5.5.0", "torchcodec", "timm",
    ]
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  install FAILED: {proc.stderr[-600:]}")
        return False
    print(f"  installed in {time.time()-t0:.0f}s")
    try:
        _UNSLOTH_MARKER.write_text(json.dumps(
            {"variant": GEMMA_MODEL_VARIANT,
             "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))
    except Exception:
        pass
    return True


if _need_unsloth() and not _UNSLOTH_MARKER.exists():
    if not _install_unsloth():
        sys.exit("[phase 0] aborting -- Unsloth stack install failed")


# ===========================================================================
# PHASE 1 -- duecare wheels + server deps + trafilatura
# ===========================================================================
print("=" * 76)
print("[phase 1] installing wheels + server deps + trafilatura")
print("=" * 76)


def install_wheels() -> int:
    if not Path("/kaggle/input").exists():
        return 0
    found = sorted(p for p in Path("/kaggle/input").rglob("*.whl")
                    if "duecare" in p.name.lower())
    print(f"  found {len(found)} duecare wheel(s)")
    if found:
        cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--no-input",
               "--disable-pip-version-check", *[str(p) for p in found]]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print(f"  installed {len(found)} wheels")
            for mod in list(sys.modules):
                if mod == "duecare" or mod.startswith("duecare."):
                    del sys.modules[mod]
        else:
            print(f"  bulk install failed: {proc.stderr[-300:]}")
    return len(found)


install_wheels()
extras = ["fastapi>=0.115.0", "uvicorn>=0.30.0"]
if INSTALL_TRAFILATURA:
    extras.append("trafilatura>=1.12")
if INSTALL_PLAYWRIGHT:
    extras.append("playwright>=1.48")
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                "--no-input", "--disable-pip-version-check", *extras],
                capture_output=True, text=True)
print(f"  installed: {' '.join(extras)}")

# Playwright needs Chromium downloaded once. Skip --with-deps on Kaggle
# (no apt root); Chromium ships with what it needs in its userland tarball.
if INSTALL_PLAYWRIGHT:
    print("  installing Chromium for Playwright (one-time, ~150 MB)...")
    cf_t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True, text=True, timeout=600)
    if proc.returncode == 0:
        print(f"  ✓ Chromium installed in {time.time()-cf_t0:.0f}s")
    else:
        print(f"  WARN: Chromium install failed ({proc.returncode}): "
              f"{proc.stderr[-300:]}. Browser tool will be unavailable; "
              f"agent will fall back to DDG HTML scrape.")



# ===========================================================================
# CLEAN SHUTDOWN -- /api/shutdown POST + /shutdown GET + floating button.
# Users can:
#   (1) click the floating "Shutdown" button in the top-right of the UI
#   (2) open <public-url>/shutdown for a full confirmation page
#   (3) POST /api/shutdown directly (curl, etc.)
# All three signal the main loop to exit; cleanup runs after.
# ===========================================================================
import threading as _shutdown_threading
_SHUTDOWN_EVENT = _shutdown_threading.Event()
_CLOUDFLARED_PROC: dict = {"p": None}


_SHUTDOWN_BUTTON_SNIPPET = """
<style>
  #_dc-shutdown-btn { position: fixed; top: 12px; right: 12px; z-index: 99999;
    background: #dc2626; color: white; padding: 8px 14px;
    border-radius: 8px; font-family: -apple-system,system-ui,sans-serif;
    font-weight: 700; font-size: 12px; cursor: pointer; border: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.18); }
  #_dc-shutdown-btn:hover { background: #991b1b; }
</style>
<button id="_dc-shutdown-btn" onclick="
  if(!confirm('Shut down Duecare?')) return;
  fetch('/api/shutdown',{method:'POST'}).then(()=>{
    document.body.innerHTML=
      '<div style=\"padding:60px;text-align:center;font-family:system-ui\">'+
      '<h1 style=\"color:#047857\">Shutting down\u2026</h1>'+
      '<p style=\"color:#6b7280\">You can close this tab.</p></div>';
  });
">\u23FB Shutdown</button>
"""

_HIDE_HARNESS_TILES_SNIPPET = """
<style>
  #harness-tiles, [id^='tile-'], .harness-tile { display: none !important; }
</style>
"""


def _attach_shutdown(app, hide_harness_tiles: bool = False) -> None:
    """Bolt /api/shutdown + /shutdown + floating button onto any FastAPI app."""
    from fastapi.responses import HTMLResponse, JSONResponse
    from starlette.middleware.base import BaseHTTPMiddleware

    def _api_shutdown():
        _shutdown_threading.Thread(
            target=lambda: (time.sleep(0.5), _SHUTDOWN_EVENT.set()),
            daemon=True, name="shutdown-fire").start()
        return JSONResponse({"shutting_down": True,
                             "message": "Cell will exit within ~5 seconds."})

    def _shutdown_page():
        html = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Shut down Duecare</title><style>"
            "body{font-family:-apple-system,system-ui,sans-serif;"
            "background:#f8fafc;color:#1f2937;display:flex;"
            "align-items:center;justify-content:center;min-height:100vh;"
            "margin:0}.box{background:white;border:1px solid #e5e7eb;"
            "border-radius:14px;padding:40px 50px;text-align:center;"
            "max-width:480px}h1{color:#dc2626;margin:0 0 14px}"
            "p{color:#6b7280;line-height:1.6;margin:0 0 24px}"
            "button{background:#dc2626;color:white;padding:12px 28px;"
            "border:none;border-radius:10px;font-weight:700;font-size:15px;"
            "cursor:pointer}button:hover{background:#991b1b}"
            ".meta{color:#6b7280;font-size:12px;margin-top:18px}"
            "</style></head><body><div class='box'>"
            "<h1>Shut down Duecare?</h1>"
            "<p>Stops the FastAPI server, closes the browser session "
            "(if any), terminates the cloudflared tunnel, and exits "
            "the Kaggle cell. Re-run the cell to restart.</p>"
            "<button onclick='doShutdown()'>Confirm shutdown</button>"
            "<div class='meta' id='status'></div></div>"
            "<script>async function doShutdown(){"
            "document.getElementById('status').textContent='shutting down...';"
            "try{await fetch('/api/shutdown',{method:'POST'});"
            "document.querySelector('.box').innerHTML="
            "\"<h1 style='color:#047857'>Shutting down</h1>\"+"
            "\"<p>You can close this tab. The Kaggle cell will exit shortly.</p>\";"
            "}catch(e){document.getElementById('status').textContent='error: '+e.message;}}"
            "</script></body></html>")
        return HTMLResponse(html)

    app.add_api_route("/api/shutdown", _api_shutdown, methods=["POST"])
    app.add_api_route("/shutdown", _shutdown_page, methods=["GET"])

    # Inject the floating shutdown button into the main page via middleware.
    # Filters: only path "/" + content-type text/html. Streaming endpoints
    # like /api/chat (SSE / JSON) pass through untouched.
    extras = _SHUTDOWN_BUTTON_SNIPPET
    if hide_harness_tiles:
        extras = _HIDE_HARNESS_TILES_SNIPPET + extras

    class _UIInjector(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if request.url.path != "/":
                return response
            ct = response.headers.get("content-type", "")
            if not ct.startswith("text/html"):
                return response
            chunks = []
            async for c in response.body_iterator:
                chunks.append(c)
            try:
                html = b"".join(chunks).decode("utf-8")
            except UnicodeDecodeError:
                return response
            if "</body>" in html:
                html = html.replace("</body>", extras + "</body>", 1)
            else:
                html = html + extras
            new_headers = {k: v for k, v in response.headers.items()
                           if k.lower() != "content-length"}
            return HTMLResponse(html,
                                status_code=response.status_code,
                                headers=new_headers)

    app.add_middleware(_UIInjector)

# ===========================================================================
# PHASE 2 -- Load Gemma 4
# ===========================================================================
print("=" * 76)
print(f"[phase 2] loading Gemma 4 ({GEMMA_MODEL_VARIANT})")
print("=" * 76)


@dataclass
class LoadedModel:
    model: Any
    tokenizer: Any
    variant: str
    backend_call: Any


def load_gemma() -> Optional[LoadedModel]:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        if out.returncode != 0 or not out.stdout.strip():
            print("  no GPU detected")
            return None
        lines = [l.strip() for l in out.stdout.strip().split("\n") if l.strip()]
        gpu_count = len(lines)
        print(f"  GPU: {lines[0].split(',')[0].strip()} x{gpu_count}")
    except Exception as e:
        print(f"  nvidia-smi failed: {e}")
        return None

    if not os.environ.get("HF_TOKEN"):
        try:
            from kaggle_secrets import UserSecretsClient   # type: ignore
            for label in ("HF_TOKEN", "HUGGINGFACE_TOKEN"):
                try:
                    tok = UserSecretsClient().get_secret(label)
                    if tok:
                        os.environ["HF_TOKEN"] = tok.strip()
                        break
                except Exception:
                    continue
        except Exception:
            pass

    import torch
    if _need_unsloth():
        try:
            from unsloth import FastModel
            from unsloth.chat_templates import get_chat_template
        except Exception as e:
            print(f"  unsloth import FAILED: {e}")
            return None
        repo = f"unsloth/gemma-4-{GEMMA_HF_REPO_VARIANT}"
        device_map = "balanced" if (gpu_count >= 2) else "auto"
        try:
            model, tokenizer = FastModel.from_pretrained(
                model_name=repo, dtype=None,
                max_seq_length=GEMMA_MAX_SEQ_LEN,
                load_in_4bit=GEMMA_LOAD_IN_4BIT,
                full_finetuning=False, device_map=device_map)
        except Exception as e:
            print(f"  FastModel failed: {e}")
            return None
        try:
            tokenizer = get_chat_template(tokenizer,
                                           chat_template="gemma-4-thinking")
        except Exception:
            pass
    else:
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
        except Exception as e:
            print(f"  transformers import failed: {e}")
            return None
        repo = f"google/gemma-4-{GEMMA_MODEL_VARIANT}"
        try:
            tokenizer = AutoTokenizer.from_pretrained(repo)
            model = AutoModelForCausalLM.from_pretrained(
                repo, device_map="auto",
                torch_dtype=torch.bfloat16,
                load_in_4bit=GEMMA_LOAD_IN_4BIT)
        except Exception as e:
            print(f"  transformers load failed: {e}")
            return None

    def _gemma(messages, max_new_tokens=512, temperature=0.7,
               top_p=0.95, top_k=64):
        inputs = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True,
            tokenize=True, return_dict=True, return_tensors="pt").to("cuda")
        with torch.inference_mode():
            out = model.generate(
                **inputs, max_new_tokens=max_new_tokens, use_cache=True,
                temperature=temperature, top_p=top_p, top_k=top_k,
                pad_token_id=tokenizer.eos_token_id)
        text = tokenizer.batch_decode(out)[0]
        if "<|turn>model" in text:
            text = text.split("<|turn>model", 1)[1]
        if "<channel|>" in text:
            text = text.split("<channel|>", 1)[1]
        text = text.split("<turn|>", 1)[0]
        return text.replace("<bos>", "").replace("<eos>", "").strip()

    return LoadedModel(model=model, tokenizer=tokenizer,
                       variant=GEMMA_MODEL_VARIANT,
                       backend_call=_gemma)


LOADED = load_gemma()
if LOADED is None:
    sys.exit("[phase 2] could not load Gemma -- aborting")
GEMMA = LOADED.backend_call
print(f"  loaded.")


# ===========================================================================
# PHASE 3 -- Wire harness primitives + research tools
# ===========================================================================
print("=" * 76)
print("[phase 3] wiring harness + research tools")
print("=" * 76)

from duecare.chat.harness import (
    default_harness, GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH,
)
from duecare.research_tools import (
    WebFetchTool, WikipediaTool, PIIFilter,
    FastWebSearchTool, BrowserTool, get_recent_audit,
)

HARNESS = default_harness()
GREP_FN  = HARNESS["grep_call"]
RAG_FN   = HARNESS["rag_call"]
TOOLS_FN = HARNESS["tools_call"]
print(f"  harness: GREP={len(GREP_RULES)} RAG={len(RAG_CORPUS)} "
      f"Tools={len(_TOOL_DISPATCH)}")

# PII filter -- HARD GATE. Every outbound web query passes through this
# BEFORE the network call. Composite victim names are explicitly NOT in
# the allow_org_names list -- only public agency names that look like
# person names (per the existing PIIFilter heuristic).
PII = PIIFilter(allow_org_names=[
    "Pacific Coast Manpower",
    "Hong Kong City Credit Management Group",
    "Al-Rashid Household Services",   # public composite agency names only
])

# BYOK architecture: NO API keys are read from env or Kaggle Secrets at
# startup. The user pastes keys into the BYOK panel in the UI; those
# keys are stored in their browser localStorage and sent on each
# /api/chat request as a `byok_keys` dict. The dispatcher routes:
#
#   byok_keys.tavily   -> Tavily API (free 1k/mo)
#   byok_keys.brave    -> Brave Search API (free 2k/mo)
#   byok_keys.serper   -> Serper / Google (paid)
#   no keys            -> BrowserTool (Playwright real browser via
#                          brave.com / duckduckgo.com / ecosia.org)
#                          OR DDG HTML scrape (last resort)
#
# Every call passes through PIIFilter first; every search is audit-logged
# (sha256 of query, never plaintext).
SEARCH  = FastWebSearchTool(pii_filter=PII, max_results=5,
                              prefer_browser_fallback=True)
BROWSER = BrowserTool(pii_filter=PII)
FETCH   = WebFetchTool(pii_filter=PII, max_chars=AGENT_FETCH_CHARS)
WIKI    = WikipediaTool(pii_filter=PII)
print(f"  research tools wired:")
print(f"    fast_web_search  (BYOK dispatcher; per-call key from request)")
print(f"    browser          (Playwright real browser; "
      f"available={BROWSER.available})")
print(f"    web_fetch        (httpx + trafilatura)")
print(f"    wikipedia        (REST API, no key)")
print(f"  all PII-filtered + audit-logged")


# ===========================================================================
# Agentic loop
# ===========================================================================
def _make_agent_tools(byok_keys: Optional[dict] = None) -> dict:
    """Build the per-turn tool dispatch with BYOK keys baked in.
    byok_keys is a dict like {'tavily':'...', 'brave':'...', ...} from
    the user's BYOK panel. Empty dict -> no-key paths only."""
    bk = byok_keys or {}
    backend_desc = FastWebSearchTool.describe_backend(bk)
    return {
        "web_search": {
            "callable": lambda **kw: SEARCH.search(byok_keys=bk, **kw),
            "schema": {
                "name": "web_search",
                "description": (f"Web search ({backend_desc['note']}). "
                                f"Use when you need to find URLs about "
                                f"a topic. Returns title + URL + snippet."),
                "params": {"query": "str (required)",
                           "max_results": "int (default 5)"},
            },
        },
        "browser_open": {
            "callable": lambda **kw: BROWSER.navigate(**kw),
            "schema": {
                "name": "browser_open",
                "description": ("Open a URL in the headless browser "
                                "(Playwright). Use to LOAD a page; pair "
                                "with browser_extract or browser_links."),
                "params": {"url": "str (required, http(s)://)"},
            },
        },
        "browser_extract": {
            "callable": lambda **kw: BROWSER.extract_text(**kw),
            "schema": {
                "name": "browser_extract",
                "description": ("Extract text from the currently-open "
                                "browser page. Optionally scope to a CSS "
                                "selector."),
                "params": {"selector": "str (optional CSS selector)",
                           "max_chars": "int (default 8000)"},
            },
        },
        "browser_links": {
            "callable": lambda **kw: BROWSER.get_links(**kw),
            "schema": {
                "name": "browser_links",
                "description": ("Return all <a href> links on the "
                                "currently-open browser page."),
                "params": {"max_links": "int (default 50)"},
            },
        },
        "web_fetch": {
            "callable": lambda **kw: FETCH.fetch(**kw),
            "schema": {
                "name": "web_fetch",
                "description": ("Fetch a single URL and extract its main "
                                "content as Markdown via trafilatura "
                                "(no browser needed; faster than browser_open "
                                "for simple HTML pages)."),
                "params": {"url": "str (required, http(s)://)"},
            },
        },
        "wikipedia": {
            "callable": lambda **kw: WIKI.lookup(**kw),
            "schema": {
                "name": "wikipedia",
                "description": ("Look up a Wikipedia article by title. "
                                "Best for stable legal/historical "
                                "references (ILO conventions, statutes, "
                                "treaties)."),
                "params": {"title": "str (required)"},
            },
        },
    }


# Default tool palette (no BYOK keys; for startup logs)
AGENT_TOOLS = _make_agent_tools()


_AGENT_DECISION_PROMPT = """\
You are a research assistant for a migrant-worker safety expert. The
user has asked a question. Decide whether to search the web for
context, and if so, which tool to call.

Available tools:
{tools}

Past research steps (in order):
{past_steps}

User question:
{user_question}

Respond with ONE of these strict-JSON formats and nothing else:

If you have enough info to answer (or further search won't help):
{{"action": "done", "reason": "<short why>"}}

If you want to call a tool:
{{"action": "tool", "tool": "<name>", "args": {{"<arg>": "<val>", ...}}, "reason": "<short why>"}}
"""


def _format_tool_schemas(tool_dict: Optional[dict] = None) -> str:
    tools = tool_dict or AGENT_TOOLS
    lines = []
    for t in tools.values():
        s = t["schema"]
        params = ", ".join(f"{k}: {v}" for k, v in s["params"].items())
        lines.append(f"  - {s['name']}({params}) -- {s['description']}")
    return "\n".join(lines)


def _format_past_steps(steps: list) -> str:
    if not steps:
        return "  (no past steps)"
    out = []
    for i, s in enumerate(steps, 1):
        out.append(f"  [{i}] called {s['tool']} with {s['args']}")
        # Summarize the result
        result_summary = (s.get("result_summary") or "")[:240]
        out.append(f"      -> {result_summary}")
    return "\n".join(out)


def _parse_decision(text: str) -> dict:
    """Best-effort JSON parse. Strip markdown fences if present."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
        t = t.strip()
    if t.startswith("json"):
        t = t[4:].strip()
    # Find first { ... } block
    m = re.search(r"\{.*\}", t, re.DOTALL)
    if m:
        t = m.group(0)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        return {"action": "done", "reason": f"could not parse: {text[:120]}"}


def run_agent(user_question: str,
              byok_keys: Optional[dict] = None) -> dict:
    """Multi-step agentic loop. Gemma decides search/fetch/wiki/done.
    byok_keys is the per-request BYOK dict from the UI panel."""
    tools = _make_agent_tools(byok_keys=byok_keys)
    steps = []
    findings = []
    for step_idx in range(AGENT_MAX_STEPS):
        prompt = _AGENT_DECISION_PROMPT.format(
            tools=_format_tool_schemas(tools),
            past_steps=_format_past_steps(steps),
            user_question=user_question,
        )
        msgs = [
            {"role": "system",
             "content": [{"type": "text",
                          "text": "You output ONLY the requested JSON. "
                                  "No preamble, no markdown."}]},
            {"role": "user", "content": [{"type": "text", "text": prompt}]},
        ]
        try:
            raw = GEMMA(msgs, max_new_tokens=200, temperature=0.3)
        except Exception as e:
            steps.append({"step": step_idx + 1, "error": f"gemma decide: {e}"})
            break
        decision = _parse_decision(raw)
        action = decision.get("action", "done")
        if action == "done":
            steps.append({"step": step_idx + 1, "action": "done",
                          "reason": decision.get("reason", "")})
            break
        tool_name = decision.get("tool", "")
        args = decision.get("args", {}) or {}
        tool = tools.get(tool_name)
        if tool is None:
            steps.append({"step": step_idx + 1,
                          "action": "error",
                          "error": f"unknown tool: {tool_name}",
                          "raw_decision": raw[:200]})
            break
        # Run the tool
        try:
            result = tool["callable"](**args)
        except Exception as e:
            steps.append({"step": step_idx + 1, "tool": tool_name,
                          "args": args, "error": str(e)})
            break

        # Summarize the result for the next step's context
        if not result.success:
            result_summary = f"ERROR: {result.error}"
        else:
            if tool_name == "web_search":
                items = result.items[:5]
                result_summary = (
                    f"{len(items)} results. " +
                    "; ".join(f"[{i+1}] {it['title'][:60]} ({it['url'][:60]})"
                              for i, it in enumerate(items)))
            elif tool_name == "web_fetch":
                if result.items:
                    item = result.items[0]
                    result_summary = (
                        f"{item.get('title', '?')[:80]}: "
                        f"{item.get('text', '')[:300]}")
                else:
                    result_summary = "(empty)"
            elif tool_name == "wikipedia":
                if result.items:
                    item = result.items[0]
                    result_summary = (
                        f"{item.get('title', '?')}: "
                        f"{item.get('extract', '')[:300]}")
                else:
                    result_summary = "(no article)"
            else:
                result_summary = result.summary or "(no summary)"

        steps.append({
            "step":           step_idx + 1,
            "action":         "tool",
            "tool":           tool_name,
            "args":           args,
            "reason":         decision.get("reason", ""),
            "result_summary": result_summary,
            "success":        result.success,
        })
        # Save the full result to findings for inclusion in pre-context
        if result.success:
            findings.append({
                "tool":  tool_name,
                "args":  args,
                "items": result.items,
            })
    return {"steps": steps, "findings": findings}


def format_agent_findings(agent_out: dict) -> str:
    """Compose the agent findings into a pre-context block Gemma will read."""
    if not agent_out.get("findings"):
        return ""
    lines = ["=== AGENTIC RESEARCH FINDINGS ==="]
    for f in agent_out["findings"]:
        tool = f["tool"]
        args = f["args"]
        items = f["items"]
        if tool == "web_search":
            lines.append(f"[search] {args.get('query', '')!r}:")
            for it in items[:3]:
                lines.append(f"  - {it.get('title', '?')[:80]}")
                lines.append(f"    {it.get('url', '')}")
                lines.append(f"    {it.get('snippet', '')[:200]}")
        elif tool == "web_fetch":
            for it in items[:1]:
                lines.append(f"[fetched] {it.get('url', '')}")
                lines.append(f"  title: {it.get('title', '')[:120]}")
                text = it.get("text", "")[:1500]
                lines.append(f"  excerpt:\n  {text}")
        elif tool == "wikipedia":
            for it in items[:1]:
                lines.append(f"[wikipedia] {it.get('title', '')}")
                lines.append(f"  {it.get('extract', '')[:1200]}")
    return "\n".join(lines)


# ===========================================================================
# FastAPI app + UI
# ===========================================================================
print("=" * 76)
print("[phase 4] launching FastAPI server")
print("=" * 76)

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Duecare Chat with Agentic Research")
_attach_shutdown(app)


class ChatRequest(BaseModel):
    message: str
    history: list = []          # [{role, content}, ...]
    persona_on: bool = True
    grep_on: bool = True
    rag_on: bool = True
    tools_on: bool = True
    agentic_on: bool = True
    max_new_tokens: int = 1024
    # BYOK -- bring-your-own-key. Any subset; empty dict = no-key paths only.
    byok_keys: dict = {}


@app.get("/")
def index() -> HTMLResponse:
    return HTMLResponse(_PAGE_HTML)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "model": GEMMA_MODEL_VARIANT}


class BackendProbeRequest(BaseModel):
    byok_keys: dict = {}


@app.post("/api/backends")
def backends(req: BackendProbeRequest) -> dict:
    """Tell the UI which backend would be picked given the user's
    current BYOK keys. Called whenever the user types/clears a key in
    the BYOK panel so the active-backend label updates live."""
    info = FastWebSearchTool.describe_backend(req.byok_keys)
    return {
        "active":     info["backend"],
        "kind":       info["kind"],          # "byok-api" | "no-key"
        "note":       info["note"],
        "pii_filter": "active",
        "audit_log":  str(Path("/kaggle/working/duecare_search_audit.jsonl")),
        "browser_available": BROWSER.available,
    }


@app.get("/api/audit")
def audit(limit: int = 20) -> dict:
    """Recent search audit entries. Plaintext queries NOT included --
    only sha256 hashes + metadata."""
    return {"recent": get_recent_audit(limit=limit)}


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    pre_blocks = []
    grep_hits = []
    rag_docs = []
    tool_calls = []
    agent = {"steps": [], "findings": []}

    if req.grep_on:
        grep_out = GREP_FN(req.message)
        grep_hits = grep_out.get("hits", [])
        if grep_hits:
            pre_blocks.append("=== GREP HITS ===\n" + "\n".join(
                f"- [{h.get('severity', '?').upper()}] {h.get('rule')}: "
                f"{h.get('citation', '')}" for h in grep_hits[:6]))

    if req.rag_on:
        rag_out = RAG_FN(req.message, top_k=3)
        rag_docs = rag_out.get("docs", [])
        if rag_docs:
            pre_blocks.append("=== RAG DOCS ===\n" + "\n".join(
                f"- [{d.get('id')}] {d.get('title', '')[:80]} "
                f"({d.get('source', '')[:40]})\n  "
                f"{(d.get('snippet') or '')[:200]}"
                for d in rag_docs[:3]))

    if req.tools_on:
        try:
            t_out = TOOLS_FN([{"role": "user",
                               "content": [{"type": "text",
                                            "text": req.message}]}])
            tool_calls = t_out.get("tool_calls", [])
            if tool_calls:
                pre_blocks.append("=== TOOL RESULTS ===\n" + "\n".join(
                    f"- {tc.get('name')}({tc.get('args')}) -> "
                    f"{json.dumps(tc.get('result'))[:300]}"
                    for tc in tool_calls[:4]))
        except Exception as e:
            tool_calls = []

    if req.agentic_on:
        agent = run_agent(req.message, byok_keys=req.byok_keys)
        agent_block = format_agent_findings(agent)
        if agent_block:
            pre_blocks.append(agent_block)

    pre_context = "\n\n".join(pre_blocks)
    final_user = (f"{pre_context}\n\n=== USER MESSAGE ===\n{req.message}"
                  if pre_context else req.message)

    # Compose Gemma messages
    messages = []
    if req.persona_on:
        messages.append({"role": "system",
                         "content": [{"type": "text", "text": DUECARE_PERSONA}]})
    for h in req.history[-6:]:   # last 3 turns
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"],
                             "content": [{"type": "text", "text": h["content"]}]})
    messages.append({"role": "user",
                     "content": [{"type": "text", "text": final_user}]})

    t0 = time.time()
    try:
        response = GEMMA(messages, max_new_tokens=req.max_new_tokens,
                          temperature=0.7)
    except Exception as e:
        return {"error": f"gemma generation failed: {e}"}
    elapsed_ms = int((time.time() - t0) * 1000)

    return {
        "response":      response,
        "merged_prompt": final_user,
        "grep_hits":     grep_hits,
        "rag_docs":      rag_docs,
        "tool_calls":    tool_calls,
        "agent":         agent,
        "elapsed_ms":    elapsed_ms,
        "model":         GEMMA_MODEL_VARIANT,
    }


# ===========================================================================
# UI -- single HTML page with 5 toggle tiles
# ===========================================================================
_PAGE_HTML = """<!doctype html><html><head>
<meta charset="utf-8">
<title>Duecare Chat with Agentic Research</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif;
         max-width: 1180px; margin: 24px auto; padding: 0 24px;
         color: #1f2937; background: #f8fafc; }
  h1 { color: #1e40af; letter-spacing: -0.02em; margin: 0 0 4px; }
  .sub { color: #6b7280; font-size: 13px; margin: 0 0 16px; }
  .badge { display: inline-block; background: #fef3c7; color: #92400e;
           padding: 2px 9px; border-radius: 999px; font-size: 11px;
           font-weight: 700; margin-left: 6px; }
  .layout { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }
  .col { display: flex; flex-direction: column; gap: 12px; }
  .card { background: white; border: 1px solid #e5e7eb;
          border-radius: 12px; padding: 14px; }
  .conv { min-height: 320px; max-height: 540px; overflow-y: auto;
          background: white; border: 1px solid #e5e7eb;
          border-radius: 12px; padding: 14px; }
  .turn { margin-bottom: 14px; }
  .turn-user { color: #1e40af; font-weight: 700; font-size: 12px;
               margin-bottom: 4px; }
  .turn-assistant { color: #047857; font-weight: 700; font-size: 12px;
                    margin-bottom: 4px; }
  .turn-body { white-space: pre-wrap; line-height: 1.5; font-size: 14px; }
  textarea { width: 100%; min-height: 60px; font-family: ui-monospace,
             Menlo, Consolas, monospace; font-size: 13px;
             padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;
             box-sizing: border-box; resize: vertical; }
  button { background: #1e40af; color: white; padding: 9px 16px;
           border: none; border-radius: 8px; font-weight: 600;
           font-size: 13px; cursor: pointer; }
  button:hover { background: #1e3a8a; }
  button:disabled { background: #9ca3af; cursor: not-allowed; }
  .tiles { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
  .tile { padding: 10px 12px; border: 2px solid #e5e7eb; border-radius: 10px;
          background: #f9fafb; cursor: pointer; transition: all 0.15s;
          text-align: center; }
  .tile.on { background: var(--c); border-color: var(--c); color: white; }
  .tile-title { font-weight: 700; font-size: 12px; margin-bottom: 2px; }
  .tile-desc { font-size: 10px; opacity: 0.85; line-height: 1.3; }
  pre { background: #1f2937; color: #f9fafb; padding: 10px;
        border-radius: 8px; overflow-x: auto; font-size: 11px;
        line-height: 1.4; max-height: 400px; overflow-y: auto;
        white-space: pre-wrap; word-wrap: break-word; }
  .meta { color: #6b7280; font-size: 11px; margin-top: 6px; }
  .agent-step { background: #f1f5f9; padding: 8px 10px; border-radius: 6px;
                margin-bottom: 6px; font-size: 11px; line-height: 1.4; }
  .agent-step .tool { font-weight: 700; color: #1e40af; }
  h3 { margin: 0 0 6px; font-size: 13px; color: #6b7280;
       text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; }
</style></head><body>

<h1>Duecare Chat with Agentic Research <span class="badge">APPENDIX A4 · Proof-of-concept</span></h1>
<p class="sub">
  Same harness as chat-playground-with-grep-rag-tools, plus a fifth
  toggle for <b>Agentic Research</b>: Gemma 4 multi-step web research
  loop. Default (no keys) uses a real headless browser (Playwright) to
  search brave.com / duckduckgo.com / ecosia.org. <b>Bring your own
  optional API keys</b> below for faster paths. Every outbound query
  passes through the PII filter; queries are audit-logged by hash, never
  by plaintext.
</p>

<div class="card" style="background:#fef3c7; border-color:#f59e0b; padding:10px 14px; display:flex; gap:18px; align-items:center; margin-bottom:10px">
  <div>
    <span style="font-weight:700; color:#92400e">🔒 PII filter ACTIVE</span>
    <span class="meta" id="backend-info" style="margin-left:10px"></span>
  </div>
  <div style="flex:1"></div>
  <div>
    <button onclick="toggleByok()" style="background:#92400e; padding:6px 12px; font-size:12px">BYOK keys</button>
    <button onclick="loadAudit()" style="background:#92400e; padding:6px 12px; font-size:12px; margin-left:6px">Search audit</button>
  </div>
</div>

<div class="card" id="byok-panel" style="display:none; margin-bottom:14px; background:#f8fafc; border-color:#3b82f6">
  <h3 style="margin:0 0 6px; font-size:13px; color:#1e40af; text-transform:uppercase; letter-spacing:0.05em; font-weight:700">
    Bring Your Own Key (optional · stored only in your browser)
  </h3>
  <p style="margin:0 0 10px; font-size:12px; color:#6b7280; line-height:1.5">
    Paste any of these to use the API-backed fast path instead of the
    real-browser default. Keys are saved in localStorage on YOUR
    device and sent on each chat request — never persisted server-side.
    Leave blank to use the no-key browser fallback (slower but no
    third-party).
  </p>
  <div style="display:grid; grid-template-columns: 200px 1fr 220px; gap:8px; align-items:center; margin-bottom:6px">
    <label style="margin:0; font-size:12px"><b>Tavily</b> <span class="meta">(free 1k/mo)</span></label>
    <input type="password" id="byok-tavily" placeholder="tvly-..." style="font-family: ui-monospace, Menlo, Consolas, monospace; font-size:12px; padding:6px; border:1px solid #d1d5db; border-radius:6px">
    <span class="meta">app.tavily.com</span>

    <label style="margin:0; font-size:12px"><b>Brave Search</b> <span class="meta">(free 2k/mo, CC)</span></label>
    <input type="password" id="byok-brave" placeholder="BSA..." style="font-family: ui-monospace, Menlo, Consolas, monospace; font-size:12px; padding:6px; border:1px solid #d1d5db; border-radius:6px">
    <span class="meta">api.search.brave.com</span>

    <label style="margin:0; font-size:12px"><b>Serper</b> <span class="meta">(paid Google wrap)</span></label>
    <input type="password" id="byok-serper" placeholder="..." style="font-family: ui-monospace, Menlo, Consolas, monospace; font-size:12px; padding:6px; border:1px solid #d1d5db; border-radius:6px">
    <span class="meta">serper.dev</span>
  </div>
  <div style="margin-top:10px">
    <button onclick="saveByok()">Save</button>
    <button onclick="clearByok()" style="background:#dc2626">Clear all</button>
    <span class="meta" id="byok-status" style="margin-left:10px"></span>
  </div>
</div>

<div class="layout">
  <div class="col">
    <div class="conv" id="conv">
      <div class="meta">No messages yet. Try: "What is the current POEA fee cap for HK domestic workers?" or "What does ILO C189 say about overtime?" — the agentic loop will fetch fresh context.</div>
    </div>
    <div class="card">
      <div class="tiles">
        <div class="tile on" data-key="persona" style="--c: #7c3aed">
          <div class="tile-title">Persona</div>
          <div class="tile-desc">40-yr expert</div>
        </div>
        <div class="tile on" data-key="grep" style="--c: #dc2626">
          <div class="tile-title">GREP</div>
          <div class="tile-desc">22 rules</div>
        </div>
        <div class="tile on" data-key="rag" style="--c: #2563eb">
          <div class="tile-title">RAG</div>
          <div class="tile-desc">18 docs</div>
        </div>
        <div class="tile on" data-key="tools" style="--c: #16a34a">
          <div class="tile-title">Tools</div>
          <div class="tile-desc">4 lookups</div>
        </div>
        <div class="tile on" data-key="agentic" style="--c: #f59e0b">
          <div class="tile-title">Agentic</div>
          <div class="tile-desc">Web search</div>
        </div>
      </div>
      <textarea id="msg" placeholder="Type a question..."></textarea>
      <div style="margin-top: 10px; display: flex; align-items: center; gap: 8px">
        <button id="send" onclick="send()">Send</button>
        <button onclick="clearConv()" style="background: #6b7280">Clear</button>
        <span class="meta" id="status"></span>
      </div>
    </div>
  </div>

  <div class="col">
    <div class="card">
      <h3>Agent steps (last turn)</h3>
      <div id="agent-steps">
        <div class="meta">Send a message with Agentic ON to see the loop.</div>
      </div>
    </div>
    <div class="card">
      <h3>Merged prompt (last turn)</h3>
      <pre id="merged">(none yet)</pre>
    </div>
  </div>
</div>

<script>
const conv = document.getElementById('conv');
let history = [];

document.querySelectorAll('.tile').forEach(t => {
  t.addEventListener('click', () => t.classList.toggle('on'));
});

function getToggles() {
  const on = {};
  document.querySelectorAll('.tile').forEach(t => {
    on[t.dataset.key] = t.classList.contains('on');
  });
  return on;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, m => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

function appendTurn(role, body) {
  const div = document.createElement('div');
  div.className = 'turn';
  div.innerHTML = `<div class="turn-${role}">${role.toUpperCase()}</div>` +
                  `<div class="turn-body">${escapeHtml(body)}</div>`;
  conv.appendChild(div);
  conv.scrollTop = conv.scrollHeight;
}

function renderAgent(agent) {
  const el = document.getElementById('agent-steps');
  if (!agent || !agent.steps || agent.steps.length === 0) {
    el.innerHTML = '<div class="meta">No agent steps (Agentic was OFF, or Gemma chose "done" immediately).</div>';
    return;
  }
  el.innerHTML = agent.steps.map(s => {
    if (s.action === 'done') {
      return `<div class="agent-step"><b>step ${s.step}</b>: <span class="tool">DONE</span> — ${escapeHtml(s.reason || '')}</div>`;
    }
    if (s.action === 'tool') {
      return `<div class="agent-step"><b>step ${s.step}</b>: <span class="tool">${escapeHtml(s.tool)}</span>(${escapeHtml(JSON.stringify(s.args))})<br><span class="meta">${escapeHtml(s.reason || '')}</span><br><i>${escapeHtml(String(s.result_summary || '').slice(0, 240))}</i></div>`;
    }
    return `<div class="agent-step"><b>step ${s.step}</b>: ${escapeHtml(JSON.stringify(s))}</div>`;
  }).join('');
}

async function send() {
  const msgEl = document.getElementById('msg');
  const text = msgEl.value.trim();
  if (!text) return;
  const status = document.getElementById('status');
  const sendBtn = document.getElementById('send');
  sendBtn.disabled = true;
  status.textContent = ' thinking...';
  appendTurn('user', text);
  msgEl.value = '';
  const tog = getToggles();
  const body = {
    message: text, history: history,
    persona_on: tog.persona, grep_on: tog.grep, rag_on: tog.rag,
    tools_on: tog.tools, agentic_on: tog.agentic,
    max_new_tokens: 1024,
    byok_keys: getByokKeys(),
  };
  try {
    const r = await fetch('/api/chat', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    const data = await r.json();
    if (data.error) {
      appendTurn('assistant', '[ERROR] ' + data.error);
    } else {
      appendTurn('assistant', data.response);
      history.push({role: 'user', content: text});
      history.push({role: 'assistant', content: data.response});
      renderAgent(data.agent);
      document.getElementById('merged').textContent = data.merged_prompt;
      status.textContent = ` ${data.elapsed_ms} ms`;
    }
  } catch (e) {
    appendTurn('assistant', '[ERROR] ' + e.message);
  }
  sendBtn.disabled = false;
}

function clearConv() {
  history = [];
  conv.innerHTML = '<div class="meta">Cleared.</div>';
  document.getElementById('agent-steps').innerHTML = '<div class="meta">Send a message with Agentic ON to see the loop.</div>';
  document.getElementById('merged').textContent = '(none yet)';
}

document.getElementById('msg').addEventListener('keydown', e => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault(); send();
  }
});

// ===== BYOK panel =====
function getByokKeys() {
  const out = {};
  for (const k of ['tavily', 'brave', 'serper']) {
    const v = localStorage.getItem('duecare_byok_' + k);
    if (v && v.trim()) out[k] = v.trim();
  }
  return out;
}

function saveByok() {
  for (const k of ['tavily', 'brave', 'serper']) {
    const v = document.getElementById('byok-' + k).value.trim();
    if (v) localStorage.setItem('duecare_byok_' + k, v);
    else   localStorage.removeItem('duecare_byok_' + k);
  }
  document.getElementById('byok-status').textContent = ' saved.';
  loadBackend();
  setTimeout(() => document.getElementById('byok-status').textContent = '',
              2000);
}

function clearByok() {
  for (const k of ['tavily', 'brave', 'serper']) {
    localStorage.removeItem('duecare_byok_' + k);
    document.getElementById('byok-' + k).value = '';
  }
  document.getElementById('byok-status').textContent = ' cleared.';
  loadBackend();
}

function loadByokIntoPanel() {
  for (const k of ['tavily', 'brave', 'serper']) {
    const v = localStorage.getItem('duecare_byok_' + k);
    if (v) document.getElementById('byok-' + k).value = v;
  }
}

function toggleByok() {
  const p = document.getElementById('byok-panel');
  p.style.display = (p.style.display === 'none') ? 'block' : 'none';
  if (p.style.display === 'block') loadByokIntoPanel();
}

async function loadBackend() {
  try {
    const r = await fetch('/api/backends', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({byok_keys: getByokKeys()}),
    });
    const d = await r.json();
    const browserNote = d.browser_available ? ' · browser ✓' : ' · browser ✗';
    document.getElementById('backend-info').textContent =
      `· Active: ${d.active} (${d.kind})${browserNote}  · ${d.note}`;
  } catch (e) {}
}

async function loadAudit() {
  const r = await fetch('/api/audit?limit=30');
  const d = await r.json();
  const lines = d.recent.map(e =>
    `${e.ts}  [${e.backend}]  q=${e.query_sha256.slice(0,16)}...  `
    + `len=${e.query_len}  results=${e.result_count}  `
    + (e.pii_blocked ? 'PII-BLOCKED' : 'sent') +
    (e.error ? ` ERR=${e.error.slice(0,80)}` : ''));
  alert('SEARCH AUDIT (most recent 30)\\n\\n' +
        (lines.length ? lines.join('\\n') : '(no entries yet)'));
}

loadBackend();
</script>
</body></html>"""


def _server() -> None:
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


threading.Thread(target=_server, daemon=True,
                 name="duecare-agentic").start()
time.sleep(2.0)


# ===========================================================================
# PHASE 5 -- cloudflared tunnel
# ===========================================================================
print("=" * 76)
print(f"[phase 5] opening {TUNNEL} tunnel")
print("=" * 76)


def open_tunnel() -> str:
    if TUNNEL == "none":
        return f"http://localhost:{PORT}"
    import shutil as _shutil, urllib.request as _urlreq, stat as _stat
    cf_bin = _shutil.which("cloudflared")
    if cf_bin is None:
        cf_bin = "/tmp/cloudflared"
        if not os.path.exists(cf_bin):
            print("  downloading cloudflared...")
            try:
                _urlreq.urlretrieve(
                    "https://github.com/cloudflare/cloudflared/releases/"
                    "latest/download/cloudflared-linux-amd64", cf_bin)
                os.chmod(cf_bin,
                         _stat.S_IRWXU | _stat.S_IXGRP | _stat.S_IXOTH)
            except Exception as e:
                print(f"  download failed: {e}")
                return f"http://localhost:{PORT}"
    proc = subprocess.Popen(
        [cf_bin, "tunnel", "--url", f"http://localhost:{PORT}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1)
    _CLOUDFLARED_PROC['p'] = proc
    public_url = f"http://localhost:{PORT}"
    t0 = time.time()
    while time.time() - t0 < 60:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.1); continue
        if "trycloudflare.com" in line:
            m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
            if m:
                public_url = m.group(0); break
    # Drain stdout daemon
    threading.Thread(target=lambda: [None for _ in proc.stdout],
                     daemon=True).start()
    return public_url


PUBLIC_URL = open_tunnel()


# ===========================================================================
# Done
# ===========================================================================
print("\n" + "=" * 76)
print("DUECARE CHAT WITH AGENTIC RESEARCH IS LIVE")
print("=" * 76)
print(f"\n  open this URL on your laptop:")
print(f"\n      {PUBLIC_URL}\n")
print(f"  toggles:  Persona / GREP / RAG / Tools / Agentic")
print(f"  agent:    web_search (DuckDuckGo) + web_fetch (httpx+trafilatura)")
print(f"            + wikipedia (REST API). All open-source, no API keys.")
print(f"  loop:     up to {AGENT_MAX_STEPS} steps, "
      f"{AGENT_FETCH_CHARS} chars per fetched page")
print(f"  privacy:  every web call passes through PIIFilter first")
print(f"\n  stop the demo by interrupting this cell.\n")
print("=" * 76)

try:
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")

# Cleanup on shutdown
print("\n  shutting down cleanly...")
try:
    if _CLOUDFLARED_PROC.get("p"):
        _CLOUDFLARED_PROC["p"].terminate()
        try:
            _CLOUDFLARED_PROC["p"].wait(timeout=5)
        except Exception:
            _CLOUDFLARED_PROC["p"].kill()
        print("  cloudflared tunnel closed")
except Exception as _e:
    print(f"  cloudflared close: {_e}")
try:
    from duecare.research_tools.browser_tool import shutdown as _browser_shutdown
    _browser_shutdown()
    print("  browser session closed (if any)")
except Exception:
    pass
print("  shutdown complete -- cell exiting.\n")
