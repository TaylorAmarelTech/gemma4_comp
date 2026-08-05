# <!-- duecare:kernel-intro -->
# DueCare — Sentinel / research monitor (search + submit flow)
# Appendix notebook #A18 of 24 in the DueCare submission.
#
# Submit a public URL or paste text; Gemma 4 + harness decides
# whether the content yields new corridor info that should be
# proposed as a pack diff. Curator approves before any mutation.
# Mirrors sentinel.html + research-monitor.html + submit-information.html.

"""
============================================================================
  DUECARE A-18 SENTINEL / RESEARCH MONITOR -- Kaggle notebook
============================================================================
  Pipeline:
    1. Install DueCare + Unsloth + Gemma 4 (small variant default)
    2. Workbench UI: paste a URL or text + select target pack
    3. Fetch URL (urllib) or use inline text
    4. Run text through GREP rules + Gemma 4 assessment
    5. Compute relevance score; tag as approve/review/reject
    6. Emit proposed pack diff JSON for curator review

  Output: /kaggle/working
    <run_id>_proposals.json            list of proposed diffs
    <run_id>_proposals.jsonl           streaming variant
    <run_id>_metadata.json             config + summary
    <run_id>_bundle.zip                manifest + above

  Run-ID format: a18_sentinel_{iso_ts}

  Lane 04 / 05. Closes the search/submit gap from sentinel.html.

  Built with Google's Gemma 4, used under the Apache License 2.0.
============================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path


# ===========================================================================
# CONFIG
# ===========================================================================
GEMMA_MODEL_VARIANT = os.environ.get("DUECARE_GEMMA_VARIANT", "e2b-it")
GEMMA_LOAD_IN_4BIT = True
GEMMA_MAX_SEQ_LEN = 4096
PORT = 8080
TUNNEL = "cloudflared"
OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# PHASE 0 -- Unsloth stack
# ===========================================================================
_marker = Path("/tmp/.duecare_sentinel_unsloth_done")
if not _marker.exists():
    print("[phase 0] installing Unsloth stack")
    try:
        import numpy as _np, PIL as _pil
        np_pin = f"numpy=={_np.__version__}"
        pil_pin = f"pillow=={_pil.__version__}"
    except Exception:
        np_pin, pil_pin = "numpy", "pillow"
    installer = (["uv", "pip", "install", "-qqq", "--system"]
                 if subprocess.run(["uv", "--version"],
                                    capture_output=True).returncode == 0
                 else [sys.executable, "-m", "pip", "install",
                       "-q", "--no-input", "--disable-pip-version-check"])
    subprocess.run(installer + [
        "torch>=2.8.0", "triton>=3.4.0", np_pin, pil_pin,
        "torchvision", "bitsandbytes",
        "unsloth", "unsloth_zoo>=2026.4.6",
        "transformers==5.5.0", "torchcodec", "timm",
    ], capture_output=True, text=True)
    try:
        _marker.write_text("ok")
    except Exception:
        pass


# ===========================================================================
# PHASE 1 -- DueCare from GitHub
# ===========================================================================
DUECARE_VERSION = os.environ.get("DUECARE_VERSION", "0.17.0")
DUECARE_REPO = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "master"
DUECARE_PACKAGES = ["duecare-llm-chat"]


def install_duecare_from_github() -> bool:
    base_url = (f"https://github.com/{DUECARE_REPO}/releases/download/"
                f"v{DUECARE_VERSION}")
    success = 0
    for pkg in DUECARE_PACKAGES:
        wheel = f"{pkg.replace('-', '_')}-{DUECARE_VERSION}-py3-none-any.whl"
        cmd = [sys.executable, "-m", "pip", "install", "--no-input",
               "--disable-pip-version-check", "--timeout=60",
               f"{base_url}/{wheel}"]
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
        raise SystemExit(f"DueCare install: {proc.stderr[-300:]}")
    for mod in list(sys.modules):
        if mod == "duecare" or mod.startswith("duecare."):
            del sys.modules[mod]
    return True


print("\n[1/4] DueCare from GitHub")
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0",
                  "python-multipart>=0.0.9"],
                  capture_output=True, text=True)


# ===========================================================================
# 2. Load Gemma 4 + harness
# ===========================================================================
print("\n[2/4] loading Gemma 4 + harness")
from unsloth import FastModel
from unsloth.chat_templates import get_chat_template
import torch

try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-18-sentinel-research-monitor")
except Exception:
    def dc_log(*a, **kw): return None
    def set_kernel_id(*a, **kw): return None

_GEMMA_REPO = f"unsloth/gemma-4-{GEMMA_MODEL_VARIANT}-bnb-4bit"
_t0 = time.time()
model, tokenizer = FastModel.from_pretrained(
    model_name=_GEMMA_REPO,
    max_seq_length=GEMMA_MAX_SEQ_LEN,
    load_in_4bit=GEMMA_LOAD_IN_4BIT,
    dtype=None, full_finetuning=False,
)
tokenizer = get_chat_template(tokenizer, chat_template="gemma-4-thinking")
print(f"  + base loaded in {time.time() - _t0:.0f}s")

try:
    from duecare.chat.harness import GREP_RULES, _grep_call
    _HARNESS_AVAILABLE = True
    print(f"  + harness: {len(GREP_RULES)} GREP rules")
except Exception:
    _HARNESS_AVAILABLE = False
    def _grep_call(t): return {"rules_fired": [], "elapsed_ms": 0}


# ===========================================================================
# 3. Sentinel pipeline
# ===========================================================================
SENTINEL_PROMPT = (
    "You are a curator deciding whether the following text contains "
    "NEW information that should be proposed as an addition to a "
    "DueCare corridor pack. Output a structured assessment with:\n"
    "  - relevance (0.0-1.0)\n"
    "  - extracted_facts (bullet list of statutes / fee caps / NGO "
    "    contacts mentioned)\n"
    "  - rationale (why this should or should not become a pack diff)"
)


def _fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={
        "User-Agent": "DueCare-Sentinel/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"<script[^>]*>.*?</script>", " ", text,
                    flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text,
                    flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:8000]


def _gemma_assess(text: str, target_pack: str) -> str:
    messages = [
        {"role": "system", "content":
         SENTINEL_PROMPT + f"\n\nTarget pack: {target_pack}"},
        {"role": "user", "content": text},
    ]
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True,
        tokenize=True, return_dict=True, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        out = model.generate(
            **inputs, max_new_tokens=512,
            use_cache=True, temperature=0.3, top_p=0.95)
    t = tokenizer.batch_decode(out)[0]
    if "<|turn>model" in t: t = t.split("<|turn>model", 1)[1]
    if "<channel|>" in t: t = t.split("<channel|>", 1)[1]
    t = t.split("<turn|>", 1)[0]
    return t.replace("<bos>", "").replace("<eos>", "").strip()


def propose_diff(source_url: str = "", inline_text: str = "",
                  target_pack: str = "ph-hk-domestic-worker") -> dict:
    if not source_url and not inline_text:
        return {"ok": False, "error": "supply source_url or inline_text"}
    t0 = time.time()
    try:
        text = inline_text or _fetch_url(source_url)
    except Exception as e:
        return {"ok": False, "error":
                f"fetch: {type(e).__name__}: {str(e)[:200]}"}
    grep_result = _grep_call(text)
    n_fired = len(grep_result.get("rules_fired", []))
    try:
        assessment = _gemma_assess(text, target_pack)
    except Exception as e:
        assessment = f"(assessment failed: {type(e).__name__})"
    relevance = min(1.0, 0.15 * n_fired + 0.0005 * len(assessment))
    if relevance >= 0.6:
        verdict = "approve"
    elif relevance >= 0.3:
        verdict = "review"
    else:
        verdict = "reject"
    diff_id = "diff_" + hashlib.sha256(
        (source_url + inline_text[:200]).encode()).hexdigest()[:12]
    return {
        "ok": True, "diff_id": diff_id,
        "target_pack": target_pack,
        "source_url": source_url,
        "source_text_len": len(text),
        "grep_rules_fired": n_fired,
        "relevance_score": round(relevance, 3),
        "harness_verdict": verdict,
        "assessment": assessment,
        "elapsed_ms": int((time.time() - t0) * 1000),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ===========================================================================
# 4. State + workbench shell
# ===========================================================================
_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = f"a18_sentinel_{_run_ts}"
PROPOSALS: list[dict] = []
RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_proposals.json"
JSONL_PATH = OUTPUT_DIR / f"{RUN_ID}_proposals.jsonl"
META_PATH = OUTPUT_DIR / f"{RUN_ID}_metadata.json"
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"
JSONL_PATH.touch(exist_ok=True)


def _flush():
    payload = {
        "schema_version": "1.0",
        "kernel_id": "a-18-sentinel-research-monitor",
        "run_id": RUN_ID,
        "config": {"model_variant": GEMMA_MODEL_VARIANT,
                   "model_path": _GEMMA_REPO,
                   "harness_enabled": _HARNESS_AVAILABLE},
        "metadata": {"host": "kaggle"
                     if Path("/kaggle").exists() else "local"},
        "summary": {
            "n_proposals": len(PROPOSALS),
            "verdict_counts": {
                v: sum(1 for p in PROPOSALS
                        if p.get("harness_verdict") == v)
                for v in ("approve", "review", "reject")
            },
        },
        "results": PROPOSALS,
        "proposals": PROPOSALS,    # legacy alias (data_primitives.md 1.1)
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2,
                                          ensure_ascii=False),
                              encoding="utf-8")
    META_PATH.write_text(json.dumps(
        {k: v for k, v in payload.items() if k != "proposals"},
        indent=2, ensure_ascii=False), encoding="utf-8")
    with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
        _z.writestr("manifest.json", json.dumps({
            "schema_version": "1.0", "run_id": RUN_ID,
            "kernel_id": "a-18-sentinel-research-monitor",
        }, indent=2))
        _z.write(RESULTS_PATH, "proposals.json")
        _z.write(JSONL_PATH, "proposals.jsonl")
        _z.write(META_PATH, "metadata.json")


INDEX_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-17 . Sentinel / research monitor</title>
<link rel="stylesheet" href="/static/_chrome.css">
<style>
  body{background:#F7F6F1;color:#0E1116;
       font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
       margin:0;padding:0}
  .page{max-width:980px;margin:0 auto;padding:32px 28px 80px}
  h1{font-size:28px;margin:0 0 6px}
  .lede{color:#5B5F68;margin:0 0 28px;max-width:740px}
  .panel{background:#EFEDE4;border:1px solid #DDD8C9;
         border-radius:12px;padding:18px 20px;margin:14px 0}
  .panel h2{font-size:17px;margin:0 0 12px}
  input[type=text],input[type=url],textarea{width:100%;
        padding:10px 12px;border:1px solid #DDD8C9;border-radius:8px;
        background:#F7F6F1;font:inherit;margin-top:6px}
  textarea{min-height:160px}
  button.primary{background:#0E1116;color:#F7F6F1;border:none;
                 border-radius:999px;padding:11px 22px;
                 font-size:13.5px;font-weight:600;cursor:pointer;
                 margin-top:10px}
  .row{background:#FFF;border:1px solid #EFEDE4;border-radius:10px;
       padding:12px 14px;margin:8px 0;font-size:13.5px}
  .verdict{display:inline-block;padding:2px 10px;border-radius:999px;
           font-size:11px;font-weight:600}
  .verdict.approve{background:#3E8C65;color:#fff}
  .verdict.review{background:#A97935;color:#fff}
  .verdict.reject{background:#9E3F3F;color:#fff}
  pre{font-family:"JetBrains Mono",monospace;font-size:12.5px;
      background:rgba(0,0,0,.04);padding:10px 12px;border-radius:6px;
      white-space:pre-wrap;word-break:break-word}
  .dl a{color:#0E1116;text-decoration:underline}
</style></head><body>
<div class="page">
  <h1>DueCare A-17 . Sentinel / research monitor</h1>
  <p class="lede">Submit a public URL or paste text. The harness
    decides whether the content yields new corridor info that should
    be proposed as a pack diff. Curator approves before mutation.</p>
  <div class="panel">
    <h2>Submit a candidate</h2>
    <input type="url" id="src-url" placeholder="https://...">
    <textarea id="inline-text"
              placeholder="...or paste text directly here"></textarea>
    <input type="text" id="target-pack" value="ph-hk-domestic-worker">
    <br><button class="primary" onclick="submitOne()">Propose diff</button>
  </div>
  <div class="panel">
    <h2>Proposals this session</h2>
    <div id="rows"></div>
  </div>
  <p class="dl">Bundle: <a id="bundle-link" href="#">(none yet)</a></p>
</div>
<script>
function _el(tag,cls,txt){const e=document.createElement(tag);
  if(cls)e.className=cls;if(txt!=null)e.textContent=String(txt);return e}

async function submitOne(){
  const url=document.getElementById('src-url').value.trim();
  const text=document.getElementById('inline-text').value.trim();
  const pack=document.getElementById('target-pack').value.trim()
            ||'ph-hk-domestic-worker';
  if(!url&&!text){alert('provide URL or text');return}
  await fetch('/api/propose',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({source_url:url,inline_text:text,
                          target_pack:pack})
  }).then(r=>r.json());
  document.getElementById('src-url').value='';
  document.getElementById('inline-text').value='';
  refreshState();
}

async function refreshState(){
  const r=await fetch('/api/state').then(r=>r.json());
  const wrap=document.getElementById('rows');wrap.replaceChildren();
  for(const p of (r.proposals||[])){
    const c=_el('div','row');
    c.appendChild(_el('div',null,
      p.diff_id+' . target: '+p.target_pack+
      ' . GREP fired: '+p.grep_rules_fired+
      ' . relevance: '+p.relevance_score));
    c.appendChild(_el('span','verdict '+p.harness_verdict,
                       p.harness_verdict));
    if(p.source_url){
      const a=document.createElement('a');a.href=p.source_url;
      a.target='_blank';a.textContent=p.source_url;
      a.style.marginLeft='10px';a.style.fontSize='12px';
      c.appendChild(a);
    }
    c.appendChild(_el('pre',null,p.assessment));
    wrap.appendChild(c);
  }
  if(r.bundle_name){
    const a=document.getElementById('bundle-link');
    a.href='/artifact/'+encodeURIComponent(r.bundle_name);
    a.textContent=r.bundle_name+' ('+r.bundle_size_kb+' KB)';
  }
}
refreshState();
</script></body></html>
"""


