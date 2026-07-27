#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Getting Started Kaggle notebook: the onboarding hub.

The friendly front door for the whole DueCare project. It has two jobs: (1) get a first-time reader
SET UP -- on Kaggle or in their own code -- in a couple of minutes, and (2) give them a CATALOG of
everything DueCare publishes (analysis notebooks, applied use-case notebooks, advanced surfaces, and
datasets) with a one-line description and a direct Kaggle link for each. It also carries a decision
guide ("I want to ... -> open this"), a tools-at-a-glance table, the reproduce-in-3-lines snippet,
and the trust boundary.

The notebook is FULLY SELF-CONTAINED on Kaggle: no dataset, no model, no internet. The first code
cell embeds the shared DueCare visualization toolkit (scripts/_notebook_viz.py: PALETTE + HELPERS)
plus a small block of light catalog data and a compact, offline `analyze()` indicator scan (a
representative subset of the production 451-rule GREP layer) so every code cell runs on CPU.

    python scripts/build_getting_started_notebook.py

ASCII-only (no Kaggle mojibake). Emitted HTML avoids the Kaggle-viewer-stripped patterns
(no flexbox, no inline scripting, no capped-height scroll boxes, no pinned positioning).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _notebook_viz import HELPERS, PALETTE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "getting_started"
KERNEL_ID = "taylorsamarel/duecare-getting-started"
TITLE = "DueCare Getting Started"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"
DATA_PAGE = "https://duecare-ai.com/data"

