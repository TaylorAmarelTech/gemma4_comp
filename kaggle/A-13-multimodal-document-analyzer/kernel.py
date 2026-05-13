# <!-- duecare:kernel-intro -->
# DueCare — Multimodal document analyzer (Gemma 4 vision)
# Appendix notebook #A13 of 24 in the DueCare submission.
#
# Upload a photo of a recruitment contract, passport letter, or job
# advertisement; Gemma 4's vision capability extracts the text,
# the harness flags risks (passport retention, illegal fees,
# contract substitution), and emits a structured risk envelope
# with citations.
#
# Demo path: Run All -> open URL -> drop contract.jpg -> read structured envelope.

"""
============================================================================
  DUECARE A-13 MULTIMODAL DOCUMENT ANALYZER -- Kaggle notebook
============================================================================
  Per the hackathon rubric requirement that Gemma 4's UNIQUE features
  (multimodal understanding) be load-bearing rather than decorative,
  A-12 is the multimodal anchor of the appendix.

  Output: /kaggle/working
    <run_id>_multimodal_results.json    full per-upload results
    <run_id>_metadata.json              config + summary
    <run_id>_bundle.zip                 manifest + above
  Run-ID format: a12_multimodal_{variant}_{iso_ts}

  Requirements:
    - GPU: T4 (e4b-it default); e2b-it also vision-capable
    - Internet: ON (GitHub + HF Hub model download)

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
============================================================================
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Optional


# ===========================================================================
# CONFIG
# ===========================================================================
GEMMA_MODEL_VARIANT = os.environ.get("DUECARE_GEMMA_VARIANT", "e4b-it")
GEMMA_LOAD_IN_4BIT  = True
GEMMA_MAX_SEQ_LEN   = 8192
PORT                = 8080
TUNNEL              = "cloudflared"

OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# PHASE 0 -- Unsloth stack
# ===========================================================================
_UNSLOTH_MARKER = Path("/tmp/.duecare_multimodal_unsloth_done")


def _install_unsloth_stack() -> bool:
    print("[phase 0] installing Unsloth stack")
    try:
        import numpy as _np, PIL as _pil
        np_pin = f"numpy=={_np.__version__}"
        pil_pin = f"pillow=={_pil.__version__}"
    except Exception:
        np_pin, pil_pin = "numpy", "pillow"
    if subprocess.run(["uv", "--version"],
                        capture_output=True).returncode == 0:
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
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  INSTALL FAILED: {proc.stderr[-500:]}")
        return False
    try:
        _UNSLOTH_MARKER.write_text("ok")
    except Exception:
        pass
    return True


if not _UNSLOTH_MARKER.exists():
    _install_unsloth_stack()


# ===========================================================================
# PHASE 1 -- DueCare from GitHub
# ===========================================================================
DUECARE_VERSION    = "0.1.0"
DUECARE_REPO       = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "44f3465"
DUECARE_PACKAGES   = ["duecare-llm-chat"]


def install_duecare_from_github() -> bool:
    print("[install] DueCare from GitHub")
    base_url = (f"https://github.com/{DUECARE_REPO}/releases/download/"
                f"v{DUECARE_VERSION}")
    success = 0
    for pkg in DUECARE_PACKAGES:
        wheel = f"{pkg.replace('-', '_')}-{DUECARE_VERSION}-py3-none-any.whl"
        url = f"{base_url}/{wheel}"
        cmd = [sys.executable, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "--timeout=60", url]
        if subprocess.run(cmd, capture_output=True, text=True,
                            timeout=90).returncode == 0:
            success += 1
    if success == len(DUECARE_PACKAGES):
        for mod in list(sys.modules):
            if mod == "duecare" or mod.startswith("duecare."):
                del sys.modules[mod]
        return True
    git_pkgs = [
        f"git+https://github.com/{DUECARE_REPO}.git@{DUECARE_COMMIT_SHA}"
        f"#subdirectory=packages/{p}" for p in DUECARE_PACKAGES
    ]
    cmd = [sys.executable, "-m", "pip", "install", "--no-input",
           "--disable-pip-version-check", "--timeout=300", *git_pkgs]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
    if proc.returncode != 0:
        raise SystemExit(
            f"DueCare GitHub install failed: {proc.stderr[-300:]}")
    for mod in list(sys.modules):
        if mod == "duecare" or mod.startswith("duecare."):
            del sys.modules[mod]
    return True


print("\n[1/4] DueCare from GitHub")
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0",
                  "python-multipart>=0.0.9", "pillow>=10.0.0"],
                  capture_output=True, text=True)


# ===========================================================================
# 2. Load Gemma 4 vision model
# ===========================================================================
print("\n[2/4] loading Gemma 4 vision model")
from unsloth import FastModel
from unsloth.chat_templates import get_chat_template
from PIL import Image
import torch

try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-12-multimodal-document-analyzer")
except Exception:
    def dc_log(*a, **kw): return None
    def set_kernel_id(*a, **kw): return None

_GEMMA_REPO = f"unsloth/gemma-4-{GEMMA_MODEL_VARIANT}-bnb-4bit"
_t0 = time.time()
model, tokenizer = FastModel.from_pretrained(
    model_name=_GEMMA_REPO,
    max_seq_length=GEMMA_MAX_SEQ_LEN,
    load_in_4bit=GEMMA_LOAD_IN_4BIT,
    dtype=None,
    full_finetuning=False,
)
tokenizer = get_chat_template(tokenizer, chat_template="gemma-4-thinking")
print(f"  + base loaded in {time.time() - _t0:.0f}s")

try:
    from duecare.chat.harness import GREP_RULES, _grep_call, _heuristic_tool_calls
    _HARNESS_AVAILABLE = True
    print(f"  + harness available: {len(GREP_RULES)} GREP rules")
except Exception:
    _HARNESS_AVAILABLE = False
    GREP_RULES = []
    def _grep_call(t): return {"rules_fired": [], "elapsed_ms": 0}
    def _heuristic_tool_calls(t): return {"tools_called": [], "elapsed_ms": 0}


# ===========================================================================
# 3. Vision pipeline
# ===========================================================================
VISION_PROMPT = (
    "You are analyzing a photo of a labour-related document (recruitment "
    "contract, passport notice, job advertisement, or fee receipt). "
    "Your task:\n"
    "  1. Extract the visible text VERBATIM.\n"
    "  2. List any exploitative clauses (passport retention, illegal "
    "     fees, contract substitution, isolation requirements).\n"
    "  3. Cite applicable ILO conventions (C029, C181, C189) and "
    "     national statutes you recognise.\n"
    "  4. Suggest NGO referrals if abuse indicators are present."
)


def vision_call(image: Image.Image, user_question: str = "") -> str:
    messages = [
        {"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text", "text":
             f"{VISION_PROMPT}\n\nUser question: {user_question}".strip()},
        ]},
    ]
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True,
        tokenize=True, return_dict=True, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        out = model.generate(
            **inputs, max_new_tokens=768,
            use_cache=True, temperature=0.7, top_p=0.95)
    text = tokenizer.batch_decode(out)[0]
    if "<|turn>model" in text:
        text = text.split("<|turn>model", 1)[1]
    if "<channel|>" in text:
        text = text.split("<channel|>", 1)[1]
    text = text.split("<turn|>", 1)[0]
    return text.replace("<bos>", "").replace("<eos>", "").strip()


def analyze_upload(raw: bytes, mime: str, user_question: str = "") -> dict:
    img_sha = hashlib.sha256(raw).hexdigest()[:16]
    upload_id = f"doc_{img_sha[:12]}"
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as e:
        return {"upload_id": upload_id,
                "error": f"image decode: {type(e).__name__}: {str(e)[:200]}"}
    t0 = time.time()
    dc_log("a12.upload", "vision call started", upload_id=upload_id)
    try:
        vision_text = vision_call(img, user_question)
    except Exception as e:
        return {"upload_id": upload_id,
                "error": f"vision call: {type(e).__name__}: {str(e)[:300]}"}
    grep_result = _grep_call(vision_text)
    tool_result = _heuristic_tool_calls(vision_text)
    risk_flags = [
        {"label": r.get("category", "unknown"),
         "severity": r.get("severity", "medium"),
         "evidence": r.get("match_text", "")[:140]}
        for r in grep_result.get("rules_fired", [])
    ]
    import re
    citations = sorted(set(re.findall(
        r"ILO\s+(?:C0?\d{2,3}|Convention\s+\d+)|POEA\s+MC\s+[\d-]+|"
        r"RA\s+\d+|BP2MI\s+Reg\s+[\d-]+", vision_text, re.IGNORECASE)))
    elapsed = round(time.time() - t0, 2)
    dc_log("a12.upload.done", "vision pipeline complete",
            upload_id=upload_id, elapsed_s=elapsed)
    return {
        "upload_id": upload_id,
        "image_sha256": img_sha,
        "image_mime": mime,
        "image_dims": f"{img.width}x{img.height}",
        "user_question": user_question,
        "extracted_text": vision_text,
        "risk_flags": risk_flags,
        "citations": citations,
        "tools_called": tool_result.get("tools_called", []),
        "elapsed_s": elapsed,
        "error": None,
    }


# ===========================================================================
# 4. State + workbench shell
# ===========================================================================
_SHUTDOWN_EVENT = threading.Event()
_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = f"a12_multimodal_{GEMMA_MODEL_VARIANT}_{_run_ts}"
RESULTS: list[dict] = []
RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_multimodal_results.json"
META_PATH    = OUTPUT_DIR / f"{RUN_ID}_metadata.json"
BUNDLE_PATH  = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"
_session_t0 = time.time()


def _flush_bundle():
    payload = {
        "schema_version": "1.0",
        "kernel_id": "a-12-multimodal-document-analyzer",
        "run_id": RUN_ID,
        "config": {
            "model_variant": GEMMA_MODEL_VARIANT,
            "model_path": _GEMMA_REPO,
            "model_kind": "stock-multimodal",
            "harness_enabled": _HARNESS_AVAILABLE,
            "max_new_tokens": 768,
        },
        "metadata": {
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime(_session_t0)),
            "kaggle_kernel_id": "a-12-multimodal-document-analyzer",
            "host": "kaggle" if Path("/kaggle").exists() else "local",
        },
        "summary": {
            "n_uploads": len(RESULTS),
            "n_with_risk_flags": sum(1 for r in RESULTS
                                       if r.get("risk_flags")),
        },
        "results": RESULTS,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2,
                                          ensure_ascii=False),
                              encoding="utf-8")
    META_PATH.write_text(json.dumps(
        {k: v for k, v in payload.items() if k != "results"},
        indent=2, ensure_ascii=False), encoding="utf-8")
    with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
        _z.writestr("manifest.json", json.dumps({
            "schema_version": "1.0",
            "run_id": RUN_ID,
            "kernel_id": "a-12-multimodal-document-analyzer",
            "files": ["multimodal_results.json", "metadata.json"],
        }, indent=2))
        _z.write(RESULTS_PATH, "multimodal_results.json")
        _z.write(META_PATH, "metadata.json")


INDEX_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-12 . Multimodal document analyzer</title>
<link rel="stylesheet" href="/static/_chrome.css">
<style>
  body{background:#F7F6F1;color:#0E1116;font-family:-apple-system,
       BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;margin:0;
       padding:0;line-height:1.55}
  .page{max-width:980px;margin:0 auto;padding:32px 28px 80px}
  h1{font-size:28px;margin:0 0 6px}
  .lede{color:#5B5F68;margin:0 0 28px;max-width:740px}
  .upload-zone{background:#EFEDE4;border:1px dashed #8A8E97;
               border-radius:12px;padding:28px 22px;margin-bottom:18px;
               text-align:center}
  .upload-zone input[type=file]{width:80%;padding:10px;
                                border:1px solid #DDD8C9;border-radius:6px;
                                background:#F7F6F1;cursor:pointer}
  .question{width:100%;padding:12px 16px;margin-top:14px;
            border:1px solid #DDD8C9;border-radius:8px;
            background:#F7F6F1;font:inherit}
  button.primary{background:#0E1116;color:#F7F6F1;border:none;
                 border-radius:999px;padding:11px 22px;font-size:13.5px;
                 font-weight:600;cursor:pointer;margin-top:12px}
  button.primary:disabled{opacity:.45;cursor:not-allowed}
  .result{background:#EFEDE4;border:1px solid #DDD8C9;
          border-radius:12px;padding:18px 20px;margin:14px 0}
  .result h3{margin:0 0 8px;font-size:15px}
  .result pre{font-family:"JetBrains Mono",ui-monospace,monospace;
              font-size:12.5px;background:rgba(0,0,0,.04);padding:10px 12px;
              border-radius:6px;white-space:pre-wrap;word-break:break-word}
  .flag{display:inline-block;padding:3px 10px;border-radius:999px;
        background:#F5E8E8;color:#6B2929;font-size:12px;
        margin:2px 6px 2px 0;font-weight:600}
  .flag.high{background:#9E3F3F;color:#fff}
  .cite{display:inline-block;padding:3px 10px;border-radius:999px;
        background:#EAF2EC;color:#1F4F33;font-size:12px;
        margin:2px 6px 2px 0;font-weight:600}
  .meta{color:#5B5F68;font-size:12.5px;margin-top:10px}
  .dl{margin-top:16px}
  .dl a{color:#0E1116;text-decoration:underline;text-underline-offset:3px}
</style></head><body>
<div class="page">
  <h1>DueCare A-12 . Multimodal document analyzer</h1>
  <p class="lede">Upload a contract / passport / job-ad photo. Gemma 4
    vision extracts the text; the harness flags risks and cites ILO
    conventions. No image leaves this kernel.</p>
  <div class="upload-zone">
    <input type="file" id="image-input"
            accept="image/png,image/jpeg,image/webp">
    <input type="text" id="question" class="question"
            placeholder="Optional question (e.g. 'is this fee legal?')">
    <button class="primary" id="analyze-btn" disabled
            onclick="analyzeUpload()">Analyze with Gemma 4 vision</button>
  </div>
  <div id="results"></div>
  <p class="dl">Bundle: <a href="#" id="bundle-link">(no uploads yet)</a></p>
</div>
<script>
const inp=document.getElementById('image-input');
const btn=document.getElementById('analyze-btn');
inp.addEventListener('change',()=>{btn.disabled=!inp.files.length});
async function analyzeUpload(){
  const file=inp.files[0];if(!file)return;
  btn.disabled=true;btn.textContent='analyzing ...';
  const fd=new FormData();fd.append('image',file);
  fd.append('user_question',document.getElementById('question').value||'');
  let r;try{r=await fetch('/api/analyze',{method:'POST',body:fd}).then(r=>r.json())}
  catch(e){btn.disabled=false;btn.textContent='Analyze with Gemma 4 vision';return}
  btn.disabled=false;btn.textContent='Analyze with Gemma 4 vision';
  appendResult(r);
}
function appendResult(r){
  const wrap=document.getElementById('results');
  const card=document.createElement('div');card.className='result';
  if(r.error){
    const h=document.createElement('h3');h.textContent='Error: '+r.upload_id;
    const pre=document.createElement('pre');pre.textContent=r.error;
    card.appendChild(h);card.appendChild(pre);
  }else{
    const h=document.createElement('h3');
    h.textContent='Upload '+r.upload_id+' ('+r.image_dims+', '+r.image_mime+')';
    card.appendChild(h);
    if((r.risk_flags||[]).length){
      const d=document.createElement('div');
      for(const f of r.risk_flags){
        const s=document.createElement('span');
        s.className='flag'+(f.severity==='high'?' high':'');
        s.textContent=f.label+' ('+f.severity+')';
        d.appendChild(s);
      }
      card.appendChild(d);
    }
    if((r.citations||[]).length){
      const d=document.createElement('div');d.style.marginTop='6px';
      for(const c of r.citations){
        const s=document.createElement('span');s.className='cite';
        s.textContent=c;d.appendChild(s);
      }
      card.appendChild(d);
    }
    const pre=document.createElement('pre');
    pre.textContent=r.extracted_text;card.appendChild(pre);
    const m=document.createElement('div');m.className='meta';
    m.textContent='sha256: '+r.image_sha256+' . '+r.elapsed_s+'s';
    card.appendChild(m);
  }
  wrap.insertBefore(card,wrap.firstChild);
  refreshBundle();
}
async function refreshBundle(){
  const r=await fetch('/api/bundle-info').then(r=>r.json());
  if(r.bundle_name){
    const a=document.getElementById('bundle-link');
    a.href='/artifact/'+encodeURIComponent(r.bundle_name);
    a.textContent=r.bundle_name+' ('+r.n_uploads+' uploads, '+r.size_kb+' KB)';
  }
}
refreshBundle();
</script></body></html>
"""


