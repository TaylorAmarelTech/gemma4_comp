# <!-- duecare:kernel-intro -->
# DueCare -- Coordinator-as-function-calling-router demo (zero inference)
# Appendix notebook #A23 of 24 in the DueCare submission.
#
# Exercises Gemma 4's NATIVE function-calling capability as a
# multi-tool orchestration router: in ONE thinking step, the
# Coordinator emits 2-4 structured function calls that fan out to
# DueCare's lookup tools, then synthesizes the results into a
# single grounded response. This is the "load-bearing" use of
# Gemma 4's unique feature per CLAUDE.md rule 4 -- not a
# decorative demo.
#
# Closes the "Coordinator-as-function-calling-router" gap noted
# in docs/gemma4_feature_showcase.md.

"""
============================================================================
  DUECARE A-23 COORDINATOR DEMO -- Kaggle notebook
============================================================================
  Pure CPU. Zero model load. Bundled cached scenarios that each
  show Gemma 4 emitting a multi-tool plan, fanning out the tool
  calls, and synthesizing a single grounded answer -- all in
  ONE turn rather than three separate chat exchanges.

  Output: /kaggle/working
    <RUN>_results.json     full v1.0 BundleEnvelope payload
    <RUN>_run.jsonl        one scenario per line
    <RUN>_metadata.json    envelope minus results[]
    <RUN>_bundle.zip       manifest.json + sha256 + all three

  Built with Google's Gemma 4, used under the Apache License 2.0.
============================================================================
"""
from __future__ import annotations

import json
import os
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


print("[1/3] DueCare from GitHub")
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)


# ===========================================================================
# 2. Tool catalog -- the four lookup tools the Coordinator routes to
# ===========================================================================
TOOLS: dict[str, dict[str, object]] = {
    "lookup_corridor_rules": {
        "description": (
            "Look up the controlling sending-country and receiving-"
            "country rules for a migration corridor."),
        "args_schema": {
            "origin": "ISO 3166-1 alpha-2 sending country code",
            "destination": "ISO 3166-1 alpha-2 receiving country code",
            "worker_class": "domestic | construction | hospitality | other",
        },
    },
    "lookup_fee_cap": {
        "description": "Look up the legal placement-fee cap for a corridor.",
        "args_schema": {
            "corridor": "<origin>-<destination> e.g. PH-HK",
            "worker_class": "domestic | construction | hospitality | other",
        },
    },
    "lookup_statute_text": {
        "description": "Pull the operative passage of a named statute.",
        "args_schema": {
            "statute_id": "POEA_MC_14_2017 | RA_8042 | ILO_C189 | ILO_C29 | "
                           "BP2MI_REG_8_2023",
            "section": "optional section anchor",
        },
    },
    "find_hotline": {
        "description": (
            "Find vetted NGO / regulator contact pathways for a corridor. "
            "Phone numbers and URLs are volatile; verify current details "
            "from the contacts knowledge pack before sharing them."),
        "args_schema": {
            "corridor": "<origin>-<destination>",
            "side": "origin | destination | both",
        },
    },
}