# ---------------------------------------------------------------------------
# Cell 1 (first code cell): PALETTE + HELPERS + this light catalog data block.
# Pure ASCII, self-contained, CPU-only. Defines the catalog lists, the URL
# helpers, the Kaggle-safe styled-HTML catalog renderer, and a compact offline
# analyze() so every later code cell runs without a dataset or a model.
# ---------------------------------------------------------------------------
LIGHT_DATA = '''from IPython.display import HTML, Markdown, display

OWNER = "taylorsamarel"
REPO_URL = "https://github.com/TaylorAmarelTech/gemma4_comp"
DATA_PAGE = "https://duecare-ai.com/data"
CODE_BASE = "https://www.kaggle.com/code/" + OWNER
DS_BASE = "https://www.kaggle.com/datasets/" + OWNER

def kurl(slug):
    return CODE_BASE + "/" + slug

def dsurl(slug):
    return DS_BASE + "/" + slug

# The published headline (verified from the duecare-harness-benchmark-grades panel).
HEADLINE = {"lift": 40.7, "pct_improved": 99.8, "n_pairs": 7953, "n_lower": 15, "model": "gemma4:31b"}

# ---- The catalog. Each row: title, kaggle slug, one-line blurb, status, and
# (for notebooks) the dataset to attach. "live" = published; "planned" = on the
# roadmap, not yet published (rendered without a live link so no one clicks a 404).
ANALYSIS = [
    {"t": "Start Here: Harness-Lift Benchmark", "slug": "duecare-harness-lift-benchmark-start-here", "status": "live", "needs": "duecare-harness-benchmark-grades",
     "blurb": "The benchmark front door: the headline result and the cross-model board, recomputed live, with a guided tour of the whole collection."},
    {"t": "Does A Safety Harness Help (flagship)", "slug": "duecare-does-a-safety-harness-help", "status": "live", "needs": "duecare-harness-benchmark-grades",
     "blurb": "The publication-grade walk-through: thirteen sections, dozens of live charts, the +40.7 headline, and the honest counter-evidence."},
    {"t": "Perdim Grades Explorer", "slug": "duecare-perdim-grades-explorer", "status": "live", "needs": "duecare-harness-perdim-grades",
     "blurb": "The exhaustive one-judge-call-per-dimension sweep: per-dimension A-E lift, sliceable by model and judge."},
    {"t": "Cross-Model Leaderboard Deep-Dive", "slug": "duecare-cross-model-leaderboard-deep-dive", "status": "live", "needs": "duecare-harness-benchmark-grades",
     "blurb": "Every model ranked by raw lift and by ceiling-adjusted normalized gain, so a strong baseline is compared fairly with a weak one."},
    {"t": "Harness Grades Data Card", "slug": "duecare-harness-grades-data-card", "status": "live", "needs": "duecare-harness-benchmark-grades",
     "blurb": "What is inside the grades panel: schema, provenance, coverage, and how to load it. Read this before trusting the charts."},
    {"t": "Prompt And Response NLP Explorer", "slug": "duecare-prompt-and-response-nlp-explorer", "status": "live", "needs": "duecare-prompt-response-showcase",
     "blurb": "Text analytics over the prompt/response showcase: length, vocabulary, and refusal / citation markers."},
    {"t": "Prompt Intent And Attack Explorer", "slug": "duecare-prompt-intent-and-attack-explorer", "status": "live", "needs": "duecare-prompt-response-showcase",
     "blurb": "The attack taxonomy: intent, framing, and category coverage of the adversarial prompt set."},
    {"t": "CoT Reasoning Explorer", "slug": "duecare-cot-reasoning-explorer", "status": "live", "needs": "duecare-cot-reasoning",
     "blurb": "Browse the chain-of-thought reasoning traces the harness produces, prompt by prompt."},
    {"t": "CoT Reasoning Analysis", "slug": "duecare-cot-reasoning-analysis", "status": "live", "needs": "duecare-cot-reasoning",
     "blurb": "Quantitative analysis of the reasoning chains: structure, length, and indicator / citation density."},
    {"t": "CoT Reasoning Data Card", "slug": "duecare-cot-reasoning-data-card", "status": "live", "needs": "duecare-cot-reasoning",
     "blurb": "Schema and provenance of the chain-of-thought dataset."},
    {"t": "CoT Direction And Intent Explorer", "slug": "duecare-cot-direction-and-intent-explorer", "status": "live", "needs": "duecare-cot-reasoning",
     "blurb": "Where each reasoning chain points: direction, intent, and refusal geometry."},
    {"t": "Corridor And Sector Atlas", "slug": "duecare-corridor-and-sector-atlas", "status": "live", "needs": "duecare-harness-benchmark-grades",
     "blurb": "Lift mapped across migration corridors and labor sectors, so you can see it holds beyond one geography."},
]

APPLIED = [
    {"t": "NGO Case Triage", "slug": "duecare-ngo-case-triage", "status": "live", "needs": "none",
     "blurb": "Paste a worker account, get an ILO-grounded triage: indicators, risk level, evidence gaps, next steps, referrals, and a draft note. Offline."},
    {"t": "Platform Moderation At Scale", "slug": "duecare-platform-moderation-at-scale", "status": "live", "needs": "none",
     "blurb": "Screen risky recruitment posts and ads into a review queue with a reason for every decision. Offline."},
    {"t": "Worker Self Check", "slug": "duecare-worker-self-check", "status": "live", "needs": "none",
     "blurb": "A worker pastes a suspicious message and gets a plain-language warning and next steps. Offline."},
    {"t": "Chain Of Thought Generator", "slug": "duecare-chain-of-thought-generator", "status": "live", "needs": "none",
     "blurb": "Turn a prompt into a structured, ILO-grounded reasoning chain. Offline."},
    {"t": "Regulator Compliance", "slug": "duecare-regulator-compliance", "status": "planned", "needs": "none",
     "blurb": "Compliance-monitoring view for labor ministries and regulators: corridor rules, fee caps, and an evidence trail."},
    {"t": "Developer Integration", "slug": "duecare-developer-integration", "status": "planned", "needs": "none",
     "blurb": "The software-to-software path: call the harness from your own code, structured request in and structured analysis out."},
]

ADVANCED = [
    {"t": "The Entire System", "slug": "duecare-the-entire-system", "status": "planned", "needs": "none",
     "blurb": "End-to-end tour of the whole DueCare substrate: runtime, harness layers, knowledge, training, and judging."},
    {"t": "Semantic Landscape", "slug": "duecare-semantic-landscape", "status": "planned", "needs": "none",
     "blurb": "An embedding-space map of the prompt and knowledge corpus: clusters, gaps, and coverage."},
    {"t": "Cross-Industry Capabilities", "slug": "duecare-cross-industry-capabilities", "status": "planned", "needs": "none",
     "blurb": "The same harness across domains beyond trafficking (tax evasion, financial crime, and more)."},
    {"t": "Knowledge Base Explorer", "slug": "duecare-knowledge-base-explorer", "status": "planned", "needs": "none",
     "blurb": "Browse the GREP rules, the RAG corpus, the ILO instruments, and the corridor fee-caps behind the harness."},
]

DATASETS = [
    {"t": "Harness Benchmark Grades", "slug": "duecare-harness-benchmark-grades", "status": "live",
     "blurb": "The judged panel: one 0-100 score per (model, arm, prompt, judge) plus five A-E components. Scores only, no response text, no PII."},
    {"t": "Harness Perdim Grades", "slug": "duecare-harness-perdim-grades", "status": "live",
     "blurb": "The exhaustive one-judge-call-per-dimension scores, re-versioned as the sweep grows."},
    {"t": "Prompt Response Showcase", "slug": "duecare-prompt-response-showcase", "status": "live",
     "blurb": "Representative prompt / response pairs that feed the NLP and intent explorers."},
    {"t": "CoT Reasoning", "slug": "duecare-cot-reasoning", "status": "live",
     "blurb": "Chain-of-thought reasoning traces distilled from the benchmark."},
    {"t": "Cross-Model Harness Leaderboard", "slug": "duecare-cross-model-harness-leaderboard", "status": "live",
     "blurb": "A citable flat CSV of the cross-model board: lift, normalized gain, and win rate per model."},
    {"t": "Harness Lift Controls", "slug": "duecare-harness-lift-controls", "status": "live",
     "blurb": "The placebo, negative-control, and applicability-audit results. Scores only, no PII."},
    {"t": "Measured Review Curriculum 200k", "slug": "duecare-measured-review-curriculum-200k", "status": "live",
     "blurb": "The training curriculum distilled from the benchmark (SFT / DPO rows). The committed 74,640-row seed corpus lives in the repo."},
]

# ---- Kaggle-safe styled-HTML catalog table. Inline styles only; it avoids the
# Kaggle-viewer-stripped patterns (no flexbox, no inline scripting, no capped
# scroll boxes, no pinned positioning). Live rows link out; planned rows render
# as muted text with a "not yet published" note so nothing 404s.
def _pill(status):
    if status == "live":
        return '<span style="background:#e6f0ec;color:#1f5a66;border:1px solid #cfe3e6;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:700">live</span>'
    return '<span style="background:#f0e7dd;color:#8a5a2e;border:1px solid #e6d3bf;border-radius:10px;padding:1px 8px;font-size:11px;font-weight:700">planned</span>'

def _cell_title(row, base):
    if row["status"] == "live":
        return '<a href="' + base + "/" + row["slug"] + '" style="color:#1f5a66;font-weight:700;text-decoration:none">' + row["t"] + '</a>'
    return '<span style="color:#5B5F68;font-weight:700">' + row["t"] + '</span> <span style="color:#8A8E97;font-size:11px">(not yet published)</span>'

def catalog_html(rows, kind="code", caption=""):
    base = CODE_BASE if kind == "code" else DS_BASE
    parts = []
    if caption:
        parts.append('<div style="font-weight:700;color:#14181B;font-family:Inter,system-ui,sans-serif;margin:6px 0 4px 0;font-size:14px">' + caption + '</div>')
    parts.append('<table style="width:100%;border-collapse:collapse;font-family:Inter,system-ui,sans-serif;margin:2px 0 12px 0">')
    parts.append('<thead><tr>'
                 '<th style="background:#EFEDE4;color:#14181B;border-bottom:2px solid #2f7d8c;padding:8px 12px;text-align:left;width:34%">Surface</th>'
                 '<th style="background:#EFEDE4;color:#14181B;border-bottom:2px solid #2f7d8c;padding:8px 12px;text-align:left">What it is</th>'
                 '</tr></thead><tbody>')
    for row in rows:
        parts.append('<tr>'
                     '<td style="padding:8px 12px;border-bottom:1px solid #E8E4D7;vertical-align:top">' + _cell_title(row, base) + '<br>' + _pill(row["status"]) + '</td>'
                     '<td style="padding:8px 12px;border-bottom:1px solid #E8E4D7;vertical-align:top;color:#2A2D34;font-size:13px">' + row["blurb"] + '</td>'
                     '</tr>')
    parts.append('</tbody></table>')
    return "".join(parts)

# ---- A compact, offline forced-labour indicator scan. Representative subset of
# the production 451-rule GREP layer: deterministic, on-device, no model, no net.
_ANALYZE_PATTERNS = [
    ("passport_retention", "passport / ID retention", "ILO C029", ["passport", "id card", "took my papers", "keep my documents", "keeps our documents"]),
    ("wage_withholding", "wage withholding", "ILO C095", ["not been paid", "not paid", "unpaid", "withheld my wages", "no salary"]),
    ("debt_bondage", "debt bondage", "ILO C029", ["recruitment fee", "placement fee", "pay off the debt", "work off the", "repaying the debt"]),
    ("restricted_movement", "restricted movement", "ILO C029", ["not allowed to leave", "cannot leave", "locked", "no day off"]),
    ("threats", "threats / intimidation", "ILO C029", ["threatened", "report to immigration", "report us to immigration", "deport", "call the police"]),
    ("excessive_overtime", "excessive overtime", "ILO C029", ["seven days a week", "no rest", "very long hours", "long days"]),
    ("isolation", "isolation", "ILO C029", ["phone was taken", "cannot contact", "no contact with my family", "took my phone"]),
    ("contract_substitution", "contract substitution", "ILO C181", ["promised one wage", "different contract", "changed the contract", "paid a different amount"]),
]

def analyze(text):
    """Representative, offline forced-labour indicator scan.

    Returns a dict: text, n_indicators, risk_level, risk_reason, indicators (each with the ILO label,
    the matched cue, and the controlling instrument). Deterministic and on-device -- a compact subset
    of the production 451-rule GREP layer. In production the full harness adds retrieval and Gemma 4
    reasoning; the applied use-case notebooks expose triage() / moderate() / check() / generate_chain().
    """
    low = " " + " ".join(str(text).lower().split()) + " "
    hits = []
    for indicator, label, ref, cues in _ANALYZE_PATTERNS:
        for cue in cues:
            if cue in low:
                hits.append({"indicator": indicator, "label": label, "ilo_ref": ref, "cue": cue})
                break
    n = len(hits)
    level = "HIGH" if n >= 4 else "ELEVATED" if n >= 2 else "WATCH" if n == 1 else "LOW"
    reason = (str(n) + " forced-labour indicator" + ("" if n == 1 else "s") + " matched") if n else "no indicators matched (absence is not evidence of safety)"
    return {"text": text, "n_indicators": n, "risk_level": level, "risk_reason": reason, "indicators": hits}

_RISK_COLOR = {"HIGH": EMBER, "ELEVATED": WARN, "WATCH": WARN, "LOW": GOOD}

def show_analysis(text):
    """Run analyze() and render it: a risk stat card + the detected-indicator table."""
    res = analyze(text)
    print("TEXT:")
    print(text)
    print()
    stat_cards([(res["risk_level"], "risk level", _RISK_COLOR[res["risk_level"]]),
                (res["n_indicators"], "indicators", TEAL)])
    if res["indicators"]:
        df = pd.DataFrame([{"ILO indicator": h["label"], "matched cue": h["cue"], "instrument": h["ilo_ref"]} for h in res["indicators"]])
        display(pretty_table(df, caption="Indicators found by the embedded offline scan (a subset of the 451-rule harness)"))
    else:
        print("No indicators matched. Absence is not evidence of safety.")
    return res

print("DueCare Getting Started - setup ready.")
print("Catalog:", len(ANALYSIS), "analysis +", len(APPLIED), "applied +", len(ADVANCED), "advanced surfaces;", len(DATASETS), "datasets.")
_smoke = analyze("the employer took my passport and I have not been paid for two months")
print("analyze() smoke ->", _smoke["risk_level"], "|", [h["indicator"] for h in _smoke["indicators"]])'''

