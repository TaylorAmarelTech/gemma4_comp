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
        taylorsamarel/duecare-gemma-chat-wheels   (3 wheels: core+models+chat)
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
DATASET_SLUG = "duecare-gemma-chat-wheels"

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
print("[1/5] installing duecare-gemma-chat wheels")
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

app = create_app(gemma_call=loaded.backend, model_info=model_info)


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
        # we do a minimal cloudflared launch inline.
        import shutil as _shutil
        cf_bin = _shutil.which("cloudflared")
        if cf_bin is None:
            print(f"  cloudflared not found on PATH")
        else:
            proc = subprocess.Popen(
                [cf_bin, "tunnel", "--url", f"http://localhost:{PORT}"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)
            # Read until we see the public URL line
            t0 = time.time()
            while time.time() - t0 < 30:
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.1); continue
                print(f"  [tunnel] {line.rstrip()}")
                if "trycloudflare.com" in line:
                    # Extract the URL
                    import re
                    m = re.search(r"https://[a-z0-9\-]+\.trycloudflare\.com",
                                   line)
                    if m:
                        public_url = m.group(0)
                        print(f"  ✓ tunnel ready: {public_url}")
                        break
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
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