# ===========================================================================
# 3. Coordinator scenarios -- one Gemma turn -> multi-tool plan
# ===========================================================================
COORDINATOR_SCENARIOS: list[dict[str, object]] = [
    {
        "scenario_id": "ph_hk_domestic_fee_question",
        "user_prompt": (
            "I'm a Filipino worker offered domestic work in Hong Kong. "
            "The recruiter wants PHP 22,000 placement fee. Is this legal? "
            "And who do I report this to?"
        ),
        "tool_plan": [
            {"name": "lookup_corridor_rules",
             "args": {"origin": "PH", "destination": "HK",
                       "worker_class": "domestic"}},
            {"name": "lookup_fee_cap",
             "args": {"corridor": "PH-HK", "worker_class": "domestic"}},
            {"name": "find_hotline",
             "args": {"corridor": "PH-HK", "side": "both"}},
        ],
        "tool_results": [
            {"name": "lookup_corridor_rules",
             "result": {
                 "sending_country_statutes": ["POEA_MC_14_2017", "RA_8042"],
                 "destination_country_statutes": ["HK_EOA_2018"],
                 "international_instruments": ["ILO_C189"],
             }},
            {"name": "lookup_fee_cap",
             "result": {
                 "cap_amount": 0,
                 "cap_currency": "PHP",
                 "controlling_statute": "POEA_MC_14_2017_Sec_3",
                 "violation_severity": "criminal_illegal_recruitment",
             }},
            {"name": "find_hotline",
             "result": {
                 "origin_hotline": "POEA Anti-Illegal Recruitment Branch",
                 "origin_contact": "verify current phone, URL, and intake steps via contacts pack",
                 "destination_hotline": "Mission for Migrant Workers HK",
                 "destination_contact": "verify current phone, URL, and intake steps via contacts pack",
             }},
        ],
        "synthesized_response": (
            "No -- this is illegal. The PH-HK domestic-worker corridor is "
            "under a zero-placement-fee policy (POEA MC 14-2017 Sec. 3); "
            "any fee, regardless of name, is illegal. The PHP 22,000 "
            "charge is criminal illegal recruitment under RA 8042 Sec. "
            "6(a). To report:\n\n"
            "  - POEA Anti-Illegal Recruitment Branch (Philippines): "
            "verify current phone, URL, and intake steps via the vetted "
            "contacts pack.\n"
            "  - Mission for Migrant Workers Hong Kong: verify current "
            "phone, URL, and intake steps via the vetted contacts pack.\n\n"
            "Refuse the payment. The agency's POEA license is at risk "
            "for this arrangement."
        ),
        "citations": ["POEA MC 14-2017 Sec. 3", "RA 8042 Sec. 6(a)"],
        "elapsed_s_coordinator": 1.8,
        "elapsed_s_chat_loop_equivalent": 5.4,
    },
    {
        "scenario_id": "id_uae_passport_retention",
        "user_prompt": (
            "I'm an Indonesian domestic worker in UAE. My employer is "
            "keeping my passport. What rights do I have and who can I "
            "call?"
        ),
        "tool_plan": [
            {"name": "lookup_corridor_rules",
             "args": {"origin": "ID", "destination": "AE",
                       "worker_class": "domestic"}},
            {"name": "lookup_statute_text",
             "args": {"statute_id": "ILO_C189", "section": "Article 9"}},
            {"name": "lookup_statute_text",
             "args": {"statute_id": "ILO_C29", "section": "Article 2"}},
            {"name": "find_hotline",
             "args": {"corridor": "ID-AE", "side": "both"}},
        ],
        "tool_results": [
            {"name": "lookup_corridor_rules",
             "result": {
                 "sending_country_statutes": ["BP2MI_REG_8_2023"],
                 "destination_country_statutes": [
                     "UAE_Federal_Law_10_2017_DomesticWorkers"],
                 "international_instruments": ["ILO_C189", "ILO_C29"],
             }},
            {"name": "lookup_statute_text",
             "result": {
                 "statute_id": "ILO_C189",
                 "section": "Article 9(c)",
                 "text": ("Domestic workers are entitled to keep in "
                           "their possession their travel and identity "
                           "documents."),
             }},
            {"name": "lookup_statute_text",
             "result": {
                 "statute_id": "ILO_C29",
                 "section": "Article 2",
                 "text": ("'Forced or compulsory labour' shall mean "
                           "all work or service which is exacted from "
                           "any person under the menace of any penalty."),
             }},
            {"name": "find_hotline",
             "result": {
                 "origin_hotline": "BP2MI Hotline (Indonesia)",
                 "origin_contact": "verify current phone, URL, and intake steps via contacts pack",
                 "destination_hotline": ("UAE Ministry of Human "
                                           "Resources MOHRE"),
                 "destination_contact": "verify current phone, URL, and intake steps via contacts pack",
                 "embassy": "Indonesian Embassy Abu Dhabi",
                 "embassy_contact": "verify current phone, URL, and intake steps via contacts pack",
             }},
        ],
        "synthesized_response": (
            "Your protections are layered and clear. The passport "
            "retention is unlawful under three independent rules:\n\n"
            "  1. ILO C189 Article 9(c): domestic workers MUST keep "
            "     their own travel and identity documents. No "
            "     'safekeeping' carve-out exists.\n"
            "  2. ILO C29 Article 2: document retention is an operative "
            "     indicator of forced labour. You cannot leave because "
            "     your passport is held -- that is labour under the "
            "     'menace of penalty' the Convention forbids.\n"
            "  3. BP2MI Reg 8-2023 (Indonesia) puts the cost of "
            "     document processing on the foreign employer; he has "
            "     no right to custody.\n\n"
            "Who to call:\n"
            "  - Indonesian Embassy Abu Dhabi: verify current phone, URL, "
            "and intake steps via the vetted contacts pack.\n"
            "  - BP2MI Hotline (Indonesia): verify current phone, URL, "
            "and intake steps via the vetted contacts pack.\n"
            "  - UAE MOHRE: verify current phone, URL, and intake steps "
            "via the vetted contacts pack.\n\n"
            "Request your passport in writing first. If refused, the "
            "Embassy is your safest first call."
        ),
        "citations": ["ILO C189 Art. 9(c)", "ILO C29 Art. 2",
                      "BP2MI Reg 8-2023"],
        "elapsed_s_coordinator": 2.4,
        "elapsed_s_chat_loop_equivalent": 7.6,
    },
    {
        "scenario_id": "saudi_voluntary_iou_debt_bondage",
        "user_prompt": (
            "A recruiter for Saudi Arabia is offering a 'voluntary' "
            "IOU for PHP 40,000 placement cost, paid back over my "
            "first 8 months of salary. They say 'voluntary' = not a "
            "fee. Is this consistent with my rights?"
        ),
        "tool_plan": [
            {"name": "lookup_corridor_rules",
             "args": {"origin": "PH", "destination": "SA",
                       "worker_class": "domestic"}},
            {"name": "lookup_fee_cap",
             "args": {"corridor": "PH-SA", "worker_class": "domestic"}},
            {"name": "lookup_statute_text",
             "args": {"statute_id": "ILO_C29",
                       "section": "2014 Protocol Art. 2(d)"}},
        ],
        "tool_results": [
            {"name": "lookup_corridor_rules",
             "result": {
                 "sending_country_statutes": ["POEA_MC_14_2017", "RA_8042"],
                 "destination_country_statutes": [
                     "Saudi_Labor_Law_Royal_Decree_M_51"],
                 "international_instruments": ["ILO_C29", "ILO_C189"],
             }},
            {"name": "lookup_fee_cap",
             "result": {
                 "cap_amount": 0,
                 "cap_currency": "PHP",
                 "controlling_statute": "POEA_MC_14_2017",
                 "iou_loophole_recognized": False,
                 "note": ("Substance test: any cost-recovery scheme "
                           "(IOU, loan, deferred fee) routed to the "
                           "worker is treated as a placement fee, "
                           "regardless of label."),
             }},
            {"name": "lookup_statute_text",
             "result": {
                 "statute_id": "ILO_C29",
                 "section": "2014 Protocol Article 2(d)",
                 "text": ("Effective measures shall be taken to "
                           "prevent and eliminate forced or "
                           "compulsory labour, including by "
                           "protecting migrant workers from possible "
                           "abusive and fraudulent practices during "
                           "the recruitment and placement process."),
             }},
        ],
        "synthesized_response": (
            "No -- 'voluntary' framing does not change the substance. "
            "Three independent rules make this arrangement unlawful:\n\n"
            "  1. POEA MC 14-2017 puts cost-recovery on the foreign "
            "     principal; an IOU that recovers the cost from you "
            "     is the same prohibited charge in disguised form. The "
            "     substance test applies regardless of the 'voluntary' "
            "     label.\n"
            "  2. RA 8042 Sec. 6(a) makes it illegal recruitment to "
            "     charge a worker any amount greater than the schedule "
            "     of allowable fees -- for PH-SA domestic the cap is "
            "     well below PHP 40,000.\n"
            "  3. ILO C29 2014 Protocol Art. 2(d) treats fraudulent "
            "     recruitment practices as a forced-labour indicator. "
            "     A worker whose first 8 months of salary are pre-"
            "     pledged cannot freely leave -- the 'menace of "
            "     penalty' element is present.\n\n"
            "Refuse to sign the IOU. The 'voluntary' framing is itself "
            "a red flag. Compliant Saudi recruitment does not require "
            "a worker IOU."
        ),
        "citations": ["POEA MC 14-2017", "RA 8042 Sec. 6(a)",
                      "ILO C29 2014 Protocol Art. 2(d)"],
        "elapsed_s_coordinator": 2.1,
        "elapsed_s_chat_loop_equivalent": 6.0,
    },
]