# ---------------------------------------------------------------------------
# Cell 3: the one headline, as stat cards + an honest 99.8%-improved bar.
# ---------------------------------------------------------------------------
HEADLINE_CODE = '''stat_cards([
    ("+40.7", "mean lift (/100)", EMBER),
    ("99.8%", "prompts improved", GOOD),
    ("7,953", "paired prompts", TEAL),
    ("~1.7", "Cohen's d (large)", INK2),
])
fig, ax = plt.subplots(figsize=(9.6, 1.7))
ax.barh(["paired prompts"], [HEADLINE["pct_improved"]], color=GOOD, label="improved")
ax.barh(["paired prompts"], [100 - HEADLINE["pct_improved"]], left=[HEADLINE["pct_improved"]], color=EMBER,
        label="scored lower (" + str(HEADLINE["n_lower"]) + " prompts)")
ax.text(101, 0, str(HEADLINE["pct_improved"]) + "% improved", va="center", color=INK2, fontweight="bold", fontsize=10.5)
ax.set(xlabel="share of paired prompts (%)", xlim=(0, 120)); ax.set_yticks([]); ax.grid(axis="y", alpha=0)
_title(ax, "Wrapping a model in the DueCare harness improves almost every prompt",
       "headline model " + HEADLINE["model"] + ": +40.7 / 100 mean lift over 7,953 paired prompts; only 15 scored lower")
ax.legend(loc="lower right", fontsize=9); plt.tight_layout(); plt.show()'''

