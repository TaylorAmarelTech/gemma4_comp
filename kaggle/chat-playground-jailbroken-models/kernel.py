"""
============================================================================
  DUECARE CHAT PLAYGROUND — JAILBROKEN MODELS — Kaggle notebook
  (paste into a single code cell)
============================================================================

  APPENDIX A5. Same chat UI as chat-playground-with-grep-rag-tools (4
  harness toggles: Persona / GREP / RAG / Tools), but loads an
  abliterated / cracked / uncensored Gemma 4 variant instead of the
  stock instruct model. Demonstrates that the Duecare safety harness
  STILL transforms outputs even against intentionally-uncensored
  models -- the safety isn't in the weights, it's in the runtime.

  Default model: dealignai/Gemma-4-31B-JANG_4M-CRACK (the 31B
  "cracked" variant the project's research kernels 185-189 already
  use for jailbreak comparisons). Swap via JAILBROKEN_MODEL constant.

  Why this is APPENDIX:
    - Loads a 3rd-party abliterated/cracked model (not Google's stock)
    - Useful for red-team / safety researchers, not end users
    - Validates the rubric's "real, not faked" claim: the harness
      works EVEN when the underlying model has had its refusals
      ablated -- because GREP/RAG/Tools fire BEFORE the model sees
      the prompt, and the persona is prepended every turn.

  All 6 variants the loader supports (uncomment one in JAILBROKEN_MODEL):
    dealignai/Gemma-4-31B-JANG_4M-CRACK         -- cracked 31B (default)
    huihui-ai/gemma-4-A4B-it-abliterated        -- abliterated 26B-A4B
    huihui-ai/gemma-4-e4b-it-abliterated        -- abliterated E4B
    mlabonne/Gemma-4-E4B-it-abliterated         -- mlabonne abliterated E4B
    AEON-7/Gemma-4-A4B-it-Uncensored            -- AEON-7 uncensored 26B-A4B
    TrevorS/gemma-4-abliteration                -- TrevorS abliteration

  Requires:
    - GPU T4 x2 (default 31B variant requires ~18 GB 4-bit -> balanced)
    - Internet ON (HF Hub model download)
    - Datasets attached:
        taylorsamarel/duecare-chat-playground-jailbroken-models-wheels
    - HF_TOKEN OPTIONAL but recommended for HF Hub rate limits

  Built with Google's Gemma 4 (the underlying base; abliterated weights
  are 3rd-party derivatives). Used in accordance with the Gemma Terms of
  Use (https://ai.google.dev/gemma/terms).
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
DATASET_SLUG = "duecare-chat-playground-jailbroken-models-wheels"

# Pick ONE jailbroken variant to load. The kernel uses Unsloth FastModel
# uniformly for all of these (same loader as live-demo's stock 31B).
JAILBROKEN_MODEL = "dealignai/Gemma-4-31B-JANG_4M-CRACK"
# JAILBROKEN_MODEL = "huihui-ai/gemma-4-A4B-it-abliterated"
# JAILBROKEN_MODEL = "huihui-ai/gemma-4-e4b-it-abliterated"
# JAILBROKEN_MODEL = "mlabonne/Gemma-4-E4B-it-abliterated"
# JAILBROKEN_MODEL = "AEON-7/Gemma-4-A4B-it-Uncensored"
# JAILBROKEN_MODEL = "TrevorS/gemma-4-abliteration"

# Inferred size from the slug (used for device_map decision)
def _infer_size(slug: str) -> str:
    s = slug.lower()
    if "31b" in s:       return "31b"
    if "a4b" in s:       return "26b-a4b"
    if "e4b" in s or "e2b" in s: return "e4b"
    return "unknown"
JAILBROKEN_SIZE = _infer_size(JAILBROKEN_MODEL)
print(f"[config] jailbroken variant: {JAILBROKEN_MODEL}  (size class: {JAILBROKEN_SIZE})")

GEMMA_LOAD_IN_4BIT = True
GEMMA_DEVICE_MAP   = "auto"        # auto -> "balanced" for 31B/26B-A4B
GEMMA_MAX_SEQ_LEN  = 8192

PORT   = 8080
TUNNEL = "cloudflared"


# ===========================================================================
# PHASE 0 -- Hanchen's Unsloth stack (same install dance as live-demo)
# ===========================================================================
_UNSLOTH_MARKER = Path("/tmp/.duecare_jailbroken_unsloth_v1_done")


def _need_unsloth_stack() -> bool:
    # Big variants need it; abliterated E4B can also benefit so always install.
    return True


def _install_unsloth_stack_inline() -> bool:
    print("=" * 76)
    print("[phase 0] installing Hanchen's Unsloth Gemma 4 stack")
    print("=" * 76)
    try:
        import numpy as _np, PIL as _pil
        np_pin = f"numpy=={_np.__version__}"
        pil_pin = f"pillow=={_pil.__version__}"
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
            {"variant": JAILBROKEN_MODEL,
             "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S")},
            indent=2))
    except Exception:
        pass
    return True


if _need_unsloth_stack() and not _UNSLOTH_MARKER.exists():
    if not _install_unsloth_stack_inline():
        sys.exit("[phase 0] aborting -- Unsloth stack install failed")


# ===========================================================================
# 1. Install duecare wheels
# ===========================================================================
print("\n" + "=" * 76)
print(f"[1/5] installing duecare wheels from /kaggle/input/{DATASET_SLUG}")
print("=" * 76)


def install_chat_wheels() -> int:
    if not Path("/kaggle/input").exists():
        return 0
    found = sorted(p for p in Path("/kaggle/input").rglob("*.whl")
                    if "duecare" in p.name.lower())
    if not found:
        raise SystemExit(
            f"No duecare *.whl files in /kaggle/input. "
            f"Add Data -> Datasets -> taylorsamarel/{DATASET_SLUG}.")
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--no-input",
           "--disable-pip-version-check", *[str(p) for p in found]]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        for w in found:
            single = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet",
                 "--no-input", "--disable-pip-version-check", str(w)],
                capture_output=True, text=True)
            sym = "OK" if single.returncode == 0 else "FAIL"
            print(f"  {sym} {w.name}")
    print(f"  installed {len(found)} duecare wheels")
    return len(found)


install_chat_wheels()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                "--upgrade", "--no-input",
                "fastapi>=0.115.0", "uvicorn>=0.30.0"],
               capture_output=True, text=True)


# ===========================================================================
# CLEAN SHUTDOWN -- same pattern as the other 7 server kernels
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
  #_dc-jailbroken-warn { position: fixed; top: 12px; left: 12px; z-index: 99999;
    background: #fbbf24; color: #78350f; padding: 6px 12px; border-radius: 8px;
    font-family: -apple-system,system-ui,sans-serif; font-weight: 700;
    font-size: 11px; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }
</style>
<div id="_dc-jailbroken-warn">JAILBROKEN MODEL LOADED — refusals ablated</div>
<button id="_dc-shutdown-btn" onclick="
  if(!confirm('Shut down Duecare?')) return;
  fetch('/api/shutdown',{method:'POST'}).then(()=>{
    document.body.innerHTML=
      '<div style=\\\"padding:60px;text-align:center;font-family:system-ui\\\">'+
      '<h1 style=\\\"color:#047857\\\">Shutting down\\u2026</h1>'+
      '<p style=\\\"color:#6b7280\\\">You can close this tab.</p></div>';
  });
">\\u23FB Shutdown</button>
"""