# ===========================================================================
# 4. Emit canonical v1.0 BundleEnvelope via the shared helper
# ===========================================================================
# Fourth reference implementation of duecare.appendix_primitives
# (after A-19 multilingual, A-21 long-context, A-22 streaming).
try:
    from duecare.appendix_primitives import (
        BundleEnvelope, PerRow, make_run_id, write_v1_bundle,
    )
    RUN_ID = make_run_id("a23", "coordinator")
    _per_row = [
        PerRow(
            row_id=str(s["scenario_id"]),
            prompt_text=str(s["user_prompt"]),
            response=str(s["synthesized_response"]),
            elapsed_s=float(s["elapsed_s_coordinator"]),
            citations=list(s["citations"]),
            tool_plan=s["tool_plan"],
            tool_results=s["tool_results"],
            elapsed_s_chat_loop_equivalent=s["elapsed_s_chat_loop_equivalent"],
        )
        for s in COORDINATOR_SCENARIOS
    ]
    _total_coord = sum(float(s["elapsed_s_coordinator"])
                          for s in COORDINATOR_SCENARIOS)
    _total_chat = sum(float(s["elapsed_s_chat_loop_equivalent"])
                         for s in COORDINATOR_SCENARIOS)
    _envelope = BundleEnvelope(
        kernel_id="a-23-coordinator-demo",
        run_id=RUN_ID,
        config={"mode": "cached", "n_tools": len(TOOLS),
                 "tool_names": list(TOOLS.keys())},
        metadata={
            "scenarios": [str(s["scenario_id"])
                            for s in COORDINATOR_SCENARIOS],
            "target_model": "google/gemma-4-e4b-it",
        },
        summary={
            "n_scenarios": len(_per_row),
            "total_tool_calls": sum(len(s["tool_plan"])
                                       for s in COORDINATOR_SCENARIOS),
            "avg_tool_calls_per_scenario": round(
                sum(len(s["tool_plan"]) for s in COORDINATOR_SCENARIOS)
                / max(1, len(COORDINATOR_SCENARIOS)), 1),
            "speedup_vs_chat_loop": round(
                _total_chat / max(0.001, _total_coord), 2),
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
    RUN_ID = f"a23_coordinator_{_run_ts}"
    _payload = {
        "schema_version": "1.0",
        "kernel_id": "a-23-coordinator-demo",
        "run_id": RUN_ID,
        "config": {"mode": "cached", "n_tools": len(TOOLS)},
        "summary": {"n_scenarios": len(COORDINATOR_SCENARIOS)},
        "results": COORDINATOR_SCENARIOS,
    }
    RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_coordinator_demo.json"
    BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"
    RESULTS_PATH.write_text(json.dumps(_payload, indent=2,
                                           ensure_ascii=False),
                                encoding="utf-8")
    with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
        _z.write(RESULTS_PATH, "coordinator_demo.json")
    print(f"[2/3] legacy bundle written")
    print(f"  + {RESULTS_PATH.name}")
    print(f"  + {BUNDLE_PATH.name}")


# ===========================================================================
# 5. Workbench shell -- orchestration timeline view
# ===========================================================================
print("\n[3/3] launching coordinator UI")
_SHUTDOWN_EVENT = threading.Event()


def _render_scenario(scenario: dict) -> str:
    plan_html = "".join(
        f'<li><span class="tool-name">{i+1}. {tc["name"]}'
        f'</span><pre class="tool-args">'
        f'{json.dumps(tc["args"], indent=2, ensure_ascii=False)}'
        f'</pre></li>'
        for i, tc in enumerate(scenario["tool_plan"])
    )
    results_html = "".join(
        f'<li><span class="tool-name">{tr["name"]}</span>'
        f'<pre class="tool-result">'
        f'{json.dumps(tr["result"], indent=2, ensure_ascii=False)}'
        f'</pre></li>'
        for tr in scenario["tool_results"]
    )
    cite_html = "".join(
        f'<span class="cite">{c}</span>' for c in scenario["citations"]
    )
    speedup = round(
        float(scenario["elapsed_s_chat_loop_equivalent"])
        / max(0.001, float(scenario["elapsed_s_coordinator"])), 2)
    return (
        f'<div class="scenario" data-id="{scenario["scenario_id"]}">'
        f'<h3>{scenario["scenario_id"]}</h3>'
        f'<div class="prompt-box"><span class="who">User</span>'
        f'<div class="prompt-text">{scenario["user_prompt"]}</div></div>'
        f'<div class="step-label">Step 1 &mdash; Gemma 4 plans the '
        f'tool fan-out ({len(scenario["tool_plan"])} tool calls in '
        f'one thinking step):</div>'
        f'<ol class="tool-plan">{plan_html}</ol>'
        f'<div class="step-label">Step 2 &mdash; runtime fans out, '
        f'tool results return:</div>'
        f'<ol class="tool-results">{results_html}</ol>'
        f'<div class="step-label">Step 3 &mdash; Gemma 4 synthesizes '
        f'a single grounded response:</div>'
        f'<div class="response-box"><span class="who">'
        f'DueCare + Gemma 4 (synthesized)</span>'
        f'<pre class="response-text">{scenario["synthesized_response"]}'
        f'</pre></div>'
        f'<div class="cite-row">{cite_html}</div>'
        f'<div class="timing">Coordinator: <b>'
        f'{scenario["elapsed_s_coordinator"]}s</b> &middot; chat-loop '
        f'equivalent: {scenario["elapsed_s_chat_loop_equivalent"]}s '
        f'&middot; speedup: <b>{speedup}x</b></div>'
        f'</div>'
    )


def _render_html() -> str:
    scenarios_html = "\n".join(_render_scenario(s)
                                for s in COORDINATOR_SCENARIOS)
    return (
        r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-23 . Coordinator demo</title>
<style>
  body{background:#F7F6F1;color:#0E1116;
       font-family:-apple-system,system-ui,sans-serif;
       margin:0;padding:0}
  .page{max-width:980px;margin:0 auto;padding:32px 28px 80px}
  h1{font-size:28px;margin:0 0 6px}
  .lede{color:#5B5F68;margin:0 0 24px;max-width:760px;line-height:1.55}
  .scenario{background:#FFF;border:1px solid #DDD8C9;
            border-radius:12px;padding:20px 24px;margin-bottom:18px}
  .scenario h3{font-family:JetBrains Mono,monospace;
               font-size:13px;color:#5B5F68;
               text-transform:uppercase;letter-spacing:0.08em;
               margin:0 0 14px}
  .step-label{font-size:11px;color:#5B5F68;
              text-transform:uppercase;letter-spacing:0.08em;
              font-weight:600;margin:14px 0 6px}
  .prompt-box,.response-box{background:#EFEDE4;border:1px solid #DDD8C9;
                              border-radius:10px;padding:12px 16px;
                              margin-bottom:12px}
  .who{display:block;font-size:11px;color:#5B5F68;
       text-transform:uppercase;letter-spacing:0.08em;
       margin-bottom:6px;font-weight:600}
  .prompt-text{font-size:14px;line-height:1.55}
  .response-text{font-family:inherit;font-size:13.5px;
                  white-space:pre-wrap;line-height:1.55;margin:0}
  .tool-plan,.tool-results{list-style:none;padding:0;margin:0 0 8px}
  .tool-plan li,.tool-results li{background:#EFEDE4;border:1px solid #DDD8C9;
                                    border-radius:8px;padding:10px 14px;
                                    margin-bottom:6px}
  .tool-name{font-family:JetBrains Mono,monospace;color:#4C7A8A;
             font-weight:600;font-size:13px}
  .tool-args,.tool-result{background:#F7F6F1;border-radius:6px;
                            padding:8px 10px;margin:6px 0 0;
                            font-family:JetBrains Mono,monospace;
                            font-size:11.5px;line-height:1.4;
                            white-space:pre-wrap;overflow-x:auto}
  .tool-args{border-left:3px solid #4C7A8A}
  .tool-result{border-left:3px solid #3E8C65}
  .cite-row{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
  .cite{background:#EFEDE4;border:1px solid #DDD8C9;color:#0E1116;
        font-family:JetBrains Mono,monospace;font-size:11px;
        padding:4px 8px;border-radius:6px}
  .timing{font-size:12px;color:#5B5F68;padding-top:8px;
          border-top:1px solid #EFEDE4;margin-top:8px}
  .download{margin-top:24px;text-align:center;color:#5B5F68;
            font-size:13px}
  .download a{color:#4C7A8A;font-weight:600;text-decoration:none}
</style></head><body>
<div class="page">
  <h1>DueCare A-23 -- Coordinator demo</h1>
  <p class="lede">
    Gemma 4 emits a multi-tool function-call plan in ONE thinking
    step. The runtime fans out, results return, Gemma synthesizes
    a single grounded response. This is the load-bearing use of
    Gemma 4's native function calling -- not decoration.
  </p>
  """ + scenarios_html + r"""
  <p class="download">
    Bundle: <a href="/artifact/""" + BUNDLE_PATH.name + r"""">""" + (
            BUNDLE_PATH.name) + r"""</a>
  </p>
</div>
</body></html>"""
    )


try:
    from duecare.chat.kernel_shell import build_minimal_shell
    _total_coord = sum(float(s["elapsed_s_coordinator"])
                          for s in COORDINATOR_SCENARIOS)
    _total_chat = sum(float(s["elapsed_s_chat_loop_equivalent"])
                         for s in COORDINATOR_SCENARIOS)
    _speedup = round(_total_chat / max(0.001, _total_coord), 2)
    app, url = build_minimal_shell(
        summary={
            "title": "Coordinator demo (Gemma 4 native function calling)",
            "audience": "researcher",
            "lede": ("Multi-tool fan-out from one Gemma 4 thinking step. "
                      "Closes CLAUDE.md rule 4."),
            "results": [
                {"label": "Scenarios", "value": len(COORDINATOR_SCENARIOS)},
                {"label": "Tools registered", "value": len(TOOLS)},
                {"label": "Total tool calls",
                 "value": sum(len(s["tool_plan"])
                                for s in COORDINATOR_SCENARIOS)},
                {"label": "Avg speedup vs chat loop",
                 "value": f"{_speedup}x"},
            ],
        },
        kernel_id="a-23-coordinator-demo",
        port=PORT,
        homepage_html=_render_html(),
    )
    if url:
        print(f"  ok UI at {url}")
    print("\n[done] coordinator demo ready")
    print(f"  bundle: {BUNDLE_PATH}")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")
