"""
============================================================================
  DUECARE CHAT PLAYGROUND with GREP/RAG/Tools  --  Kaggle notebook
  (paste into a single code cell)
============================================================================

  Same chat UI as the chat-playground notebook, but with FOUR TOGGLE
  TILES that let you turn safety-harness layers on/off per message:

      Persona  expert anti-trafficking persona prepended to context
      GREP     22 regex KB rules (trafficking patterns + ILO citations
                 + corridor fee caps + ILO indicators + meta patterns)
      RAG      BM25 retrieval over an 18-doc starter corpus (ILO
                 conventions, POEA/BP2MI circulars, HK statutes,
                 NGO briefs)
      Tools    4 lookup functions + heuristic dispatcher (corridor
                 fee caps, fee camouflage decoder, ILO indicator
                 matcher, NGO intake hotlines)

  All safety content lives in the duecare-llm-chat wheel
  (duecare.chat.harness). This kernel is just:
      Gemma load + create_app(**default_harness()) + cloudflared.

  Updating rules / corpus / tools no longer requires a kernel re-paste
  -- just bump the wheel.

  Requires:
    - GPU T4 x2 (default 31b-it); single T4 fine for E2B/E4B
    - Internet ON
    - Datasets attached:
        taylorsamarel/duecare-chat-playground-with-grep-rag-tools-wheels
        google/gemma-4 (any variant; auto-detected)
    - HF_TOKEN OPTIONAL
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
DATASET_SLUG = "duecare-chat-playground-with-grep-rag-tools-wheels"

# Pick which Gemma 4 to load. All 4 instruct variants supported via
# Unsloth FastModel (Daniel Hanchen's reference recipe).
GEMMA_MODEL_VARIANT = "31b-it"
GEMMA_LOAD_IN_4BIT  = True
GEMMA_DEVICE_MAP    = "auto"
GEMMA_MAX_SEQ_LEN   = 8192

PORT   = 8080
TUNNEL = "cloudflared"


# ===========================================================================
# PHASE 0 -- install Hanchen's pinned Unsloth stack BEFORE any torch import.
# ===========================================================================
_UNSLOTH_MARKER = Path("/tmp/.duecare_unsloth_stack_v1_done")


def _need_unsloth_stack() -> bool:
    return GEMMA_MODEL_VARIANT in ("31b-it", "26b-a4b-it")


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
    return {"e2b-it": 2.0, "e4b-it": 4.0,
            "26b-a4b-it": 26.0, "31b-it": 31.0}.get(variant.lower(), 0.0)


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


def load_gemma() -> Optional[LoadedModel]:
    gpu = _detect_gpu()
    print(f"  GPU: {gpu['name']} x{gpu['count']}  ({gpu['vram_gb']:.1f} GB)"
          if gpu["available"] else "  GPU: none")
    if not gpu["available"]:
        return None
    try:
        import torch
        from unsloth import FastModel
    except Exception as e:
        print(f"  FastModel import FAILED: {type(e).__name__}: {e}")
        return None
    variant = GEMMA_MODEL_VARIANT
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
app = create_app(
    gemma_call=loaded.backend,
    model_info=model_info,
    **default_harness(),
)
_attach_shutdown(app)

print(f"  ✓ harness loaded: {len(GREP_RULES)} GREP rules, "
      f"{len(RAG_CORPUS)} RAG docs, {len(_TOOL_DISPATCH)} tools")


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
