"""
============================================================================
  DUECARE CONTENT CLASSIFICATION PLAYGROUND -- Kaggle notebook
============================================================================

  CORE notebook (3rd in the canonical order). The HANDS-ON sandbox where
  judges learn HOW Duecare classifies content before they see the polished
  live-demo. Pairs with `content-knowledge-builder-playground` (the
  knowledge-base sandbox); both are prerequisites for understanding what
  the live-demo notebook actually does.

  How this differs from `gemma-content-classification-evaluation`:

    * The classifier-evaluation notebook is the polished NGO/agency
      DASHBOARD — form, history queue, threshold filter, production UI.
    * THIS notebook is a PLAYGROUND for understanding the mechanics.
      You see the raw prompt Gemma actually receives, the raw response
      it produces, the parsed JSON envelope, and you can switch between
      classification SCHEMAS (single-label, multi-label, multi-vector).
      No history queue, no threshold filter -- just paste, classify,
      inspect.

  The four sections you can switch between:

    1. SINGLE-LABEL classification (one category from a fixed set)
    2. MULTI-LABEL classification (any subset of a tag set)
    3. RISK-VECTOR classification (per-dimension magnitude scores)
    4. CUSTOM SCHEMA (paste your own JSON Schema, get strict-JSON output)

  Each classification shows:
    - the merged prompt Gemma actually saw (byte-for-byte)
    - the raw response Gemma produced (no parsing)
    - the parsed JSON envelope (with validation errors highlighted)
    - elapsed_ms + tokens generated

  Requirements:
    - GPU: T4 x2 (default model is E4B-it; switchable to E2B for CPU-fast)
    - Internet: ON (cloudflared tunnel + HF Hub model download)
    - Wheels dataset: duecare-content-classification-playground-wheels (3 wheels)
    - Secrets: HF_TOKEN

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
============================================================================
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


# ===========================================================================
# CONFIG
# ===========================================================================
DATASET_SLUG          = "duecare-content-classification-playground-wheels"
GEMMA_MODEL_VARIANT   = "e4b-it"        # "e2b-it" | "e4b-it" | "26b-a4b-it" | "31b-it"
GEMMA_LOAD_IN_4BIT    = True
GEMMA_MAX_SEQ_LEN     = 8192
PORT                  = 8080
TUNNEL                = "cloudflared"   # "cloudflared" | "none"

GEMMA_HF_REPO_VARIANT = (
    GEMMA_MODEL_VARIANT
    .replace("e2b-it", "E2B-it").replace("e4b-it", "E4B-it")
    .replace("26b-a4b-it", "26B-A4B-it").replace("31b-it", "31B-it"))


# ===========================================================================
# PHASE 0 -- Hanchen's Unsloth stack (subprocess, before torch import)
# ===========================================================================
_UNSLOTH_MARKER = Path("/tmp/.duecare_classification_pg_unsloth_v1_done")


def _need_unsloth() -> bool:
    return GEMMA_MODEL_VARIANT in ("31b-it", "26b-a4b-it")


def _install_unsloth_stack() -> bool:
    print("=" * 76)
    print("[phase 0] installing Hanchen's Unsloth Gemma 4 stack")
    print("=" * 76)
    try:
        import numpy as _np_v, PIL as _pil_v
        np_pin = f"numpy=={_np_v.__version__}"
        pil_pin = f"pillow=={_pil_v.__version__}"
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
    print(f"  $ {' '.join(cmd[:6])} ... ({len(cmd)} packages total)")
    t0 = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"  install FAILED: {proc.stderr[-600:]}")
        return False
    print(f"  installed in {time.time() - t0:.0f}s")
    try:
        _UNSLOTH_MARKER.write_text(json.dumps(
            {"variant": GEMMA_MODEL_VARIANT,
             "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))
    except Exception:
        pass
    return True


if _need_unsloth():
    if _UNSLOTH_MARKER.exists():
        print(f"[phase 0] Unsloth marker present; skipping install")
    else:
        if not _install_unsloth_stack():
            sys.exit("[phase 0] aborting -- Unsloth stack install failed")


# ===========================================================================
# PHASE 1 -- duecare wheels + minimal server deps
# ===========================================================================
def install_deps() -> int:
    print("=" * 76)
    print("[phase 1] installing duecare wheels + server deps")
    print("=" * 76)
    # Server deps (always needed; FastAPI playground)
    cmd_srv = [sys.executable, "-m", "pip", "install", "--quiet",
               "--no-input", "--disable-pip-version-check",
               "fastapi>=0.115", "uvicorn>=0.30", "pydantic>=2.0"]
    subprocess.run(cmd_srv, capture_output=True, text=True)
    # Wheels
    if not Path("/kaggle/input").exists():
        return 0
    wheels = sorted(p for p in Path("/kaggle/input").rglob("*.whl")
                    if "duecare" in p.name.lower())
    print(f"  found {len(wheels)} duecare wheel(s)")
    if wheels:
        cmd = [sys.executable, "-m", "pip", "install", "--quiet",
               "--no-input", "--disable-pip-version-check",
               *[str(w) for w in wheels]]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print(f"  installed {len(wheels)} wheels")
            for mod in list(sys.modules):
                if mod == "duecare" or mod.startswith("duecare."):
                    del sys.modules[mod]
        else:
            print(f"  wheel install FAILED: {proc.stderr[-300:]}")
    return len(wheels)


N_WHEELS = install_deps()


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
# PHASE 2 -- Load Gemma 4
# ===========================================================================
@dataclass
class LoadedModel:
    model: Any
    tokenizer: Any
    variant: str


def load_gemma() -> Optional[LoadedModel]:
    print("=" * 76)
    print(f"[phase 2] loading Gemma 4 ({GEMMA_MODEL_VARIANT})")
    print("=" * 76)
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        if out.returncode != 0 or not out.stdout.strip():
            print("  no GPU detected (CPU mode possible for E2B only)")
            return None
        lines = [l.strip() for l in out.stdout.strip().split("\n") if l.strip()]
        gpu_count = len(lines)
        print(f"  GPU: {lines[0].split(',')[0].strip()} x{gpu_count}")
    except Exception as e:
        print(f"  nvidia-smi failed: {e}")
        return None

    # HF token
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

    if _need_unsloth():
        try:
            from unsloth import FastModel
            from unsloth.chat_templates import get_chat_template
        except Exception as e:
            print(f"  unsloth import FAILED: {e}")
            return None
        repo = f"unsloth/gemma-4-{GEMMA_HF_REPO_VARIANT}"
        device_map = "balanced" if gpu_count >= 2 else "auto"
        print(f"  loading {repo} via Unsloth FastModel (device_map={device_map})")
        try:
            model, tokenizer = FastModel.from_pretrained(
                model_name=repo, dtype=None, max_seq_length=GEMMA_MAX_SEQ_LEN,
                load_in_4bit=GEMMA_LOAD_IN_4BIT, full_finetuning=False,
                device_map=device_map)
        except Exception as e:
            print(f"  FastModel.from_pretrained FAILED: {e}")
            return None
        try:
            tokenizer = get_chat_template(tokenizer,
                                          chat_template="gemma-4-thinking")
        except Exception:
            pass
    else:
        # Legacy transformers path for E4B / E2B (faster startup)
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch
        except Exception as e:
            print(f"  transformers import FAILED: {e}")
            return None
        repo = f"google/gemma-4-{GEMMA_MODEL_VARIANT}"
        print(f"  loading {repo} via transformers")
        try:
            tokenizer = AutoTokenizer.from_pretrained(repo)
            model = AutoModelForCausalLM.from_pretrained(
                repo, device_map="auto",
                torch_dtype=torch.bfloat16,
                load_in_4bit=GEMMA_LOAD_IN_4BIT)
        except Exception as e:
            print(f"  transformers load FAILED: {e}")
            return None

    print(f"  loaded.")
    return LoadedModel(model=model, tokenizer=tokenizer,
                       variant=GEMMA_MODEL_VARIANT)


LOADED = load_gemma()


# ===========================================================================
# Gemma call
# ===========================================================================
def make_gemma_call(loaded: LoadedModel):
    import torch

    def _call(messages: list, max_new_tokens: int = 1024,
              temperature: float = 0.3) -> str:
        inputs = loaded.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True,
            tokenize=True, return_dict=True, return_tensors="pt",
        ).to("cuda")
        with torch.inference_mode():
            out = loaded.model.generate(
                **inputs, max_new_tokens=max_new_tokens, use_cache=True,
                temperature=temperature, top_p=0.95, top_k=64,
                pad_token_id=loaded.tokenizer.eos_token_id)
        text = loaded.tokenizer.batch_decode(out)[0]
        if "<|turn>model" in text:
            text = text.split("<|turn>model", 1)[1]
        if "<channel|>" in text:
            text = text.split("<channel|>", 1)[1]
        text = text.split("<turn|>", 1)[0]
        return text.replace("<bos>", "").replace("<eos>", "").strip()
    return _call


# ===========================================================================
# Classification schemas (the 4 schema modes the playground exposes)
# ===========================================================================
SCHEMA_PERSONAS = {
    "single_label": (
        "You are a content-safety classifier. Read the content and assign "
        "EXACTLY ONE category from the provided set. Respond with strict "
        "JSON only: {\"category\": \"<one>\", \"confidence\": <0..1>, "
        "\"rationale\": \"<one sentence>\"}."
    ),
    "multi_label": (
        "You are a content-safety classifier. Read the content and assign "
        "ANY SUBSET of the provided tag set that applies. Respond with "
        "strict JSON: {\"tags\": [\"<tag>\", ...], \"confidences\": "
        "{\"<tag>\": <0..1>}, \"rationale\": \"<one sentence>\"}."
    ),
    "risk_vector": (
        "You are a migrant-worker safety analyst. Read the content and "
        "score it on each dimension. Respond with strict JSON: "
        "{\"vectors\": [{\"dimension\": \"<name>\", \"magnitude\": <0..1>, "
        "\"evidence\": \"<short quote>\"}], \"overall_risk\": <0..1>, "
        "\"recommended_action\": \"<allow|log|review|escalate>\"}."
    ),
    "custom": (
        "You are a strict-JSON output engine. Read the content and produce "
        "output that conforms exactly to the JSON Schema provided in the "
        "user message. Output JSON only -- no preamble."
    ),
}

DEFAULT_LABEL_SETS = {
    "single_label": [
        "predatory_recruitment", "debt_bondage", "passport_retention",
        "wage_violation", "fee_violation", "trafficking_pattern",
        "legitimate_recruitment", "unrelated",
    ],
    "multi_label": [
        "ilo_indicator", "fee_violation", "passport_retention",
        "wage_withholding", "freedom_of_movement", "deception",
        "abuse_of_vulnerability", "isolation",
    ],
    "risk_vector": [
        "ilo_forced_labor_indicators", "fee_violation",
        "wage_protection_violation", "freedom_of_movement_restriction",
        "document_retention", "deception_at_recruitment",
    ],
}


def _build_user_message(schema: str, content: str,
                        label_set: Optional[list] = None,
                        custom_schema: Optional[str] = None) -> str:
    if schema == "custom" and custom_schema:
        return (f"JSON SCHEMA the response must conform to:\n"
                f"{custom_schema}\n\n"
                f"=== CONTENT ===\n{content}")
    labels = label_set or DEFAULT_LABEL_SETS.get(schema, [])
    return (f"=== AVAILABLE LABELS ===\n{json.dumps(labels)}\n\n"
            f"=== CONTENT TO CLASSIFY ===\n{content}")


# ===========================================================================
# FastAPI playground app
# ===========================================================================
def build_app():
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel

    app = FastAPI(title="Duecare Content Classification Playground")

    class ClassifyRequest(BaseModel):
        schema: str = "single_label"
        content: str
        label_set: Optional[list] = None
        custom_schema: Optional[str] = None
        max_new_tokens: int = 1024
        temperature: float = 0.3

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _PAGE_HTML

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True, "model_loaded": LOADED is not None}

    @app.get("/api/schemas")
    def schemas() -> dict:
        return {
            "schemas": list(SCHEMA_PERSONAS.keys()),
            "default_label_sets": DEFAULT_LABEL_SETS,
            "personas": SCHEMA_PERSONAS,
        }

    @app.post("/api/classify")
    def classify(req: ClassifyRequest) -> dict:
        if LOADED is None:
            return {"error": "model not loaded"}
        persona = SCHEMA_PERSONAS.get(req.schema, SCHEMA_PERSONAS["single_label"])
        user_text = _build_user_message(
            req.schema, req.content,
            label_set=req.label_set, custom_schema=req.custom_schema)
        messages = [
            {"role": "system",
             "content": [{"type": "text", "text": persona}]},
            {"role": "user",
             "content": [{"type": "text", "text": user_text}]},
        ]
        gemma = make_gemma_call(LOADED)
        t0 = time.time()
        raw = gemma(messages, max_new_tokens=req.max_new_tokens,
                    temperature=req.temperature)
        elapsed_ms = int((time.time() - t0) * 1000)
        # Parse JSON best-effort
        parsed = None
        parse_error = None
        try:
            # Strip markdown code fences if present
            txt = raw.strip()
            if txt.startswith("```"):
                txt = txt.split("\n", 1)[1] if "\n" in txt else txt
                if txt.endswith("```"):
                    txt = txt.rsplit("```", 1)[0]
                txt = txt.strip()
            if txt.startswith("json"):
                txt = txt[4:].strip()
            parsed = json.loads(txt)
        except Exception as e:
            parse_error = f"{type(e).__name__}: {e}"
        return {
            "merged_prompt": persona + "\n\n" + user_text,
            "raw_response": raw,
            "parsed": parsed,
            "parse_error": parse_error,
            "elapsed_ms": elapsed_ms,
            "schema": req.schema,
            "model": GEMMA_MODEL_VARIANT,
        }

    return app


# ===========================================================================
# UI (single HTML page; no external deps)
# ===========================================================================
_PAGE_HTML = """<!doctype html><html><head>
<meta charset="utf-8">
<title>Duecare Content Classification Playground</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif;
         max-width: 1100px; margin: 30px auto; padding: 0 24px;
         color: #1f2937; background: #f8fafc; }
  h1 { color: #1e40af; letter-spacing: -0.02em; margin: 0 0 6px; }
  .sub { color: #6b7280; margin: 0 0 24px; line-height: 1.5; }
  .card { background: white; border: 1px solid #e5e7eb;
          border-radius: 12px; padding: 18px; margin-bottom: 14px; }
  label { display: block; font-weight: 600; font-size: 13px;
          color: #1f2937; margin-bottom: 6px; }
  textarea { width: 100%; min-height: 120px; font-family: ui-monospace,
             SFMono-Regular, Menlo, Consolas, monospace; font-size: 13px;
             padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;
             box-sizing: border-box; resize: vertical; }
  select, input[type=number] {
             padding: 8px 10px; border: 1px solid #d1d5db;
             border-radius: 8px; font-size: 13px; }
  button { background: #1e40af; color: white; padding: 10px 18px;
           border: none; border-radius: 8px; font-weight: 600;
           font-size: 14px; cursor: pointer; }
  button:hover { background: #1e3a8a; }
  button:disabled { background: #9ca3af; cursor: not-allowed; }
  .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .pill { display: inline-block; background: #ddd6fe; color: #5b21b6;
          padding: 2px 9px; border-radius: 999px; font-size: 11px;
          font-weight: 600; margin-left: 6px; }
  .col-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .panel { background: #f8fafc; border: 1px solid #e5e7eb;
           border-radius: 8px; padding: 12px; }
  .panel h3 { margin: 0 0 8px; font-size: 13px; color: #6b7280;
              text-transform: uppercase; letter-spacing: 0.05em;
              font-weight: 700; }
  pre { background: #1f2937; color: #f9fafb; padding: 12px;
        border-radius: 8px; overflow-x: auto; font-size: 12px;
        line-height: 1.5; max-height: 380px; overflow-y: auto; }
  .meta { color: #6b7280; font-size: 12px; margin-top: 8px; }
  .err { color: #b91c1c; font-weight: 600; }
  .ok  { color: #047857; font-weight: 600; }
  details summary { cursor: pointer; font-weight: 600; padding: 6px 0; }
</style></head><body>

<h1>Duecare Content Classification Playground <span class="pill">CORE · Hands-on</span></h1>
<p class="sub">
  Paste content, pick a schema, classify. See the merged prompt Gemma
  receives, the raw response, the parsed JSON envelope, and elapsed time.
  Lighter than the NGO classifier dashboard — designed for understanding
  the mechanics, not for production triage.
</p>

<div class="card">
  <div class="row" style="margin-bottom: 12px">
    <div>
      <label>Schema</label>
      <select id="schema">
        <option value="single_label">single_label — exactly one category</option>
        <option value="multi_label">multi_label — any subset of tags</option>
        <option value="risk_vector">risk_vector — per-dimension scores</option>
        <option value="custom">custom — your own JSON schema</option>
      </select>
    </div>
    <div>
      <label>Max tokens</label>
      <input type="number" id="max_tokens" value="1024" min="128" max="4096" style="width: 100px">
    </div>
    <div>
      <label>Temperature</label>
      <input type="number" id="temperature" value="0.3" min="0" max="2" step="0.1" style="width: 80px">
    </div>
  </div>
  <label>Content</label>
  <textarea id="content" placeholder="Paste a recruitment post, a contract excerpt, a WhatsApp chat, a complaint letter, or any other text you want classified."></textarea>
  <details style="margin-top: 10px">
    <summary>Custom label set / JSON Schema (optional)</summary>
    <textarea id="custom" style="margin-top: 8px; min-height: 80px"
              placeholder='For custom schema mode: paste your JSON Schema. For other modes: a JSON array of label strings to override the defaults.'></textarea>
  </details>
  <div style="margin-top: 14px">
    <button onclick="doClassify()">Classify</button>
    <span id="status" class="meta"></span>
  </div>
</div>

<div id="result" style="display: none">
  <div class="card">
    <h3 style="margin: 0 0 8px; font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700">Parsed envelope</h3>
    <pre id="parsed"></pre>
    <div id="parse_err" class="err meta"></div>
  </div>
  <div class="col-grid">
    <div class="panel">
      <h3>Merged prompt Gemma saw</h3>
      <pre id="merged"></pre>
    </div>
    <div class="panel">
      <h3>Raw response</h3>
      <pre id="raw"></pre>
    </div>
  </div>
  <div class="meta" id="meta"></div>
</div>

<script>
async function doClassify() {
  const schema = document.getElementById('schema').value;
  const content = document.getElementById('content').value.trim();
  if (!content) { alert("Paste some content first."); return; }
  const status = document.getElementById('status');
  const customRaw = document.getElementById('custom').value.trim();
  let label_set = null;
  let custom_schema = null;
  if (customRaw) {
    if (schema === 'custom') {
      custom_schema = customRaw;
    } else {
      try { label_set = JSON.parse(customRaw); } catch (e) {
        alert("custom field is not valid JSON: " + e.message); return;
      }
    }
  }
  status.textContent = " classifying...";
  document.getElementById('result').style.display = 'none';
  const t0 = performance.now();
  try {
    const r = await fetch('/api/classify', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        schema, content, label_set, custom_schema,
        max_new_tokens: parseInt(document.getElementById('max_tokens').value),
        temperature: parseFloat(document.getElementById('temperature').value),
      }),
    });
    const data = await r.json();
    const elapsed = Math.round(performance.now() - t0);
    status.textContent = " done (" + elapsed + " ms client roundtrip)";
    document.getElementById('parsed').textContent = data.parsed
      ? JSON.stringify(data.parsed, null, 2) : '(parse failed -- see error below)';
    document.getElementById('parse_err').textContent = data.parse_error || '';
    document.getElementById('merged').textContent = data.merged_prompt;
    document.getElementById('raw').textContent = data.raw_response;
    document.getElementById('meta').textContent =
      'schema: ' + data.schema + '  ·  model: ' + data.model +
      '  ·  Gemma elapsed: ' + data.elapsed_ms + ' ms';
    document.getElementById('result').style.display = 'block';
  } catch (e) {
    status.textContent = " error: " + e.message;
  }
}
</script>
</body></html>"""


# ===========================================================================
# Launch FastAPI server + cloudflared
# ===========================================================================
def launch_server() -> Optional[str]:
    print("=" * 76)
    print(f"[serve] starting FastAPI on 0.0.0.0:{PORT}")
    print("=" * 76)
    import uvicorn
    app = build_app()
    _attach_shutdown(app)
    t = threading.Thread(target=lambda: uvicorn.run(
        app, host="0.0.0.0", port=PORT, log_level="warning"),
        daemon=True, name="duecare-class-pg")
    t.start()
    time.sleep(2.0)

    if TUNNEL != "cloudflared":
        return f"http://localhost:{PORT}"

    # cloudflared quick-tunnel
    cf = "/usr/local/bin/cloudflared" if Path("/usr/local/bin/cloudflared").exists() else "cloudflared"
    try:
        subprocess.run([cf, "--version"], capture_output=True, check=True)
    except Exception:
        # Try to install
        print("  cloudflared not found; installing...")
        try:
            subprocess.run(
                ["wget", "-q", "-O", "/usr/local/bin/cloudflared",
                 "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"],
                check=True)
            subprocess.run(["chmod", "+x", "/usr/local/bin/cloudflared"], check=True)
            cf = "/usr/local/bin/cloudflared"
        except Exception as e:
            print(f"  cloudflared install failed: {e}")
            return f"http://localhost:{PORT}"

    proc = subprocess.Popen(
        [cf, "tunnel", "--url", f"http://localhost:{PORT}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        bufsize=1)
    # R2 fix: register the proc so the shutdown handler can terminate
    # the cloudflared tunnel. Without this, re-running the cell spawns
    # additional cloudflared processes until something binds.
    _CLOUDFLARED_PROC["p"] = proc

    # Daemon thread that drains stdout to prevent pipe-buffer fill (the
    # known cloudflared 1033 root cause).
    public_url = {"u": None}
    def _drain():
        for line in proc.stdout:
            if "trycloudflare.com" in line and "https://" in line:
                import re
                m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                if m:
                    public_url["u"] = m.group(0)
    threading.Thread(target=_drain, daemon=True).start()

    # Wait for URL up to 30 sec
    for _ in range(60):
        if public_url["u"]:
            break
        time.sleep(0.5)
    return public_url["u"] or f"http://localhost:{PORT}"


# ===========================================================================
# Main
# ===========================================================================
if __name__ == "__main__" or True:
    if LOADED is None:
        print("\n" + "=" * 76)
        print("[abort] Gemma 4 did not load. Cannot serve playground.")
        print("=" * 76)
    else:
        url = launch_server()
        print("\n" + "=" * 76)
        print("DUECARE CONTENT CLASSIFICATION PLAYGROUND IS LIVE")
        print("=" * 76)
        print(f"\n  open this URL on your laptop:")
        print(f"\n      {url}\n")
        print(f"  schemas: single_label / multi_label / risk_vector / custom")
        print(f"  shows:   merged prompt Gemma saw, raw response, parsed JSON")
        print(f"  model:   {GEMMA_MODEL_VARIANT}")
        print(f"\n  stop the demo by interrupting this cell.\n")
        print("=" * 76)
        # Block until shutdown signal (via /api/shutdown) or interrupt
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