def _attach_shutdown(app) -> None:
    """Bolt /api/shutdown + /shutdown + floating button + jailbroken-warn
    banner onto any FastAPI app."""
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
            "<p>Stops the FastAPI server, terminates the cloudflared "
            "tunnel, and exits the Kaggle cell. Re-run the cell to restart.</p>"
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

    extras = _SHUTDOWN_BUTTON_SNIPPET

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
# 2. Load the jailbroken Gemma 4 via Unsloth FastModel (same as live-demo)
# ===========================================================================
print("\n" + "=" * 76)
print(f"[2/5] loading jailbroken Gemma 4 via Unsloth FastModel")
print(f"      model: {JAILBROKEN_MODEL}")
print("=" * 76)


@dataclass
class LoadedModel:
    backend: Any
    tokenizer: Any
    model: Any
    name: str
    size_class: str
    quantization: str
    device: str


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


def load_jailbroken_gemma() -> Optional[LoadedModel]:
    gpu = _detect_gpu()
    print(f"  GPU: {gpu['name']} x{gpu['count']}  ({gpu['vram_gb']:.1f} GB)"
          if gpu["available"] else "  GPU: none")
    if not gpu["available"]:
        print("  no GPU; cannot load jailbroken variant.")
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

    try:
        import torch
        from unsloth import FastModel
    except Exception as e:
        print(f"  FastModel import FAILED: {type(e).__name__}: {e}")
        return None

    # device_map: balanced for 31B + 26B-A4B (need 2x T4); auto otherwise
    eff_dmap = GEMMA_DEVICE_MAP
    if eff_dmap == "auto" and JAILBROKEN_SIZE in ("31b", "26b-a4b"):
        eff_dmap = "balanced" if gpu["count"] >= 2 else "auto"

    print(f"  FastModel.from_pretrained({JAILBROKEN_MODEL},")
    print(f"                              max_seq={GEMMA_MAX_SEQ_LEN},")
    print(f"                              4bit={GEMMA_LOAD_IN_4BIT},")
    print(f"                              device_map={eff_dmap})")
    t0 = time.time()
    try:
        model, tokenizer = FastModel.from_pretrained(
            model_name=JAILBROKEN_MODEL,
            dtype=None,
            max_seq_length=GEMMA_MAX_SEQ_LEN,
            load_in_4bit=GEMMA_LOAD_IN_4BIT,
            full_finetuning=False,
            device_map=eff_dmap,
        )
    except Exception as e:
        print(f"  FastModel FAILED: {type(e).__name__}: {str(e)[:300]}")
        print(f"  This variant may not be quantization-compatible OR ")
        print(f"  the HF Hub repo may be gated/private. Try a different ")
        print(f"  JAILBROKEN_MODEL from the list at the top of the cell.")
        return None
    print(f"  loaded in {time.time()-t0:.0f}s")

    # Apply Hanchen's recommended chat template (works for Gemma 4 base)
    try:
        from unsloth.chat_templates import get_chat_template
        tokenizer = get_chat_template(tokenizer,
                                       chat_template="gemma-4-thinking")
        print("  applied chat_template=gemma-4-thinking")
    except Exception as e:
        print(f"  WARN: get_chat_template failed: {type(e).__name__}: {e}")
        print(f"        (jailbroken variants may have non-standard chat templates;")
        print(f"         continuing with the tokenizer's default)")

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
        name=JAILBROKEN_MODEL,
        size_class=JAILBROKEN_SIZE,
        quantization="4-bit nf4" if GEMMA_LOAD_IN_4BIT else "bf16",
        device=(f"balanced ({gpu['count']}x {gpu['name']})"
                if eff_dmap == "balanced" else "cuda:0"))


