"""
============================================================================
  DUECARE CONTENT KNOWLEDGE BUILDER PLAYGROUND -- Kaggle notebook
============================================================================

  CORE notebook (4th in the canonical order). The HANDS-ON sandbox where
  judges learn HOW Duecare's knowledge base is built and extended before
  they see the polished live-demo. Pairs with
  `content-classification-playground` (the classification sandbox); both
  are prerequisites for understanding what the live-demo notebook does.

  How this differs from `chat-playground-with-grep-rag-tools`:

    * The chat-playground-with-grep-rag-tools is a CHAT UI with toggle
      tiles + Persona library + per-message custom rule additions. It's
      a CONSUMER of the harness for chat conversations.
    * THIS notebook is a BUILDER. You don't chat -- you EDIT the
      knowledge base inline:
        * GREP rules: add/edit regex patterns + severity + ILO citation
        * RAG corpus: add/edit documents + see them indexed in real time
        * Tools: add lookup tables (corridor caps, fee camouflage,
                  NGO intake) + test the lookups
        * Test panel: paste a sample text, see EXACTLY what fires
          across your edited knowledge base
        * Export/import the full knowledge base as JSON
        * Diff against the bundled built-ins

  The five tabs:

    1. GREP RULES  -- regex patterns + severity + citation + indicator
    2. RAG CORPUS  -- documents + source + index BM25 inline
    3. TOOLS       -- lookup tables (corridor caps, fee camouflage, NGO)
    4. TEST        -- paste sample text, see what fires
    5. EXPORT      -- download / upload the full knowledge JSON

  Requirements:
    - GPU: NOT REQUIRED for the builder UI. The TEST tab uses Gemma 4
      to compose harness pre-context but the rule/RAG/tool firing logic
      is pure Python.
    - Internet: ON (cloudflared tunnel)
    - Wheels dataset: duecare-content-knowledge-builder-playground-wheels
    - Secrets: HF_TOKEN (only for the optional Gemma test in TEST tab)

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
============================================================================
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ===========================================================================
# CONFIG
# ===========================================================================
DATASET_SLUG = "duecare-content-knowledge-builder-playground-wheels"
PORT         = 8080
TUNNEL       = "cloudflared"     # "cloudflared" | "none"

# Optional Gemma backend for the TEST tab. Defaults to E4B-it but can be
# disabled to make this a pure CPU notebook (no GPU needed at all).
ENABLE_GEMMA       = True
GEMMA_MODEL_VARIANT = "e4b-it"
GEMMA_LOAD_IN_4BIT  = True

GEMMA_HF_REPO_VARIANT = (
    GEMMA_MODEL_VARIANT
    .replace("e2b-it", "E2B-it").replace("e4b-it", "E4B-it")
    .replace("26b-a4b-it", "26B-A4B-it").replace("31b-it", "31B-it"))


# ===========================================================================
# PHASE 1 -- minimal install (server deps + duecare wheels)
# ===========================================================================
def install_deps() -> int:
    print("=" * 76)
    print("[phase 1] installing server deps + duecare wheels")
    print("=" * 76)
    cmd = [sys.executable, "-m", "pip", "install", "--quiet",
           "--no-input", "--disable-pip-version-check",
           "fastapi>=0.115", "uvicorn>=0.30", "pydantic>=2.0"]
    subprocess.run(cmd, capture_output=True, text=True)
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
# Load the BUILT-IN knowledge base from the duecare-llm-chat package
# (the user starts with this and edits ON TOP of it)
# ===========================================================================
def load_builtin_knowledge() -> dict:
    print("=" * 76)
    print("[load] reading bundled knowledge base from duecare.chat.harness")
    print("=" * 76)
    try:
        from duecare.chat.harness import (
            GREP_RULES, RAG_CORPUS, CORRIDOR_FEE_CAPS,
            FEE_CAMOUFLAGE_DICT, NGO_INTAKE, ILO_INDICATORS,
        )
    except Exception as e:
        print(f"  duecare.chat.harness import FAILED: {e}")
        return {"grep_rules": [], "rag_corpus": [],
                "corridor_fee_caps": {}, "fee_camouflage": {},
                "ngo_intake": {}, "ilo_indicators": []}
    knowledge = {
        "grep_rules":        [dict(r) for r in GREP_RULES],
        "rag_corpus":        [dict(d) for d in RAG_CORPUS],
        "corridor_fee_caps": dict(CORRIDOR_FEE_CAPS),
        "fee_camouflage":    dict(FEE_CAMOUFLAGE_DICT),
        "ngo_intake":        dict(NGO_INTAKE),
        "ilo_indicators":    [dict(i) if isinstance(i, dict) else {"name": str(i)}
                                for i in ILO_INDICATORS],
    }
    print(f"  GREP rules:        {len(knowledge['grep_rules'])}")
    print(f"  RAG corpus:        {len(knowledge['rag_corpus'])}")
    print(f"  Corridor fee caps: {len(knowledge['corridor_fee_caps'])}")
    print(f"  Fee camouflage:    {len(knowledge['fee_camouflage'])}")
    print(f"  NGO intake:        {len(knowledge['ngo_intake'])}")
    print(f"  ILO indicators:    {len(knowledge['ilo_indicators'])}")
    return knowledge


BUILTIN = load_builtin_knowledge()


# ===========================================================================
# Pure-Python rule firing (no Gemma needed for the builder logic)
# ===========================================================================
def fire_grep_rules(text: str, rules: list) -> list:
    hits = []
    for r in rules:
        patterns = r.get("patterns") or []
        all_required = bool(r.get("all_required", True))
        matches = []
        for p in patterns:
            try:
                m = re.search(p, text, re.IGNORECASE)
            except re.error:
                continue
            if m:
                matches.append({"pattern": p, "match": m.group(0)[:80]})
        fired = (len(matches) == len(patterns) and patterns) if all_required \
                else bool(matches)
        if fired:
            hits.append({
                "rule":      r.get("rule") or r.get("id") or "?",
                "severity":  r.get("severity", "unknown"),
                "citation":  r.get("citation", ""),
                "indicator": r.get("indicator", ""),
                "matches":   matches,
            })
    return hits


def bm25_score(query_tokens: list, doc_tokens: list,
               idf: dict, avg_dl: float, k1: float = 1.5,
               b: float = 0.75) -> float:
    if not doc_tokens:
        return 0.0
    score = 0.0
    tf = Counter(doc_tokens)
    dl = len(doc_tokens)
    for tok in query_tokens:
        if tok not in idf:
            continue
        f = tf.get(tok, 0)
        denom = f + k1 * (1 - b + b * dl / avg_dl) if avg_dl > 0 else f
        if denom > 0:
            score += idf[tok] * (f * (k1 + 1)) / denom
    return score


def _tokenize(text: str) -> list:
    return [t for t in re.findall(r"\w+", text.lower()) if len(t) > 2]


def index_rag(corpus: list) -> dict:
    docs_tokens = []
    df: Counter = Counter()
    for d in corpus:
        text = " ".join(filter(None, [
            d.get("title", ""), d.get("snippet", ""), d.get("body", ""),
            d.get("summary", "")]))
        toks = _tokenize(text)
        docs_tokens.append(toks)
        for t in set(toks):
            df[t] += 1
    n = len(corpus) or 1
    idf = {t: math.log((n - c + 0.5) / (c + 0.5) + 1) for t, c in df.items()}
    avg_dl = (sum(len(t) for t in docs_tokens) / n) if n > 0 else 0
    return {"docs_tokens": docs_tokens, "idf": idf, "avg_dl": avg_dl}


def rag_query(query: str, corpus: list, index: dict, top_k: int = 3) -> list:
    q_toks = _tokenize(query)
    scored = []
    for i, d in enumerate(corpus):
        s = bm25_score(q_toks, index["docs_tokens"][i],
                       index["idf"], index["avg_dl"])
        if s > 0:
            scored.append((s, i, d))
    scored.sort(key=lambda x: -x[0])
    return [{
        "id":      d.get("id") or f"doc_{i}",
        "title":   d.get("title", ""),
        "source":  d.get("source", ""),
        "snippet": (d.get("snippet") or d.get("body") or "")[:240],
        "score":   round(s, 3),
    } for s, i, d in scored[:top_k]]


# ===========================================================================
# Optional Gemma backend (TEST tab "ask Gemma" feature)
# ===========================================================================
GEMMA = {"call": None, "loaded": False}


def maybe_load_gemma() -> None:
    if not ENABLE_GEMMA:
        return
    print("=" * 76)
    print(f"[gemma] attempting load ({GEMMA_MODEL_VARIANT})")
    print("=" * 76)
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5)
        if out.returncode != 0 or not out.stdout.strip():
            print("  no GPU; skipping Gemma load (TEST tab will skip ask-Gemma)")
            return
    except Exception:
        return
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
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch
    except Exception as e:
        print(f"  transformers import FAILED: {e}")
        return
    repo = f"google/gemma-4-{GEMMA_MODEL_VARIANT}"
    print(f"  loading {repo}")
    try:
        tok = AutoTokenizer.from_pretrained(repo)
        model = AutoModelForCausalLM.from_pretrained(
            repo, device_map="auto",
            torch_dtype=torch.bfloat16,
            load_in_4bit=GEMMA_LOAD_IN_4BIT)
    except Exception as e:
        print(f"  load FAILED: {e}")
        return

    def _call(messages: list, max_new_tokens: int = 512) -> str:
        inputs = tok.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True,
            return_dict=True, return_tensors="pt").to("cuda")
        with torch.inference_mode():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens,
                                  use_cache=True, temperature=0.6,
                                  pad_token_id=tok.eos_token_id)
        text = tok.batch_decode(out)[0]
        if "<|turn>model" in text:
            text = text.split("<|turn>model", 1)[1]
        text = text.split("<turn|>", 1)[0]
        return text.replace("<bos>", "").replace("<eos>", "").strip()

    GEMMA["call"] = _call
    GEMMA["loaded"] = True
    print("  Gemma loaded.")


maybe_load_gemma()


# ===========================================================================
# In-memory knowledge state (the working copy the user edits)
# ===========================================================================
STATE = {
    "knowledge": json.loads(json.dumps(BUILTIN)),  # deep copy
    "rag_index": index_rag(BUILTIN["rag_corpus"]),
}


# ===========================================================================
# FastAPI app
# ===========================================================================
def build_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel

    app = FastAPI(title="Duecare Content Knowledge Builder Playground")

    class GrepRule(BaseModel):
        rule: str
        patterns: list[str]
        all_required: bool = True
        severity: str = "medium"
        citation: str = ""
        indicator: str = ""

    class RagDoc(BaseModel):
        id: str
        title: str
        source: str = ""
        snippet: str = ""
        body: str = ""

    class TestRequest(BaseModel):
        text: str
        ask_gemma: bool = False

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _PAGE_HTML

    @app.get("/healthz")
    def healthz() -> dict:
        return {"ok": True, "gemma": GEMMA["loaded"]}

    @app.get("/api/knowledge")
    def get_knowledge() -> dict:
        return {
            "knowledge": STATE["knowledge"],
            "builtin_counts": {
                "grep_rules":        len(BUILTIN["grep_rules"]),
                "rag_corpus":        len(BUILTIN["rag_corpus"]),
                "corridor_fee_caps": len(BUILTIN["corridor_fee_caps"]),
                "fee_camouflage":    len(BUILTIN["fee_camouflage"]),
                "ngo_intake":        len(BUILTIN["ngo_intake"]),
                "ilo_indicators":    len(BUILTIN["ilo_indicators"]),
            },
        }

    @app.post("/api/grep/add")
    def grep_add(rule: GrepRule) -> dict:
        STATE["knowledge"]["grep_rules"].append(rule.model_dump())
        return {"ok": True, "n_rules": len(STATE["knowledge"]["grep_rules"])}

    @app.post("/api/grep/remove/{idx}")
    def grep_remove(idx: int) -> dict:
        rules = STATE["knowledge"]["grep_rules"]
        if 0 <= idx < len(rules):
            rules.pop(idx)
            return {"ok": True, "n_rules": len(rules)}
        raise HTTPException(404, "rule index out of range")

    @app.post("/api/rag/add")
    def rag_add(doc: RagDoc) -> dict:
        STATE["knowledge"]["rag_corpus"].append(doc.model_dump())
        STATE["rag_index"] = index_rag(STATE["knowledge"]["rag_corpus"])
        return {"ok": True, "n_docs": len(STATE["knowledge"]["rag_corpus"])}

    @app.post("/api/rag/remove/{idx}")
    def rag_remove(idx: int) -> dict:
        corpus = STATE["knowledge"]["rag_corpus"]
        if 0 <= idx < len(corpus):
            corpus.pop(idx)
            STATE["rag_index"] = index_rag(corpus)
            return {"ok": True, "n_docs": len(corpus)}
        raise HTTPException(404, "doc index out of range")

    @app.post("/api/test")
    def test(req: TestRequest) -> dict:
        text = req.text
        # GREP firing
        grep_hits = fire_grep_rules(text, STATE["knowledge"]["grep_rules"])
        # RAG retrieval
        rag_hits = rag_query(text, STATE["knowledge"]["rag_corpus"],
                              STATE["rag_index"], top_k=3)
        # Tool lookups (lightweight, just shows what's in the dictionaries)
        tool_results = {
            "corridor_caps": [
                {"corridor": k, "data": v}
                for k, v in STATE["knowledge"]["corridor_fee_caps"].items()
                if any(part in text.lower()
                       for part in (k.split("_") if isinstance(k, str) else []))
            ][:3],
            "fee_camouflage": [
                {"label": k, "data": v}
                for k, v in STATE["knowledge"]["fee_camouflage"].items()
                if k.lower().replace("_", " ") in text.lower()
            ][:5],
            "ngo_intake": list(STATE["knowledge"]["ngo_intake"].items())[:3],
        }
        # Compose the harness pre-context (what would go to Gemma)
        ctx_lines = []
        if grep_hits:
            ctx_lines.append("=== GREP HITS ===")
            for h in grep_hits[:5]:
                ctx_lines.append(
                    f"- [{h['severity'].upper()}] {h['rule']}: "
                    f"{h.get('citation', '')}")
        if rag_hits:
            ctx_lines.append("=== RAG DOCS ===")
            for d in rag_hits:
                ctx_lines.append(
                    f"- [{d['id']}] {d['title']} ({d['source']})")
        pre_context = "\n".join(ctx_lines)

        gemma_response = None
        if req.ask_gemma and GEMMA["loaded"]:
            messages = [
                {"role": "user", "content": [{"type": "text",
                  "text": (f"{pre_context}\n\n=== USER MESSAGE ===\n{text}"
                            if pre_context else text)}]},
            ]
            try:
                gemma_response = GEMMA["call"](messages, max_new_tokens=400)
            except Exception as e:
                gemma_response = f"(gemma call failed: {e})"

        return {
            "grep_hits":      grep_hits,
            "rag_docs":       rag_hits,
            "tools":          tool_results,
            "merged_pre_ctx": pre_context,
            "gemma_response": gemma_response,
            "gemma_loaded":   GEMMA["loaded"],
        }

    @app.get("/api/export")
    def export() -> dict:
        return STATE["knowledge"]

    @app.post("/api/import")
    def import_(payload: dict) -> dict:
        for key in ("grep_rules", "rag_corpus", "corridor_fee_caps",
                    "fee_camouflage", "ngo_intake", "ilo_indicators"):
            if key in payload:
                STATE["knowledge"][key] = payload[key]
        STATE["rag_index"] = index_rag(STATE["knowledge"]["rag_corpus"])
        return {"ok": True, "counts": {
            k: len(v) if hasattr(v, "__len__") else 0
            for k, v in STATE["knowledge"].items()
        }}

    @app.post("/api/reset")
    def reset() -> dict:
        STATE["knowledge"] = json.loads(json.dumps(BUILTIN))
        STATE["rag_index"] = index_rag(STATE["knowledge"]["rag_corpus"])
        return {"ok": True, "reset_to": "builtin"}

    return app


# ===========================================================================
# UI (single HTML page)
# ===========================================================================
_PAGE_HTML = """<!doctype html><html><head>
<meta charset="utf-8">
<title>Duecare Content Knowledge Builder Playground</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif;
         max-width: 1200px; margin: 30px auto; padding: 0 24px;
         color: #1f2937; background: #f8fafc; }
  h1 { color: #1e40af; letter-spacing: -0.02em; margin: 0 0 6px; }
  .sub { color: #6b7280; margin: 0 0 20px; line-height: 1.5; }
  .pill { display: inline-block; background: #ddd6fe; color: #5b21b6;
          padding: 2px 9px; border-radius: 999px; font-size: 11px;
          font-weight: 600; margin-left: 6px; }
  .tabs { display: flex; gap: 4px; margin-bottom: 0; border-bottom: 2px solid #e5e7eb; }
  .tab { padding: 10px 18px; background: #f1f5f9; border: 1px solid #e5e7eb;
         border-bottom: none; border-radius: 8px 8px 0 0; cursor: pointer;
         font-weight: 600; font-size: 13px; color: #6b7280; }
  .tab.active { background: white; color: #1e40af; border-color: #e5e7eb; }
  .panel { background: white; border: 1px solid #e5e7eb;
           border-top: none; border-radius: 0 0 12px 12px; padding: 20px;
           margin-bottom: 20px; }
  label { display: block; font-weight: 600; font-size: 13px;
          color: #1f2937; margin-bottom: 4px; margin-top: 8px; }
  input[type=text], textarea, select {
    width: 100%; padding: 8px 10px; border: 1px solid #d1d5db;
    border-radius: 8px; font-size: 13px; box-sizing: border-box;
    font-family: ui-monospace, Menlo, Consolas, monospace;
  }
  textarea { min-height: 80px; resize: vertical; }
  button { background: #1e40af; color: white; padding: 8px 14px;
           border: none; border-radius: 8px; font-weight: 600;
           font-size: 13px; cursor: pointer; }
  button.secondary { background: #6b7280; }
  button.danger { background: #dc2626; }
  button:hover { opacity: 0.9; }
  .row { display: flex; gap: 8px; align-items: center; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th, td { padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: left;
           vertical-align: top; }
  th { color: #6b7280; font-weight: 700; text-transform: uppercase;
       letter-spacing: 0.05em; font-size: 11px; }
  pre { background: #1f2937; color: #f9fafb; padding: 12px;
        border-radius: 8px; overflow-x: auto; font-size: 12px;
        line-height: 1.5; max-height: 300px; overflow-y: auto; }
  .badge { display: inline-block; padding: 1px 8px; border-radius: 999px;
           font-size: 10px; font-weight: 700; text-transform: uppercase; }
  .badge.high { background: #fee2e2; color: #991b1b; }
  .badge.medium { background: #fef3c7; color: #92400e; }
  .badge.low { background: #dbeafe; color: #1e40af; }
  .badge.critical { background: #1f2937; color: #fff; }
  .meta { color: #6b7280; font-size: 12px; }
  .stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px;
           margin-bottom: 14px; }
  .stat { background: #f1f5f9; padding: 10px 12px; border-radius: 8px;
          text-align: center; }
  .stat-num { font-size: 22px; font-weight: 700; color: #1e40af; }
  .stat-label { font-size: 11px; color: #6b7280; text-transform: uppercase;
                font-weight: 600; }
</style></head><body>

<h1>Duecare Content Knowledge Builder Playground <span class="pill">CORE · Hands-on</span></h1>
<p class="sub">
  The HANDS-ON sandbox for building Duecare's knowledge base. Add or remove
  GREP regex rules, RAG documents, and lookup-table entries inline; test
  what fires on a sample text; export/import the full knowledge JSON.
  This is what you'd extend before deploying Duecare to a new domain.
</p>

<div class="stats" id="stats"></div>

<div class="tabs">
  <div class="tab active" onclick="showTab('grep')">GREP rules</div>
  <div class="tab" onclick="showTab('rag')">RAG corpus</div>
  <div class="tab" onclick="showTab('tools')">Tools (lookups)</div>
  <div class="tab" onclick="showTab('test')">Test</div>
  <div class="tab" onclick="showTab('export')">Export / Import</div>
</div>

<div class="panel" id="tab-grep">
  <h3 style="margin-top:0">Add a GREP rule</h3>
  <label>Rule name (id)</label>
  <input type="text" id="g-rule" placeholder="e.g. usury_high_apr_local">
  <label>Patterns (one regex per line)</label>
  <textarea id="g-patterns" placeholder="\\b6[5-9]%\\s*APR\\b
\\b7[0-9]%\\s*APR\\b"></textarea>
  <div class="row">
    <div style="flex:1">
      <label>Severity</label>
      <select id="g-severity">
        <option>critical</option><option>high</option>
        <option selected>medium</option><option>low</option>
      </select>
    </div>
    <div style="flex:1">
      <label>All patterns required?</label>
      <select id="g-allreq"><option value="true">Yes</option><option value="false">No (any one)</option></select>
    </div>
  </div>
  <label>Citation</label>
  <input type="text" id="g-cite" placeholder="HK Money Lenders Ord. Cap. 163 §24">
  <label>Indicator (what this means)</label>
  <input type="text" id="g-indicator" placeholder="Usurious lending rate exceeds statutory cap">
  <div style="margin-top:12px">
    <button onclick="addGrep()">Add rule</button>
  </div>
  <h3 style="margin-top:24px">Current GREP rules</h3>
  <table id="g-table"></table>
</div>

<div class="panel" id="tab-rag" style="display:none">
  <h3 style="margin-top:0">Add a RAG document</h3>
  <div class="row">
    <div style="flex:1">
      <label>ID</label>
      <input type="text" id="r-id" placeholder="ILO_C029_Art_1">
    </div>
    <div style="flex:2">
      <label>Title</label>
      <input type="text" id="r-title" placeholder="ILO C029 Article 1: prohibition of forced labour">
    </div>
  </div>
  <label>Source</label>
  <input type="text" id="r-source" placeholder="ILO Convention No. 29 (1930)">
  <label>Snippet (the chunk BM25 indexes)</label>
  <textarea id="r-snippet" placeholder="Each Member of the International Labour Organisation undertakes to suppress the use of forced or compulsory labour in all its forms within the shortest possible period..."></textarea>
  <div style="margin-top:12px">
    <button onclick="addRag()">Add doc</button>
    <span class="meta">BM25 index rebuilds automatically.</span>
  </div>
  <h3 style="margin-top:24px">Current RAG corpus</h3>
  <table id="r-table"></table>
</div>

<div class="panel" id="tab-tools" style="display:none">
  <p class="meta">Lookup tables that back the function-calling layer. Editable in the JSON exporter — UI editing for these is a placeholder; use Export → edit JSON → Import for now.</p>
  <h3>Corridor fee caps</h3>
  <pre id="t-corridor"></pre>
  <h3>Fee camouflage labels</h3>
  <pre id="t-feecam"></pre>
  <h3>NGO intake hotlines</h3>
  <pre id="t-ngo"></pre>
</div>

<div class="panel" id="tab-test" style="display:none">
  <label>Sample text to fire your knowledge base against</label>
  <textarea id="test-text" style="min-height:120px"
            placeholder="I run an employment agency in Hong Kong charging 68% APR for placement loans. We hold worker passports for safekeeping. Salary: HKD 4630/month, 48 hours/week, 18-month contracts."></textarea>
  <div style="margin-top:10px">
    <button onclick="runTest(false)">Fire rules + retrieve</button>
    <button onclick="runTest(true)" class="secondary">+ ask Gemma</button>
    <span class="meta" id="test-meta"></span>
  </div>
  <div id="test-result" style="margin-top:18px; display:none">
    <h3 style="margin-top:0">GREP hits</h3>
    <pre id="test-grep"></pre>
    <h3>RAG retrieval</h3>
    <pre id="test-rag"></pre>
    <h3>Merged pre-context (what Gemma would see)</h3>
    <pre id="test-merged"></pre>
    <div id="test-gemma-wrap" style="display:none">
      <h3>Gemma response</h3>
      <pre id="test-gemma"></pre>
    </div>
  </div>
</div>

<div class="panel" id="tab-export" style="display:none">
  <button onclick="doExport()">Download knowledge JSON</button>
  <button onclick="doImport()" class="secondary">Upload + import JSON</button>
  <button onclick="doReset()" class="danger">Reset to bundled built-ins</button>
  <input type="file" id="import-file" accept="application/json" style="display:none" onchange="handleImportFile(event)">
  <h3 style="margin-top:18px">Live preview</h3>
  <pre id="export-preview"></pre>
</div>

<script>
let knowledge = {};

async function loadKnowledge() {
  const r = await fetch('/api/knowledge');
  const data = await r.json();
  knowledge = data.knowledge;
  renderStats(data.builtin_counts);
  renderGrep();
  renderRag();
  renderTools();
  renderExport();
}

function renderStats(builtin) {
  const k = knowledge;
  const html = [
    ['GREP', k.grep_rules.length, builtin.grep_rules],
    ['RAG', k.rag_corpus.length, builtin.rag_corpus],
    ['Corridors', Object.keys(k.corridor_fee_caps).length, builtin.corridor_fee_caps],
    ['Fee labels', Object.keys(k.fee_camouflage).length, builtin.fee_camouflage],
    ['NGO', Object.keys(k.ngo_intake).length, builtin.ngo_intake],
    ['ILO ind.', k.ilo_indicators.length, builtin.ilo_indicators],
  ].map(([label, cur, base]) => {
    const delta = cur - base;
    const deltaTxt = delta === 0 ? '' :
      ('<span style="color:' + (delta > 0 ? '#047857' : '#b91c1c') +
        ';font-size:10px;font-weight:600">' +
        (delta > 0 ? '+' : '') + delta + ' from base</span>');
    return '<div class="stat"><div class="stat-num">' + cur + '</div>' +
            '<div class="stat-label">' + label + '</div>' + deltaTxt + '</div>';
  }).join('');
  document.getElementById('stats').innerHTML = html;
}

function renderGrep() {
  const rows = knowledge.grep_rules.map((r, i) =>
    '<tr><td><b>' + escapeHtml(r.rule || '?') + '</b></td>' +
    '<td><span class="badge ' + (r.severity || 'medium') + '">' +
       (r.severity || 'medium') + '</span></td>' +
    '<td><code>' + (r.patterns || []).map(escapeHtml).join('<br>') + '</code></td>' +
    '<td>' + escapeHtml(r.citation || '') + '<br><span class="meta">' +
       escapeHtml(r.indicator || '') + '</span></td>' +
    '<td><button class="danger" onclick="removeGrep(' + i + ')">×</button></td></tr>'
  ).join('');
  document.getElementById('g-table').innerHTML =
    '<thead><tr><th>Rule</th><th>Sev</th><th>Patterns</th><th>Citation / indicator</th><th></th></tr></thead><tbody>' +
    rows + '</tbody>';
}

function renderRag() {
  const rows = knowledge.rag_corpus.map((d, i) =>
    '<tr><td><b>' + escapeHtml(d.id || '?') + '</b><br><span class="meta">' +
       escapeHtml(d.source || '') + '</span></td>' +
    '<td>' + escapeHtml(d.title || '') + '<br><span class="meta">' +
       escapeHtml((d.snippet || d.body || '').slice(0, 220)) + '</span></td>' +
    '<td><button class="danger" onclick="removeRag(' + i + ')">×</button></td></tr>'
  ).join('');
  document.getElementById('r-table').innerHTML =
    '<thead><tr><th>ID / source</th><th>Title / snippet</th><th></th></tr></thead><tbody>' +
    rows + '</tbody>';
}

function renderTools() {
  document.getElementById('t-corridor').textContent =
    JSON.stringify(knowledge.corridor_fee_caps, null, 2);
  document.getElementById('t-feecam').textContent =
    JSON.stringify(knowledge.fee_camouflage, null, 2);
  document.getElementById('t-ngo').textContent =
    JSON.stringify(knowledge.ngo_intake, null, 2);
}

function renderExport() {
  document.getElementById('export-preview').textContent =
    JSON.stringify(knowledge, null, 2);
}

async function addGrep() {
  const rule = {
    rule: document.getElementById('g-rule').value.trim(),
    patterns: document.getElementById('g-patterns').value.trim().split('\\n')
              .filter(p => p.trim()),
    all_required: document.getElementById('g-allreq').value === 'true',
    severity: document.getElementById('g-severity').value,
    citation: document.getElementById('g-cite').value.trim(),
    indicator: document.getElementById('g-indicator').value.trim(),
  };
  if (!rule.rule || !rule.patterns.length) {
    alert('rule name + at least one pattern required'); return;
  }
  await fetch('/api/grep/add', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(rule)});
  ['g-rule','g-patterns','g-cite','g-indicator'].forEach(id =>
    document.getElementById(id).value = '');
  await loadKnowledge();
}

async function removeGrep(i) {
  await fetch('/api/grep/remove/' + i, {method: 'POST'});
  await loadKnowledge();
}

async function addRag() {
  const doc = {
    id: document.getElementById('r-id').value.trim(),
    title: document.getElementById('r-title').value.trim(),
    source: document.getElementById('r-source').value.trim(),
    snippet: document.getElementById('r-snippet').value.trim(),
    body: '',
  };
  if (!doc.id || !doc.title) {
    alert('id and title required'); return;
  }
  await fetch('/api/rag/add', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(doc)});
  ['r-id','r-title','r-source','r-snippet'].forEach(id =>
    document.getElementById(id).value = '');
  await loadKnowledge();
}

async function removeRag(i) {
  await fetch('/api/rag/remove/' + i, {method: 'POST'});
  await loadKnowledge();
}

async function runTest(askGemma) {
  const text = document.getElementById('test-text').value.trim();
  if (!text) { alert('paste sample text'); return; }
  const meta = document.getElementById('test-meta');
  meta.textContent = ' running...';
  const r = await fetch('/api/test', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text, ask_gemma: askGemma})});
  const data = await r.json();
  document.getElementById('test-grep').textContent =
    JSON.stringify(data.grep_hits, null, 2);
  document.getElementById('test-rag').textContent =
    JSON.stringify(data.rag_docs, null, 2);
  document.getElementById('test-merged').textContent =
    data.merged_pre_ctx || '(no rules fired and no docs retrieved)';
  if (data.gemma_response !== null) {
    document.getElementById('test-gemma').textContent = data.gemma_response;
    document.getElementById('test-gemma-wrap').style.display = 'block';
  } else if (askGemma && !data.gemma_loaded) {
    document.getElementById('test-gemma').textContent =
      '(Gemma not loaded; rebuild with ENABLE_GEMMA=True and a GPU)';
    document.getElementById('test-gemma-wrap').style.display = 'block';
  } else {
    document.getElementById('test-gemma-wrap').style.display = 'none';
  }
  document.getElementById('test-result').style.display = 'block';
  meta.textContent = ' done.';
}

async function doExport() {
  const r = await fetch('/api/export');
  const data = await r.json();
  const blob = new Blob([JSON.stringify(data, null, 2)],
                        {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'duecare_knowledge.json';
  a.click();
}

function doImport() { document.getElementById('import-file').click(); }

async function handleImportFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  const text = await file.text();
  try {
    const obj = JSON.parse(text);
    await fetch('/api/import', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: text});
    await loadKnowledge();
    alert('imported.');
  } catch (err) { alert('import failed: ' + err.message); }
}

async function doReset() {
  if (!confirm('reset to bundled built-ins?')) return;
  await fetch('/api/reset', {method: 'POST'});
  await loadKnowledge();
}

function showTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.style.display = 'none');
  event.currentTarget.classList.add('active');
  document.getElementById('tab-' + name).style.display = 'block';
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, m => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

loadKnowledge();
</script>
</body></html>"""


# ===========================================================================
# Server launch (FastAPI + cloudflared) -- mirrors the classification
# playground; no GPU required for the builder UI itself.
# ===========================================================================
def launch_server() -> Optional[str]:
    print("=" * 76)
    print(f"[serve] starting FastAPI on 0.0.0.0:{PORT}")
    print("=" * 76)
    import uvicorn
    app = build_app()
    _attach_shutdown(app)
    threading.Thread(target=lambda: uvicorn.run(
        app, host="0.0.0.0", port=PORT, log_level="warning"),
        daemon=True, name="duecare-kb-builder").start()
    time.sleep(2.0)

    if TUNNEL != "cloudflared":
        return f"http://localhost:{PORT}"

    cf = "/usr/local/bin/cloudflared" if Path("/usr/local/bin/cloudflared").exists() else "cloudflared"
    try:
        subprocess.run([cf, "--version"], capture_output=True, check=True)
    except Exception:
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
    # R2 fix: register the proc so shutdown can terminate the tunnel.
    _CLOUDFLARED_PROC["p"] = proc
    public_url = {"u": None}
    def _drain():
        for line in proc.stdout:
            if "trycloudflare.com" in line and "https://" in line:
                m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                if m:
                    public_url["u"] = m.group(0)
    threading.Thread(target=_drain, daemon=True).start()
    for _ in range(60):
        if public_url["u"]:
            break
        time.sleep(0.5)
    return public_url["u"] or f"http://localhost:{PORT}"


# ===========================================================================
# Main
# ===========================================================================
url = launch_server()
print("\n" + "=" * 76)
print("DUECARE CONTENT KNOWLEDGE BUILDER PLAYGROUND IS LIVE")
print("=" * 76)
print(f"\n  open this URL on your laptop:")
print(f"\n      {url}\n")
print(f"  tabs:    GREP rules / RAG corpus / Tools / Test / Export-Import")
print(f"  Gemma:   {'loaded (TEST tab can ask Gemma)' if GEMMA['loaded'] else 'not loaded (TEST tab still works for rule firing + RAG retrieval)'}")
print(f"\n  stop the demo by interrupting this cell.\n")
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
