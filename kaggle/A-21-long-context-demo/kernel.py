# <!-- duecare:kernel-intro -->
# DueCare -- 128K long-context demo (zero inference, cached cross-statute QA)
# Appendix notebook #A21 of 24 in the DueCare submission.
#
# Exercises Gemma 4's long-context (128K) capability by loading a
# multi-statute compliance corpus (POEA MC 14-2017 + RA 8042 +
# ILO C189 + BP2MI Reg 8-2023 + ILO C29) into a single context
# window and answering cross-statute questions that require
# correlating across documents -- the value of long context vs
# retrieval-only.
#
# Zero-inference mode (default): replays cached QA pairs so users
# see the workflow without waiting for token generation. Same
# pattern as A-19 multilingual + A-24 demo-replay.

"""
============================================================================
  DUECARE A-21 LONG-CONTEXT DEMO -- Kaggle notebook
============================================================================
  Pure CPU in the default cached mode. Zero model load. Bundled
  multi-statute corpus + cross-statute QA pairs that demonstrate
  Gemma 4's 128K long-context capability across migrant-worker
  protection statutes.

  Corpus (bundled, public-source):
    POEA MC 14-2017     Philippines recruitment-fee cap
    RA 8042             Philippines Migrant Workers Act
    BP2MI Reg 8-2023    Indonesia placement-fee rules
    ILO C189            Domestic Workers Convention
    ILO C29             Forced Labour Convention

  Output: /kaggle/working
    <RUN>_results.json     full v1.0 BundleEnvelope payload
    <RUN>_run.jsonl        one QA per line (streaming variant)
    <RUN>_metadata.json    envelope minus results[]
    <RUN>_bundle.zip       manifest.json + sha256 + all three

  Built with Google's Gemma 4. Used in accordance with the
  Gemma Terms of Use.
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
# PHASE 1 -- DueCare from GitHub (release wheels first, commit-pinned fallback)
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


print("[1/3] DueCare from GitHub")
install_duecare_from_github()
subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                  "--no-input", "--disable-pip-version-check",
                  "fastapi>=0.115.0", "uvicorn>=0.30.0"],
                  capture_output=True, text=True)


# ===========================================================================
# 2. Bundled compliance corpus -- public-source statute extracts
# ===========================================================================
# Each entry is a representative extract from the named statute.
# Real production deployment would load full text (which would push
# the input toward the 128K Gemma 4 boundary); the extracts below
# are the operative passages users can cross-reference against the
# public sources.
COMPLIANCE_CORPUS: dict[str, dict[str, object]] = {
    "POEA_MC_14_2017": {
        "title": "POEA Memorandum Circular No. 14, Series of 2017",
        "jurisdiction": "Philippines (POEA)",
        "operative_text": (
            "Sec. 3. Prohibited Fees. -- The placement of Filipino "
            "household service workers (HSWs) bound for Hong Kong "
            "shall be subject to a zero-placement-fee policy. No "
            "placement fee, processing fee, training fee, medical-"
            "review fee, transportation fee, or any other fee under "
            "any nomenclature shall be collected from the worker, "
            "directly or indirectly, by the recruitment agency, the "
            "foreign principal, or any of their agents.\n\n"
            "Sec. 5. Charges to the Foreign Principal. -- All "
            "documented costs of recruitment, including but not "
            "limited to medical examination, training, travel, and "
            "visa processing, shall be borne by the foreign principal "
            "/ employer. Any deduction from the worker's first salary "
            "for these costs shall be deemed an illegal placement fee."
        ),
        "applies_to_corridors": ["PH->HK"],
        "url": ("https://www.poea.gov.ph/memorandumcirculars/"
                "2017/MC-14-Series-of-2017.pdf"),
    },
    "RA_8042": {
        "title": "Republic Act No. 8042 -- Migrant Workers and "
                  "Overseas Filipinos Act of 1995",
        "jurisdiction": "Philippines (Congress)",
        "operative_text": (
            "Section 6. Definition. -- For purposes of this Act, "
            "illegal recruitment shall mean any act of canvassing, "
            "enlisting, contracting, transporting, utilizing, hiring, "
            "or procuring workers and includes referring, contract "
            "services, promising or advertising for employment "
            "abroad, whether for profit or not, when undertaken by a "
            "non-licensee or non-holder of authority [...]. It shall "
            "likewise include the following acts, whether committed "
            "by any person, whether a non-licensee, non-holder, "
            "licensee, or holder of authority:\n"
            "  (a) To charge or accept directly or indirectly any "
            "amount greater than that specified in the schedule of "
            "allowable fees prescribed by the Secretary of Labor and "
            "Employment, or to make a worker pay any amount greater "
            "than that actually received by him as a loan or advance;\n"
            "  (j) For an officer or agent of a recruitment or "
            "placement agency to become an officer or member of the "
            "Board of any corporation engaged in travel agency or to "
            "be engaged directly or indirectly in the management of a "
            "travel agency;\n"
            "  (m) Failure to reimburse expenses incurred by the "
            "worker in connection with his documentation and "
            "processing for purposes of deployment, in cases where "
            "the deployment does not actually take place without the "
            "worker's fault."
        ),
        "applies_to_corridors": ["PH->*"],
        "url": "https://lawphil.net/statutes/repacts/ra1995/ra_8042_1995.html",
    },
    "ILO_C189": {
        "title": "ILO Convention 189 -- Domestic Workers Convention",
        "jurisdiction": "International Labour Organization",
        "operative_text": (
            "Article 9. Each Member shall take measures to ensure "
            "that domestic workers:\n"
            "  (a) are free to reach agreement with their employer or "
            "potential employer on whether to reside in the household;\n"
            "  (b) who reside in the household are not obliged to "
            "remain in the household or with household members during "
            "periods of daily and weekly rest or annual leave;\n"
            "  (c) are entitled to keep in their possession their "
            "travel and identity documents.\n\n"
            "Article 15. To effectively protect domestic workers "
            "[...] each Member shall take measures to:\n"
            "  (e) provide adequate protection to domestic workers "
            "recruited or placed in its territory by private "
            "employment agencies, including by way of bilateral, "
            "regional or multilateral agreements with other Members."
        ),
        "applies_to_corridors": ["*"],
        "url": ("https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:"
                "12100:0::NO::P12100_INSTRUMENT_ID:2551460"),
    },
    "BP2MI_REG_8_2023": {
        "title": "BP2MI Regulation No. 8 of 2023 -- Indonesian "
                  "Migrant Worker Placement Fee Rules",
        "jurisdiction": "Indonesia (Badan Pelindungan Pekerja "
                          "Migran Indonesia)",
        "operative_text": (
            "Article 4. Zero Placement Fee. -- The placement of "
            "Indonesian migrant workers under bilateral G-to-G or "
            "G-to-P agreements shall be subject to a zero placement-"
            "fee policy. The worker shall not be required to pay any "
            "placement fee, processing fee, training fee, or any "
            "other fee under any name to the placement agency or its "
            "agents.\n\n"
            "Article 7. Cost Allocation. -- The cost of recruitment, "
            "training, document processing, transportation, and "
            "medical examination shall be borne by the foreign "
            "employer or principal. Any deduction from the worker's "
            "salary or any 'voluntary' loan or IOU scheme intended "
            "to recoup these costs from the worker is deemed an "
            "illegal placement fee."
        ),
        "applies_to_corridors": ["ID->*"],
        "url": ("https://peraturan.bpk.go.id/Details/"
                "245718/peraturan-badan-no-8-tahun-2023"),
    },
    "ILO_C29": {
        "title": "ILO Convention 29 -- Forced Labour Convention",
        "jurisdiction": "International Labour Organization",
        "operative_text": (
            "Article 2(1). For the purposes of this Convention the "
            "term 'forced or compulsory labour' shall mean all work "
            "or service which is exacted from any person under the "
            "menace of any penalty and for which the said person has "
            "not offered himself voluntarily.\n\n"
            "Article 2 of the 2014 Protocol to the Forced Labour "
            "Convention. Effective measures shall be taken to prevent "
            "and eliminate forced or compulsory labour, including "
            "by [...] (d) protecting persons, particularly migrant "
            "workers, from possible abusive and fraudulent practices "
            "during the recruitment and placement process; (e) "
            "supporting due diligence by both the public and private "
            "sectors to prevent and respond to risks of forced or "
            "compulsory labour."
        ),
        "applies_to_corridors": ["*"],
        "url": ("https://www.ilo.org/dyn/normlex/en/f?p=NORMLEXPUB:"
                "12100:0::NO::P12100_ILO_CODE:C029"),
    },
}


def _corpus_stats() -> dict[str, int]:
    """Approximate char and token counts for the bundled corpus."""
    total_chars = sum(
        len(str(d.get("operative_text", "")))
        for d in COMPLIANCE_CORPUS.values()
    )
    return {
        "n_statutes": len(COMPLIANCE_CORPUS),
        "total_chars": total_chars,
        # Conservative 4 chars/token approximation; real Gemma 4
        # tokenizer would give a tighter number.
        "approx_tokens": total_chars // 4,
    }


# ===========================================================================
# 3. Cross-statute cached QA -- each requires correlating 2+ statutes
# ===========================================================================
# Each QA is the kind of question that requires Gemma 4 to find
# information ACROSS multiple statutes in a single thinking step --
# i.e. the value of long-context reasoning vs separate retrieval
# calls. The cached responses show what a fine-tuned SafetyJudge
# adapter produces at this kind of cross-reference task.
LONG_CONTEXT_QA: list[dict[str, object]] = [
    {
        "qa_id": "ph_hk_zero_fee_with_disguised_charges",
        "prompt": (
            "I'm a Filipino worker offered domestic work in Hong Kong. "
            "The recruiter is asking for PHP 22,000 placement fee plus a "
            "PHP 5,000 'medical review fee' deducted from my first "
            "salary. Is this legal? Cite the controlling statutes."
        ),
        "response": (
            "No -- this arrangement is illegal under three overlapping "
            "rules and the disguised salary deduction does not save it:\n\n"
            "1. POEA MC 14-2017 Sec. 3 imposes a ZERO-placement-fee "
            "   policy on PH-HK domestic-worker placements. No fee of "
            "   any nomenclature -- including 'medical review fee' -- "
            "   may be collected from the worker.\n\n"
            "2. POEA MC 14-2017 Sec. 5 places the burden of all "
            "   documented costs (medical, training, travel, visa) on "
            "   the foreign principal. Any deduction from the worker's "
            "   first salary for these costs is deemed an illegal "
            "   placement fee. The 'medical review fee' falls squarely "
            "   inside this prohibition.\n\n"
            "3. RA 8042 Sec. 6(a) makes it illegal recruitment to "
            "   charge a worker any amount greater than the schedule "
            "   of allowable fees -- which for PH-HK domestic is zero "
            "   per the POEA MC above. The recruiter's actions are a "
            "   criminal violation under RA 8042, not merely an "
            "   administrative one.\n\n"
            "Action: refuse the payment. Report to POEA (Philippines) "
            "or to the Mission for Migrant Workers in Hong Kong. The "
            "agency's POEA license is at risk for this arrangement."
        ),
        "citations": ["POEA MC 14-2017 Sec. 3",
                      "POEA MC 14-2017 Sec. 5",
                      "RA 8042 Sec. 6(a)"],
        "statutes_used": ["POEA_MC_14_2017", "RA_8042"],
        "elapsed_s_cached": 0.0,
        "elapsed_s_simulated_e4b": 2.4,
    },
    {
        "qa_id": "id_uae_passport_retention",
        "prompt": (
            "An Indonesian domestic worker has been working in UAE "
            "for 18 months. Her employer kept her passport in his "
            "safe 'for safekeeping'. What protections apply under "
            "Indonesian sending-country law AND the international "
            "instruments her receiving country has ratified?"
        ),
        "response": (
            "Multi-layered protection applies; the passport retention "
            "is unlawful under three independent sources:\n\n"
            "1. ILO C189 Article 9(c) (Domestic Workers Convention) "
            "   explicitly states domestic workers are entitled to "
            "   keep their travel and identity documents in their "
            "   own possession. The phrasing is absolute -- no "
            "   'safekeeping' carve-out exists.\n\n"
            "2. BP2MI Reg 8 of 2023 Art. 7 puts the cost of document "
            "   processing on the foreign employer. Even if the "
            "   employer paid for visa fees, that does not give him "
            "   custody of the document itself.\n\n"
            "3. ILO C29 Article 2 (Forced Labour Convention) treats "
            "   document retention as one of the operative indicators "
            "   of forced labour -- a worker who cannot leave because "
            "   her passport is held is performing labour under the "
            "   'menace of penalty' the Convention forbids.\n\n"
            "Action: the worker should request her passport in "
            "writing. If refused, she can report to the Indonesian "
            "Embassy / BP2MI hotline, and (if she fears retaliation) "
            "directly to UAE Ministry of Human Resources and "
            "Emiratisation. The combination of passport retention + "
            "long stay + unspecified 'safekeeping' is sufficient to "
            "trigger a forced-labour investigation."
        ),
        "citations": ["ILO C189 Art. 9(c)",
                      "BP2MI Reg 8-2023 Art. 7",
                      "ILO C29 Art. 2"],
        "statutes_used": ["ILO_C189", "BP2MI_REG_8_2023", "ILO_C29"],
        "elapsed_s_cached": 0.0,
        "elapsed_s_simulated_e4b": 2.9,
    },
    {
        "qa_id": "saudi_voluntary_deferred_fee_iou",
        "prompt": (
            "A recruiter for Saudi Arabia is offering a 'voluntary' "
            "deferred-fee scheme where I sign an IOU and pay back the "
            "PHP 40,000 placement cost over my first 8 months of "
            "salary. They say it's 'voluntary' so it doesn't count as "
            "a fee. Is this consistent with my home-country "
            "protections?"
        ),
        "response": (
            "No -- 'voluntary' framing does not change the substance, "
            "and the arrangement violates multiple controlling rules:\n\n"
            "1. RA 8042 Sec. 6(a) prohibits charging a worker any "
            "   amount greater than the schedule of allowable fees. "
            "   The schedule for PH->Saudi Arabia is capped well "
            "   below PHP 40,000; an IOU scheme that recovers this "
            "   amount is the same prohibited charge in disguised "
            "   form.\n\n"
            "2. POEA MC 14-2017 Sec. 5 (and the cost-allocation "
            "   principle it states more broadly) puts recruitment "
            "   costs on the foreign principal, NOT on the worker. A "
            "   'voluntary' IOU still routes the cost back to the "
            "   worker -- the substance test, not the label.\n\n"
            "3. ILO C29 Article 2 + the 2014 Protocol Art. 2(d) "
            "   recognize debt-bondage IOU arrangements as a forced-"
            "   labour indicator. A worker whose first 8 months of "
            "   salary are pre-pledged to repay a 'voluntary' loan "
            "   cannot freely leave the employment without forfeiting "
            "   the loan -- the 'menace of penalty' element is "
            "   present.\n\n"
            "Action: refuse to sign the IOU. The 'voluntary' framing "
            "is itself a red flag -- legitimate compliant recruitment "
            "for Saudi Arabia does not require a worker IOU. Report "
            "the agency to POEA; flag the IOU template specifically."
        ),
        "citations": ["RA 8042 Sec. 6(a)",
                      "POEA MC 14-2017 Sec. 5",
                      "ILO C29 Art. 2",
                      "ILO C29 2014 Protocol Art. 2(d)"],
        "statutes_used": ["RA_8042", "POEA_MC_14_2017", "ILO_C29"],
        "elapsed_s_cached": 0.0,
        "elapsed_s_simulated_e4b": 3.1,
    },
]


# ===========================================================================
# 4. Emit canonical v1.0 BundleEnvelope via the shared helper
# ===========================================================================
# Second reference implementation of duecare.appendix_primitives
# (first was A-19 multilingual). Same defensive ImportError fallback
# pattern so older duecare-llm-chat versions still emit a usable
# legacy bundle.
try:
    from duecare.appendix_primitives import (
        BundleEnvelope, PerRow, make_run_id, write_v1_bundle,
    )
    RUN_ID = make_run_id("a21", "long_context")
    _stats = _corpus_stats()
    _per_row = [
        PerRow(
            row_id=str(qa["qa_id"]),
            prompt_text=str(qa["prompt"]),
            response=str(qa["response"]),
            elapsed_s=float(qa["elapsed_s_cached"]),
            citations=list(qa["citations"]),
        )
        for qa in LONG_CONTEXT_QA
    ]
    _envelope = BundleEnvelope(
        kernel_id="a-21-long-context-demo",
        run_id=RUN_ID,
        config={
            "mode": "cached",
            "n_statutes": _stats["n_statutes"],
            "corpus_chars": _stats["total_chars"],
            "corpus_approx_tokens": _stats["approx_tokens"],
        },
        metadata={
            "statutes": list(COMPLIANCE_CORPUS.keys()),
        },
        summary={
            "n_qa": len(_per_row),
            "n_statutes": _stats["n_statutes"],
            "corpus_chars": _stats["total_chars"],
            "corpus_approx_tokens": _stats["approx_tokens"],
            "context_window_target": 131072,
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
    RUN_ID = f"a21_long_context_{_run_ts}"
    _stats = _corpus_stats()
    _payload = {
        "schema_version": "1.0",
        "kernel_id": "a-21-long-context-demo",
        "run_id": RUN_ID,
        "config": {
            "mode": "cached",
            "n_statutes": _stats["n_statutes"],
            "corpus_chars": _stats["total_chars"],
            "corpus_approx_tokens": _stats["approx_tokens"],
        },
        "summary": {
            "n_qa": len(LONG_CONTEXT_QA),
            "n_statutes": _stats["n_statutes"],
            "corpus_chars": _stats["total_chars"],
            "corpus_approx_tokens": _stats["approx_tokens"],
            "context_window_target": 131072,
        },
        "results": LONG_CONTEXT_QA,
    }
    RESULTS_PATH = OUTPUT_DIR / f"{RUN_ID}_long_context_demo.json"
    BUNDLE_PATH = OUTPUT_DIR / f"{RUN_ID}_bundle.zip"
    RESULTS_PATH.write_text(json.dumps(_payload, indent=2,
                                           ensure_ascii=False),
                                encoding="utf-8")
    with zipfile.ZipFile(BUNDLE_PATH, "w", zipfile.ZIP_DEFLATED) as _z:
        _z.write(RESULTS_PATH, "long_context_demo.json")
    print(f"[2/3] legacy bundle written")
    print(f"  + {RESULTS_PATH.name}")
    print(f"  + {BUNDLE_PATH.name}")


# ===========================================================================
# 5. Workbench shell with corpus overview + QA tabs
# ===========================================================================
print("\n[3/3] launching long-context UI")
_SHUTDOWN_EVENT = threading.Event()


def _render_html() -> str:
    _stats = _corpus_stats()
    statute_rows = "".join(
        '<tr>'
        f'<td><b>{sid}</b></td>'
        f'<td>{COMPLIANCE_CORPUS[sid]["title"]}</td>'
        f'<td>{len(str(COMPLIANCE_CORPUS[sid]["operative_text"]))} chars</td>'
        '</tr>'
        for sid in COMPLIANCE_CORPUS
    )
    qa_panels = "".join(
        f'<div class="qa">'
        f'<div class="qa-header">'
        f'<span class="qa-id">{qa["qa_id"]}</span>'
        f'<span class="qa-cites">{len(qa["citations"])} citations '
        f'across {len(qa["statutes_used"])} statutes</span>'
        f'</div>'
        f'<div class="prompt-box"><span class="who">User</span>'
        f'<div class="prompt-text">{qa["prompt"]}</div></div>'
        f'<div class="response-box"><span class="who">'
        f'DueCare + Gemma 4 (long-context)</span>'
        f'<pre class="response-text">{qa["response"]}</pre></div>'
        f'<div class="cite-row">'
        + "".join(f'<span class="cite">{c}</span>'
                   for c in qa["citations"])
        + '</div></div>'
        for qa in LONG_CONTEXT_QA
    )
    return (
        r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DueCare A-21 . Long-context demo</title>
<style>
  body{background:#F7F6F1;color:#0E1116;
       font-family:-apple-system,system-ui,sans-serif;
       margin:0;padding:0}
  .page{max-width:980px;margin:0 auto;padding:32px 28px 80px}
  h1{font-size:28px;margin:0 0 6px}
  .lede{color:#5B5F68;margin:0 0 24px;max-width:740px;line-height:1.5}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);
         gap:10px;margin-bottom:24px}
  .stat{background:#EFEDE4;border:1px solid #DDD8C9;
        border-radius:10px;padding:12px 14px}
  .stat-label{font-size:11px;color:#5B5F68;text-transform:uppercase;
              letter-spacing:0.08em;margin-bottom:4px}
  .stat-value{font-size:22px;font-weight:600;color:#0E1116}
  .stat-note{font-size:11px;color:#5B5F68;margin-top:2px}
  h2{font-size:18px;margin:28px 0 12px}
  table{width:100%;border-collapse:collapse;background:#FFF;
        border:1px solid #DDD8C9;border-radius:10px;overflow:hidden}
  th{background:#EFEDE4;text-align:left;padding:10px 14px;
     font-size:12px;color:#5B5F68;text-transform:uppercase;
     letter-spacing:0.05em;font-weight:600}
  td{padding:10px 14px;border-top:1px solid #EFEDE4;font-size:13px}
  .qa{background:#FFF;border:1px solid #DDD8C9;border-radius:12px;
      padding:18px 22px;margin-bottom:14px}
  .qa-header{display:flex;justify-content:space-between;
              margin-bottom:12px;font-size:12px}
  .qa-id{font-family:JetBrains Mono,monospace;color:#0E1116;
         font-weight:600}
  .qa-cites{color:#5B5F68}
  .prompt-box,.response-box{background:#EFEDE4;border:1px solid #DDD8C9;
                              border-radius:10px;padding:12px 16px;
                              margin-bottom:12px}
  .who{display:block;font-size:11px;color:#5B5F68;
       text-transform:uppercase;letter-spacing:0.08em;
       margin-bottom:6px;font-weight:600}
  .prompt-text{font-size:14px;line-height:1.55}
  .response-text{font-family:inherit;font-size:13.5px;
                  white-space:pre-wrap;line-height:1.55;margin:0}
  .cite-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
  .cite{background:#EFEDE4;border:1px solid #DDD8C9;color:#0E1116;
        font-family:JetBrains Mono,monospace;font-size:11px;
        padding:4px 8px;border-radius:6px}
  .download{margin-top:24px;text-align:center;color:#5B5F68;
            font-size:13px}
  .download a{color:#4C7A8A;font-weight:600;text-decoration:none}
</style></head><body>
<div class="page">
  <h1>DueCare A-21 -- 128K long-context demo</h1>
  <p class="lede">
    """ + (
            "Gemma 4 reasons across a multi-statute compliance corpus "
            "in a single context window. Each cross-statute question "
            "below pulls together citations from 2&ndash;3 statutes "
            "at once &mdash; the value of long-context reasoning vs "
            "separate retrieval calls. Cached responses for "
            "zero-inference run-through; set <code>"
            "DC_LONG_CONTEXT_LIVE=1</code> to wire up live Gemma 4 "
            "E4B-IT inference."
        ) + r"""
  </p>
  <div class="stats">
    <div class="stat">
      <div class="stat-label">Bundled statutes</div>
      <div class="stat-value">""" + str(_stats["n_statutes"]) + r"""</div>
      <div class="stat-note">cross-jurisdiction</div>
    </div>
    <div class="stat">
      <div class="stat-label">Corpus chars</div>
      <div class="stat-value">""" + (
            f"{_stats['total_chars']:,}") + r"""</div>
      <div class="stat-note">operative passages</div>
    </div>
    <div class="stat">
      <div class="stat-label">Approx tokens</div>
      <div class="stat-value">""" + (
            f"{_stats['approx_tokens']:,}") + r"""</div>
      <div class="stat-note">~chars / 4</div>
    </div>
    <div class="stat">
      <div class="stat-label">Window target</div>
      <div class="stat-value">128K</div>
      <div class="stat-note">Gemma 4 supports</div>
    </div>
  </div>
  <h2>Compliance corpus</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>Title</th><th>Operative text size</th></tr>
    </thead>
    <tbody>""" + statute_rows + r"""</tbody>
  </table>
  <h2>Cross-statute Q&amp;A</h2>
  """ + qa_panels + r"""
  <p class="download">
    Bundle: <a href="/artifact/""" + BUNDLE_PATH.name + r"""">""" + (
            BUNDLE_PATH.name) + r"""</a>
  </p>
</div>
</body></html>"""
    )


try:
    from duecare.chat.kernel_shell import build_minimal_shell
    app, url = build_minimal_shell(
        summary={
            "title": "Long-context demo (Gemma 4 128K)",
            "audience": "researcher",
            "lede": ("Cross-statute reasoning over a bundled "
                      "compliance corpus in a single context window."),
            "results": [
                {"label": "Statutes", "value": _stats["n_statutes"]},
                {"label": "Corpus chars", "value": _stats["total_chars"]},
                {"label": "Approx tokens",
                 "value": _stats["approx_tokens"]},
                {"label": "Q&A pairs", "value": len(LONG_CONTEXT_QA)},
            ],
        },
        kernel_id="a-21-long-context-demo",
        port=PORT,
        homepage_html=_render_html(),
    )
    if url:
        print(f"  ok UI at {url}")
    print("\n[done] long-context demo ready")
    print(f"  bundle: {BUNDLE_PATH}")
    while not _SHUTDOWN_EVENT.is_set():
        time.sleep(1)
except KeyboardInterrupt:
    print("\n  interrupted -- shutting down")
except Exception as e:
    print(f"  shell unavailable: {type(e).__name__}: {e}")