# ---------------------------------------------------------------------------
# Cell 6: notebook -> required dataset table (setup, "Add data" step).
# ---------------------------------------------------------------------------
NEEDS_CODE = '''rows = []
for r in ANALYSIS:
    rows.append({"notebook": r["t"], "attach this dataset": r["needs"]})
for r in APPLIED:
    if r["status"] == "live":
        rows.append({"notebook": r["t"], "attach this dataset": "none (self-contained)"})
rows.append({"notebook": "DueCare Getting Started (this notebook)", "attach this dataset": "none (self-contained)"})
needs = pd.DataFrame(rows)
display(pretty_table(needs, caption="Which dataset each notebook needs -- Add data, search 'duecare', attach the one named here, then Run All"))
print("Tip: the applied use-case notebooks need no dataset at all -- just open and Run All.")'''

# ---------------------------------------------------------------------------
# Cell 8: the embedded analyze() demo (the runnable local snippet).
# ---------------------------------------------------------------------------
ANALYZE_DEMO = '''# The embedded offline analyze() -- runs right here on CPU, no install, no dataset, no model.
_ = show_analysis("I travelled abroad for a domestic job. On arrival the employer took my passport, "
                  "I have not been paid for three months, and I am told I must first work off the "
                  "recruitment fee. I am not allowed to leave the house and there is no day off.")'''

