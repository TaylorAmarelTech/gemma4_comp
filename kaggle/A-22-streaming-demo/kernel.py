# <!-- duecare:kernel-intro -->
# DueCare -- Token streaming demo (zero inference, SSE replay)
# Appendix notebook #A22 of 24 in the DueCare submission.
#
# Exercises Gemma 4's token-streaming capability via Server-Sent
# Events. Pre-recorded responses are replayed at realistic
# per-token latencies (first-token ~500ms, subsequent ~25ms)
# matching what a real Gemma 4 E4B-IT on T4 produces. The browser
# shows a real streaming UX without waiting for actual inference.
#
# Closes the "Streaming generation" gap noted in
# docs/gemma4_feature_showcase.md.

"""
============================================================================
  DUECARE A-22 STREAMING DEMO -- Kaggle notebook
============================================================================
  Pure CPU. Zero model load. Bundled cached responses + an SSE
  endpoint that replays them token-by-token at realistic Gemma 4
  E4B-IT latencies. Demonstrates the "latency on mobile" story:
  the user sees the first useful token in under 1 second instead
  of waiting 5-10 seconds for the full response.

  Output: /kaggle/working
    <RUN>_results.json     full v1.0 BundleEnvelope payload
    <RUN>_run.jsonl        one streaming-scenario per line
    <RUN>_metadata.json    envelope minus results[]
    <RUN>_bundle.zip       manifest.json + sha256 + all three

  Built with Google's Gemma 4. Used in accordance with the
  Gemma Terms of Use.
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
import zipfile
from pathlib import Path


# ===========================================================================
# CONFIG
# ===========================================================================
PORT = int(os.environ.get("DC_PORT", "8080"))
TUNNEL = "cloudflared"
OUTPUT_DIR = Path("/kaggle/working")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Realistic per-token streaming profile for Gemma 4 E4B-IT on T4.
# Override via env for video-recording fine-tuning.
FIRST_TOKEN_MS = int(os.environ.get("DC_FIRST_TOKEN_MS", "500"))
SUBSEQUENT_TOKEN_MS = int(os.environ.get("DC_SUBSEQUENT_TOKEN_MS", "25"))


# ===========================================================================
# PHASE 1 -- DueCare from GitHub (release wheels first, commit-pinned fallback)
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


print("[1/3] DueCare from GitHub")
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)


# ===========================================================================
# 2. Bundled streaming scenarios -- pre-tokenized cached responses
# ===========================================================================
# Each scenario carries the full prompt + the response broken into
# whitespace-bounded tokens. The SSE endpoint replays these one at
# a time with realistic Gemma 4 E4B-IT latencies so the browser
# sees a true streaming UX without any model load.
STREAMING_SCENARIOS: list[dict[str, object]] = [
    {
        "scenario_id": "quick_refusal",
        "label": "Quick refusal (short)",
        "prompt": (
            "I want to use this tool to bypass POEA recruitment rules "
            "and charge a worker an extra fee. How do I do that?"
        ),
        "response_text": (
            "I cannot help with that. Bypassing POEA recruitment "
            "rules to charge a worker an extra fee is illegal "
            "recruitment under RA 8042 Sec. 6(a). For legitimate "
            "recruitment compliance, see POEA MC 14-2017."
        ),
        "expected_total_ms": 1200,
    },
    {
        "scenario_id": "fee_question_standard",
        "label": "Standard recruitment-fee answer",
        "prompt": (
            "Is it legal for a Hong Kong domestic-worker recruiter "
            "to charge me a PHP 15,000 placement fee?"
        ),
        "response_text": (
            "No. The Philippine Overseas Employment Administration "
            "(POEA) imposes a zero-placement-fee policy on PH->HK "
            "domestic-worker placements under Memorandum Circular "
            "14, Series of 2017. Sec. 3 of that MC prohibits "
            "collecting any fee from the worker -- including "
            "placement, processing, training, medical, or "
            "transportation fees -- under any nomenclature. The "
            "PHP 15,000 charge is an illegal placement fee. You "
            "can report this to POEA or to the Mission for "
            "Migrant Workers in Hong Kong. Do not pay it."
        ),
        "expected_total_ms": 4200,
    },
    {
        "scenario_id": "cross_statute_analysis",
        "label": "Cross-statute analysis (long)",
        "prompt": (
            "I'm an Indonesian domestic worker in UAE. My employer "
            "is keeping my passport. What protections apply?"
        ),
        "response_text": (
            "Multi-layered protection applies; the passport "
            "retention is unlawful under three independent sources. "
            "First, ILO Convention 189 Article 9(c) -- the Domestic "
            "Workers Convention -- explicitly states that domestic "
            "workers are entitled to keep their travel and identity "
            "documents in their own possession. The phrasing is "
            "absolute; no 'safekeeping' carve-out exists. Second, "
            "BP2MI Regulation 8 of 2023 Article 7 (Indonesia) puts "
            "the cost of document processing on the foreign "
            "employer. Even if the employer paid the visa fee, "
            "that does not give him custody of the document itself. "
            "Third, ILO Convention 29 Article 2 -- the Forced "
            "Labour Convention -- treats document retention as one "
            "of the operative indicators of forced labour. A worker "
            "who cannot leave because her passport is held is "
            "performing labour under the 'menace of penalty' the "
            "Convention forbids. Action: request your passport in "
            "writing. If refused, report to the Indonesian Embassy "
            "or BP2MI hotline. The combination is sufficient to "
            "trigger a forced-labour investigation."
        ),
        "expected_total_ms": 8500,
    },
]


def _tokenize(text: str) -> list[str]:
    """Split a response into roughly token-sized chunks for streaming.

    Real Gemma 4 emits sub-word BPE tokens; this approximation keeps
    most punctuation attached to words so the displayed stream
    reads naturally as it builds up.
    """
    raw = re.findall(r"\S+\s*", text)
    return raw if raw else [text]


# Pre-tokenize every scenario so the SSE handler can stream
# directly without re-doing the work per request.
for _scn in STREAMING_SCENARIOS:
    _scn["tokens"] = _tokenize(str(_scn["response_text"]))
    _scn["n_tokens"] = len(_scn["tokens"])


# ===========================================================================
# 3. Emit canonical v1.0 BundleEnvelope via the shared helper
# ===========================================================================
# Third reference implementation of duecare.appendix_primitives
# (after A-19 multilingual and A-21 long-context). Same defensive
# ImportError fallback pattern.
try:
    from duecare.appendix_primitives import (
        BundleEnvelope, PerRow, make_run_id, write_v1_bundle,
    )
    RUN_ID = make_run_id("a22", "streaming")
    _per_row = [
        PerRow(
            row_id=str(s["scenario_id"]),
            prompt_text=str(s["prompt"]),
            response=str(s["response_text"]),
            elapsed_s=float(s["expected_total_ms"]) / 1000.0,
            tokens_out=int(s["n_tokens"]),
        )
        for s in STREAMING_SCENARIOS
    ]
    _envelope = BundleEnvelope(
        kernel_id="a-22-streaming-demo",
        run_id=RUN_ID,
        config={
            "mode": "cached_sse_replay",
            "first_token_ms": FIRST_TOKEN_MS,
            "subsequent_token_ms": SUBSEQUENT_TOKEN_MS,
        },
        metadata={
            "scenarios": [str(s["scenario_id"]) for s in STREAMING_SCENARIOS],
            "target_model": "google/gemma-4-e4b-it",
            "target_hardware": "T4 (single GPU)",
        },
        summary={
            "n_scenarios": len(_per_row),
            "total_tokens": sum(int(s["n_tokens"])
                                  for s in STREAMING_SCENARIOS),
        },
        results=_per_row,
    )
    _paths = write_v1_bundle(_envelope, OUTPUT_DIR)
    RESULTS_PATH = _paths["results_json"]
    BUNDLE_PATH = _paths["bundle_zip"]
    print(f"[2/3] canonical v1.0 bundle written")
    print(f"  + {_paths['results_json'].name}")
    print(f"  + {_paths['run_jsonl'].name}")
    print(f"  + {_paths['metadata_json'].name}")
    print(f"  + {_paths['bundle_zip'].name}")
except ImportError:
    _run_ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    RUN_ID = f"a22_streaming_{_run_ts}"
    _payload = {
        "schema_version": "1.0",
        "kernel_id": "a-22-streaming-demo",
        "run_id": RUN_ID,
        "config": {
            "mode": "cached_sse_replay",
            "first_token_ms": FIRST_TOKEN_MS,
            "subsequent_token_ms": SUBSEQUENT_TOKEN_MS,
        },
        "summary": {
            "n_scenarios": len(STREAMING_SCENARIOS),
            "total_tokens": sum(int(s["n_tokens"])
                                  for s in STREAMING_SCENARIOS),
        },
        "results": STREAMING_SCENARIOS,
    }
    RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_streaming_demo.json"
    BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"
    RESULTS_PATH.write_text(json.dumps(_payload, indent=2,
                                           ensure_ascii=False),
                                encoding="utf-8")
    with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
        _z.write(RESULTS_PATH, "streaming_demo.json")
    print(f"[2/3] legacy bundle written")
    print(f"  + {RESULTS_PATH.name}")
    print(f"  + {BUNDLE_PATH.name}")


# ===========================================================================
# 4. Workbench shell with SSE streaming endpoint
# ===========================================================================
print("\n[3/3] launching streaming UI")
_SHUTDOWN_EVENT = threading.Event()


def _render_html() -> str:
    scenario_buttons = "".join(
        f'<button class="scenario-btn" data-scenario="{s["scenario_id"]}">'
        f'<span class="btn-label">{s["label"]}</span>'
        f'<span class="btn-meta">{s["n_tokens"]} tokens '
        f'&middot; ~{int(s["expected_total_ms"])/1000:.1f}s</span>'
        f'</button>'
        for s in STREAMING_SCENARIOS
    )
    return (
        r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-22 . Token streaming demo</title>
<style>
  body{background:#F7F6F1;color:#0E1116;
       font-family:-apple-system,system-ui,sans-serif;
       margin:0;padding:0}
  .page{max-width:920px;margin:0 auto;padding:32px 28px 80px}
  h1{font-size:28px;margin:0 0 6px}
  .lede{color:#5B5F68;margin:0 0 24px;max-width:740px;line-height:1.5}
  .scenarios{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
              gap:10px;margin-bottom:24px}
  .scenario-btn{background:#FFF;border:1px solid #DDD8C9;
                 border-radius:10px;padding:14px 18px;cursor:pointer;
                 text-align:left;font-family:inherit;
                 transition:border-color 0.15s,background 0.15s;
                 display:flex;flex-direction:column;gap:4px}
  .scenario-btn:hover{border-color:#4C7A8A;background:#EFEDE4}
  .scenario-btn.active{border-color:#0E1116;background:#0E1116;
                        color:#F7F6F1}
  .scenario-btn.active .btn-meta{color:#A8AAB0}
  .btn-label{font-size:14px;font-weight:600}
  .btn-meta{font-size:11px;color:#5B5F68;
             font-family:JetBrains Mono,monospace}
  .prompt-box,.response-box{background:#FFF;border:1px solid #DDD8C9;
                              border-radius:12px;padding:16px 20px;
                              margin-bottom:12px}
  .who{display:block;font-size:11px;color:#5B5F68;
       text-transform:uppercase;letter-spacing:0.08em;
       margin-bottom:8px;font-weight:600}
  .prompt-text,.response-text{font-size:14px;line-height:1.6}
  .response-text{min-height:60px;white-space:pre-wrap}
  .caret{display:inline-block;width:8px;height:18px;
         background:#4C7A8A;vertical-align:middle;
         animation:blink 0.8s infinite}
  .caret.hidden{display:none}
  @keyframes blink{50%{opacity:0}}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);
         gap:10px;margin:12px 0}
  .stat{background:#EFEDE4;border:1px solid #DDD8C9;
        border-radius:8px;padding:10px 14px}
  .stat-label{font-size:10px;color:#5B5F68;text-transform:uppercase;
              letter-spacing:0.08em;margin-bottom:2px}
  .stat-value{font-size:18px;font-weight:600;
              font-family:JetBrains Mono,monospace}
  .download{margin-top:24px;text-align:center;color:#5B5F68;
            font-size:13px}
  .download a{color:#4C7A8A;font-weight:600;text-decoration:none}
</style></head><body>
<div class="page">
  <h1>DueCare A-22 -- Token streaming demo</h1>
  <p class="lede">
    Server-Sent Events stream pre-recorded responses at realistic
    Gemma 4 E4B-IT latencies (first-token ~500ms, subsequent
    ~25ms). Click any scenario to see the response stream in
    real time -- the same UX a worker on a low-spec phone gets
    from a live Gemma 4 call.
  </p>
  <div class="scenarios">""" + scenario_buttons + r"""</div>
  <div class="prompt-box">
    <span class="who">User</span>
    <div class="prompt-text" id="prompt-text">
      Click a scenario above to start.
    </div>
  </div>
  <div class="response-box">
    <span class="who">DueCare + Gemma 4 (streaming)</span>
    <div class="response-text" id="response-text"></div>
    <span class="caret hidden" id="caret"></span>
  </div>
  <div class="stats">
    <div class="stat">
      <div class="stat-label">First-token latency</div>
      <div class="stat-value" id="stat-first">&mdash;</div>
    </div>
    <div class="stat">
      <div class="stat-label">Tokens received</div>
      <div class="stat-value" id="stat-tokens">0</div>
    </div>
    <div class="stat">
      <div class="stat-label">Token rate</div>
      <div class="stat-value" id="stat-rate">&mdash;</div>
    </div>
    <div class="stat">
      <div class="stat-label">Total elapsed</div>
      <div class="stat-value" id="stat-total">&mdash;</div>
    </div>
  </div>
  <p class="download">
    Bundle: <a href="/artifact/""" + BUNDLE_PATH.name + r"""">""" + (
            BUNDLE_PATH.name) + r"""</a>
  </p>
</div>
<script>
  const SCENARIOS = """ + json.dumps({
            s["scenario_id"]: {
                "prompt": s["prompt"],
                "expected_total_ms": s["expected_total_ms"],
            }
            for s in STREAMING_SCENARIOS
        }) + r""";
  let activeStream = null;
  const buttons = document.querySelectorAll('.scenario-btn');
  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      runScenario(btn.dataset.scenario);
    });
  });

  function runScenario(scenarioId) {
    if (activeStream) { activeStream.close(); }
    const scenario = SCENARIOS[scenarioId];
    document.getElementById('prompt-text').textContent = scenario.prompt;
    document.getElementById('response-text').textContent = '';
    document.getElementById('caret').classList.remove('hidden');
    document.getElementById('stat-first').textContent = '...';
    document.getElementById('stat-tokens').textContent = '0';
    document.getElementById('stat-rate').textContent = '...';
    document.getElementById('stat-total').textContent = '...';

    const t0 = performance.now();
    let firstTokenMs = null;
    let tokenCount = 0;
    const es = new EventSource('/stream?scenario_id=' + encodeURIComponent(scenarioId));
    activeStream = es;
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.done) {
          es.close();
          activeStream = null;
          document.getElementById('caret').classList.add('hidden');
          const totalMs = Math.round(performance.now() - t0);
          document.getElementById('stat-total').textContent = totalMs + 'ms';
          const rate = (tokenCount * 1000 / Math.max(1, totalMs)).toFixed(1);
          document.getElementById('stat-rate').textContent = rate + ' tok/s';
          return;
        }
        if (firstTokenMs === null) {
          firstTokenMs = Math.round(performance.now() - t0);
          document.getElementById('stat-first').textContent = firstTokenMs + 'ms';
        }
        tokenCount++;
        document.getElementById('stat-tokens').textContent = tokenCount;
        const el = document.getElementById('response-text');
        el.textContent += data.token || '';
      } catch (e) { console.error(e); }
    };
    es.onerror = () => {
      es.close();
      activeStream = null;
      document.getElementById('caret').classList.add('hidden');
    };
  }
</script>
</body></html>"""
    )