print("\n[3/4] launching multimodal workbench shell")
try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": f"A-12 multimodal ({GEMMA_MODEL_VARIANT})",
        "audience": "individual_worker",
        "lede": ("Gemma 4 vision: drop a contract/passport photo + an "
                  "optional question -> structured envelope with risk "
                  "flags + ILO citations. Demonstrates Gemma 4's UNIQUE "
                  "multimodal capability per the rubric."),
        "results": [
            {"label": "Model",   "value": _GEMMA_REPO},
            {"label": "Vision",  "value": "Gemma 4 native multimodal"},
            {"label": "Harness", "value":
              "ON" if _HARNESS_AVAILABLE else "unavailable"},
            {"label": "Output",  "value": "v1.0 bundle (rolling)"},
        ],
        "links": [
            ("Experiment ladder spec",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
        ],
        "next_steps": [
            "Open the printed cloudflared URL.",
            "Drop a contract / passport / job-ad photo.",
            "Optionally type a question; click Analyze.",
            "Download the rolling bundle.zip when done.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-12-multimodal-document-analyzer",
        port=PORT, homepage_html=INDEX_HTML,
    )
    from fastapi import UploadFile, File, Form

    @app.post("/api/analyze")
    async def _analyze(image: UploadFile = File(...),
                         user_question: str = Form("")):
        raw = await image.read()
        result = analyze_upload(raw, image.content_type or "image/jpeg",
                                  user_question)
        RESULTS.append(result)
        _flush_bundle()
        return result

    @app.get("/api/bundle-info")
    def _bundle_info():
        if not BUNDLE_PATH.exists():
            return {"bundle_name": None, "n_uploads": 0, "size_kb": 0}
        return {"bundle_name": BUNDLE_PATH.name,
                "n_uploads": len(RESULTS),
                "size_kb": BUNDLE_PATH.stat().st_size // 1024}

    if public_url:
        print(f"  ok UI: {public_url}")
    print("\n[4/4] A-12 SHELL READY -- awaiting image uploads\n")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutdown complete -- cell exiting.\n")