print("\n[3/4] launching sentinel UI")
_SHUTDOWN_EVENT = threading.Event()

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": f"A-18 sentinel / research monitor ({GEMMA_MODEL_VARIANT})",
        "audience": "researcher",
        "lede": ("Submit URL or paste text; harness decides whether "
                  "the content yields a pack-worthy diff. Curator "
                  "approves before any pack mutation."),
        "results": [
            {"label": "Model",   "value": _GEMMA_REPO},
            {"label": "Harness", "value":
              "ON" if _HARNESS_AVAILABLE else "unavailable"},
        ],
        "links": [
            ("Experiment ladder",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
        ],
        "next_steps": [
            "Open the printed cloudflared URL.",
            "Paste a URL (e.g. an NGO advisory) + target pack slug.",
            "Click Propose diff; review verdict + assessment.",
            "Curator accepts (build new pack version via A-16) or "
            "rejects.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-18-sentinel-research-monitor",
        port=PORT, homepage_html=INDEX_HTML,
    )
    from fastapi import Request

    @app.post("/api/propose")
    async def _propose(req: Request):
        body = await req.json()
        result = propose_diff(
            source_url=body.get("source_url", ""),
            inline_text=body.get("inline_text", ""),
            target_pack=body.get("target_pack",
                                  "ph-hk-domestic-worker"))
        if result.get("ok"):
            PROPOSALS.append(result)
            with JSONL_PATH.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "schema_version": "1.0", "run_id": RUN_ID,
                    **result,
                }, ensure_ascii=False) + "\n")
            _flush()
        return result

    @app.get("/api/state")
    def _state():
        return {
            "proposals": PROPOSALS[-10:][::-1],
            "bundle_name": (BUNDLE_PATH.name
                              if BUNDLE_PATH.exists() else None),
            "bundle_size_kb": (BUNDLE_PATH.stat().st_size // 1024
                                 if BUNDLE_PATH.exists() else 0),
        }

    if public_url:
        print(f"  ok UI: {public_url}")
    print("\n  A-17 SENTINEL READY\n")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutdown complete -- cell exiting.\n")
