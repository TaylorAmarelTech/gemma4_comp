# <!-- duecare:kernel-intro -->
# DueCare — Knowledge-pack builder + verifier (Lane 04/05)
# Appendix notebook #A17 of 24 in the DueCare submission.
#
# Build a versioned, signed corridor knowledge pack from public
# sources. Researchers can later pull and verify the hash for a
# deterministic answer. Closes knowledge-packs.html mechanics.

"""
============================================================================
  DUECARE A-17 KNOWLEDGE-PACK BUILDER -- Kaggle notebook
============================================================================
  Pipeline:
    1. Install DueCare from GitHub (no Unsloth; CPU-only)
    2. UI: paste pack spec (slug, version, curator, document list)
    3. Fetch each doc (or accept inline text); per-doc sha256
    4. Stable-order manifest; sha256 over canonical JSON = sig
    5. Pack into <slug>-v<version>.tar.gz
    6. Verify: round-trip the tarball back through the manifest hash

  Output: /kaggle/working
    packs/<slug>/v<version>/             pack working dir
    <slug>-v<version>.tar.gz             distributable signed pack
    <slug>-v<version>-manifest.json      sidecar manifest
    <run_id>_bundle.zip                  session manifest + sidecars

  Run-ID format: a17_pack_session_{iso_ts}

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
============================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path


# ===========================================================================
# CONFIG
# ===========================================================================
PORT = 8080
TUNNEL = "cloudflared"
OUTPUT_DIR = Path("/kaggle/working")
PACKS_DIR = OUTPUT_DIR / "packs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PACKS_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# PHASE 1 -- DueCare from GitHub
# ===========================================================================
DUECARE_VERSION = "0.1.0"
DUECARE_REPO = "TaylorAmarelTech/gemma4_comp"
DUECARE_COMMIT_SHA = "main"
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
    set_kernel_id("a-17-knowledge-pack-builder")
except Exception:
    def dc_log(*a, **kw): return None
    def set_kernel_id(*a, **kw): return None


# ===========================================================================
# 2. Pack build / sign / verify
# ===========================================================================
def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fetch_doc(spec: dict) -> tuple[str, bytes]:
    doc_id = spec.get("doc_id") or f"doc_{len(spec)}"
    if "inline_text" in spec:
        return doc_id, spec["inline_text"].encode("utf-8")
    url = spec.get("source_url", "")
    if not url:
        raise ValueError(
            f"doc {doc_id} has neither inline_text nor source_url")
    req = urllib.request.Request(url, headers={
        "User-Agent": "DueCare-Pack-Builder/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read()
    return doc_id, content


def build_pack(slug: str, version: str, curator: str,
                documents: list[dict],
                description: str = "") -> dict:
    pack_dir = PACKS_DIR / slug / f"v{version}"
    pack_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = pack_dir / "docs"
    docs_dir.mkdir(exist_ok=True)
    fetched_docs: list[dict] = []
    for spec in documents:
        try:
            doc_id, content = _fetch_doc(spec)
            doc_path = docs_dir / f"{doc_id}.txt"
            doc_path.write_bytes(content)
            fetched_docs.append({
                "doc_id": doc_id,
                "source_url": spec.get("source_url", ""),
                "sha256": _sha256_bytes(content),
                "size_bytes": len(content),
                "stored_at": str(doc_path.relative_to(pack_dir)),
            })
        except Exception as e:
            fetched_docs.append({
                "doc_id": spec.get("doc_id", "unknown"),
                "source_url": spec.get("source_url", ""),
                "error": f"{type(e).__name__}: {str(e)[:200]}",
            })
    fetched_docs.sort(key=lambda d: d.get("doc_id", ""))
    manifest_base = {
        "schema_version": "1.0",
        "slug": slug,
        "version": version,
        "released": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "curator": curator,
        "description": description,
        "documents": fetched_docs,
    }
    canonical = json.dumps(manifest_base, sort_keys=True,
                              ensure_ascii=False, indent=2)
    manifest_hash = _sha256_bytes(canonical.encode("utf-8"))
    manifest = {**manifest_base,
                "manifest_hash": f"sha256:{manifest_hash}"}
    manifest_path = pack_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2,
                                          ensure_ascii=False),
                                encoding="utf-8")
    tar_path = OUTPUT_DIR / f"{slug}-v{version}.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        for p in pack_dir.rglob("*"):
            if p.is_file():
                tf.add(p, arcname=str(p.relative_to(pack_dir)))
    sidecar_path = OUTPUT_DIR / f"{slug}-v{version}-manifest.json"
    sidecar_path.write_text(json.dumps(manifest, indent=2,
                                          ensure_ascii=False),
                              encoding="utf-8")
    dc_log("a16.pack.built", "pack built", slug=slug, version=version,
            n_docs=len(fetched_docs))
    return {
        "manifest": manifest,
        "tar_path": str(tar_path),
        "manifest_path": str(sidecar_path),
        "tar_size_kb": tar_path.stat().st_size // 1024,
    }


def verify_pack(tar_path: Path) -> dict:
    with tarfile.open(tar_path, "r:gz") as tf:
        names = tf.getnames()
        manifest_member = next((n for n in names
                                  if n.endswith("manifest.json")), None)
        if not manifest_member:
            return {"ok": False, "error": "manifest.json missing"}
        manifest_raw = tf.extractfile(manifest_member).read()
        manifest = json.loads(manifest_raw)
    bundled_hash = manifest.get("manifest_hash", "")
    manifest_base = {k: v for k, v in manifest.items()
                       if k != "manifest_hash"}
    recomputed = _sha256_bytes(json.dumps(
        manifest_base, sort_keys=True, ensure_ascii=False,
        indent=2).encode("utf-8"))
    return {
        "ok": bundled_hash.endswith(recomputed),
        "bundled_hash": bundled_hash,
        "recomputed_hash": f"sha256:{recomputed}",
        "n_documents": len(manifest.get("documents", [])),
        "slug": manifest.get("slug"),
        "version": manifest.get("version"),
    }


# ===========================================================================
# 3. State + workbench shell
# ===========================================================================
_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = f"a17_pack_session_{_run_ts}"
BUILT: list[dict] = []
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"


def _flush_bundle():
    with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
        _rows = [{"slug": b["manifest"]["slug"],
                   "version": b["manifest"]["version"],
                   "manifest_hash": b["manifest"]["manifest_hash"]}
                  for b in BUILT]
        _z.writestr("manifest.json", json.dumps({
            "schema_version": "1.0",
            "kernel_id": "a-17-knowledge-pack-builder",
            "run_id": RUN_ID,
            "results": _rows,
            "packs_built": _rows,    # legacy alias (data_primitives.md 1.1)
        }, indent=2))
        for b in BUILT:
            mp = Path(b["manifest_path"])
            if mp.exists():
                _z.write(mp, mp.name)


INDEX_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-17 . Pack builder</title>
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
  textarea{width:100%;min-height:200px;border:1px solid #DDD8C9;
           border-radius:8px;padding:10px;
           font-family:"JetBrains Mono",monospace;font-size:12.5px;
           background:#F7F6F1}
  input[type=text]{padding:8px 12px;border:1px solid #DDD8C9;
                    border-radius:6px;background:#F7F6F1;font:inherit;
                    margin-right:8px}
  button.primary{background:#0E1116;color:#F7F6F1;border:none;
                 border-radius:999px;padding:11px 22px;
                 font-size:13.5px;font-weight:600;cursor:pointer;
                 margin-top:10px}
  button.secondary{background:transparent;color:#0E1116;
                   border:1px solid #DDD8C9;border-radius:999px;
                   padding:10px 18px;font-size:13px;cursor:pointer;
                   margin-top:10px}
  .row{background:#FFF;border:1px solid #EFEDE4;border-radius:10px;
       padding:10px 14px;margin:8px 0;font-size:13.5px}
  .hash{font-family:"JetBrains Mono",monospace;font-size:11.5px;
        color:#5B5F68}
  pre{font-family:"JetBrains Mono",monospace;font-size:12.5px;
      background:rgba(0,0,0,.04);padding:10px 12px;border-radius:6px;
      white-space:pre-wrap;word-break:break-word}
  .dl a{color:#0E1116;text-decoration:underline}
</style></head><body>
<div class="page">
  <h1>DueCare A-17 . Pack builder + verifier</h1>
  <p class="lede">Build a versioned, signed corridor pack. A
    researcher can later pull and verify the manifest hash for a
    deterministic answer. Lane 04 / 05.</p>
  <div class="panel">
    <h2>Build a pack</h2>
    <input type="text" id="pack-slug" placeholder="slug"
            value="demo-corridor-pack">
    <input type="text" id="pack-version" placeholder="version"
            value="1.0.0">
    <input type="text" id="pack-curator" placeholder="curator"
            value="demo-curator">
    <p style="margin:8px 0 4px;font-size:13px">Documents JSON
      (list of <code>{doc_id, source_url?, inline_text?}</code>):</p>
    <textarea id="docs-json">[
  {"doc_id": "POEA_MC_14-2017", "inline_text":
   "POEA Memorandum Circular 14-2017 caps placement fees for PH-HK domestic workers at zero."},
  {"doc_id": "ILO_C189", "inline_text":
   "ILO Convention 189 protects domestic workers' right to written contracts and prohibits fee-related coercion."}
]</textarea>
    <br><button class="primary" onclick="buildPack()">Build pack</button>
  </div>
  <div class="panel">
    <h2>Verify a pack</h2>
    <p style="margin:0 0 6px;font-size:13px">Tarball filename under
      /kaggle/working:</p>
    <input type="text" id="verify-tar" style="width:60%"
            placeholder="demo-corridor-pack-v1.0.0.tar.gz">
    <button class="secondary" onclick="verifyPack()">Verify</button>
    <pre id="verify-result">.</pre>
  </div>
  <div class="panel">
    <h2>Packs built this session</h2>
    <div id="rows"></div>
  </div>
  <p class="dl">Bundle: <a id="bundle-link" href="#">(no packs yet)</a></p>
</div>
<script>
function _el(tag,cls,txt){const e=document.createElement(tag);
  if(cls)e.className=cls;if(txt!=null)e.textContent=String(txt);return e}

async function buildPack(){
  let docs;
  try{docs=JSON.parse(document.getElementById('docs-json').value)}
  catch(e){alert('Documents JSON parse error: '+e);return}
  const body={
    slug: document.getElementById('pack-slug').value.trim(),
    version: document.getElementById('pack-version').value.trim(),
    curator: document.getElementById('pack-curator').value.trim(),
    documents: docs,
  };
  await fetch('/api/build',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body)}).then(r=>r.json());
  refreshState();
}

async function verifyPack(){
  const t=document.getElementById('verify-tar').value.trim();
  if(!t)return;
  const r=await fetch('/api/verify?t='+encodeURIComponent(t))
                .then(r=>r.json());
  document.getElementById('verify-result').textContent=
    JSON.stringify(r,null,2);
}

async function refreshState(){
  const r=await fetch('/api/state').then(r=>r.json());
  const wrap=document.getElementById('rows');wrap.replaceChildren();
  for(const b of (r.built||[])){
    const c=_el('div','row');
    c.appendChild(_el('div',null,
      b.manifest.slug+' v'+b.manifest.version+' . '+
      b.manifest.documents.length+' docs . '+b.tar_size_kb+' KB'));
    c.appendChild(_el('div','hash',b.manifest.manifest_hash));
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


print("\n[2/4] launching pack-builder UI")
_SHUTDOWN_EVENT = threading.Event()

try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": "A-16 knowledge-pack builder",
        "audience": "researcher",
        "lede": ("Build a versioned, signed corridor pack from public "
                  "sources. Researchers can later pull + verify the "
                  "hash. Lane 04 / 05."),
        "results": [
            {"label": "Compute", "value": "CPU-only"},
            {"label": "Output", "value": "<slug>-v<version>.tar.gz"},
            {"label": "Signing", "value": "sha256(manifest)"},
        ],
        "links": [
            ("Experiment ladder",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
        ],
        "next_steps": [
            "Open the printed cloudflared URL.",
            "Edit the documents JSON; click Build pack.",
            "Verify the resulting .tar.gz to confirm the hash.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-17-knowledge-pack-builder",
        port=PORT, homepage_html=INDEX_HTML,
    )
    from fastapi import Request

    @app.post("/api/build")
    async def _build(req: Request):
        body = await req.json()
        try:
            result = build_pack(
                slug=body["slug"], version=body["version"],
                curator=body.get("curator", "unknown"),
                documents=body.get("documents", []),
                description=body.get("description", ""))
            BUILT.append(result)
            _flush_bundle()
            return {"ok": True, **result}
        except Exception as e:
            return {"ok": False, "error":
                    f"{type(e).__name__}: {str(e)[:300]}"}

    @app.get("/api/verify")
    def _verify(t: str = ""):
        tar_path = OUTPUT_DIR / t
        if not tar_path.exists():
            return {"ok": False,
                    "error": f"tarball not found: {tar_path}"}
        return verify_pack(tar_path)

    @app.get("/api/state")
    def _state():
        return {
            "built": BUILT[-10:][::-1],
            "bundle_name": (BUNDLE_PATH.name
                              if BUNDLE_PATH.exists() else None),
            "bundle_size_kb": (BUNDLE_PATH.stat().st_size // 1024
                                 if BUNDLE_PATH.exists() else 0),
        }

    if public_url:
        print(f"  ok UI: {public_url}")
    print("\n  A-16 PACK BUILDER READY\n")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutdown complete -- cell exiting.\n")