# ---------------------------------------------------------------------------
# Cell 10: requirements table (CPU is enough; GPU only for model-backed runs).
# ---------------------------------------------------------------------------
REQ_CODE = '''req = pd.DataFrame({
    "you want to run": ["Analysis notebooks (charts from datasets)", "Applied use-case notebooks",
                        "This Getting Started hub", "Model-backed / live-inference notebooks",
                        "Fine-tuning / training notebooks"],
    "accelerator": ["CPU is enough", "CPU is enough", "CPU is enough", "GPU (T4)", "GPU / TPU"],
    "internet": ["off", "off", "off", "usually off", "on (to pull weights)"],
    "dataset": ["attach one (see table above)", "none", "none", "none / a model source", "a training dataset"],
})
display(pretty_table(req, caption="What you need: CPU is enough for analysis and use-case notebooks; a GPU is only for model-backed runs"))'''

# ---------------------------------------------------------------------------
# Cells 13/15/17/19: the four catalog groups (styled HTML, clickable).
# ---------------------------------------------------------------------------
CAT_ANALYSIS = '''display(HTML(catalog_html(ANALYSIS, "code", "Analysis notebooks -- the evidence: does the harness help, and where?")))'''
CAT_APPLIED = '''display(HTML(catalog_html(APPLIED, "code", "Applied use cases -- self-contained, offline products for a real reader")))'''
CAT_ADVANCED = '''display(HTML(catalog_html(ADVANCED, "code", "Advanced -- deeper structural tours (roadmap surfaces marked planned)")))'''
CAT_DATASETS = '''display(HTML(catalog_html(DATASETS, "dataset", "Datasets -- scores and labels only, no response text, no PII")))'''

# ---------------------------------------------------------------------------
# Cell 21: the decision guide ("I want to ... -> open this").
# ---------------------------------------------------------------------------
GUIDE_CODE = '''guide = pd.DataFrame({
    "I want to...": [
        "see the one headline result fast",
        "read the full, rigorous benchmark",
        "rank the models against each other",
        "see per-dimension (A-E) detail",
        "understand the data before I trust it",
        "triage a real worker account",
        "moderate recruitment posts at scale",
        "check one suspicious message (as a worker)",
        "generate an ILO-grounded reasoning chain",
        "browse the reasoning traces",
        "map lift by corridor and sector",
        "call DueCare from my own code",
    ],
    "open this": [
        "Start Here: Harness-Lift Benchmark",
        "Does A Safety Harness Help (flagship)",
        "Cross-Model Leaderboard Deep-Dive",
        "Perdim Grades Explorer",
        "Harness Grades Data Card",
        "NGO Case Triage",
        "Platform Moderation At Scale",
        "Worker Self Check",
        "Chain Of Thought Generator",
        "CoT Reasoning Explorer",
        "Corridor And Sector Atlas",
        "Developer Integration (planned) / the repo",
    ],
})
display(pretty_table(guide, caption="Which notebook for which need -- find your row, open the surface named on the right"))'''

