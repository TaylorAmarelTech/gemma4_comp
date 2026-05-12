# <!-- duecare:kernel-intro -->
# DueCare — Stock Gemma 4 chat baseline
# Appendix notebook #A01 of 13 in the DueCare submission.
#
# The before-the-harness baseline. No GREP, no RAG, no tools, no online. Pure stock Gemma 4.
#
# What to look for after Run All:
#   - Stock Gemma's answer to a recruitment-fee question shows zero ILO citations.
#   - No corridor-specific guidance; no NGO contact suggestions.
#   - Use this as the contrast for the harnessed kernels.
#
# Demo path: Run All -> open URL -> ask a corridor-specific safety question -> compare with kernel 01.
#
# Full README + cross-kernel index: see the README in this folder.

"""
============================================================================
  DUECARE GEMMA CHAT  --  Kaggle notebook (paste into a single code cell)
============================================================================

  PURE Gemma 4 chat playground. NOT the DueCare safety harness.
  No moderation pipeline, no audit trail, no evidence DB, no slideshow,
  no benchmark tab. Just:

      Gemma 4  +  chat UI  +  cloudflared tunnel  =  public URL

  Multimodal-capable: drag an image into the chat to use Gemma 4's
  vision.

  Requires:
    - GPU T4 x2 if loading 31B; single T4 fine for E2B/E4B
    - Internet ON (for GitHub package installation)
    - Optional datasets:
        google/gemma-4 (any variant; the kernel auto-detects which)
    - HF_TOKEN OPTIONAL (only needed if you want to download from HF Hub
      instead of using the locally attached Kaggle Gemma model)
============================================================================
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# CONFIG -- edit these for your run
# ---------------------------------------------------------------------------
# DEPRECATED 2026-05-11 (GitHub-only): DATASET_SLUG = "duecare-chat-playground-wheels"

# Pick which Gemma 4 to load. All 4 instruct variants supported via
# Unsloth FastModel (Daniel Hanchen's reference recipe).
#   e2b-it     ~2 GB 4-bit; single T4 or even CPU
#   e4b-it     ~5.5 GB 4-bit; single T4
#   26b-a4b-it ~14 GB 4-bit; needs 2x T4 (auto -> device_map=balanced)
#   31b-it     ~18 GB 4-bit; needs 2x T4 (auto -> device_map=balanced)
GEMMA_MODEL_VARIANT = "31b-it"
GEMMA_LOAD_IN_4BIT  = True
GEMMA_DEVICE_MAP    = "auto"     # "auto" picks "balanced" for big variants
GEMMA_MAX_SEQ_LEN   = 8192

# Server
PORT   = 8080
TUNNEL = "cloudflared"           # "cloudflared" | "ngrok" | "none"


# ===========================================================================
# PHASE 0 -- install Hanchen's pinned Unsloth stack BEFORE any torch import.
# Mirrors duecare_demo_kernel's Phase 0 verbatim. Same one-cell trick: no
# Python imports of torch/transformers happen before this subprocess call,
# so the eventual `from unsloth import FastModel` sees the freshly installed
# torch 2.8+ cleanly.
# ===========================================================================
_UNSLOTH_MARKER = Path("/tmp/.duecare_unsloth_stack_v1_done")


def _need_unsloth_stack() -> bool:
    # Every on-device variant uses Unsloth's FastModel loader.
    return GEMMA_MODEL_VARIANT not in ("cloud-gemini", "cloud-openai", "cloud-ollama")


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
# 1. Install duecare wheels (chat-only subset: core, models, chat)
# ===========================================================================
print("\n" + "=" * 76)
print(f"[1/5] installing duecare packages (GitHub-only)")
print("=" * 76)


def install_chat_wheels() -> int:
    """Install DueCare packages directly from GitHub - no datasets required!"""

    print("  → installing from GitHub (github.com/TaylorAmarelTech/gemma4_comp)")
    try:
        import urllib.request
        bootstrap_url = "https://raw.githubusercontent.com/TaylorAmarelTech/gemma4_comp/3e3ff9e3684903a66441b1ec4b143de25e7ded3e/scripts/_notebook_bootstrap.py"
        with urllib.request.urlopen(bootstrap_url, timeout=15) as response:
            bootstrap_code = response.read().decode('utf-8')

        # Execute bootstrap with error capture
        import io, contextlib
        output_buffer = io.StringIO()
        with contextlib.redirect_stdout(output_buffer):
            exec(bootstrap_code, {'__name__': '__main__'})

        output = output_buffer.getvalue()
        if "✓" in output and "duecare" in output.lower():
            print("  ✓ GitHub installation successful")
            return 1
        else:
            raise Exception("Installation didn't complete successfully")

    except Exception as e:
        print(f"  ✗ GitHub installation failed: {str(e)[:100]}...")
        print("  → Please ensure Internet is ON in Kaggle notebook settings")
        print("  → Then restart the kernel and try again")
        raise SystemExit("DueCare installation failed - internet connection required")


install_chat_wheels()

# Optional server deps (fastapi may already be on the Kaggle image, but
# we install --upgrade to be safe; uvicorn is required for run_server)
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
<div id="_dc-shutdown-overlay" role="dialog" aria-modal="true" aria-live="polite" tabindex="-1" aria-labelledby="_dc-shutdown-title">
  <div class="box">
    <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
         aria-hidden="true">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
    <h1 id="_dc-shutdown-title">Server stopped</h1>
    <p>The FastAPI server is down and the Kaggle cell will exit shortly.</p>
    <p class="meta">You can close this tab.</p>
  </div>
</div>
<template id="_dc-shutdown-tpl">
  <button class="dc-shutdown-pill" type="button" data-state="idle"
          title="Stop the FastAPI server and exit the Kaggle cell"
          aria-label="Shutdown DueCare server">
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
          overlay.focus();
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
  /* BASELINE NOTEBOOK: hide every safety-harness affordance.
     This kernel is RAW Gemma 4 chat with NO harness. Notebook #2
     (chat-playground-with-grep-rag-tools) is the version that shows
     all of these. */
  #harness-tiles,
  .harness-tiles,
  .harness-tiles-header,
  [id^='tile-'],
  .harness-tile,
  .harness-catalog,
  .harness-catalog-link,
  button[onclick*='openExamplesModal'],
  a[onclick*='openPipelineModal'],
  a[onclick*='openLayerModal'],
  a[onclick*='openGradeModal'],
  .empty-state-chips,
  .empty-hints,
  #empty-hints,
  .pipeline-link,
  .grade-link { display: none !important; }
  /* Also strip the "Click ▸ Examples for ..." prose from the empty
     state since the Examples button is hidden. */
  .empty-state strong { display: inline; }
</style>
<script>
  // Belt-and-suspenders: strip "View pipeline" / "Grade response" links
  // from assistant replies, AND rewrite the empty-state paragraph that
  // hardcodes references to harness layers + the Examples button.
  // CSS alone can't catch text content; JS rewrites it to baseline copy.
  (function() {
    const PIPELINE_RE = /View pipeline|Grade response/i;
    const BASELINE_EMPTY_TEXT =
      'Type a message below to chat with Gemma 4. This is the raw '
      + 'baseline — no safety harness, no GREP rules, no RAG context, '
      + 'no tool calls. Compare to the harness-augmented chat at '
      + 'duecare-chat-playground-with-grep-rag-tools.';
    function stripPipelineLinks() {
      document.querySelectorAll('a').forEach(a => {
        const oc = a.getAttribute('onclick') || '';
        if (oc.includes('openPipelineModal') || oc.includes('openGradeModal')
            || PIPELINE_RE.test(a.textContent)) {
          a.style.display = 'none';
          // also strip the leading " · " separator if present
          const prev = a.previousSibling;
          if (prev && prev.nodeType === 3 && prev.textContent.includes('·')) {
            prev.textContent = prev.textContent.replace(/\\s*·\\s*$/, '');
          }
        }
      });
    }
    function rewriteEmptyState() {
      // The chat package's empty <p> hardcodes references to the harness
      // and the Examples button — both of which we hide for the baseline
      // notebook. Replace the prose so the empty state matches reality.
      const empty = document.querySelector('#empty p');
      if (empty && empty.textContent.includes('Examples')) {
        empty.textContent = BASELINE_EMPTY_TEXT;
      }
      // Also clear the empty-hints chip row (populated from /api/examples)
      const hints = document.getElementById('empty-hints');
      if (hints) hints.innerHTML = '';
    }
    function applyAll() {
      stripPipelineLinks();
      rewriteEmptyState();
    }
    applyAll();
    new MutationObserver(applyAll).observe(
      document.body, {childList: true, subtree: true}
    );
  })();
</script>
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
            "<title>Shut down DueCare</title><style>"
            "body{font-family:-apple-system,system-ui,sans-serif;"
            "background:#f8fafc;color:#1f2937;display:flex;"
            "align-items:center;justify-content:center;min-height:100vh;"
            "margin:0}.box{background:white;border:1px solid #e5e7eb;"
            "border-radius:14px;padding:40px 50px;text-align:center;"
            "max-width:480px}h1{color:oklch(0.58 0.14 45);margin:0 0 14px}"
            "p{color:#6b7280;line-height:1.6;margin:0 0 24px}"
            "button{background:oklch(0.58 0.14 45);color:white;padding:12px 28px;"
            "border:none;border-radius:10px;font-weight:700;font-size:15px;"
            "cursor:pointer}button:hover{background:oklch(0.50 0.16 45)}"
            ".meta{color:#6b7280;font-size:12px;margin-top:18px}"
            "</style></head><body><div class='box'>"
            "<h1>Shut down DueCare?</h1>"
            "<p>Stops the FastAPI server, closes the browser session "
            "(if any), terminates the cloudflared tunnel, and exits "
            "the Kaggle cell. Re-run the cell to restart.</p>"
            "<button onclick='doShutdown()'>Confirm shutdown</button>"
            "<div class='meta' id='status'></div></div>"
            "<script>async function doShutdown(){"
            "document.getElementById('status').textContent='shutting down...';"
            "try{await fetch('/api/shutdown',{method:'POST'});"
            "document.querySelector('.box').innerHTML="
            "\"<h1 style='color:oklch(0.55 0.10 155)'>Shutting down</h1>\"+"
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
            # Inject on ANY text/html response — the chat UI may serve at
            # "/" or "/index.html" or another path depending on which app
            # mounts which router. Filter only by content-type, not path.
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
# 2. Load Gemma via Unsloth FastModel (Hanchen recipe verbatim)
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
    return {"e2b-it": 2.0, "e4b-it": 4.0,
            "26b-a4b-it": 26.0, "31b-it": 31.0}.get(variant.lower(), 0.0)


def _detect_gpu() -> dict:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            lines = [l.strip() for l in out.stdout.strip().split("\n")
                     if l.strip()]
            first = lines[0].split(",")
            return {"available": True, "name": first[0].strip(),
                     "vram_gb": float(first[1].strip()) / 1024.0,
                     "count": len(lines)}
    except Exception:
        pass
    return {"available": False, "name": "", "vram_gb": 0.0, "count": 0}


def load_gemma_chat() -> Optional[LoadedModel]:
    gpu = _detect_gpu()
    print(f"  GPU: {gpu['name']} x{gpu['count']}  "
          f"({gpu['vram_gb']:.1f} GB)" if gpu["available"] else "  GPU: none")
    if not gpu["available"]:
        print(f"  no GPU; chat will not be available")
        return None
    try:
        import torch
        from unsloth import FastModel
    except Exception as e:
        print(f"  FastModel import FAILED: {type(e).__name__}: {e}")
        if not _HANCHEN_STACK_INSTALLED:
            print(f"  hint: variant={GEMMA_MODEL_VARIANT} should have")
            print(f"        triggered Phase 0 install; check variant name")
        return None

    variant = GEMMA_MODEL_VARIANT
    repo_variant = (variant.replace("e2b-it", "E2B-it")
                          .replace("e4b-it", "E4B-it")
                          .replace("26b-a4b-it", "26B-A4B-it")
                          .replace("31b-it", "31B-it"))
    hf_repo = f"unsloth/gemma-4-{repo_variant}"

    # Prefer locally attached Kaggle model
    repo = hf_repo
    for v in ("1", "2", "3"):
        p = (f"/kaggle/input/models/google/gemma-4/transformers/"
             f"gemma-4-{variant}/{v}")
        if Path(p, "config.json").exists():
            repo = p
            print(f"  using local attached model: {repo}")
            break
    else:
        print(f"  no local attachment for gemma-4-{variant}, will download "
              f"from HF Hub: {hf_repo}")

    # Auto-balanced device map for big variants on multi-GPU
    eff_dmap = GEMMA_DEVICE_MAP
    if eff_dmap == "auto" and variant in ("31b-it", "26b-a4b-it"):
        if gpu["count"] >= 2:
            eff_dmap = "balanced"
            print(f"  variant={variant} + {gpu['count']}xGPU: "
                  f"device_map auto -> balanced")
        else:
            print(f"  WARN: variant={variant} typically needs 2x GPUs")

    print(f"  FastModel.from_pretrained(model={repo}, max_seq={GEMMA_MAX_SEQ_LEN}, "
          f"4bit={GEMMA_LOAD_IN_4BIT}, device_map={eff_dmap})")
    try:
        model, tokenizer = FastModel.from_pretrained(
            model_name=repo,
            dtype=None,
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

    def _gemma_call(messages: list[dict],
                     max_new_tokens: int = 512,
                     temperature: float = 1.0,
                     top_p: float = 0.95,
                     top_k: int = 64) -> str:
        # Apply chat template + generate (Hanchen's pattern).
        # Multimodal-capable: messages can include {"type":"image", "image":...}
        inputs = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to("cuda")
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            use_cache=True,
            temperature=temperature, top_p=top_p, top_k=top_k,
        )
        text = tokenizer.batch_decode(out)[0]
        # Strip the conversation prefix
        if "<|turn>model" in text:
            text = text.split("<|turn>model", 1)[1]
        # Strip the thinking-mode chain-of-thought wrapper
        if "<channel|>" in text:
            text = text.split("<channel|>", 1)[1]
        text = text.split("<turn|>", 1)[0]
        return text.replace("<bos>", "").replace("<eos>", "").strip()

    return LoadedModel(
        backend=_gemma_call,
        tokenizer=tokenizer,
        model=model,
        name=f"gemma-4-{variant}",
        size_b=_model_size_b(variant),
        quantization="4-bit nf4" if GEMMA_LOAD_IN_4BIT else "bf16",
        device=(f"balanced ({gpu['count']}x {gpu['name']})"
                if eff_dmap == "balanced" else "cuda:0"),
    )


loaded = load_gemma_chat()
if loaded is None:
    raise SystemExit(
        "Gemma load failed. Cannot run baseline batch without a model.")


# ===========================================================================
# 3. BATCH BASELINE RUNNER (the new A-01 purpose, 2026-05-11)
# ===========================================================================
# Per Taylor's experiment-ladder directive: A-01 runs the canonical test
# prompt library through the selected Gemma 4 variant WITHOUT the harness,
# then emits the artifact bundle defined by docs/appendix_artifact_schema.md
# so A-03 can pair it with the A-02 harnessed run for comparison.
print("\n" + "=" * 76)
print("[3/5] running batch baseline (no harness)")
print("=" * 76)

from duecare.chat.harness import EXAMPLE_PROMPTS

# Subset for smoke runs. Default: 25 for E2B (smoke), 100 for E4B,
# 200 for 26B/31B. Override via env DUECARE_N_PROMPTS.
_DEFAULT_N = {"e2b-it": 25, "e4b-it": 100,
              "26b-a4b-it": 200, "31b-it": 200}
_n_prompts = int(os.environ.get(
    "DUECARE_N_PROMPTS", _DEFAULT_N.get(GEMMA_MODEL_VARIANT, 25)))
_n_prompts = max(1, min(_n_prompts, len(EXAMPLE_PROMPTS)))
_prompts_subset = EXAMPLE_PROMPTS[:_n_prompts]
print(f"  prompt library: {len(EXAMPLE_PROMPTS)} total, running first {_n_prompts}")

# dc_log integration so the workbench Logs page shows progress live.
try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-01-baseline-runner")
except Exception:
    def dc_log(*a, **kw): return None  # type: ignore[no-redef]
    def set_kernel_id(*a, **kw): return None  # type: ignore[no-redef]


def _git_sha_safe() -> str:
    """Best-effort git SHA from environment (Kaggle won't have a clone)."""
    return os.environ.get("DUECARE_GIT_SHA", "unknown")


def _iso_utc(t: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def _run_id() -> str:
    ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    return f"a01_{GEMMA_MODEL_VARIANT}_stock_{ts}"


RUN_ID = _run_id()
OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_results.json"
JSONL_PATH = OUTPUT_DIR / f"{RUN_ID}_run.jsonl"
METADATA_PATH = OUTPUT_DIR / f"{RUN_ID}_metadata.json"
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"

print(f"  run_id: {RUN_ID}")
print(f"  outputs: /kaggle/working/{RUN_ID}_*")

# Detect runtime versions for metadata reproducibility.
def _pkg_version(name: str) -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version(name)
    except Exception:
        return "unknown"


_GPU_INFO = _detect_gpu()
_RUN_METADATA = {
    "started_at": _iso_utc(time.time()),
    "completed_at": None,
    "duration_s": None,
    "git_sha": _git_sha_safe(),
    "duecare_chat_version": _pkg_version("duecare-llm-chat"),
    "torch_version": _pkg_version("torch"),
    "transformers_version": _pkg_version("transformers"),
    "gpu_name": _GPU_INFO.get("name", ""),
    "gpu_memory_total_mb": int(_GPU_INFO.get("vram_gb", 0) * 1024),
    "gpu_memory_peak_mb": 0,
    "kaggle_kernel_id": "a-01-baseline-runner",
    "host": "kaggle" if Path("/kaggle").exists() else "local",
}

_RUN_CONFIG = {
    "model_variant": GEMMA_MODEL_VARIANT,
    "model_path": loaded.name,
    "model_kind": "stock",
    "adapter_path": None,
    "harness_enabled": False,
    "harness_layers": [],
    "max_new_tokens": 512,
    "temperature": 0.7,
    "top_p": 0.95,
    "n_prompts": _n_prompts,
    "prompt_filter": None,
}


def _gemma_chat_one(prompt_text: str) -> tuple[str, int, int]:
    """Run one prompt through stock Gemma 4 (no harness). Returns
    (response_text, tokens_in, tokens_out)."""
    messages = [{"role": "user", "content": prompt_text}]
    response = loaded.backend(messages, max_new_tokens=512,
                                temperature=0.7, top_p=0.95)
    tokens_in = len(loaded.tokenizer.encode(prompt_text)) if loaded.tokenizer else 0
    tokens_out = len(loaded.tokenizer.encode(response)) if loaded.tokenizer else 0
    return response, tokens_in, tokens_out


# Run the batch. Stream JSONL as we go so a crash mid-run still leaves
# usable rows on disk.
_results: list[dict] = []
_n_failed = 0
_t_total_start = time.time()
print(f"\n  starting batch ({_n_prompts} prompts) ...")
dc_log("a01.batch.start", "stock baseline batch beginning",
       run_id=RUN_ID, n_prompts=_n_prompts)

with JSONL_PATH.open("w", encoding="utf-8") as jsonl_fh:
    for idx, prompt_row in enumerate(_prompts_subset, 1):
        pid = prompt_row.get("id", f"prompt_{idx:04d}")
        ptext = prompt_row.get("text", "")
        prompt_meta = {
            k: prompt_row.get(k) for k in
            ("category", "subcategory", "sector", "corridor",
             "difficulty", "ilo_indicators", "bucket")
            if prompt_row.get(k) is not None
        }
        t0 = time.time()
        try:
            response, tokens_in, tokens_out = _gemma_chat_one(ptext)
            elapsed = time.time() - t0
            row = {
                "prompt_id": pid,
                "prompt_text": ptext,
                "prompt_metadata": prompt_meta,
                "response": response,
                "elapsed_s": round(elapsed, 2),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "harness_trace": None,
                "error": None,
            }
            print(f"  [{idx:3d}/{_n_prompts}] {pid:40s} {elapsed:5.1f}s "
                  f"in={tokens_in} out={tokens_out}")
        except Exception as e:
            elapsed = time.time() - t0
            _n_failed += 1
            row = {
                "prompt_id": pid,
                "prompt_text": ptext,
                "prompt_metadata": prompt_meta,
                "response": "",
                "elapsed_s": round(elapsed, 2),
                "tokens_in": 0,
                "tokens_out": 0,
                "harness_trace": None,
                "error": f"{type(e).__name__}: {str(e)[:300]}",
            }
            print(f"  [{idx:3d}/{_n_prompts}] {pid:40s} FAILED "
                  f"{type(e).__name__}: {str(e)[:80]}")
            dc_log("a01.batch.error", "prompt failed",
                   level="error", prompt_id=pid, err=str(e)[:200])
        _results.append(row)
        # Streaming JSONL line (top-level fields per schema).
        jsonl_fh.write(json.dumps({
            "schema_version": "1.0",
            "run_id": RUN_ID,
            "kernel_id": "a-01-baseline-runner",
            "ts": _iso_utc(time.time()),
            **row,
        }, ensure_ascii=False) + "\n")
        jsonl_fh.flush()
        if idx % 5 == 0:
            dc_log("a01.batch.progress", f"{idx}/{_n_prompts} done",
                   completed=idx, total=_n_prompts)

_t_total = time.time() - _t_total_start
_n_completed = len(_results) - _n_failed
_RUN_METADATA["completed_at"] = _iso_utc(time.time())
_RUN_METADATA["duration_s"] = round(_t_total, 1)
print(f"\n  batch complete: {_n_completed}/{len(_results)} ok, "
      f"{_n_failed} failed, {_t_total:.1f}s total")

_summary = {
    "n_completed": _n_completed,
    "n_failed": _n_failed,
    "mean_elapsed_s": round(sum(r["elapsed_s"] for r in _results) / max(1, len(_results)), 2),
    "mean_tokens_in": int(sum(r["tokens_in"] for r in _results) / max(1, len(_results))),
    "mean_tokens_out": int(sum(r["tokens_out"] for r in _results) / max(1, len(_results))),
    "total_tokens_in": sum(r["tokens_in"] for r in _results),
    "total_tokens_out": sum(r["tokens_out"] for r in _results),
}

# Build the three artifact files per the v1.0 schema.
_FULL = {
    "schema_version": "1.0",
    "kernel_id": "a-01-baseline-runner",
    "run_id": RUN_ID,
    "config": _RUN_CONFIG,
    "metadata": _RUN_METADATA,
    "summary": _summary,
    "results": _results,
}
RESULTS_PATH.write_text(json.dumps(_FULL, indent=2, ensure_ascii=False),
                          encoding="utf-8")
_METADATA_ONLY = {k: v for k, v in _FULL.items() if k != "results"}
METADATA_PATH.write_text(json.dumps(_METADATA_ONLY, indent=2, ensure_ascii=False),
                           encoding="utf-8")
print(f"  ✓ wrote {RESULTS_PATH.name}")
print(f"  ✓ wrote {JSONL_PATH.name}")
print(f"  ✓ wrote {METADATA_PATH.name}")

# Bundle ZIP with manifest for single-file Add Data attachment.
import zipfile, hashlib

def _sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


_manifest = {
    "schema_version": "1.0",
    "run_id": RUN_ID,
    "kernel_id": "a-01-baseline-runner",
    "files": ["results.json", "run.jsonl", "metadata.json"],
    "checksums": {
        "results.json": _sha256_of(RESULTS_PATH),
        "run.jsonl": _sha256_of(JSONL_PATH),
        "metadata.json": _sha256_of(METADATA_PATH),
    },
}
with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("manifest.json", json.dumps(_manifest, indent=2))
    zf.write(RESULTS_PATH, "results.json")
    zf.write(JSONL_PATH, "run.jsonl")
    zf.write(METADATA_PATH, "metadata.json")
print(f"  ✓ wrote {BUNDLE_PATH.name} ({BUNDLE_PATH.stat().st_size // 1024} KB)")

dc_log("a01.batch.done", f"baseline batch complete ({_n_completed} ok, "
       f"{_n_failed} failed, {_t_total:.0f}s)", run_id=RUN_ID,
       n_completed=_n_completed, duration_s=int(_t_total))


# ===========================================================================
# 4. Summary UI via the workbench minimal-shell
# ===========================================================================
print("\n" + "=" * 76)
print("[4/5] launching summary UI (workbench shell)")
print("=" * 76)

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": "A-01 stock baseline batch run",
        "audience": "researcher",
        "lede": ("Stock Gemma 4 (no harness) ran the canonical test prompt "
                 "library. Pair this artifact bundle with A-02's harnessed "
                 "run, then upload both to A-03 for the full lift "
                 "comparison."),
        "results": [
            {"label": "Model",   "value": f"{loaded.name} · {GEMMA_MODEL_VARIANT}"},
            {"label": "Prompts", "value": f"{_n_completed} ok / {_n_failed} failed"},
            {"label": "Wall time", "value": f"{_t_total:.0f}s"},
            {"label": "Mean elapsed", "value": f"{_summary['mean_elapsed_s']:.1f}s"},
            {"label": "Tokens in/out", "value": f"{_summary['total_tokens_in']:,} / {_summary['total_tokens_out']:,}"},
        ],
        "artifacts": [
            {"name": BUNDLE_PATH.name,   "path": str(BUNDLE_PATH)},
            {"name": RESULTS_PATH.name,  "path": str(RESULTS_PATH)},
            {"name": JSONL_PATH.name,    "path": str(JSONL_PATH)},
            {"name": METADATA_PATH.name, "path": str(METADATA_PATH)},
        ],
        "links": [
            ("Workbench (full)",
             "https://www.kaggle.com/code/taylorsamarel/duecare-exploration-workbench"),
            ("Artifact schema spec",
             "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_artifact_schema.md"),
        ],
        "next_steps": [
            f"Download {BUNDLE_PATH.name} from /artifact/{BUNDLE_PATH.name}.",
            "Run A-02 with the SAME model_variant to produce a paired harnessed bundle.",
            "Upload both bundles to A-03 for the side-by-side lift comparison.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-01-baseline-runner",
        port=PORT,
    )
    if public_url:
        print(f"  ✓ UI available at {public_url}")
    print("\n" + "=" * 76)
    print("[5/5] A-01 BASELINE RUN COMPLETE")
    print("=" * 76)
    print(f"\n   {_n_completed}/{_n_prompts} prompts ok in {_t_total:.0f}s")
    print(f"   bundle: /kaggle/working/{BUNDLE_PATH.name}")
    if public_url:
        print(f"   UI:     {public_url}")
    print(f"\n   Next: run A-02 with model_variant={GEMMA_MODEL_VARIANT} "
          f"to produce a paired harnessed bundle.\n")
    print("=" * 76)
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

# Cleanup on shutdown.
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
print("  shutdown complete -- cell exiting.\n")
