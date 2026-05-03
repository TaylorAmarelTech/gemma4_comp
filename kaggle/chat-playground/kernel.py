"""
============================================================================
  DUECARE GEMMA CHAT  --  Kaggle notebook (paste into a single code cell)
============================================================================

  PURE Gemma 4 chat playground. NOT the Duecare safety harness.
  No moderation pipeline, no audit trail, no evidence DB, no slideshow,
  no benchmark tab. Just:

      Gemma 4  +  chat UI  +  cloudflared tunnel  =  public URL

  Multimodal-capable: drag an image into the chat to use Gemma 4's
  vision.

  Requires:
    - GPU T4 x2 if loading 31B; single T4 fine for E2B/E4B
    - Internet ON
    - Datasets attached:
        taylorsamarel/duecare-chat-playground-wheels   (3 wheels: core+models+chat)
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
DATASET_SLUG = "duecare-chat-playground-wheels"

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
    big = ("31b-it", "26b-a4b-it")
    return GEMMA_MODEL_VARIANT in big


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
print("[1/5] installing duecare-chat-playground wheels")
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
  // Belt-and-suspenders: also strip the "View pipeline" link from any
  // assistant reply DOM after render, in case CSS alone doesn't catch
  // the inline-styled inserts the chat JS emits per message.
  (function() {
    const PIPELINE_RE = /View pipeline|Grade response/i;
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
    stripPipelineLinks();
    new MutationObserver(stripPipelineLinks).observe(
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
        "Gemma load failed. Cannot start chat server without a model.")


# ===========================================================================
# 3. Build + launch chat FastAPI server
# ===========================================================================
print("\n" + "=" * 76)
print("[3/5] launching chat server")
print("=" * 76)

from duecare.chat import create_app
# Pull just the example prompts + docs from the harness module --
# NOT the harness layer callables. The whole point of this notebook
# is RAW Gemma chat with no GREP/RAG/Tools/Persona; we still want the
# 204-prompt Examples library + the doc-extension content so a judge
# can run the SAME prompt here vs in the toggle notebook and compare.
from duecare.chat.harness import EXAMPLE_PROMPTS, LAYER_DOCS
import uvicorn

model_info = {
    "loaded": True,
    "name": loaded.name,
    "size_b": loaded.size_b,
    "quantization": loaded.quantization,
    "device": loaded.device,
    "display": f"{loaded.name} · {loaded.size_b:.1f}B · "
                f"{loaded.quantization}",
}

from duecare.chat.harness import grade_response, RUBRICS_REQUIRED

app = create_app(
    gemma_call=loaded.backend,
    model_info=model_info,
    # No grep_call / rag_call / tools_call -- raw Gemma. The Grade
    # rubric is wired even in the raw playground so users can quantify
    # how a stock response (no harness) scores on the rubric -- this
    # is the contrast point that makes the harness-on/harness-off
    # numbers meaningful.
    grade_call=grade_response,
    rubrics_required_categories=list(RUBRICS_REQUIRED.keys()),
    example_prompts=EXAMPLE_PROMPTS,
    layer_docs={"examples": LAYER_DOCS.get("examples", "")},
)
# Force RAW playground: defeat the chat package's persona-default fallback
# (line 152 of duecare/chat/app.py does `persona_default or DEFAULT_PERSONA`,
# which makes persona always look "wired" -- hides the toggle tile row by
# explicitly emptying the persona default here).
app.state.persona_default = ""
_attach_shutdown(app, hide_harness_tiles=True)


def _server_thread():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


server_t = threading.Thread(target=_server_thread, daemon=True,
                              name="duecare-chat-server")
server_t.start()
print(f"  server thread started on 0.0.0.0:{PORT}")
time.sleep(2.0)


# ===========================================================================
# 4. Cloudflared tunnel
# ===========================================================================
print("\n" + "=" * 76)
print(f"[4/5] opening {TUNNEL} tunnel")
print("=" * 76)

public_url = f"http://localhost:{PORT}"
if TUNNEL != "none":
    # Reuse the server package's tunnel helper if available; otherwise
    # roll our own minimal cloudflared launcher.
    try:
        # Note: duecare-llm-server is NOT in this notebook's wheel set;
        # we do a minimal cloudflared launch inline. Kaggle minimal
        # images don't ship cloudflared, so download the linux-amd64
        # release binary on demand (~30 MB, ~5 s).
        import shutil as _shutil, urllib.request as _urlreq, stat as _stat
        cf_bin = _shutil.which("cloudflared")
        if cf_bin is None:
            cf_bin = "/tmp/cloudflared"
            if not os.path.exists(cf_bin):
                print(f"  cloudflared not on PATH -- downloading "
                      f"linux-amd64 release ...")
                _url = ("https://github.com/cloudflare/cloudflared/"
                         "releases/latest/download/cloudflared-linux-amd64")
                _urlreq.urlretrieve(_url, cf_bin)
                os.chmod(cf_bin, _stat.S_IRWXU | _stat.S_IXGRP
                                  | _stat.S_IXOTH)
                print(f"  ✓ downloaded "
                      f"{os.path.getsize(cf_bin)//1_000_000} MB to {cf_bin}")
            else:
                print(f"  reusing cached cloudflared at {cf_bin}")
        proc = subprocess.Popen(
            [cf_bin, "tunnel", "--url", f"http://localhost:{PORT}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
        _CLOUDFLARED_PROC['p'] = proc
        # Read until we see the public URL line
        t0 = time.time()
        while time.time() - t0 < 60:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.1); continue
            print(f"  [tunnel] {line.rstrip()}")
            if "trycloudflare.com" in line:
                import re
                m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com",
                               line)
                if m:
                    public_url = m.group(0)
                    print(f"  ✓ tunnel ready: {public_url}")
                    break
        # CRITICAL: keep draining cloudflared's stdout in a daemon
        # thread so the OS pipe buffer never fills. If we don't drain,
        # cloudflared blocks on write within ~minutes of chatty heartbeat
        # logs and the tunnel stops forwarding -> Cloudflare 1033s the
        # next request.
        def _drain_stdout(p=proc):
            try:
                for raw_line in p.stdout:
                    pass  # discard; the URL was already captured above
            except Exception:
                pass
        threading.Thread(target=_drain_stdout, daemon=True,
                          name="cloudflared-stdout-drain").start()
    except Exception as e:
        print(f"  tunnel error: {type(e).__name__}: {e}")


# ===========================================================================
# 5. Print URL prominently and block
# ===========================================================================
print("\n" + "=" * 76)
print("[5/5] DUECARE GEMMA CHAT IS LIVE")
print("=" * 76)
print(f"\n   open this URL on your laptop:")
print(f"\n       {public_url}\n")
print(f"   model:    {loaded.name}  ·  {loaded.size_b:.1f}B  ·  "
      f"{loaded.quantization}")
print(f"   device:   {loaded.device}")
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
