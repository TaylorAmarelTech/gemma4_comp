"""
============================================================================
  DUECARE CONTENT CLASSIFIER  --  Kaggle notebook (paste in single cell)
============================================================================

  Structured-output companion to the chat playground. Submit content
  (text + optional screenshot) and Gemma returns a strict JSON envelope:

      {
        "classification": "predatory_recruitment_debt_bondage",
        "classification_label": "Predatory recruitment with debt bondage",
        "confidence": 0.92,
        "overall_risk": 0.88,
        "risk_vectors": [
          {"dimension": "ilo_forced_labor_indicators",
           "magnitude": 0.95, "direction": "high",
           "evidence": "..."},
          ...
        ],
        "recommended_action": "escalate_to_regulator",
        "rationale": "...",
        "ngo_referrals": ["POEA", "BP2MI", "MfMW HK"]
      }

  UI features:
    - Form-based input (textarea + image upload)
    - Visualized result card: risk bar, per-vector magnitude bars,
      confidence, NGO referral pills, recommended action pill
    - History queue with risk-threshold slider for filtering
    - View pipeline modal showing full transformation flow

  Same Persona / GREP / RAG / Tools harness as the chat playground.
  Default persona is the strict-JSON classifier instruction.

  Requires:
    - GPU T4 x2 (default 31b-it); single T4 fine for E2B/E4B
    - Internet ON
    - Datasets attached:
        taylorsamarel/duecare-content-classifier-wheels (3 wheels)
        google/gemma-4 (any IT variant)
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


DATASET_SLUG = "duecare-gemma-content-classification-evaluation-wheels"
GEMMA_MODEL_VARIANT = "31b-it"
GEMMA_LOAD_IN_4BIT  = True
GEMMA_DEVICE_MAP    = "auto"
GEMMA_MAX_SEQ_LEN   = 8192
PORT   = 8080
TUNNEL = "cloudflared"

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
    installer = (["uv", "pip", "install", "-qqq", "--system"]
                  if uv_check.returncode == 0
                  else [sys.executable, "-m", "pip", "install",
                          "-q", "--no-input", "--disable-pip-version-check"])
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
        print(f"  INSTALL FAILED ({proc.returncode}): {proc.stderr[-600:]}")
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


print("\n" + "=" * 76)
print(f"[1/5] installing duecare wheels from /kaggle/input/{DATASET_SLUG}")
print("=" * 76)


def install_chat_wheels() -> int:
    if not Path("/kaggle/input").exists():
        return 0
    found = sorted(p for p in Path("/kaggle/input").rglob("*.whl")
                    if "duecare" in p.name.lower())
    if not found:
        raise SystemExit(f"No duecare *.whl files. "
                          f"Add Data -> taylorsamarel/{DATASET_SLUG}.")
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--no-input",
            "--disable-pip-version-check", *[str(p) for p in found]]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  bulk install failed: {proc.stderr[-300:]}")
    print(f"  ✓ installed {len(found)} duecare wheels")
    return len(found)


install_chat_wheels()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--upgrade", "--no-input",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)


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
        tokenizer = get_chat_template(tokenizer, chat_template="gemma-4-thinking")
    except Exception:
        pass

    def _gemma_call(messages, max_new_tokens=2048, temperature=0.3,
                     top_p=0.95, top_k=64):
        inputs = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt").to("cuda")
        out = model.generate(
            **inputs, max_new_tokens=max_new_tokens,
            use_cache=True,
            temperature=temperature, top_p=top_p, top_k=top_k)
        text = tokenizer.batch_decode(out)[0]
        if "<|turn>model" in text: text = text.split("<|turn>model", 1)[1]
        if "<channel|>" in text: text = text.split("<channel|>", 1)[1]
        text = text.split("<turn|>", 1)[0]
        return text.replace("<bos>", "").replace("<eos>", "").strip()

    return LoadedModel(
        backend=_gemma_call, tokenizer=tokenizer, model=model,
        name=f"gemma-4-{variant}", size_b=_model_size_b(variant),
        quantization="4-bit nf4" if GEMMA_LOAD_IN_4BIT else "bf16",
        device=(f"balanced ({gpu['count']}x {gpu['name']})"
                if eff_dmap == "balanced" else "cuda:0"))


loaded = load_gemma()
if loaded is None:
    raise SystemExit("Gemma load failed.")


print("\n" + "=" * 76)
print("[3/5] launching classifier server")
print("=" * 76)

from duecare.chat import create_classifier_app
from duecare.chat.harness import (
    default_harness, GREP_RULES, RAG_CORPUS, _TOOL_DISPATCH,
    CLASSIFIER_EXAMPLES,
)
import uvicorn

model_info = {
    "loaded": True, "name": loaded.name, "size_b": loaded.size_b,
    "quantization": loaded.quantization, "device": loaded.device,
    "display": f"{loaded.name} · {loaded.size_b:.1f}B · "
                f"{loaded.quantization}",
}

# Override default_harness()'s example_prompts (chat-style) with the
# classifier-specific examples (recruitment posts / documents /
# narratives / receipts / police reports / borderline cases). Each
# entry has its own optional SVG mockup image_data_uri so judges can
# see classification of multimodal content.
_h = default_harness()
_h["example_prompts"] = list(CLASSIFIER_EXAMPLES)

app = create_classifier_app(
    gemma_call=loaded.backend,
    model_info=model_info,
    **_h,
)

print(f"  ✓ harness loaded: {len(GREP_RULES)} GREP rules, "
      f"{len(RAG_CORPUS)} RAG docs, {len(_TOOL_DISPATCH)} tools")
print(f"  ✓ classifier examples loaded: {len(CLASSIFIER_EXAMPLES)} "
      f"items across recruitment posts / documents / narratives / "
      f"police reports / compliance / borderline / off-topic")


def _server_thread():
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


server_t = threading.Thread(target=_server_thread, daemon=True,
                              name="duecare-classifier-server")
server_t.start()
print(f"  server thread started on 0.0.0.0:{PORT}")
time.sleep(2.0)


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
                os.chmod(cf_bin, _stat.S_IRWXU | _stat.S_IXGRP | _stat.S_IXOTH)
                print(f"  ✓ downloaded "
                      f"{os.path.getsize(cf_bin)//1_000_000} MB to {cf_bin}")
        proc = subprocess.Popen(
            [cf_bin, "tunnel", "--url", f"http://localhost:{PORT}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
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
        def _drain_stdout(p=proc):
            try:
                for _ in p.stdout: pass
            except Exception: pass
        threading.Thread(target=_drain_stdout, daemon=True,
                          name="cloudflared-stdout-drain").start()
    except Exception as e:
        print(f"  tunnel error: {type(e).__name__}: {e}")


print("\n" + "=" * 76)
print("[5/5] DUECARE CONTENT CLASSIFIER is LIVE")
print("=" * 76)
print(f"\n   open this URL on your laptop:")
print(f"\n       {public_url}\n")
print(f"   model:    {loaded.name}  ·  {loaded.size_b:.1f}B  ·  "
      f"{loaded.quantization}")
print(f"   device:   {loaded.device}")
print(f"   harness:  Persona (JSON output) + GREP ({len(GREP_RULES)} rules) + "
      f"RAG ({len(RAG_CORPUS)} docs) + Tools ({len(_TOOL_DISPATCH)} fns)")
print(f"\n   Submit content on the LEFT panel. Result card on the RIGHT")
print(f"   shows: classification + risk bars + per-vector magnitudes +")
print(f"   confidence + NGO referrals + raw JSON. History queue at the")
print(f"   bottom has a risk-threshold slider for filtering past results.")
print(f"\n   stop the playground by interrupting this cell.\n")
print("=" * 76)

try:
    while True:
        time.sleep(60)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