loaded = load_jailbroken_gemma()
if loaded is None:
    raise SystemExit("Jailbroken model load failed.")


# ===========================================================================
# 3. Wire chat app + harness (same as chat-playground-with-grep-rag-tools)
# ===========================================================================
print("\n" + "=" * 76)
print("[3/5] launching chat server (Persona + GREP + RAG + Tools)")
print("=" * 76)

from duecare.chat import create_app
from duecare.chat.harness import (
    default_harness, GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH,
)
import uvicorn

model_info = {
    "loaded": True,
    "name": loaded.name,
    "size_class": loaded.size_class,
    "quantization": loaded.quantization,
    "device": loaded.device,
    "display": (f"{loaded.name.split('/')[-1]} · {loaded.size_class} · "
                f"{loaded.quantization} · JAILBROKEN"),
}

app = create_app(
    gemma_call=loaded.backend,
    model_info=model_info,
    **default_harness(),
)
_attach_shutdown(app)
print(f"  harness loaded: {len(GREP_RULES)} GREP rules, "
      f"{len(RAG_CORPUS)} RAG docs, {len(_TOOL_DISPATCH)} tools")


def _server_thread():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


server_t = threading.Thread(target=_server_thread, daemon=True,
                              name="duecare-jailbroken-server")
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
            if "trycloudflare.com" in line:
                m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com", line)
                if m:
                    public_url = m.group(0)
                    print(f"  tunnel ready: {public_url}")
                    break

        def _drain_stdout(p=proc):
            try:
                for _ in p.stdout: pass
            except Exception:
                pass
        threading.Thread(target=_drain_stdout, daemon=True,
                          name="cloudflared-stdout-drain").start()
    except Exception as e:
        print(f"  tunnel error: {type(e).__name__}: {e}")


# ===========================================================================
# 5. Print URL prominently and block until shutdown
# ===========================================================================
print("\n" + "=" * 76)
print("DUECARE CHAT (JAILBROKEN MODEL) is LIVE")
print("=" * 76)
print(f"\n   open this URL on your laptop:")
print(f"\n       {public_url}\n")
print(f"   model:    {loaded.name}")
print(f"   size:     {loaded.size_class}")
print(f"   device:   {loaded.device}")
print(f"   harness:  Persona + GREP ({len(GREP_RULES)}) + "
      f"RAG ({len(RAG_CORPUS)}) + Tools ({len(_TOOL_DISPATCH)})")
print(f"\n   The yellow banner top-left reminds you the model is ABLATED.")
print(f"   Toggle the harness ON/OFF to see the safety harness still works")
print(f"   even when the model has had its refusals removed.")
print(f"\n   shutdown:  click the red button (top-right) or open "
      f"{public_url}/shutdown")
print(f"              or interrupt this cell.\n")
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
print("  shutdown complete -- cell exiting.\n")