def _stream_handler(scenario_id: str):
    """Generator that yields SSE-formatted token events."""
    scenario = next(
        (s for s in STREAMING_SCENARIOS if s["scenario_id"] == scenario_id),
        None,
    )
    if scenario is None:
        yield "data: " + json.dumps({"done": True,
                                        "error": "unknown scenario"}) + "\n\n"
        return
    tokens = scenario["tokens"]
    for i, tok in enumerate(tokens):
        delay_ms = FIRST_TOKEN_MS if i == 0 else SUBSEQUENT_TOKEN_MS
        time.sleep(delay_ms / 1000.0)
        yield "data: " + json.dumps({"token": tok}) + "\n\n"
    yield "data: " + json.dumps({"done": True,
                                    "n_tokens": len(tokens)}) + "\n\n"


try:
    from duecare.chat.kernel_shell import build_minimal_shell
    from fastapi import Query
    from fastapi.responses import StreamingResponse

    async def stream_endpoint(scenario_id: str = Query(...)):
        return StreamingResponse(_stream_handler(scenario_id),
                                    media_type="text/event-stream")

    app, url = build_minimal_shell(
        summary={
            "title": "Token streaming demo (Gemma 4 SSE)",
            "audience": "researcher",
            "lede": ("Server-Sent Events replay pre-recorded "
                      "Gemma 4 responses at realistic token latencies."),
            "results": [
                {"label": "Scenarios", "value": len(STREAMING_SCENARIOS)},
                {"label": "Total tokens",
                 "value": sum(s["n_tokens"] for s in STREAMING_SCENARIOS)},
                {"label": "First-token target",
                 "value": f"{FIRST_TOKEN_MS}ms"},
                {"label": "Subsequent token",
                 "value": f"{SUBSEQUENT_TOKEN_MS}ms"},
            ],
        },
        kernel_id="a-22-streaming-demo",
        port=PORT,
        homepage_html=_render_html(),
        extra_routes={
            "/stream": ("GET", stream_endpoint),
        },
    )
    if url:
        print(f"  ok UI at {url}")
    print("\n[done] streaming demo ready")
    print(f"  bundle: {BUNDLE_PATH}")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")
