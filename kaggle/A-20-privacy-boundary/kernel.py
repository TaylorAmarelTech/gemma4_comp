# <!-- duecare:kernel-intro -->
# DueCare — Privacy boundary visualization (trust surface)
# Appendix notebook #A20 of 24 in the DueCare submission.
#
# Side-by-side: what stays on the caseworker's machine vs what
# would leave if "Share aggregate" is clicked. Mirrors
# privacy-boundary.html.

"""
============================================================================
  DUECARE A-20 PRIVACY BOUNDARY -- Kaggle notebook
============================================================================
  Pure CPU. Zero inference. Pre-baked sample intake + redaction +
  salt-hash + aggregate side-by-side, with the BOUNDARY between
  local-only and outside-the-machine drawn explicitly.

  Output: /kaggle/working
    a20_privacy_boundary_demo.json   the side-by-side state
    a20_privacy_boundary_bundle.zip  manifest + above

  Built with Google's Gemma 4. Used in accordance with the Gemma Terms of Use.
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
import zipfile
from pathlib import Path


# ===========================================================================
# CONFIG
# ===========================================================================
PORT = 8080
TUNNEL = "cloudflared"
OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# PHASE 1 -- DueCare from GitHub (lightweight; no Unsloth)
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


print("[1/2] DueCare from GitHub")
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)


# ===========================================================================
# 2. Demo state (100% synthetic)
# ===========================================================================
SALT = "demo-salt-not-for-production"

SAMPLE_INTAKE = (
    "My name is Maria Santos and I came from Manila to Hong Kong. "
    "I work as a domestic helper for Sterling House Services. The "
    "recruiter Bright Horizon Manpower Services took USD 2100 in "
    "fees. They took my passport (EB1234567) too. My phone is "
    "+639012345678 but my employer checks. Email me at "
    "maria.santos31@gmail.com instead. I live at 88 Nathan Road, "
    "Hong Kong."
)

PII_PATTERNS = [
    ("PHONE", re.compile(r"\+?\d[\d\s\-]{7,15}\d")),
    ("EMAIL", re.compile(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("PASSPORT", re.compile(r"\b[A-Z]{1,2}\d{6,9}\b")),
    ("AMOUNT", re.compile(
        r"(?:USD|PHP|HK\$|HKD|SAR|AED|QAR)\s*\d{1,7}",
        re.IGNORECASE)),
    ("PERSON", re.compile(
        r"\b[A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?")),
]


def _salted(value: str) -> str:
    return hashlib.sha256(
        (SALT + ":" + value).encode("utf-8")).hexdigest()[:16]


def stage_redact(text: str) -> tuple[str, list[dict]]:
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
            "original_value": value,
            "salted_hash": _salted(value),
        })
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts), entities


redacted_text, entities = stage_redact(SAMPLE_INTAKE)

LOCAL_STATE = {
    "raw_intake": SAMPLE_INTAKE,
    "redacted_intake": redacted_text,
    "entities": entities,
}
AGGREGATE_STATE = {
    "period_days": 90,
    "n_cases": 47,
    "entity_label_counts": {
        "PERSON": 24, "PASSPORT": 8, "PHONE": 11, "EMAIL": 6,
        "AMOUNT": 17,
    },
    "repeat_hashes": [
        {"hash_prefix": h["salted_hash"][:8] + "...",
         "case_count": 3} for h in entities[:2]
    ],
    "note": "No PII. All hashes are salted; the salt itself is "
            "not exported.",
}

DEMO_PAYLOAD = {
    "schema_version": "1.0",
    "kernel_id": "a-20-privacy-boundary",
    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "local_state": LOCAL_STATE,
    "aggregate_state_what_would_leave": AGGREGATE_STATE,
}
# Canonical RunID per docs/data_primitives.md so multiple recordings
# don't collide.
_run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
RUN_ID = f"a20_privacy_{_run_ts}"
DEMO_PAYLOAD["run_id"] = RUN_ID
RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_privacy_boundary_demo.json"
BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"
RESULTS_PATH.write_text(json.dumps(DEMO_PAYLOAD, indent=2,
                                       ensure_ascii=False),
                            encoding="utf-8")
with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
    _z.write(RESULTS_PATH, "privacy_boundary_demo.json")
print(f"  + {RESULTS_PATH.name}")
print(f"  + {BUNDLE_PATH.name}")

try:
    from duecare.chat._dc_log import set_kernel_id
    set_kernel_id("a-20-privacy-boundary")
except Exception:
    def set_kernel_id(*a, **kw): return None


# ===========================================================================
# 3. Workbench shell with side-by-side HTML
# ===========================================================================
print("\n[2/2] launching privacy-boundary UI")
_SHUTDOWN_EVENT = threading.Event()


def _render_html(payload: dict) -> str:
    raw = payload["local_state"]["raw_intake"]
    redacted = payload["local_state"]["redacted_intake"]
    ents = payload["local_state"]["entities"]
    agg = payload["aggregate_state_what_would_leave"]
    ents_html = "".join(
        f'<div class="ent-row"><span class="lbl">{e["label"]}</span>'
        f'<span class="raw">{e["original_value"]}</span>'
        f'<span class="arrow">-&gt;</span>'
        f'<span class="hash">{e["salted_hash"]}</span></div>'
        for e in ents
    )
    return (
        r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-20 . Privacy boundary</title>
<style>
  body{background:#F7F6F1;color:#0E1116;
       font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
       margin:0;padding:0}
  .page{max-width:1200px;margin:0 auto;padding:32px 28px 80px}
  h1{font-size:28px;margin:0 0 6px}
  .lede{color:#5B5F68;margin:0 0 28px;max-width:780px}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;
        margin-top:8px}
  .col{background:#FFF;border:1px solid #DDD8C9;border-radius:12px;
       padding:18px 20px;position:relative}
  .col.local{border-left:6px solid #3E8C65}
  .col.outside{border-left:6px solid #9E3F3F}
  .col h2{font-size:17px;margin:0 0 12px}
  .col h2 .pill{display:inline-block;font-size:11px;padding:2px 10px;
                 border-radius:999px;font-weight:600;margin-left:8px}
  .col.local h2 .pill{background:#3E8C65;color:#fff}
  .col.outside h2 .pill{background:#9E3F3F;color:#fff}
  .raw-text{background:#FFF6F6;border:1px solid #F5C9C9;
            border-radius:8px;padding:12px 14px;font-size:13.5px;
            white-space:pre-wrap;line-height:1.55}
  .redacted-text{background:#EAF2EC;border:1px solid #B8D9C2;
                  border-radius:8px;padding:12px 14px;font-size:13.5px;
                  white-space:pre-wrap;line-height:1.55}
  pre{font-family:"JetBrains Mono",monospace;font-size:12.5px;
      background:rgba(0,0,0,.04);padding:12px 14px;border-radius:8px;
      white-space:pre-wrap;word-break:break-word;margin:6px 0 0}
  .ent-table{margin-top:12px}
  .ent-row{display:grid;grid-template-columns:90px 1fr 30px 1fr;
            align-items:center;padding:5px 0;font-size:12.5px;
            border-bottom:1px dotted #DDD8C9}
  .ent-row .lbl{font-family:"JetBrains Mono",monospace;
                 font-size:11px;color:#5B5F68;font-weight:600}
  .ent-row .raw{font-family:"JetBrains Mono",monospace;
                 background:#FFF6F6;padding:1px 6px;border-radius:4px}
  .ent-row .arrow{text-align:center;color:#5B5F68}
  .ent-row .hash{font-family:"JetBrains Mono",monospace;
                  background:#EAF2EC;padding:1px 6px;border-radius:4px;
                  font-size:11px}
  .boundary-band{margin:18px 0;padding:14px 18px;
                  background:#0E1116;color:#F7F6F1;border-radius:10px;
                  font-family:"JetBrains Mono",monospace;font-size:13px;
                  text-align:center}
  .note{margin-top:14px;color:#5B5F68;font-size:12.5px;font-style:italic}
</style></head><body>
<div class="page">
  <h1>DueCare A-20 . Privacy boundary</h1>
  <p class="lede">Side-by-side: what stays on the caseworker's
    machine (left) vs what would leave if the operator clicks
    "share aggregate" (right). Salted hashes are one-way; the salt
    itself is never exported. Mirrors privacy-boundary.html.</p>

  <div class="grid">
    <div class="col local">
      <h2>Local (stays on the device)
          <span class="pill">never leaves</span></h2>
      <h3 style="margin:6px 0 4px;font-size:13px;
                  text-transform:uppercase;letter-spacing:.05em;
                  color:#5B5F68">Raw intake (PII present)</h3>
      <div class="raw-text">"""
        + raw
        + r"""</div>
      <h3 style="margin:14px 0 4px;font-size:13px;
                  text-transform:uppercase;letter-spacing:.05em;
                  color:#5B5F68">Redacted (used for local DB)</h3>
      <div class="redacted-text">"""
        + redacted
        + r"""</div>
      <h3 style="margin:14px 0 4px;font-size:13px;
                  text-transform:uppercase;letter-spacing:.05em;
                  color:#5B5F68">Salt-hash mapping (local-only)</h3>
      <div class="ent-table">"""
        + ents_html
        + r"""</div>
      <p class="note">The raw column above NEVER persists to disk
        beyond this in-session view. The local SQLite store only
        keeps the redacted text + the hash column.</p>
    </div>

    <div class="col outside">
      <h2>Outside-the-machine (aggregate only, after Share)
          <span class="pill">explicit consent</span></h2>
      <h3 style="margin:6px 0 4px;font-size:13px;
                  text-transform:uppercase;letter-spacing:.05em;
                  color:#5B5F68">Aggregate signal preview</h3>
      <pre>"""
        + json.dumps(agg, indent=2, ensure_ascii=False)
        + r"""</pre>
      <p class="note">This is the ONLY object that leaves the
        machine, and only after the operator clicks Share. No PII.
        Hashes are salted-and-truncated; the salt is not exported.
        A regulator who receives this object cannot reverse it to
        the original names / passports / phones.</p>
    </div>
  </div>

  <div class="boundary-band">
    THE LINE BETWEEN LOCAL AND OUTSIDE IS THE OPERATOR'S CLICK
  </div>

  <p style="text-align:center;color:#5B5F68;font-size:13px;
            margin-top:14px">
    Download: <a href="/artifact/""" + BUNDLE_PATH.name + r"""">""" + (
        BUNDLE_PATH.name) + r"""</a>
  </p>
</div></body></html>"""
    )


try:
    from duecare.chat.kernel_shell import build_minimal_shell
    summary_payload = {
        "title": "A-20 Privacy boundary visualization",
        "audience": "all",
        "lede": ("Side-by-side: what stays local vs what would "
                  "leave on Share. The trust visualization."),
        "results": [
            {"label": "Compute",  "value": "CPU-only, no model load"},
            {"label": "Output",   "value": "static demo state"},
            {"label": "Audience", "value": "all 5 lanes"},
        ],
        "links": [
            ("Experiment ladder",
              "https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/docs/appendix_experiment_ladder.md"),
        ],
        "next_steps": [
            "Open the printed cloudflared URL.",
            "Use this surface to anchor the privacy boundary "
            "explanation in the video pitch.",
        ],
    }
    app, public_url = build_minimal_shell(
        summary=summary_payload,
        kernel_id="a-20-privacy-boundary",
        port=PORT, homepage_html=_render_html(DEMO_PAYLOAD),
    )
    if public_url:
        print(f"  ok UI: {public_url}")
    print("\n  A-20 PRIVACY-BOUNDARY READY\n")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")

print("\n  shutdown complete -- cell exiting.\n")
