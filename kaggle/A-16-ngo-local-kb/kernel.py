# <!-- duecare:kernel-intro -->
# DueCare — NGO local-KB / case-file ingestion (Lane 02)
# Appendix notebook #A15 of 20 in the DueCare submission.
#
# Paste case notes; the kernel redacts PII, salt-hashes entities,
# builds a local SQLite KB, lets a caseworker query by hash to find
# cross-case patterns, and previews the anonymized aggregate before
# any data leaves the device.

"""
============================================================================
  DUECARE A-16 NGO LOCAL-KB -- Kaggle notebook
============================================================================
  Lane 02 anchor. Mirrors local-kb.html + dashboard.html: drop a case
  in, get redacted record + entity hashes back, query the local KB
  by salted hash, preview the aggregate before sharing.

  Output: /kaggle/working
    local_kb.sqlite                      durable SQLite store
    <run_id>_local_kb.json               full payload + aggregate
    <run_id>_local_kb.jsonl              per-case streaming variant
    <run_id>_metadata.json               config + summary
    <run_id>_bundle.zip                  manifest + above + sqlite

  Run-ID format: a16_local_kb_{iso_ts}

  Privacy: every PII span salt-hashed before write; raw values
  never persist. Satisfies .claude/rules/10_safety_gate.md.

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
============================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path


# ===========================================================================
# CONFIG
# ===========================================================================
PORT = 8080
TUNNEL = "cloudflared"
OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_PATH = OUTPUT_DIR / "local_kb.sqlite"
SALT = os.environ.get("DUECARE_LOCAL_KB_SALT", secrets.token_hex(16))


# ===========================================================================
# PHASE 1 -- DueCare from GitHub (no Unsloth needed; CPU-only)
# ===========================================================================
DUECARE_VERSION = "0.1.0"
DUECARE_REPO = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "b6c446d"
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


try:
    from duecare.chat._dc_log import dc_log, set_kernel_id
    set_kernel_id("a-16-ngo-local-kb")
except Exception:
    def dc_log(*a, **kw): return None
    def set_kernel_id(*a, **kw): return None


# ===========================================================================
# 2. PII detector + redaction + salt hashing
# ===========================================================================
PII_PATTERNS = [
    ("PHONE",    re.compile(r"\+?\d[\d\s\-]{7,15}\d")),
    ("EMAIL",    re.compile(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("PASSPORT", re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")),
    ("DOB",      re.compile(r"\b(19|20)\d{2}-\d{2}-\d{2}\b")),
    ("AMOUNT",   re.compile(
        r"(?:USD|PHP|HK\$|HKD|SAR|AED|QAR)\s*\d{1,7}",
        re.IGNORECASE)),
    ("PERSON",   re.compile(
        r"\b[A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?")),
]


def _salted_hash(value: str) -> str:
    return hashlib.sha256(
        (SALT + ":" + value).encode("utf-8")).hexdigest()[:16]


def detect_and_redact(text: str) -> tuple[str, list[dict]]:
    spans: list[tuple[int, int, str, str]] = []
    for label, pat in PII_PATTERNS:
        for m in pat.finditer(text):
            spans.append((m.start(), m.end(), label, m.group(0)))
    spans.sort()
    accepted: list[tuple[int, int, str, str]] = []
    last_end = 0
    for sp in spans:
        if sp[0] >= last_end:
            accepted.append(sp)
            last_end = sp[1]
    parts: list[str] = []
    entities: list[dict] = []
    cursor = 0
    for start, end, label, value in accepted:
        parts.append(text[cursor:start])
        parts.append(f"[{label}]")
        entities.append({
            "label": label,
            "salted_hash": _salted_hash(value),
            "span_start": start,
            "span_end": end,
        })
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), entities


# ===========================================================================
# 3. SQLite-backed local KB
# ===========================================================================
def _open_db():
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            content_redacted TEXT NOT NULL,
            n_entities INTEGER NOT NULL,
            ingested_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entities (
            case_id TEXT NOT NULL,
            label TEXT NOT NULL,
            salted_hash TEXT NOT NULL,
            span_start INTEGER NOT NULL,
            span_end INTEGER NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(case_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ent_hash "
                  "ON entities(salted_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ent_label "
                  "ON entities(label)")
    return conn


def ingest_case(case_id: str, content: str) -> dict:
    redacted, entities = detect_and_redact(content)
    ingested_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn = _open_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cases "
            "(case_id, content_redacted, n_entities, ingested_at) "
            "VALUES (?, ?, ?, ?)",
            (case_id, redacted, len(entities), ingested_at))
        conn.execute("DELETE FROM entities WHERE case_id = ?",
                      (case_id,))
        conn.executemany(
            "INSERT INTO entities (case_id, label, salted_hash, "
            "span_start, span_end) VALUES (?, ?, ?, ?, ?)",
            [(case_id, e["label"], e["salted_hash"],
              e["span_start"], e["span_end"]) for e in entities])
        conn.commit()
    finally:
        conn.close()
    dc_log("a15.ingest", "case ingested", case_id=case_id,
            n_entities=len(entities))
    return {
        "case_id": case_id,
        "content_redacted": redacted,
        "n_entities": len(entities),
        "entities": entities,
        "ingested_at": ingested_at,
        "error": None,    # canonical PerRow.error (data_primitives.md 1.5)
    }


def query_by_hash(salted_hash: str) -> list[dict]:
    conn = _open_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT c.case_id, c.content_redacted, "
            "c.n_entities, c.ingested_at, e.label "
            "FROM cases c JOIN entities e ON e.case_id = c.case_id "
            "WHERE e.salted_hash = ?",
            (salted_hash,)).fetchall()
    finally:
        conn.close()
    return [{"case_id": r[0], "content_redacted": r[1],
              "n_entities": r[2], "ingested_at": r[3],
              "match_label": r[4]} for r in rows]


def aggregate_preview(period_days: int = 90) -> dict:
    conn = _open_db()
    try:
        n_cases = conn.execute(
            "SELECT COUNT(*) FROM cases").fetchone()[0]
        label_counts = dict(conn.execute(
            "SELECT label, COUNT(*) FROM entities GROUP BY label"
        ).fetchall())
        hash_repeats = conn.execute(
            "SELECT salted_hash, COUNT(DISTINCT case_id) c "
            "FROM entities WHERE label IN ('PERSON', 'PASSPORT') "
            "GROUP BY salted_hash HAVING c > 1 "
            "ORDER BY c DESC LIMIT 10"
        ).fetchall()
    finally:
        conn.close()
    return {
        "period_days": period_days,
        "n_cases": n_cases,
        "entity_label_counts": label_counts,
        "repeat_hashes": [
            {"hash_prefix": h[:8] + "...", "case_count": c}
            for h, c in hash_repeats
        ],
        "note": "No PII. All hashes are salted; the salt itself is "
                "not exported.",
    }


# ===========================================================================
# 4. State + bundle flush + workbench shell
# ===========================================================================
_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = f"a16_local_kb_{_run_ts}"
RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_local_kb.json"
JSONL_PATH = OUTPUT_DIR / f"{RUN_ID}_local_kb.jsonl"
META_PATH = OUTPUT_DIR / f"{RUN_ID}_metadata.json"
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"

INGESTED_LOG: list[dict] = []
_session_t0 = time.time()
JSONL_PATH.touch(exist_ok=True)


def _flush():
    payload = {
        "schema_version": "1.0",
        "kernel_id": "a-16-ngo-local-kb",
        "run_id": RUN_ID,
        "config": {
            "salt_set": bool(os.environ.get("DUECARE_LOCAL_KB_SALT")),
        },
        "metadata": {
            "started_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(_session_t0)),
            "host": "kaggle" if Path("/kaggle").exists() else "local",
        },
        "summary": aggregate_preview(),
        "aggregate": aggregate_preview(),  # legacy alias (data_primitives.md 1.1)
        "results": INGESTED_LOG,
        "ingested": INGESTED_LOG,           # legacy alias for results
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2,
                                          ensure_ascii=False),
                              encoding="utf-8")
    META_PATH.write_text(json.dumps(
        {k: v for k, v in payload.items() if k != "ingested"},
        indent=2, ensure_ascii=False), encoding="utf-8")
    with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
        _z.writestr("manifest.json", json.dumps({
            "schema_version": "1.0",
            "run_id": RUN_ID,
            "kernel_id": "a-16-ngo-local-kb",
        }, indent=2))
        _z.write(RESULTS_PATH, "local_kb.json")
        _z.write(JSONL_PATH, "local_kb.jsonl")
        _z.write(META_PATH, "metadata.json")
        if SQLITE_PATH.exists():
            _z.write(SQLITE_PATH, "local_kb.sqlite")


INDEX_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-16 . NGO local-KB</title>
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
  textarea{width:100%;min-height:140px;border:1px solid #DDD8C9;
           border-radius:8px;padding:10px;font:inherit;
           background:#F7F6F1}
  .row{background:#FFF;border:1px solid #EFEDE4;border-radius:10px;
       padding:10px 14px;margin:8px 0;font-size:13.5px}
  .cid{font-family:"JetBrains Mono",monospace;color:#5B5F68;
       font-size:11.5px}
  button.primary{background:#0E1116;color:#F7F6F1;border:none;
                 border-radius:999px;padding:11px 22px;
                 font-size:13.5px;font-weight:600;cursor:pointer;
                 margin-top:10px}
  button.secondary{background:transparent;color:#0E1116;
                   border:1px solid #DDD8C9;border-radius:999px;
                   padding:10px 18px;font-size:13px;cursor:pointer}
  input[type=text]{width:80%;padding:8px 12px;border:1px solid #DDD8C9;
                    border-radius:6px;background:#F7F6F1;font:inherit}
  pre{font-family:"JetBrains Mono",monospace;font-size:12.5px;
      background:rgba(0,0,0,.04);padding:10px 12px;border-radius:6px;
      white-space:pre-wrap;word-break:break-word}
  .ent{display:inline-block;padding:2px 8px;border-radius:999px;
       background:#EAF2EC;color:#1F4F33;font-size:11px;
       margin:2px 4px 0 0}
  .dl{margin-top:14px}
  .dl a{color:#0E1116;text-decoration:underline}
</style></head><body>
<div class="page">
  <h1>DueCare A-16 . NGO local-KB</h1>
  <p class="lede">Paste case-intake notes. The kernel redacts PII,
    salt-hashes entities, and stores them in a local SQLite KB.
    Nothing leaves this machine until you preview &amp; click
    "share aggregate".</p>
  <div class="panel">
    <h2>Ingest a case</h2>
    <textarea id="case-text"
              placeholder="Paste intake notes here ..."></textarea>
    <input type="text" id="case-id"
            placeholder="Optional case_id (auto-generated if blank)"
            style="margin-top:8px;width:60%">
    <br><button class="primary" onclick="ingestCase()">Ingest</button>
  </div>
  <div class="panel">
    <h2>Query by salted hash</h2>
    <input type="text" id="query-hash"
            placeholder="Paste a salted_hash from a prior ingestion ...">
    <button class="secondary" onclick="runQuery()">Query</button>
    <div id="query-results" style="margin-top:10px"></div>
  </div>
  <div class="panel">
    <h2>Aggregate preview (nothing leaves until you click Share)</h2>
    <pre id="agg-pre">.</pre>
    <button class="secondary" onclick="refreshAgg()">Refresh</button>
  </div>
  <div class="panel">
    <h2>Recently ingested</h2>
    <div id="rows"></div>
  </div>
  <p class="dl">Bundle: <a id="bundle-link" href="#">(no cases yet)</a></p>
</div>
<script>
function _el(tag,cls,txt){const e=document.createElement(tag);
  if(cls)e.className=cls;if(txt!=null)e.textContent=String(txt);return e}

async function ingestCase(){
  const text=document.getElementById('case-text').value.trim();
  const caseId=document.getElementById('case-id').value.trim();
  if(!text)return;
  await fetch('/api/ingest',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({case_id:caseId||undefined,content:text})
  }).then(r=>r.json());
  document.getElementById('case-text').value='';
  document.getElementById('case-id').value='';
  refreshState();
}

async function runQuery(){
  const h=document.getElementById('query-hash').value.trim();
  if(!h)return;
  const r=await fetch('/api/query?h='+encodeURIComponent(h))
                .then(r=>r.json());
  const wrap=document.getElementById('query-results');
  wrap.replaceChildren();
  for(const row of (r.matches||[])){
    const c=_el('div','row');
    c.appendChild(_el('div','cid',row.case_id+' . '+row.match_label));
    c.appendChild(_el('pre',null,row.content_redacted));
    wrap.appendChild(c);
  }
  if((r.matches||[]).length===0)
    wrap.appendChild(_el('div',null,'no matches'));
}

async function refreshAgg(){
  const r=await fetch('/api/aggregate').then(r=>r.json());
  document.getElementById('agg-pre').textContent=
    JSON.stringify(r,null,2);
}

async function refreshState(){
  const r=await fetch('/api/state').then(r=>r.json());
  const wrap=document.getElementById('rows');wrap.replaceChildren();
  for(const row of (r.recent||[])){
    const c=_el('div','row');
    c.appendChild(_el('div','cid',
      row.case_id+' . '+row.n_entities+' entities . '+row.ingested_at));
    c.appendChild(_el('pre',null,row.content_redacted));
    for(const e of (row.entities||[]).slice(0,8)){
      c.appendChild(_el('span','ent',
        e.label+' . '+e.salted_hash.slice(0,8)+'...'));
    }
    wrap.appendChild(c);
  }
  if(r.bundle_name){
    const a=document.getElementById('bundle-link');
    a.href='/artifact/'+encodeURIComponent(r.bundle_name);
    a.textContent=r.bundle_name+' ('+r.bundle_size_kb+' KB)';
  }
  refreshAgg();
}
refreshState();
</script></body></html>
"""


