"""
============================================================================
  DUECARE HARNESS CHAT  --  unified Kaggle notebook (single core)
  (paste into a single code cell)
============================================================================

  THE one-notebook configurable Duecare interface. Everything in the
  submission visible here:

      Persona      expert anti-trafficking persona prepended to context
      GREP         49 regex KB rules (trafficking patterns + ILO
                     citations + corridor fee caps + kafala framework
                     + Lebanon / Kuwait / Gulf rules)
      RAG          BM25 retrieval over a 33-doc reference corpus
      Tools        5 lookup functions (corridor fee caps, fee
                     camouflage, ILO indicators, NGO intake, ILO
                     Convention reference)
      Online       optional agentic web search via Playwright (BYOK
                     for cloud-search APIs; falls back to DuckDuckGo
                     HTML when no key)
      Grade        4 modes (Universal / Expert / Deep / Combined) --
                     Universal = 17-dim multi-signal grader, Deep =
                     LLM-as-judge sending response back to the loaded
                     model with one yes/no question per dimension

  MODEL SELECTOR via GEMMA_MODEL_VARIANT env var or edit default below:

      e2b-it             google/gemma-4-2b-it          single T4
      e4b-it             google/gemma-4-4b-it          single T4
      26b-a4b-it         google/gemma-4-26b-a4b-it     T4 x2 (4-bit)
      31b-it             google/gemma-4-31b-it         T4 x2 (4-bit)
      jailbroken-31b     dealignai/Gemma-4-31B-JANG_4M-CRACK
      jailbroken-e4b     mlabonne/Gemma-4-E4B-it-abliterated
      cloud-gemini       Gemini API (set GEMINI_API_KEY)
      cloud-openai       OpenAI-compat (OPENAI_API_KEY + _BASE_URL +
                                          _MODEL)
      cloud-ollama       Ollama (OLLAMA_HOST, OLLAMA_MODEL)

  All safety content lives in duecare-llm-chat wheel. This kernel is:
      model load + create_app(**default_harness()) + cloudflared.

  Requires:
    - GPU T4 x2 (default 31b-it); single T4 for E2B/E4B; CPU OK for
      cloud-* variants
    - Internet ON
    - Datasets attached:
        taylorsamarel/duecare-harness-chat-wheels
        google/gemma-4 (any variant; auto-detected when on-device)
    - HF_TOKEN OPTIONAL (required for gated 31B/26B-A4B variants)
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
DATASET_SLUG = "duecare-harness-chat-wheels"

# Pick which model to load. Override at runtime by exporting the env var:
#   %env GEMMA_MODEL_VARIANT=e4b-it     (in a Kaggle cell BEFORE this one)
# Recognised values:
#   e2b-it / e4b-it / 26b-a4b-it / 31b-it          on-device Gemma 4
#   jailbroken-31b / jailbroken-e4b                 abliterated variants
#   cloud-gemini / cloud-openai / cloud-ollama      BYOK cloud routes
GEMMA_MODEL_VARIANT = os.environ.get("GEMMA_MODEL_VARIANT", "e4b-it")
GEMMA_LOAD_IN_4BIT  = os.environ.get("GEMMA_LOAD_IN_4BIT", "1") == "1"
GEMMA_DEVICE_MAP    = "auto"
GEMMA_MAX_SEQ_LEN   = int(os.environ.get("GEMMA_MAX_SEQ_LEN", "8192"))

# Online search (optional). The chat UI surfaces an "Online" toggle when
# this is True; when False the toggle is hidden and online_search_call
# is not wired into the harness.
ENABLE_ONLINE_SEARCH = os.environ.get("ENABLE_ONLINE_SEARCH", "1") == "1"

# Cloud-route credentials (only read for matching cloud-* variants)
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL    = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_HOST     = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "gemma2:2b")

# HuggingFace model id resolution per variant
_VARIANT_HF_ID = {
    "e2b-it":         "google/gemma-4-2b-it",
    "e4b-it":         "google/gemma-4-4b-it",
    "26b-a4b-it":     "google/gemma-4-26b-a4b-it",
    "31b-it":         "google/gemma-4-31b-it",
    "jailbroken-31b": "dealignai/Gemma-4-31B-JANG_4M-CRACK",
    "jailbroken-e4b": "mlabonne/Gemma-4-E4B-it-abliterated",
}

PORT   = 8080
TUNNEL = "cloudflared"


# ===========================================================================
# PHASE 0 -- install Hanchen's pinned Unsloth stack BEFORE any torch import.
# ===========================================================================
_UNSLOTH_MARKER = Path("/tmp/.duecare_unsloth_stack_v1_done")


def _need_unsloth_stack() -> bool:
    # Heavy on-device variants need the Unsloth FastModel stack;
    # cloud routes need nothing GPU-side.
    return GEMMA_MODEL_VARIANT in (
        "31b-it", "26b-a4b-it", "jailbroken-31b", "jailbroken-e4b",
    )


def _is_cloud_variant() -> bool:
    return GEMMA_MODEL_VARIANT.startswith("cloud-")


def _install_unsloth_stack_inline() -> bool:
    print("=" * 76)
    print("[phase 0] installing Hanchen's Unsloth Gemma 4 stack")
    print("=" * 76)
    print(f"  variant: {GEMMA_MODEL_VARIANT}  (one-cell run -- no restart)")
    try:
        import numpy as _np, PIL as _pil
        np_pin = f"numpy=={_np.__version__}"
        pil_pin = f"pillow=={_pil.__version__}"
    except Exception:
        np_pin, pil_pin = "numpy", "pillow"
    uv_check = subprocess.run(["uv", "--version"],
                                capture_output=True, text=True)
    if uv_check.returncode == 0:
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
    print(f"  $ {' '.join(cmd)}")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  INSTALL FAILED ({proc.returncode}): "
              f"{proc.stderr[-600:]}")
        return False
    print(f"  ✓ Hanchen stack installed in {time.time()-t0:.0f}s")
    try:
        _UNSLOTH_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _UNSLOTH_MARKER.write_text(json.dumps(
            {"variant": GEMMA_MODEL_VARIANT,
             "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))
    except Exception:
        pass
    return True


_HANCHEN_STACK_INSTALLED = False
if _need_unsloth_stack():
    if _UNSLOTH_MARKER.exists():
        print(f"[phase 0] Unsloth stack marker present; skipping install")
        _HANCHEN_STACK_INSTALLED = True
    else:
        _HANCHEN_STACK_INSTALLED = _install_unsloth_stack_inline()


# ===========================================================================
# 1. Install duecare wheels (chat = UI + harness content)
# ===========================================================================
print("\n" + "=" * 76)
print(f"[1/5] installing duecare wheels from /kaggle/input/{DATASET_SLUG}")
print("=" * 76)


def install_chat_wheels() -> int:
    if not Path("/kaggle/input").exists():
        print("  (not in Kaggle; skipping wheel install)")
        return 0
    found = sorted(p for p in Path("/kaggle/input").rglob("*.whl")
                    if "duecare" in p.name.lower())
    if not found:
        raise SystemExit(
            "No duecare *.whl files in /kaggle/input. "
            f"Add Data -> Datasets -> taylorsamarel/{DATASET_SLUG}.")
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--no-input",
            "--disable-pip-version-check", *[str(p) for p in found]]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  bulk install failed: {proc.stderr[-300:]}")
        for w in found:
            single = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet",
                 "--no-input", "--disable-pip-version-check", str(w)],
                capture_output=True, text=True)
            sym = "✓" if single.returncode == 0 else "✗"
            print(f"  {sym} {w.name}")
    print(f"  ✓ installed {len(found)} duecare wheels")
    return len(found)


install_chat_wheels()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--upgrade", "--no-input",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)



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
  /* Header-integrated shutdown button — placed into header.bar by JS so
     it sits next to the model badge instead of floating over the UI.
     Falls back to a fixed bottom-right position if header not found. */
  .dc-shutdown-pill {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 12px;
    background: rgba(220, 38, 38, 0.18);
    color: #fca5a5;
    border: 1px solid rgba(220, 38, 38, 0.35);
    border-radius: 999px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    font-weight: 600; font-size: 11.5px; line-height: 1;
    cursor: pointer;
    transition: all 0.15s ease;
    user-select: none;
    white-space: nowrap;
  }
  .dc-shutdown-pill:hover {
    background: rgba(220, 38, 38, 0.92);
    color: #fff;
    border-color: rgba(255, 255, 255, 0.2);
  }
  .dc-shutdown-pill[data-state="confirming"] {
    background: rgba(245, 158, 11, 0.92);
    color: #fff;
    border-color: rgba(255, 255, 255, 0.2);
  }
  .dc-shutdown-pill[data-state="shutting"] {
    background: rgba(107, 114, 128, 0.92);
    color: #fff;
    cursor: wait;
  }
  .dc-shutdown-pill[data-state="done"] {
    background: rgba(16, 185, 129, 0.92);
    color: #fff;
    cursor: default;
  }
  .dc-shutdown-pill svg {
    width: 12px; height: 12px;
    flex-shrink: 0;
    display: block;
  }
  /* Fallback fixed position: only used when header.bar is NOT found.
     Bottom-right so it doesn't overlap a header. */
  .dc-shutdown-pill.dc-floating {
    position: fixed;
    bottom: 14px; right: 14px;
    z-index: 99999;
    padding: 8px 14px;
    background: rgba(220, 38, 38, 0.92);
    color: #fff;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
  }
  /* Full-screen success overlay shown after shutdown completes */
  #_dc-shutdown-overlay {
    position: fixed; inset: 0; z-index: 100000;
    display: none;
    align-items: center; justify-content: center;
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.97) 0%, rgba(30, 41, 59, 0.97) 100%);
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    -webkit-backdrop-filter: blur(8px); backdrop-filter: blur(8px);
  }
  #_dc-shutdown-overlay.show { display: flex; }
  #_dc-shutdown-overlay .box {
    text-align: center;
    padding: 44px 52px;
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid rgba(71, 85, 105, 0.5);
    border-radius: 16px;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
    max-width: 440px;
  }
  #_dc-shutdown-overlay svg.icon {
    width: 56px; height: 56px;
    color: #10b981;
    margin: 0 auto 14px;
    display: block;
  }
  #_dc-shutdown-overlay h1 {
    margin: 0 0 8px 0;
    font-size: 22px; font-weight: 700;
    color: #f1f5f9;
  }
  #_dc-shutdown-overlay p {
    margin: 0; color: #94a3b8;
    font-size: 13.5px; line-height: 1.5;
  }
  #_dc-shutdown-overlay .meta {
    margin-top: 14px;
    color: #64748b; font-size: 11.5px;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
</style>
<div id="_dc-shutdown-overlay" role="dialog" aria-modal="true" aria-live="polite">
  <div class="box">
    <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
         aria-hidden="true">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
    <h1>Server stopped</h1>
    <p>The FastAPI server is down and the Kaggle cell will exit shortly.</p>
    <p class="meta">You can close this tab.</p>
  </div>
</div>
<template id="_dc-shutdown-tpl">
  <button class="dc-shutdown-pill" type="button" data-state="idle"
          title="Stop the FastAPI server and exit the Kaggle cell"
          aria-label="Shutdown Duecare server">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
         aria-hidden="true">
      <path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path>
      <line x1="12" y1="2" x2="12" y2="12"></line>
    </svg>
    <span class="dc-shutdown-label">Shutdown</span>
  </button>
</template>
<script>
(function() {
  function mount() {
    var tpl = document.getElementById('_dc-shutdown-tpl');
    var overlay = document.getElementById('_dc-shutdown-overlay');
    if (!tpl || !overlay) return;
    var btn = tpl.content.firstElementChild.cloneNode(true);
    // Try to inject into the chat header bar; otherwise float bottom-right
    var header = document.querySelector('header.bar');
    if (header) {
      header.appendChild(btn);
    } else {
      btn.classList.add('dc-floating');
      document.body.appendChild(btn);
    }
    var lbl = btn.querySelector('.dc-shutdown-label');
    var confirmTimer = null;
    function setState(state, text) {
      btn.dataset.state = state;
      if (text) lbl.textContent = text;
    }
    btn.addEventListener('click', function() {
      var s = btn.dataset.state || 'idle';
      if (s === 'shutting' || s === 'done') return;
      if (s === 'confirming') {
        if (confirmTimer) clearTimeout(confirmTimer);
        setState('shutting', 'Stopping…');
        try {
          fetch('/api/shutdown', {method: 'POST'}).catch(function(){});
        } catch (e) {}
        setTimeout(function() {
          setState('done', 'Stopped');
          overlay.classList.add('show');
        }, 350);
      } else {
        setState('confirming', 'Click again to confirm');
        confirmTimer = setTimeout(function() {
          if (btn.dataset.state === 'confirming') {
            setState('idle', 'Shutdown');
          }
        }, 4000);
      }
    });
  }
  // Run on DOM ready, and again after 800ms in case the header is hydrated
  // late by the chat UI's own JS.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
  setTimeout(function() {
    // If we mounted floating + a header has since appeared, move into it
    var existing = document.querySelector('header.bar .dc-shutdown-pill');
    var floating = document.querySelector('body > .dc-shutdown-pill.dc-floating');
    if (!existing && floating) {
      var header = document.querySelector('header.bar');
      if (header) {
        floating.classList.remove('dc-floating');
        header.appendChild(floating);
      }
    }
  }, 800);
})();
</script>
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
# 2. Load Gemma via Unsloth FastModel
# ===========================================================================
print("\n" + "=" * 76)
print("[2/5] loading Gemma 4 via Unsloth FastModel")
print("=" * 76)


@dataclass
class LoadedModel:
    backend: Any
    tokenizer: Any
    model: Any
    name: str
    size_b: float
    quantization: str
    device: str


def _model_size_b(variant: str) -> float:
    return {
        "e2b-it": 2.0, "e4b-it": 4.0,
        "26b-a4b-it": 26.0, "31b-it": 31.0,
        "jailbroken-31b": 31.0, "jailbroken-e4b": 4.0,
        "cloud-gemini": 0.0, "cloud-openai": 0.0, "cloud-ollama": 0.0,
    }.get(variant.lower(), 0.0)


def _detect_gpu() -> dict:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            lines = [l.strip() for l in out.stdout.strip().split("\n") if l.strip()]
            first = lines[0].split(",")
            return {"available": True, "name": first[0].strip(),
                     "vram_gb": float(first[1].strip()) / 1024.0,
                     "count": len(lines)}
    except Exception:
        pass
    return {"available": False, "name": "", "vram_gb": 0.0, "count": 0}


def _load_cloud_route() -> Optional[LoadedModel]:
    """Cloud-route variants: route gemma_call to a hosted API instead
    of loading a model locally. No GPU needed."""
    variant = GEMMA_MODEL_VARIANT
    if variant == "cloud-gemini":
        if not GEMINI_API_KEY:
            print("  cloud-gemini selected but GEMINI_API_KEY not set; "
                    "set it and re-run.")
            return None
        import urllib.request as _u, json as _json
        def _gemini_call(messages, **gen_kwargs):
            # Compact messages → Gemini's contents format
            user_text = ""
            for m in messages:
                if m.get("role") == "user":
                    for c in m.get("content", []):
                        if isinstance(c, dict) and c.get("type") == "text":
                            user_text += c.get("text", "") + "\n"
                        elif isinstance(c, str):
                            user_text += c + "\n"
            payload = _json.dumps({"contents": [{
                "parts": [{"text": user_text.strip()}]
            }]}).encode("utf-8")
            url = ("https://generativelanguage.googleapis.com/v1beta/"
                     "models/gemini-1.5-flash:generateContent?key="
                     + GEMINI_API_KEY)
            req = _u.Request(url, data=payload,
                             headers={"Content-Type": "application/json"})
            with _u.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read())
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                return f"[gemini error: {data}]"
        return LoadedModel(
            backend=_gemini_call, tokenizer=None, model=None,
            name="gemini-1.5-flash (cloud)", size_b=0.0,
            quantization="cloud-hosted", device="cloud:gemini",
        )
    if variant == "cloud-openai":
        if not OPENAI_API_KEY:
            print("  cloud-openai selected but OPENAI_API_KEY not set.")
            return None
        import urllib.request as _u, json as _json
        def _openai_call(messages, max_new_tokens=512, temperature=1.0,
                          top_p=0.95, **gen_kwargs):
            api_msgs = []
            for m in messages:
                content = ""
                for c in m.get("content", []):
                    if isinstance(c, dict) and c.get("type") == "text":
                        content += c.get("text", "")
                    elif isinstance(c, str):
                        content += c
                api_msgs.append({"role": m.get("role", "user"),
                                  "content": content})
            payload = _json.dumps({
                "model": OPENAI_MODEL, "messages": api_msgs,
                "max_tokens": max_new_tokens,
                "temperature": temperature, "top_p": top_p,
            }).encode("utf-8")
            req = _u.Request(
                f"{OPENAI_BASE_URL}/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}",
                         "Content-Type": "application/json"})
            with _u.urlopen(req, timeout=120) as resp:
                data = _json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
        return LoadedModel(
            backend=_openai_call, tokenizer=None, model=None,
            name=f"{OPENAI_MODEL} (cloud)", size_b=0.0,
            quantization="cloud-hosted", device="cloud:openai",
        )
    if variant == "cloud-ollama":
        import urllib.request as _u, json as _json
        def _ollama_call(messages, max_new_tokens=512, temperature=1.0,
                          **gen_kwargs):
            api_msgs = []
            for m in messages:
                content = ""
                for c in m.get("content", []):
                    if isinstance(c, dict) and c.get("type") == "text":
                        content += c.get("text", "")
                    elif isinstance(c, str):
                        content += c
                api_msgs.append({"role": m.get("role", "user"),
                                  "content": content})
            payload = _json.dumps({
                "model": OLLAMA_MODEL, "messages": api_msgs,
                "stream": False,
                "options": {"temperature": temperature,
                              "num_predict": max_new_tokens},
            }).encode("utf-8")
            req = _u.Request(
                f"{OLLAMA_HOST}/api/chat", data=payload,
                headers={"Content-Type": "application/json"})
            with _u.urlopen(req, timeout=300) as resp:
                data = _json.loads(resp.read())
            return data.get("message", {}).get("content",
                                                 f"[ollama error: {data}]")
        return LoadedModel(
            backend=_ollama_call, tokenizer=None, model=None,
            name=f"{OLLAMA_MODEL} (ollama)", size_b=0.0,
            quantization="ollama-hosted", device=f"ollama:{OLLAMA_HOST}",
        )
    return None


def load_gemma() -> Optional[LoadedModel]:
    # Cloud routes don't need GPU detection or Unsloth
    if _is_cloud_variant():
        print(f"  variant={GEMMA_MODEL_VARIANT} → routing to cloud API")
        return _load_cloud_route()
    gpu = _detect_gpu()
    print(f"  GPU: {gpu['name']} x{gpu['count']}  ({gpu['vram_gb']:.1f} GB)"
          if gpu["available"] else "  GPU: none")
    if not gpu["available"]:
        print("  No GPU available. Re-run with one of the cloud-* "
                "variants (cloud-gemini / cloud-openai / cloud-ollama) "
                "or attach a T4.")
        return None
    try:
        import torch
        from unsloth import FastModel
    except Exception as e:
        print(f"  FastModel import FAILED: {type(e).__name__}: {e}")
        return None
    variant = GEMMA_MODEL_VARIANT
    # Resolve HF model id: explicit jailbroken id or the unsloth mirror
    if variant.startswith("jailbroken-"):
        repo = _VARIANT_HF_ID.get(variant, variant)
    else:
        repo_variant = (variant.replace("e2b-it", "E2B-it")
                              .replace("e4b-it", "E4B-it")
                              .replace("26b-a4b-it", "26B-A4B-it")
                              .replace("31b-it", "31B-it"))
        hf_repo = f"unsloth/gemma-4-{repo_variant}"
        repo = hf_repo
        for v in ("1", "2", "3"):
            p = (f"/kaggle/input/models/google/gemma-4/transformers/"
                 f"gemma-4-{variant}/{v}")
            if Path(p, "config.json").exists():
                repo = p; break
        if repo == hf_repo:
            print(f"  no local attachment; will download from HF Hub: {hf_repo}")
        else:
            print(f"  using local attached model: {repo}")
    eff_dmap = GEMMA_DEVICE_MAP
    if eff_dmap == "auto" and variant in ("31b-it", "26b-a4b-it"):
        eff_dmap = "balanced" if gpu["count"] >= 2 else "auto"
    print(f"  FastModel.from_pretrained(model={repo}, "
          f"max_seq={GEMMA_MAX_SEQ_LEN}, "
          f"4bit={GEMMA_LOAD_IN_4BIT}, device_map={eff_dmap})")
    try:
        model, tokenizer = FastModel.from_pretrained(
            model_name=repo, dtype=None,
            max_seq_length=GEMMA_MAX_SEQ_LEN,
            load_in_4bit=GEMMA_LOAD_IN_4BIT,
            full_finetuning=False,
            device_map=eff_dmap,
        )
    except Exception as e:
        print(f"  FastModel FAILED: {type(e).__name__}: {str(e)[:300]}")
        return None
    try:
        from unsloth.chat_templates import get_chat_template
        tokenizer = get_chat_template(tokenizer,
                                       chat_template="gemma-4-thinking")
    except Exception:
        pass

    def _gemma_call(messages, max_new_tokens=512, temperature=1.0,
                     top_p=0.95, top_k=64):
        inputs = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt").to("cuda")
        out = model.generate(
            **inputs, max_new_tokens=max_new_tokens,
            use_cache=True,
            temperature=temperature, top_p=top_p, top_k=top_k)
        text = tokenizer.batch_decode(out)[0]
        if "<|turn>model" in text:
            text = text.split("<|turn>model", 1)[1]
        if "<channel|>" in text:
            text = text.split("<channel|>", 1)[1]
        text = text.split("<turn|>", 1)[0]
        return text.replace("<bos>", "").replace("<eos>", "").strip()

    return LoadedModel(
        backend=_gemma_call, tokenizer=tokenizer, model=model,
        name=f"gemma-4-{variant}",
        size_b=_model_size_b(variant),
        quantization="4-bit nf4" if GEMMA_LOAD_IN_4BIT else "bf16",
        device=(f"balanced ({gpu['count']}x {gpu['name']})"
                if eff_dmap == "balanced" else "cuda:0"))


loaded = load_gemma()
if loaded is None:
    raise SystemExit("Gemma load failed.")


# ===========================================================================
# 3. Build + launch chat server (Persona + GREP + RAG + Tools all wired
#    via duecare.chat.harness.default_harness())
# ===========================================================================
print("\n" + "=" * 76)
print("[3/5] launching chat server (Persona + GREP + RAG + Tools wired)")
print("=" * 76)

from duecare.chat import create_app
from duecare.chat.harness import (
    default_harness, GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH,
)
import uvicorn

model_info = {
    "loaded": True, "name": loaded.name, "size_b": loaded.size_b,
    "quantization": loaded.quantization, "device": loaded.device,
    "display": f"{loaded.name} · {loaded.size_b:.1f}B · "
                f"{loaded.quantization}",
}

# All 4 layers (Persona / GREP / RAG / Tools) wired in one line.
# The chat package's DEFAULT_PERSONA is used unless overridden.
# 5th layer (Online) is wired below if ENABLE_ONLINE_SEARCH=1.
_create_kwargs = {
    "gemma_call": loaded.backend,
    "model_info": model_info,
    **default_harness(),
}

# Wire the online_search_call kwarg so the chat UI surfaces the 5th
# tile. The actual search function is defined further down (after
# create_app) — define a forward-reference shim now and bind it later.
_online_search_fn = {"f": None}
def _online_search_dispatch(query: str, top_n: int = 5) -> dict:
    f = _online_search_fn["f"]
    if f is None:
        return {"query": query, "results": [], "source": "not_wired"}
    return f(query, top_n=top_n)
if ENABLE_ONLINE_SEARCH:
    _create_kwargs["online_search_call"] = _online_search_dispatch
app = create_app(**_create_kwargs)
_attach_shutdown(app)

print(f"  ✓ harness loaded: {len(GREP_RULES)} GREP rules, "
      f"{len(RAG_CORPUS)} RAG docs, {len(_TOOL_DISPATCH)} tools")


# ===========================================================================
# 4.5  ONLINE SEARCH (optional fifth layer)
# ===========================================================================
# Adds /api/online-search?q=... endpoint that scrapes DuckDuckGo's HTML
# results page (no API key needed, no Playwright). Returns top-N
# {title, url, snippet} results. The chat UI does not yet have an
# Online toggle wired into the message flow; for now this is
# accessible via curl + via the agentic-research kernel (A4) which has
# the full Playwright integration.
#
# Disable by setting ENABLE_ONLINE_SEARCH=0 in the environment.
if ENABLE_ONLINE_SEARCH:
    import urllib.parse as _ulp, urllib.request as _urlreq
    from fastapi import HTTPException as _HTTPException

    def _online_search(query: str, top_n: int = 5) -> dict:
        """Scrape DuckDuckGo HTML for top results. Free, no key.
        Best-effort: DDG's HTML can change; this returns [] on parse
        failure rather than crashing. For production-grade search use
        the agentic-research kernel (A4) with a Brave Search API key."""
        if not query or len(query.strip()) < 2:
            return {"query": query, "results": [], "source": "noop"}
        if len(query) > 500:
            query = query[:500]
        url = "https://html.duckduckgo.com/html/?q=" + _ulp.quote(query)
        try:
            req = _urlreq.Request(
                url,
                headers={"User-Agent": ("Mozilla/5.0 (compatible; "
                                          "DuecareHarness/1.0)")},
            )
            with _urlreq.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            return {"query": query, "results": [],
                    "source": "ddg_html",
                    "error": f"{type(e).__name__}: {e}"}
        # Lightweight regex parse — DDG HTML wraps results in
        # <a class="result__a" href="...">title</a> with snippets in
        # <a class="result__snippet">snippet</a>.
        result_re = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        snippet_re = re.compile(
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        def _strip_html(s: str) -> str:
            return re.sub(r"<[^>]+>", "", s).strip()
        urls_titles = [(u, _strip_html(t))
                         for u, t in result_re.findall(html)][:top_n]
        snippets = [_strip_html(s) for s in snippet_re.findall(html)][:top_n]
        results = []
        for i, (u, t) in enumerate(urls_titles):
            # DDG redirects via /l/?uddg=... — extract the real URL
            real = u
            m = re.search(r"uddg=([^&]+)", u)
            if m:
                try:
                    real = _ulp.unquote(m.group(1))
                except Exception:
                    pass
            results.append({
                "rank":    i + 1,
                "title":   t,
                "url":     real,
                "snippet": snippets[i] if i < len(snippets) else "",
            })
        return {"query": query, "results": results, "source": "ddg_html"}

    @app.get("/api/online-search")
    def api_online_search(q: str = "", top_n: int = 5):
        """Online search hook. Not yet wired into the chat message
        flow — call directly via curl, or use kernel A4 (agentic-
        research) for the Playwright-based version."""
        if not q:
            raise _HTTPException(400, "q (query) parameter is required")
        return _online_search(q, top_n=max(1, min(int(top_n), 20)))

    # Bind the search function into the create_app callable shim
    # so the chat send pipeline picks it up when the Online toggle
    # is enabled.
    _online_search_fn["f"] = _online_search
    print(f"  ✓ online search wired: GET /api/online-search?q=... + Online toggle tile")
else:
    print(f"  · online search disabled (ENABLE_ONLINE_SEARCH=0)")


def _server_thread():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


server_t = threading.Thread(target=_server_thread, daemon=True,
                              name="duecare-toggle-server")
server_t.start()
print(f"  server thread started on 0.0.0.0:{PORT}")
time.sleep(2.0)


# ===========================================================================
# 4. Cloudflared tunnel (auto-download if not on PATH)
# ===========================================================================
print("\n" + "=" * 76)
print(f"[4/5] opening {TUNNEL} tunnel")
print("=" * 76)

public_url = f"http://localhost:{PORT}"
if TUNNEL != "none":
    try:
        import shutil as _shutil, urllib.request as _urlreq, stat as _stat
        cf_bin = _shutil.which("cloudflared")
        if cf_bin is None:
            cf_bin = "/tmp/cloudflared"
            if not os.path.exists(cf_bin):
                print(f"  cloudflared not on PATH -- downloading ...")
                _url = ("https://github.com/cloudflare/cloudflared/"
                         "releases/latest/download/cloudflared-linux-amd64")
                _urlreq.urlretrieve(_url, cf_bin)
                os.chmod(cf_bin, _stat.S_IRWXU | _stat.S_IXGRP
                                  | _stat.S_IXOTH)
                print(f"  ✓ downloaded "
                      f"{os.path.getsize(cf_bin)//1_000_000} MB to {cf_bin}")
        proc = subprocess.Popen(
            [cf_bin, "tunnel", "--url", f"http://localhost:{PORT}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
        _CLOUDFLARED_PROC['p'] = proc
        t0 = time.time()
        while time.time() - t0 < 60:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.1); continue
            print(f"  [tunnel] {line.rstrip()}")
            if "trycloudflare.com" in line:
                m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
                if m:
                    public_url = m.group(0)
                    print(f"  ✓ tunnel ready: {public_url}")
                    break
        # Drain cloudflared stdout in a daemon thread so the OS pipe
        # buffer never fills (otherwise cloudflared blocks on write
        # and the tunnel 1033s within minutes).
        def _drain_stdout(p=proc):
            try:
                for _ in p.stdout: pass
            except Exception: pass
        threading.Thread(target=_drain_stdout, daemon=True,
                          name="cloudflared-stdout-drain").start()
    except Exception as e:
        print(f"  tunnel error: {type(e).__name__}: {e}")


# ===========================================================================
# 5. Print URL prominently and block
# ===========================================================================
print("\n" + "=" * 76)
print("[5/5] DUECARE CHAT PLAYGROUND with GREP/RAG/Tools is LIVE")
print("=" * 76)
print(f"\n   open this URL on your laptop:")
print(f"\n       {public_url}\n")
print(f"   model:    {loaded.name}  ·  {loaded.size_b:.1f}B  ·  "
      f"{loaded.quantization}")
print(f"   device:   {loaded.device}")
print(f"   harness:  Persona + GREP ({len(GREP_RULES)} rules) + "
      f"RAG ({len(RAG_CORPUS)} docs) + Tools ({len(_TOOL_DISPATCH)} fns)")
print(f"\n   In the chat UI, scroll to the bottom of the composer to find")
print(f"   4 colored tile cards: Persona (purple) / GREP (red) / "
      f"RAG (blue) / Tools (green).")
print(f"   Click a tile to toggle it ON/OFF for the next message.")
print(f"   Click '▸ view' on each tile to inspect the catalog.")
print(f"\n   stop the playground by interrupting this cell.\n")
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