# ---------------------------------------------------------------------------
# Cell 23: the tools at a glance + a live analyze() call.
# ---------------------------------------------------------------------------
TOOLS_CODE = '''tools = pd.DataFrame({
    "function": ["analyze(text)", "triage(account)", "moderate(post)", "check(message)", "generate_chain(prompt)"],
    "what it returns": [
        "indicators found + risk level (embedded in THIS notebook, offline)",
        "a full case: indicators, evidence gaps, next steps, referrals, and a draft note",
        "a moderation decision + a reason for a recruitment post or ad",
        "a plain-language warning + next steps for one worker message",
        "a structured, ILO-grounded reasoning chain for a prompt",
    ],
    "where to find it": [
        "this notebook (Section 4)",
        "NGO Case Triage",
        "Platform Moderation At Scale",
        "Worker Self Check",
        "Chain Of Thought Generator",
    ],
})
display(pretty_table(tools, caption="The DueCare tools at a glance -- analyze() is embedded here; the rest live in the use-case notebooks"))

# analyze() live on a second composite account (a fishing-vessel case):
_ = show_analysis("I was recruited onto a fishing boat. The broker charged me a large placement fee and I am "
                  "still repaying the debt. We stay at sea for weeks, my phone was taken, and the captain keeps "
                  "our documents on board.")'''

# ---------------------------------------------------------------------------
# Cell 26: trust boundary + closing stat cards + final handoff print.
# ---------------------------------------------------------------------------
BOUNDARY_CODE = '''flow = pd.DataFrame({
    "surface": ["Applied use-case notebooks", "Published datasets", "This Getting Started hub"],
    "what it handles": ["worker text you paste (composite / test data only)",
                        "scores and labels only -- no response text, no PII",
                        "a static catalog plus a tiny offline indicator scan"],
    "leaves the machine?": ["never (pure local Python)", "already public, contains no PII", "never"],
})
display(pretty_table(flow, caption="Trust boundary -- what stays local"))
stat_cards([("0", "bytes leave by default", GOOD), ("local", "where analyze() runs", TEAL), ("MIT", "license", INK2)])
print("Go deeper:")
print("  Start Here  ->", kurl("duecare-harness-lift-benchmark-start-here"))
print("  Flagship    ->", kurl("duecare-does-a-safety-harness-help"))
print("  Data page   ->", DATA_PAGE)
print("  Repository  ->", REPO_URL)
print()
print("Getting Started >>> open Start Here for the benchmark, or an applied use-case notebook to try the tools offline.")'''


