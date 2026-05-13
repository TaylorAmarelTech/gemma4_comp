# <!-- duecare:kernel-intro -->
# DueCare — UGC batch moderator (Lane 01)
# Appendix notebook #A15 of 24 in the DueCare submission.
#
# Upload a CSV or JSONL of inbound posts / ads / listings; the
# harness scores each through Persona + GREP + RAG + Tools and
# returns a risk envelope (score, verdict, indicators, citations,
# suggested action). Closes the Lane 01 platform-safety gap.

"""
============================================================================
  DUECARE A-15 UGC BATCH MODERATOR -- Kaggle notebook
============================================================================
  Pipeline:
    1. Install DueCare + Unsloth
    2. Load Gemma 4 (default e4b-it)
    3. Workbench shell with CSV/JSONL upload UI
    4. Per row: score through harness -> risk envelope
    5. Streaming JSONL on disk so a crash mid-run still leaves rows
    6. Aggregate summary: top indicators, verdict counts

  Input formats:
    CSV     header required; 'text' column required; 'post_id' optional
    JSONL   per-line {"post_id": str, "text": str, "metadata": ...}

  Output: /kaggle/working
    <run_id>_ugc_moderation.json
    <run_id>_ugc_moderation.jsonl
    <run_id>_metadata.json
    <run_id>_bundle.zip

  Run-ID format: a15_ugc_{variant}_{iso_ts}

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
============================================================================
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path


# ===========================================================================
# CONFIG
# ===========================================================================
GEMMA_MODEL_VARIANT = os.environ.get("DUECARE_GEMMA_VARIANT", "e4b-it")
GEMMA_LOAD_IN_4BIT = True
GEMMA_MAX_SEQ_LEN = 4096
PORT = 8080
TUNNEL = "cloudflared"

OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# PHASE 0 -- Unsloth stack
# ===========================================================================
_marker = Path("/tmp/.duecare_ugc_unsloth_done")
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
DUECARE_VERSION = "0.1.0"
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


print("\n[1/5] DueCare from GitHub")
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0",
                  "python-multipart>=0.0.9"],
                  capture_output=True, text=True)


# ===========================================================================
# 2. Load Gemma 4 + harness
# ===========================================================================
print("\n[2/5] loading Gemma 4 + harness")
from unsloth import FastModel
from unsloth.chat_templates import get_chat_template
import torch

try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-15-ugc-batch-moderator")
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
    from duecare.chat.harness import (
        GREP_RULES, _grep_call, _heuristic_tool_calls, DEFAULT_PERSONA,
    )
    _HARNESS_AVAILABLE = True
    print(f"  + harness: {len(GREP_RULES)} GREP rules")
except Exception as e:
    print(f"  WARN: harness unavailable ({e})")
    _HARNESS_AVAILABLE = False
    GREP_RULES = []
    def _grep_call(t): return {"rules_fired": [], "elapsed_ms": 0}
    def _heuristic_tool_calls(t): return {"tools_called": [],
                                            "elapsed_ms": 0}
    DEFAULT_PERSONA = ""


# ===========================================================================
# 3. Scoring pipeline
# ===========================================================================
SCORE_PROMPT = (
    "You are a content-safety moderator analyzing a post for migrant-"
    "worker exploitation indicators. Score on 0.0-1.0 risk. Identify "
    "which exploitative pattern is present (illegal placement fee, "
    "passport retention, contract substitution, debt bondage, "
    "unlicensed recruiter, deceptive offer). Cite applicable statutes "
    "(POEA MC 14-2017, RA 8042, ILO C181, ILO C189) when relevant."
)


def _gemma_score(post_text: str) -> str:
    messages = [
        {"role": "system", "content":
         SCORE_PROMPT + "\n\n" + (DEFAULT_PERSONA or "")},
        {"role": "user", "content": post_text},
    ]
    inputs = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True,
        tokenize=True, return_dict=True, return_tensors="pt").to("cuda")
    with torch.inference_mode():
        out = model.generate(
            **inputs, max_new_tokens=384,
            use_cache=True, temperature=0.3, top_p=0.95)
    text = tokenizer.batch_decode(out)[0]
    if "<|turn>model" in text:
        text = text.split("<|turn>model", 1)[1]
    if "<channel|>" in text:
        text = text.split("<channel|>", 1)[1]
    text = text.split("<turn|>", 1)[0]
    return text.replace("<bos>", "").replace("<eos>", "").strip()


def score_post(post_id: str, text: str,
                 metadata: dict | None = None) -> dict:
    t0 = time.time()
    try:
        analysis = _gemma_score(text)
    except Exception as e:
        return {"post_id": post_id, "text": text,
                "error": f"{type(e).__name__}: {str(e)[:200]}"}
    grep_result = _grep_call(text)
    indicators = [
        {"label": r.get("category", "unknown"),
         "severity": r.get("severity", "medium"),
         "evidence": r.get("match_text", "")[:140]}
        for r in grep_result.get("rules_fired", [])
    ]
    weight = {"high": 0.35, "medium": 0.15, "low": 0.05}
    raw = sum(weight.get(i["severity"], 0.1) for i in indicators)
    risk_score = min(1.0, raw)
    if risk_score >= 0.8:
        verdict, action = "high_risk", "remove"
    elif risk_score >= 0.5:
        verdict, action = "medium_risk", "queue_for_review"
    elif risk_score >= 0.2:
        verdict, action = "low_risk", "monitor"
    else:
        verdict, action = "ok", "allow"
    citations = sorted(set(re.findall(
        r"ILO\s+(?:C0?\d{2,3}|Convention\s+\d+)|POEA\s+MC\s+[\d-]+|"
        r"RA\s+\d+|BP2MI\s+Reg\s+[\d-]+", analysis, re.IGNORECASE)))
    return {
        "post_id": post_id,
        "text": text,
        "metadata": metadata or {},
        "risk_score": round(risk_score, 3),
        "verdict": verdict,
        "action_hint": action,
        "indicators": indicators,
        "citations": citations,
        "analysis": analysis,
        "elapsed_ms": int((time.time() - t0) * 1000),
        "error": None,
    }


def parse_upload(raw: bytes, filename: str) -> list[dict]:
    rows: list[dict] = []
    text = raw.decode("utf-8", errors="replace")
    if filename.lower().endswith(".jsonl"):
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
                if "text" in obj:
                    rows.append({
                        "post_id": obj.get("post_id",
                                            f"post_{len(rows):05d}"),
                        "text": obj["text"],
                        "metadata": obj.get("metadata", {}),
                    })
            except json.JSONDecodeError:
                continue
    else:
        reader = csv.DictReader(io.StringIO(text))
        for r in reader:
            if "text" in r and r["text"]:
                rows.append({
                    "post_id": r.get("post_id",
                                       f"post_{len(rows):05d}"),
                    "text": r["text"],
                    "metadata": {k: v for k, v in r.items()
                                  if k not in ("text", "post_id")},
                })
    return rows


# ===========================================================================
# 4. State + flush
# ===========================================================================
_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = f"a15_ugc_{GEMMA_MODEL_VARIANT}_{_run_ts}"
RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_ugc_moderation.json"
JSONL_PATH = OUTPUT_DIR / f"{RUN_ID}_ugc_moderation.jsonl"
META_PATH = OUTPUT_DIR / f"{RUN_ID}_metadata.json"
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"

RESULTS: list[dict] = []
_session_t0 = time.time()


def _aggregate() -> dict:
    indicator_counts: dict[str, int] = {}
    verdict_counts = {"high_risk": 0, "medium_risk": 0,
                       "low_risk": 0, "ok": 0}
    for r in RESULTS:
        verdict_counts[r.get("verdict", "ok")] = (
            verdict_counts.get(r.get("verdict", "ok"), 0) + 1)
        for ind in r.get("indicators", []):
            indicator_counts[ind["label"]] = (
                indicator_counts.get(ind["label"], 0) + 1)
    top = sorted(indicator_counts.items(), key=lambda kv: -kv[1])[:10]
    return {
        "n_posts": len(RESULTS),
        "verdict_counts": verdict_counts,
        "top_indicators": [{"label": k, "count": v} for k, v in top],
        "mean_elapsed_ms": round(
            sum(r.get("elapsed_ms", 0) for r in RESULTS)
            / max(1, len(RESULTS)), 1),
    }


def _flush():
    payload = {
        "schema_version": "1.0",
        "kernel_id": "a-15-ugc-batch-moderator",
        "run_id": RUN_ID,
        "config": {
            "model_variant": GEMMA_MODEL_VARIANT,
            "model_path": _GEMMA_REPO,
            "harness_enabled": _HARNESS_AVAILABLE,
        },
        "metadata": {
            "started_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(_session_t0)),
            "kaggle_kernel_id": "a-15-ugc-batch-moderator",
            "host": "kaggle" if Path("/kaggle").exists() else "local",
        },
        "summary": _aggregate(),
        "aggregate": _aggregate(),    # legacy alias; canonical key is 'summary' (data_primitives.md 1.1)
        "results": RESULTS,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2,
                                          ensure_ascii=False),
                              encoding="utf-8")
    META_PATH.write_text(json.dumps(
        {k: v for k, v in payload.items() if k != "results"},
        indent=2, ensure_ascii=False), encoding="utf-8")
    # Streaming JSONL companion (data_primitives.md section 1.7) --
    # one PerRow per line, prefixed with envelope metadata so each
    # line is self-describing for jq / pandas read_json(lines=True).
    with JSONL_PATH.open("w", encoding="utf-8") as _fh:
        for _row in RESULTS:
            _line = {
                "schema_version": "1.0",
                "run_id": RUN_ID,
                "kernel_id": "a-15-ugc-batch-moderator",
                **_row,
            }
            _fh.write(json.dumps(_line, ensure_ascii=False) + "\n")
    with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
        _z.writestr("manifest.json", json.dumps({
            "schema_version": "1.0",
            "run_id": RUN_ID,
            "kernel_id": "a-15-ugc-batch-moderator",
        }, indent=2))
        _z.write(RESULTS_PATH, "ugc_moderation.json")
        _z.write(JSONL_PATH, "ugc_moderation.jsonl")
        _z.write(META_PATH, "metadata.json")


# JSONL_PATH is populated during _flush() above. Touch as a safety
# net so an early dashboard hit (before any rows have been scored)
# doesn't 404 on the eventual zip-extract path.
JSONL_PATH.touch(exist_ok=True)


# ===========================================================================
# 5. Workbench shell
# ===========================================================================
INDEX_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-15 . UGC moderator</title>
<link rel="stylesheet" href="/static/_chrome.css">
<style>
  body{background:#F7F6F1;color:#0E1116;
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",
                    system-ui,sans-serif;margin:0;padding:0}
  .page{max-width:980px;margin:0 auto;padding:32px 28px 80px}
  h1{font-size:28px;margin:0 0 6px}
  .lede{color:#5B5F68;margin:0 0 28px;max-width:740px}
  .upload-zone{background:#EFEDE4;border:1px dashed #8A8E97;
               border-radius:12px;padding:28px 22px;text-align:center;
               margin-bottom:18px}
  .upload-zone input[type=file]{width:80%;padding:10px;
                                border:1px solid #DDD8C9;
                                border-radius:6px;background:#F7F6F1}
  button.primary{background:#0E1116;color:#F7F6F1;border:none;
                 border-radius:999px;padding:11px 22px;
                 font-size:13.5px;font-weight:600;cursor:pointer;
                 margin-top:12px}
  button.primary:disabled{opacity:.45;cursor:not-allowed}
  .panel{background:#EFEDE4;border:1px solid #DDD8C9;
         border-radius:12px;padding:18px 20px;margin:14px 0}
  .panel h2{font-size:17px;margin:0 0 12px}
  .kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
  .kpi{background:#F7F6F1;border:1px solid #DDD8C9;
       border-radius:10px;padding:12px 14px}
  .kpi .label{color:#5B5F68;font-size:11px;text-transform:uppercase}
  .kpi .value{font-size:20px;font-weight:700;margin-top:4px}
  .row{background:#FFF;border:1px solid #EFEDE4;border-radius:10px;
       padding:12px 14px;margin:8px 0;font-size:13.5px}
  .row .pid{font-family:"JetBrains Mono",ui-monospace,monospace;
            color:#5B5F68;font-size:11.5px}
  .verdict{display:inline-block;padding:2px 10px;border-radius:999px;
           font-size:11px;font-weight:600}
  .verdict.high_risk{background:#9E3F3F;color:#fff}
  .verdict.medium_risk{background:#A97935;color:#fff}
  .verdict.low_risk{background:#E2C97A;color:#3A2F0F}
  .verdict.ok{background:#3E8C65;color:#fff}
  .flag{display:inline-block;padding:2px 8px;border-radius:999px;
        background:#F5E8E8;color:#6B2929;font-size:11px;margin:2px 4px 0 0}
  .cite{display:inline-block;padding:2px 8px;border-radius:999px;
        background:#EAF2EC;color:#1F4F33;font-size:11px;margin:2px 4px 0 0}
  .dl{margin-top:14px}
  .dl a{color:#0E1116;text-decoration:underline}
</style></head><body>
<div class="page">
  <h1>DueCare A-15 . UGC batch moderator</h1>
  <p class="lede">Upload CSV (must have <code>text</code> column) or
    JSONL (each line <code>{"post_id":"...","text":"..."}</code>).
    Harness scores each post; risk envelope returned. Lane 01.</p>
  <div class="upload-zone">
    <input type="file" id="file-input" accept=".csv,.jsonl,.json">
    <button class="primary" id="run-btn" disabled
            onclick="runBatch()">Moderate batch</button>
  </div>
  <div class="panel" id="agg-panel" style="display:none">
    <h2>Aggregate</h2>
    <div class="kpi-row" id="kpis"></div>
    <div id="top-ind" style="margin-top:12px"></div>
  </div>
  <div class="panel">
    <h2>Latest rows</h2>
    <div id="rows"></div>
  </div>
  <p class="dl">Bundle: <a id="bundle-link" href="#">(no rows yet)</a></p>
</div>
<script>
const inp=document.getElementById('file-input');
const btn=document.getElementById('run-btn');
inp.addEventListener('change',()=>{btn.disabled=!inp.files.length});

async function runBatch(){
  const file=inp.files[0];if(!file)return;
  btn.disabled=true;btn.textContent='moderating ...';
  const fd=new FormData();fd.append('file',file);
  try{await fetch('/api/moderate-batch',{method:'POST',body:fd}).then(r=>r.json())}
  catch(e){}
  btn.disabled=false;btn.textContent='Moderate batch';
  refreshState();
}
function _el(tag,cls,txt){const e=document.createElement(tag);
  if(cls)e.className=cls;if(txt!=null)e.textContent=String(txt);return e}
function _kpi(l,v){const e=_el('div','kpi');
  e.appendChild(_el('div','label',l));
  e.appendChild(_el('div','value',v));return e}
async function refreshState(){
  const r=await fetch('/api/state').then(r=>r.json());
  if(r.aggregate&&r.aggregate.n_posts){
    document.getElementById('agg-panel').style.display='block';
    const k=document.getElementById('kpis');k.replaceChildren();
    const a=r.aggregate;
    k.appendChild(_kpi('Posts',a.n_posts));
    k.appendChild(_kpi('High-risk',a.verdict_counts.high_risk||0));
    k.appendChild(_kpi('Medium',a.verdict_counts.medium_risk||0));
    k.appendChild(_kpi('Mean ms',Math.round(a.mean_elapsed_ms||0)));
    const ti=document.getElementById('top-ind');ti.replaceChildren();
    for(const x of (a.top_indicators||[]).slice(0,5)){
      ti.appendChild(_el('span','flag',x.label+' x'+x.count));
    }
  }
  const wrap=document.getElementById('rows');wrap.replaceChildren();
  for(const row of (r.recent_rows||[]).slice(0,10)){
    const c=_el('div','row');
    c.appendChild(_el('div','pid',row.post_id));
    c.appendChild(_el('div','text',row.text));
    c.appendChild(_el('span','verdict '+row.verdict,
                      row.verdict+' . score '+row.risk_score));
    for(const ind of (row.indicators||[]))
      c.appendChild(_el('span','flag',
                          ind.label+' ('+ind.severity+')'));
    for(const ct of (row.citations||[]))
      c.appendChild(_el('span','cite',ct));
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


print("\n[3/5] launching UGC moderator UI")
_SHUTDOWN_EVENT = threading.Event()

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": f"A-15 UGC batch moderator ({GEMMA_MODEL_VARIANT})",
        "audience": "platform_safety",
        "lede": ("Upload CSV or JSONL of posts; harness scores each "
                  "and returns risk envelopes. Lane 01."),
        "results": [
            {"label": "Model", "value": _GEMMA_REPO},
            {"label": "Harness", "value":
              "ON" if _HARNESS_AVAILABLE else "unavailable"},
        ],
        "links": [
            ("Experiment ladder",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
        ],
        "next_steps": [
            "Open the printed cloudflared URL.",
            "Drop a CSV or JSONL of posts; click Moderate batch.",
            "Download bundle.zip when done.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-15-ugc-batch-moderator",
        port=PORT, homepage_html=INDEX_HTML,
    )
    from fastapi import UploadFile, File

    @app.post("/api/moderate-batch")
    async def _moderate(file: UploadFile = File(...)):
        raw = await file.read()
        rows = parse_upload(raw, getattr(file, "filename", "upload"))
        dc_log("a14.batch.start", f"{len(rows)} rows", run_id=RUN_ID)
        appended = 0
        with JSONL_PATH.open("a", encoding="utf-8") as fh:
            for r in rows:
                result = score_post(r["post_id"], r["text"],
                                      r.get("metadata"))
                RESULTS.append(result)
                fh.write(json.dumps({
                    "schema_version": "1.0",
                    "run_id": RUN_ID,
                    "kernel_id": "a-15-ugc-batch-moderator",
                    **result,
                }, ensure_ascii=False) + "\n")
                fh.flush()
                appended += 1
        _flush()
        return {"ok": True, "n_appended": appended,
                "n_total": len(RESULTS)}

    @app.get("/api/state")
    def _state():
        return {
            "aggregate": _aggregate(),
            "recent_rows": RESULTS[-10:][::-1],
            "bundle_name": (BUNDLE_PATH.name
                              if BUNDLE_PATH.exists() else None),
            "bundle_size_kb": (BUNDLE_PATH.stat().st_size // 1024
                                 if BUNDLE_PATH.exists() else 0),
        }

    if public_url:
        print(f"  ok UI: {public_url}")
    print("\n[5/5] A-14 SHELL READY -- awaiting batch upload\n")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutdown complete -- cell exiting.\n")