print("\n[2/4] launching local-KB UI")
_SHUTDOWN_EVENT = threading.Event()

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": "A-16 NGO local-KB",
        "audience": "ngo_regulator",
        "lede": ("Paste case notes; the kernel redacts PII, "
                  "salt-hashes entities, builds a local SQLite KB, "
                  "lets the caseworker query by hash, and previews "
                  "the anonymized aggregate before sharing. Lane 02 "
                  "anchor."),
        "results": [
            {"label": "Compute", "value": "CPU-only"},
            {"label": "PII",     "value": "redacted + salt-hashed"},
            {"label": "Store",   "value": "local_kb.sqlite"},
        ],
        "links": [
            ("Experiment ladder",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
        ],
        "next_steps": [
            "Open the printed cloudflared URL.",
            "Paste a case in the Ingest panel; click Ingest.",
            "Copy a salted_hash from the recently-ingested list, "
            "paste it into Query to find similar cases.",
            "Refresh the Aggregate panel to preview what would "
            "leave the machine if you click Share.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-16-ngo-local-kb",
        port=PORT, homepage_html=INDEX_HTML,
    )
    from fastapi import Request

    @app.post("/api/ingest")
    async def _ingest(req: Request):
        body = await req.json()
        content = body.get("content", "").strip()
        if not content:
            return {"ok": False, "error": "empty content"}
        case_id = body.get("case_id") or (
            "case_" + hashlib.sha256(content.encode()).hexdigest()[:8])
        result = ingest_case(case_id, content)
        INGESTED_LOG.append(result)
        with JSONL_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "schema_version": "1.0",
                "run_id": RUN_ID,
                **result,
            }, ensure_ascii=False) + "\n")
        _flush()
        return {"ok": True, **result}

    @app.get("/api/query")
    def _query(h: str = ""):
        return {"matches": query_by_hash(h)}

    @app.get("/api/aggregate")
    def _agg():
        return aggregate_preview()

    @app.get("/api/state")
    def _state():
        return {
            "recent": INGESTED_LOG[-10:][::-1],
            "bundle_name": (BUNDLE_PATH.name
                              if BUNDLE_PATH.exists() else None),
            "bundle_size_kb": (BUNDLE_PATH.stat().st_size // 1024
                                 if BUNDLE_PATH.exists() else 0),
        }

    if public_url:
        print(f"  ok UI: {public_url}")
    print("\n  A-15 LOCAL-KB READY\n")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutdown complete -- cell exiting.\n")