def _toc() -> str:
    items = [
        ("1", "Setup instructions (Kaggle and your own code)", "setup"),
        ("2", "The catalog: every published surface", "catalog"),
        ("3", "Which notebook for which need", "need"),
        ("4", "The tools at a glance", "tools"),
        ("5", "Reproduce the headline in three lines", "reproduce"),
        ("6", "Trust boundary and where to go deeper", "deeper"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c: list = []

    # ---- Section 0: hero + what DueCare is + the one headline + TOC ----
    c.append(md(
        "# DueCare Getting Started\n\n"
        "**The onboarding hub for the DueCare project.** DueCare tests whether a thin, model-agnostic "
        "legal-grounding layer -- fired indicator rules, retrieved law, and deterministic tools, added to "
        "the prompt and nothing else -- makes any LLM safer and more useful for migrant-worker "
        "anti-trafficking. It does not touch the model's weights; it changes what the model is given, then "
        "measures the difference with a panel of independent judges across five reasoned safety dimensions. "
        "The result is large and consistent: wrapping a model in the DueCare harness lifts it **+40.7 / 100** "
        "on the safety rubric and improves **99.8%** of prompts.\n\n"
        "This notebook is the front door. It has two jobs: (1) get you **set up** -- on Kaggle or in your own "
        "code -- in a couple of minutes, and (2) give you a **map of everything** DueCare publishes, with a "
        "one-line description and a direct link for each surface, so you can jump straight to what you need.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> Everything in this notebook runs on **CPU with no dataset attached**. The catalog links out to the "
        "individual notebooks; each analysis notebook says which public dataset to attach. All data here is "
        "composite / synthetic -- no real people, no real PII."))

    # ---- Setup cell (first code cell): PALETTE + HELPERS + light catalog data ----
    c.append(md(
        "## Setup -- run this cell first\n\n"
        "The first code cell embeds the shared DueCare visualization toolkit (the paper / ink / teal theme, "
        "`stat_cards`, and `pretty_table`) plus a small block of catalog data and a compact, offline "
        "`analyze()` indicator scan. After it runs once, every other cell is self-contained: **no dataset, no "
        "model, no internet.**"))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + LIGHT_DATA))

    # ---- The one headline ----
    c.append(md(
        "### The one headline\n\n"
        "One number carries the whole project: a thin grounding layer lifts the headline model **+40.7 out of "
        "100** on the safety rubric, over **7,953 paired prompts**, improving **99.8%** of them (only 15 scored "
        "lower). The effect is large (Cohen's d about 1.7), and it holds for every model and every judge. The "
        "full evidence, recomputed live, is in the flagship and Start Here notebooks in the catalog below."))
    c.append(code(HEADLINE_CODE))

    # ---- Section 1: SETUP INSTRUCTIONS ----
    c.append(md(
        '<a id="setup"></a>\n## 1 - Setup instructions\n\n'
        "Two audiences, two paths. Pick the one that fits you."))
    c.append(md(
        "### 1A - On Kaggle (the easy path)\n\n"
        "1. **Open** the notebook you want from the catalog in Section 2 (each title links straight to it on "
        "Kaggle).\n"
        "2. Click **Copy & Edit** (top right) to get your own editable copy.\n"
        "3. If the notebook needs data, open the right sidebar, click **Add Input** (or **Add data**), "
        "**search `duecare`**, and attach the dataset the notebook asks for -- the table below maps each "
        "notebook to its dataset.\n"
        "4. Click **Run All**. Analysis and use-case notebooks finish in seconds to a few minutes on the "
        "default **CPU** machine -- no GPU, no internet, and no API key.\n\n"
        "The applied use-case notebooks (NGO Case Triage, Platform Moderation, Worker Self Check, Chain Of "
        "Thought Generator) are fully self-contained: they need **no dataset at all** -- just open and Run All."))
    c.append(code(NEEDS_CODE))
    c.append(md(
        "### 1B - In your own code\n\n"
        "Install the DueCare packages and call the harness from Python:\n\n"
        "```bash\n"
        "pip install duecare-llm-core duecare-llm-chat\n"
        "```\n\n"
        "or install the latest straight from source:\n\n"
        "```bash\n"
        "pip install \"git+https://github.com/TaylorAmarelTech/gemma4_comp\"\n"
        "```\n\n"
        "A minimal analysis call looks like this (a compact, offline version of `analyze()` is embedded in "
        "this notebook, so you can run it right here without installing anything):\n\n"
        "```python\n"
        "from duecare.chat import analyze          # the production entry point\n"
        "result = analyze(\"the employer took my passport and I have not been paid for two months\")\n"
        "print(result[\"risk_level\"], result[\"indicators\"])\n"
        "```\n\n"
        "To work with the published data instead, point pandas at any attached dataset:\n\n"
        "```python\n"
        "import pandas as pd, glob\n"
        "grades = pd.read_csv(glob.glob(\"/kaggle/input/**/panel_grades.csv\", recursive=True)[0])\n"
        "```\n\n"
        "The cell below runs the **embedded** offline `analyze()` on a composite worker account so you can see "
        "the shape of the result immediately."))
    c.append(code(ANALYZE_DEMO))
    c.append(md(
        "### 1C - Requirements\n\n"
        "**CPU is enough** for every analysis and use-case notebook in this hub -- they read published score "
        "tables and run deterministic Python. You only need a **GPU** for the model-backed notebooks that "
        "actually load Gemma 4 for live inference, and a **GPU or TPU** for the fine-tuning notebooks."))
    c.append(code(REQ_CODE))

    # ---- Section 2: THE CATALOG ----
    c.append(md(
        '<a id="catalog"></a>\n## 2 - The catalog: every published surface\n\n'
        "Everything DueCare publishes, grouped into four shelves. **Live** surfaces link straight to Kaggle; a "
        "few surfaces marked **planned** are on the roadmap and not yet published (they are shown without a "
        "link so nothing 404s). Slugs match the titles, so a link is just "
        "`kaggle.com/code/taylorsamarel/<slug>`."))
    c.append(md("### 2A - Analysis\n\nThe evidence layer: does the harness help, by how much, and where?"))
    c.append(code(CAT_ANALYSIS))
    c.append(md("### 2B - Applied use cases\n\nSelf-contained, offline products aimed at a specific reader -- a caseworker, a platform, a worker, a developer."))
    c.append(code(CAT_APPLIED))
    c.append(md("### 2C - Advanced\n\nDeeper structural tours of the system and its knowledge (roadmap surfaces are marked planned)."))
    c.append(code(CAT_ADVANCED))
    c.append(md("### 2D - Datasets\n\nThe public data behind the analysis notebooks -- scores and labels only, never response text or PII."))
    c.append(code(CAT_DATASETS))

    # ---- Section 3: WHICH NOTEBOOK FOR WHICH NEED ----
    c.append(md(
        '<a id="need"></a>\n## 3 - Which notebook for which need\n\n'
        "A decision guide. Find the row that matches what you are trying to do, and open the surface named on "
        "the right (its link is in the catalog above)."))
    c.append(code(GUIDE_CODE))

    # ---- Section 4: THE TOOLS ----
    c.append(md(
        '<a id="tools"></a>\n## 4 - The tools at a glance\n\n'
        "The applied notebooks each expose one easy entry point. They share the same grounded engine; each "
        "returns a structured result you can render, store, or hand-review. `analyze()` is embedded in this "
        "notebook (it ran in Section 1B and runs again below); the others live one click away in the use-case "
        "notebooks."))
    c.append(code(TOOLS_CODE))

    # ---- Section 5: REPRODUCE THE HEADLINE ----
    c.append(md(
        '<a id="reproduce"></a>\n## 5 - Reproduce the headline in three lines\n\n'
        "The +40.7 headline is not asserted -- it is recomputed from the public grades panel. Attach the "
        "[`duecare-harness-benchmark-grades`](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades) "
        "dataset to any notebook and run:\n\n"
        "```python\n"
        "import pandas as pd, glob\n"
        "g = pd.read_csv(glob.glob(\"/kaggle/input/**/panel_grades.csv\", recursive=True)[0])\n"
        "d = g[g.model == \"gemma4:31b\"].groupby([\"prompt_id\", \"arm\"]).score_0_100.mean().unstack()\n"
        "print((d[\"harness_core\"] - d[\"baseline\"]).mean())   # about +40.7\n"
        "```\n\n"
        "Average the three judges per (prompt, arm), pair harness_core against baseline per prompt, and take "
        "the mean. The flagship and Start Here notebooks do exactly this, then break it down by model, judge, "
        "dimension, difficulty, corridor, and category -- and list every prompt the harness did not help."))

    # ---- Section 6: TRUST BOUNDARY + WHERE TO GO DEEPER ----
    c.append(md(
        '<a id="deeper"></a>\n## 6 - Trust boundary and where to go deeper\n\n'
        "DueCare is built so the most sensitive data -- a worker's own words -- never has to leave the "
        "machine. The applied notebooks run as pure local Python; the published datasets are scores and labels "
        "only, with no response text and no PII. This hub itself only renders a static catalog and a tiny "
        "offline scan.\n\n"
        "- **The data page:** [duecare-ai.com/data](https://duecare-ai.com/data) collects the knowledge "
        "surfaces and the benchmark data in one place.\n"
        "- **The source:** the [repository](https://github.com/TaylorAmarelTech/gemma4_comp) has the harness, "
        "the grader, the fine-tuning path, and the exhaustive per-dimension sweep.\n\n"
        "**Honest boundary.** The benchmark measures **LLM-judge rubric scores over synthetic / composite "
        "prompts** -- improved *tested behaviour* (indicator naming, legal citation, refusal discipline, "
        "resource routing, privacy), not a claim of real-world detection. The judges are language models, not "
        "anti-trafficking professionals. License: MIT."))
    c.append(code(BOUNDARY_CODE))

    nb = nbf.v4.new_notebook()
    nb["cells"] = c
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                      "language_info": {"name": "python"}}
    nbf.write(nb, str(nb_dir / "notebook.ipynb"))

    meta = {"id": KERNEL_ID, "title": TITLE, "code_file": "notebook.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": False, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"kernel_id": KERNEL_ID, "title": TITLE, "cells": len(c),
            "code_cells": sum(1 for x in c if x.cell_type == "code"), "notebook_dir": str(nb_dir)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    summary = build(args.output, force=args.force)
    slug = summary["kernel_id"].split("/", 1)[1]
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    assert slug == "duecare-getting-started", f"unexpected slug: {slug!r}"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
