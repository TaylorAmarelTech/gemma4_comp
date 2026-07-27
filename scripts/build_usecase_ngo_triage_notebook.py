#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare NGO Case Triage Kaggle notebook.

An applied, easy-to-use notebook for the NGO caseworker / hotline responder: paste a migrant
worker's account and get a structured, ILO-grounded triage -- the forced-labour indicators it
contains, the risk level, which of the ILO indicators are present vs absent, the evidence gaps
(with the follow-up question to ask), concrete next steps, referral resources, and a draft
complaint-note stub grounded in the cited ILO instruments.

The notebook is FULLY SELF-CONTAINED on Kaggle: no dataset, no model, no internet. The first code
cell embeds two builder-time toolkits -- the shared DueCare notebook visualization helpers
(scripts/_notebook_viz.py) AND the grounded DueCare indicator engine (scripts/_usecase_engine.py:
scan / risk_level / generate_chain plus the ILO knowledge maps). It is a REPRESENTATIVE,
deterministic subset of the real 451-rule GREP layer + ILO knowledge packs; production uses the
full harness with retrieval and Gemma 4 reasoning.

    python scripts/build_usecase_ngo_triage_notebook.py

ASCII-only (no Kaggle mojibake). No [:N] truncation of any displayed account or result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _notebook_viz import HELPERS, PALETTE  # noqa: E402
from _usecase_engine import ENGINE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "usecase_ngo_triage"
KERNEL_ID = "taylorsamarel/duecare-ngo-case-triage"
TITLE = "DueCare NGO Case Triage"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

# ---------------------------------------------------------------------------
# Cell 4: the triage() entry point + renderers. Pure, deterministic, offline.
# ---------------------------------------------------------------------------
TRIAGE_DEFS = '''# The easy-to-use entry point. triage() is pure + deterministic; the render_* helpers draw it.
RISK_COLOR = {"HIGH": EMBER, "ELEVATED": WARN, "WATCH": WARN, "LOW": GOOD}
_QMAP = dict(INDICATOR_QUESTIONS)   # indicator -> the follow-up question to ask

def _next_steps(level, hits):
    """3-5 concrete caseworker actions, tuned to which indicators fired."""
    inds = {h["indicator"] for h in hits}
    steps = ["Record the worker's account verbatim in a secure case file: dates, places, names, and amounts."]
    if "document_retention" in inds:
        steps.append("Establish who physically holds the worker's passport / ID and on what basis (document retention is an ILO C029 indicator).")
    if "recruitment_fee" in inds:
        steps.append("Itemise every fee and deduction and compare to the corridor fee cap: worker-paid recruitment fees breach ILO C181 Art.7.")
    if ("wage_withholding" in inds) or ("debt_bondage" in inds):
        steps.append("Reconstruct the wage-and-debt ledger (promised vs paid vs deducted) to test for wage withholding or debt bondage.")
    steps.append("Ask the targeted follow-up questions under 'evidence gaps' to confirm or rule out the ambiguous indicators.")
    if level in ("HIGH", "ELEVATED"):
        steps.append("Escalate to a supervisor and prepare a referral to the appropriate hotline / labour attache (see referral resources).")
    else:
        steps.append("Keep the case open and schedule a follow-up: the absence of indicators in one message is not evidence of safety.")
    return steps[:5]

def _draft_note(hits, level):
    """A short, citation-grounded complaint-note stub for caseworker review (not a legal determination)."""
    if not hits:
        return ("Draft note (composite, for review): on the information provided, no forced-labour indicators from "
                "the ILO framework were clearly present. Absence of indicators in a single account is not evidence "
                "of safety -- ask the follow-up questions and keep the case open.")
    refs = sorted({h["ilo_ref"] for h in hits})
    labels = [h["label"] for h in hits]
    return ("Draft note (composite, for caseworker review -- verify the facts before filing): the worker's account "
            "raises a " + level + " concern. Indicators observed: " + "; ".join(labels) + ". These engage the "
            "following instruments: " + " | ".join(refs) + ". Recommend documenting each indicator with dates and "
            "amounts, confirming document custody and the fee/debt ledger, and routing the worker to the referral "
            "resources below. This note states concerns and citations only; it is not a legal determination.")

def triage(worker_account):
    """Triage a migrant worker's account into a structured, ILO-grounded case summary.

    Returns a dict with: risk_level / risk_reason, detected_indicators (each carrying the ILO label,
    the matched cue, and the controlling instrument), which of the ILO indicators are present vs
    absent, evidence_gaps (ambiguous / absent indicators paired with the follow-up question to ask),
    3-5 recommended_next_steps, referral_resources, and a citation-grounded draft_complaint_note.
    Deterministic, offline, CPU-only -- a representative subset of the DueCare harness.
    """
    hits = scan(worker_account)
    level, why = risk_level(hits)
    present_set = {h["indicator"] for h in hits}
    indicators_present = [{"indicator": i, "label": ILO_INDICATORS[i], "ilo_ref": ILO_REFS.get(i, "ILO 2012")}
                          for i in ILO_INDICATORS if i in present_set]
    indicators_absent = [i for i in ILO_INDICATORS if i not in present_set]
    evidence_gaps = [{"indicator": i, "label": ILO_INDICATORS[i], "follow_up": _QMAP[i]} for i in indicators_absent]
    return {
        "risk_level": level,
        "risk_reason": why,
        "n_indicators": len(hits),
        "detected_indicators": hits,
        "indicators_present": indicators_present,
        "indicators_absent": indicators_absent,
        "evidence_gaps": evidence_gaps,
        "recommended_next_steps": _next_steps(level, hits),
        "referral_resources": HOTLINES,
        "draft_complaint_note": _draft_note(hits, level),
    }

# ---- rendering: a risk stat card + a detected-indicator table + a present/absent bar ----
def indicator_bar(res, title="ILO forced-labour indicators: present vs not evident", subtitle=None):
    inds = list(ILO_INDICATORS.keys()); labels = [ILO_INDICATORS[i] for i in inds]
    present = {d["indicator"] for d in res["detected_indicators"]}
    vals = [1 if i in present else 0 for i in inds]
    y = np.arange(len(inds)); fig, ax = plt.subplots(figsize=(9.8, 0.42 * len(inds) + 1.5))
    ax.barh(y, [1] * len(inds), color=PAPER3, edgecolor=PAPER, linewidth=0.8, zorder=1)
    ax.barh(y, vals, color=[EMBER if v else PAPER3 for v in vals], edgecolor=PAPER, linewidth=0.8, zorder=2)
    for yi, v in zip(y, vals):
        ax.text(1.03, yi, "PRESENT" if v else "not evident", va="center", fontsize=8.5,
                color=EMBER if v else INK4, fontweight="bold" if v else "normal")
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.invert_yaxis()
    ax.set_xlim(0, 1.35); ax.set_xticks([]); ax.grid(False)
    _title(ax, title, subtitle or (res["risk_level"] + " -- " + res["risk_reason"]))
    plt.tight_layout(); plt.show()

def _risk_card(res):
    stat_cards([(res["risk_level"], "risk level", RISK_COLOR.get(res["risk_level"], INK2)),
                (res["n_indicators"], "indicators flagged", TEAL),
                (len(res["evidence_gaps"]), "follow-ups to ask", INK2)])

def _detected_table(res):
    if res["detected_indicators"]:
        det = pd.DataFrame([{"ILO indicator": d["label"], "matched cue": d["snippet"], "controlling instrument": d["ilo_ref"]}
                            for d in res["detected_indicators"]])
        display(pretty_table(det, caption="Detected forced-labour indicators -- the matched cue and the ILO instrument it engages"))
    else:
        print("No forced-labour indicators were detected in this account (LOW). Absence is not evidence of safety -- ask the follow-ups.")

def render_triage(account, res=None):
    """Risk card + detected-indicator table + present/absent bar (the compact worked-example view)."""
    res = res or triage(account)
    print("WORKER ACCOUNT:"); print(account); print()
    _risk_card(res); _detected_table(res); indicator_bar(res)
    return res

def render_case(account, res=None):
    """The full case view: render_triage + evidence gaps + next steps + referral resources + draft note."""
    res = render_triage(account, res)
    gaps = res["evidence_gaps"]
    if gaps:
        gdf = pd.DataFrame([{"ambiguous / absent indicator": g["label"], "follow-up question to ask": g["follow_up"]} for g in gaps])
        display(pretty_table(gdf, caption="Evidence gaps -- indicators not yet evident, with the question a caseworker should ask next"))
    print("RECOMMENDED NEXT STEPS:")
    for i, s in enumerate(res["recommended_next_steps"], 1):
        print("  " + str(i) + ". " + s)
    print()
    rdf = pd.DataFrame([{"region": k, "referral": v} for k, v in res["referral_resources"].items() if k != "note"])
    display(pretty_table(rdf, caption="Referral resources (verify the current in-country number before use -- see note)"))
    print("NOTE:", res["referral_resources"]["note"]); print()
    print("DRAFT COMPLAINT NOTE (composite -- for caseworker review):"); print(res["draft_complaint_note"])
    return res

print("triage() ready. Tracking", len(ILO_INDICATORS), "ILO indicators;",
      len(PATTERNS), "demo indicator rules;", len(FEE_CAMOUFLAGE), "fee-camouflage labels.")
_smoke = triage("the employer took my passport and I have not been paid for two months")
print("smoke ->", "risk:", _smoke["risk_level"], "| indicators:", [d["indicator"] for d in _smoke["detected_indicators"]])'''

# ---------------------------------------------------------------------------
# Cell 6: TRY YOUR OWN -- the paste cell, placed early so it is obvious.
# ---------------------------------------------------------------------------
TRY = '''# ============================================================================
#  TRY YOUR OWN -- paste a worker's account between the triple quotes and run.
#  (Composite or test data please: no real PII in a shared notebook.)
# ============================================================================
worker_account = """I travelled abroad to work as a live-in domestic worker. On arrival the employer took my
passport and said she would keep it safe. I was promised 1,200 a month, but I have not been paid for three
months, and I am told I must first work off the 3,000 recruitment fee. I am not allowed to leave the house
alone, and there is no day off."""

result = triage(worker_account)
render_case(worker_account, result)'''

# ---------------------------------------------------------------------------
# Cell 8: how it works -- each layer live.
# ---------------------------------------------------------------------------
HOWITWORKS = '''# Layer 1 live: scan() returns the ILO indicators it finds, each with the matched cue.
probe = "the employer took my passport and I have not been paid for two months"
print("scan() on a short probe ->")
for h in scan(probe):
    print("   -", h["indicator"], "|", h["snippet"], "|", h["ilo_ref"])
print()

# The engine's coverage (a representative subset of the production harness).
stat_cards([(len(ILO_INDICATORS), "ILO indicators tracked", TEAL),
            (len(PATTERNS), "demo indicator rules", INK2),
            (len(FEE_CAMOUFLAGE), "fee-camouflage labels", WARN),
            ("451", "GREP rules in production", EMBER)])

# Layer 2 + 3: the three deterministic layers behind triage().
layers = pd.DataFrame({
    "layer": ["1. Indicator scan", "2. ILO knowledge", "3. Reasoning"],
    "what it does": [
        "match forced-labour cues in the worker's text (a representative subset of 451 GREP rules)",
        "map each hit to the controlling ILO instrument (C029, C095, C181, ICRMW, ...)",
        "risk level + present/absent + evidence gaps + next steps + a citation-grounded draft note"],
    "engine call": ["scan(text)", "ILO_REFS / ILO_INDICATORS", "risk_level(); triage(); generate_chain()"]})
display(pretty_table(layers, caption="How triage() reaches an answer -- three deterministic layers, all on-device"))

# The risk banding (risk_level).
thr = pd.DataFrame({
    "indicators found": ["4 or more", "2 - 3", "1", "0"],
    "risk level": ["HIGH", "ELEVATED", "WATCH", "LOW"],
    "meaning": ["multiple forced-labour indicators present",
                "several indicators present -- warrants review",
                "one indicator -- ask follow-up questions",
                "no clear indicators (not evidence of safety)"]})
display(pretty_table(thr, caption="Risk banding used by risk_level()"))
print("The ILO set here is the 2012 forced-labour indicators (11) plus a recruitment-fee indicator (ILO C181 / Fair Recruitment).")'''

# ---------------------------------------------------------------------------
# Cell 10: the four composite worker accounts.
# ---------------------------------------------------------------------------
ACCOUNTS_DEF = '''# Four composite / synthetic worker accounts. No real people, no real PII.
ACCOUNTS = {
"A -- domestic worker, Gulf": """I travelled abroad to work as a live-in domestic worker. The employer took my
passport on arrival, I have not been paid for three months, and I am told I must work off the recruitment fee
before I can receive wages. I am not allowed to leave the house, and there is no day off.""",
"B -- construction, city": """I work on a construction site. The company has not paid our wages for two months
and keeps saying the money will come later. The foreman threatened to report us to immigration if we complain.
We sleep in a crowded room and work seven days a week.""",
"C -- fishing vessel": """I was recruited onto a fishing boat. The broker charged me a large placement fee, and
I am still repaying the debt and cannot leave until it is paid off. We stay at sea for weeks, and my phone was
taken, so I cannot contact my family. The captain keeps our identity documents on board.""",
"D -- agriculture, seasonal": """I pick fruit on a farm through a labour contractor. He promised one wage but
paid a different amount, and my pay is reduced by deductions for transport and tools. The hours are very long,
often long days with no rest.""",
}
print("defined", len(ACCOUNTS), "composite accounts:")
for k in ACCOUNTS:
    print("   -", k)'''

EX_A = '''_ = render_triage(ACCOUNTS["A -- domestic worker, Gulf"])'''
EX_B = '''_ = render_triage(ACCOUNTS["B -- construction, city"])'''
EX_C = '''_ = render_triage(ACCOUNTS["C -- fishing vessel"])'''
EX_D = '''_ = render_triage(ACCOUNTS["D -- agriculture, seasonal"])'''

# ---------------------------------------------------------------------------
# Cell 20: batch triage -- a case queue sorted by risk.
# ---------------------------------------------------------------------------
BATCH = '''# A real intake is a queue. Add a benign check-in and a pre-departure question to the four accounts,
# triage them all, and sort so the most urgent surface first.
QUEUE = dict(ACCOUNTS)
QUEUE["E -- factory (benign check-in)"] = """I have a stable job at an electronics factory. My salary arrives on
time every month, I get one rest day a week, and I can come and go freely. I would like advice on opening a bank
account to send money to my family."""
QUEUE["F -- pre-departure question"] = """An agency offered me a construction job abroad and asked for a
placement fee of 2,000 before I leave. The pay and hours sound normal. Should I be worried about the fee?"""

_RANK = {"HIGH": 3, "ELEVATED": 2, "WATCH": 1, "LOW": 0}
rows = []
for label, acct in QUEUE.items():
    r = triage(acct)
    rows.append({"case": label, "risk": r["risk_level"], "indicators": r["n_indicators"],
                 "flagged indicators": ", ".join(d["label"] for d in r["detected_indicators"]) or "(none)",
                 "_rank": _RANK[r["risk_level"]]})
q = (pd.DataFrame(rows).sort_values(["_rank", "indicators"], ascending=False)
     .drop(columns="_rank").reset_index(drop=True))
display(pretty_table(q, caption="Case queue sorted by risk -- triage the most urgent accounts first", bars=["indicators"]))

# Risk distribution across the queue.
order = ["HIGH", "ELEVATED", "WATCH", "LOW"]
counts = [int((q["risk"] == lv).sum()) for lv in order]
fig, ax = plt.subplots(figsize=(8.6, 3.7))
bars = ax.bar(order, counts, color=[RISK_COLOR[lv] for lv in order], edgecolor=PAPER, linewidth=1.1, width=0.62)
for b, cnt in zip(bars, counts):
    ax.text(b.get_x() + b.get_width() / 2, cnt + 0.03, str(cnt), ha="center", va="bottom",
            fontsize=12, fontweight="bold", color=INK2)
ax.set_ylabel("cases"); ax.set_ylim(0, max(counts) + 1); ax.grid(axis="x", alpha=0)
_title(ax, "Risk distribution across the case queue", "six composite accounts, triaged offline")
plt.tight_layout(); plt.show()
print("queue:", {lv: c for lv, c in zip(order, counts)})'''

# ---------------------------------------------------------------------------
# Cell 22: the full reasoned chain (transparency layer).
# ---------------------------------------------------------------------------
CHAIN = '''# generate_chain() exposes the structured reasoning: restate neutrally, ask one question per ILO
# indicator, walk the recruitment-to-remedy lifecycle, then run the counterfactual checks.
chain = generate_chain(ACCOUNTS["A -- domestic worker, Gulf"])
cdf = pd.DataFrame(chain, columns=["step", "reasoning"])
display(pretty_table(cdf, caption="generate_chain() -- the audit trail behind the triage for composite worker A"))
present = sum(1 for _, t in chain if "PRESENT" in t)
print("chain length:", len(chain), "steps |", present, "indicators marked PRESENT |",
      "lifecycle stages:", len(LIFECYCLE), "| counterfactual checks:", len(COUNTERFACTUALS))'''

# ---------------------------------------------------------------------------
# Cell 24: trust boundary -- what stays local.
# ---------------------------------------------------------------------------
BOUNDARY = '''# The data-flow boundary, made explicit. Nothing here calls out; triage() is pure local Python.
flow = pd.DataFrame({
    "data": ["raw worker account (names, IDs, phone, messages)",
             "uploaded documents / photos",
             "the structured triage() result",
             "anonymized, pre-approved case envelope"],
    "where it lives": ["the caseworker's device only",
                       "the caseworker's device only",
                       "the caseworker's device only",
                       "shared upstream only if the caseworker explicitly approves"],
    "leaves the device?": ["never", "never", "never by default", "only after anonymizer + human approval"]})
display(pretty_table(flow, caption="Trust boundary -- what stays local and what could ever leave"))

stat_cards([("0", "bytes leave by default", GOOD),
            ("local", "where triage() runs", TEAL),
            ("opt-in", "any upstream sharing", EMBER)])
print("This notebook runs entirely offline. In production the DueCare anonymizer (a hard PII gate) redacts names,")
print("IDs, phone numbers, and addresses BEFORE any envelope can be shared, and the caseworker controls every step.")'''


def _toc() -> str:
    items = [
        ("1", "Try your own account", "try"),
        ("2", "How it works: indicators -> ILO knowledge -> reasoning", "how"),
        ("3", "Worked examples: four composite worker accounts", "examples"),
        ("4", "Batch triage: a case queue sorted by risk", "batch"),
        ("5", "The full reasoned chain (transparency layer)", "chain"),
        ("6", "Trust boundary: what stays on the device", "boundary"),
        ("7", "Go to production: the full DueCare harness", "production"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c: list = []

    # ---- Section 0: hero + who it is for + the problem + TOC + honest boundary ----
    c.append(md(
        "# DueCare NGO Case Triage\n\n"
        "**For the NGO caseworker and hotline responder.** A migrant worker sends you a long, worried message, and "
        "twenty more are in the queue. This notebook turns one worker's account into a **structured triage** in "
        "seconds: the forced-labour indicators it contains, the risk level, the exact ILO instrument each indicator "
        "engages, the follow-up questions still worth asking, concrete next steps, referral resources, and a draft "
        "complaint-note you can edit -- all **on your own device**, with no model, no internet, and nothing leaving "
        "the machine.\n\n"
        "**The problem it helps with.** Triaging many worker messages quickly, consistently, and with the right law "
        "and referral attached is hard to do by hand and easy to do unevenly. `triage()` gives every account the "
        "same structured, ILO-grounded first pass, so nothing obvious is missed and the urgent cases rise to the "
        "top.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** This notebook runs a **representative, deterministic subset** of the "
        "DueCare harness -- a compact indicator scanner plus the ILO knowledge map -- so it is fully reproducible "
        "offline. It is a first-pass triage aid: **not** a trafficking determination, **not** legal advice, and "
        "**not** a substitute for a trained caseworker. Every account here is composite / synthetic (no real people, "
        "no real PII). Production DueCare uses the full 451-rule GREP layer, retrieval, and Gemma 4 reasoning (see "
        "the final section)."))

    # ---- Setup ----
    c.append(md(
        "## Setup -- run these two cells once\n\n"
        "The first cell embeds the DueCare notebook visualization toolkit **and** the grounded indicator engine "
        "(the ILO indicators, the `scan()` / `risk_level()` / `generate_chain()` logic, and the knowledge maps). "
        "The second defines `triage()` and the renderers. After both run, everything else is self-contained: **no "
        "dataset, no model, no internet.**"))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + ENGINE))
    c.append(code(TRIAGE_DEFS))

    # ---- Section 1: TRY YOUR OWN ----
    c.append(md(
        '<a id="try"></a>\n## 1 - Try your own account\n\n'
        "**Edit the `worker_account` string in the next cell** -- paste a worker's message (composite or test data, "
        "please: no real PII in a shared notebook) -- and run it. `triage()` returns the structured result and "
        "`render_case()` prints the full case view: risk card, detected indicators, evidence gaps, next steps, "
        "referrals, and a draft note. Everything runs locally.\n\n"
        "*(Run the two setup cells above first -- they embed the visualization toolkit and the DueCare indicator "
        "engine so the notebook is completely self-contained.)*"))
    c.append(code(TRY))

    # ---- Section 2: how it works ----
    c.append(md(
        '<a id="how"></a>\n## 2 - How it works: indicators -> ILO knowledge -> reasoning\n\n'
        "`triage()` is three small, transparent layers -- no black box:\n\n"
        "```\n"
        "worker account (raw text, stays on the device)\n"
        "        |\n"
        "  [1] indicator scan   regex cues for the ILO forced-labour indicators\n"
        "        |              (a representative subset of the 451-rule DueCare GREP layer)\n"
        "  [2] ILO knowledge    map each hit to its controlling instrument (C029, C095, C181, ICRMW, ...)\n"
        "        |\n"
        "  [3] reasoning        risk level + present/absent + evidence gaps + next steps + draft note\n"
        "        |\n"
        "  structured triage (a dict you can render, store, or hand-review -- no raw text leaves)\n"
        "```\n\n"
        "The next cell shows each layer live: the raw `scan()` output, the engine's coverage, the three-layer map, "
        "and the risk banding."))
    c.append(code(HOWITWORKS))

    # ---- Section 3: worked examples ----
    c.append(md(
        '<a id="examples"></a>\n## 3 - Worked examples: four composite worker accounts\n\n'
        "Four **composite / synthetic** accounts -- a domestic worker in the Gulf, a construction worker, a "
        "fishing-vessel crew member, and a seasonal farm worker. Each is run through `render_triage()`, which shows "
        "the risk card, the detected-indicator table (with the matched cue and ILO instrument), and the "
        "present/absent indicator bar. No account describes a real person."))
    c.append(code(ACCOUNTS_DEF))
    c.append(md(
        "### 3A - Composite worker A: domestic worker, Gulf corridor\n"
        "Live-in domestic work: passport taken on arrival, months of unpaid wages, a recruitment-fee debt, and "
        "confinement to the house."))
    c.append(code(EX_A))
    c.append(md(
        "### 3B - Composite worker B: construction\n"
        "Unpaid wages, a threat to report the workers to immigration, crowded housing, and a seven-day week."))
    c.append(code(EX_B))
    c.append(md(
        "### 3C - Composite worker C: fishing vessel\n"
        "A placement-fee debt that cannot be paid off, a confiscated phone, and identity documents held by the "
        "captain."))
    c.append(code(EX_C))
    c.append(md(
        "### 3D - Composite worker D: seasonal agriculture\n"
        "A contractor who promised one wage and paid another, deductions that shrink the pay, and very long days -- "
        "fewer indicators, so a lower band."))
    c.append(code(EX_D))

    # ---- Section 4: batch triage ----
    c.append(md(
        '<a id="batch"></a>\n## 4 - Batch triage: a case queue sorted by risk\n\n'
        "Real intake is a queue, not one message. Here the four accounts above plus a **benign check-in** and a "
        "**pre-departure question** are triaged together and sorted so the highest-risk cases surface first. The "
        "benign and single-indicator cases matter as much as the severe ones: a triage aid that cries wolf on every "
        "message is useless, so the tool must also say **LOW** and **WATCH** when that is what the text supports."))
    c.append(code(BATCH))

    # ---- Section 5: the reasoned chain ----
    c.append(md(
        '<a id="chain"></a>\n## 5 - The full reasoned chain (the transparency layer)\n\n'
        "`generate_chain()` exposes the reasoning behind a triage: it restates the situation neutrally, asks one "
        "structured question per ILO indicator (marking each PRESENT with its cue and instrument, or 'not evident'), "
        "walks the recruitment-to-remedy lifecycle, and runs a set of counterfactual checks (could a lawful "
        "arrangement explain this?). This is the audit trail a caseworker or reviewer can read to see exactly why "
        "the tool reached its conclusion."))
    c.append(code(CHAIN))

    # ---- Section 6: trust boundary ----
    c.append(md(
        '<a id="boundary"></a>\n## 6 - Trust boundary: what stays on the caseworker\'s device\n\n'
        "The worker's words are among the most sensitive data an NGO handles. This tool is built so the raw account "
        "**never has to leave the machine**:\n\n"
        "- **Raw accounts, documents, IDs, and photos stay local.** `triage()` is pure Python running in this "
        "notebook -- no request goes anywhere.\n"
        "- **Only an anonymized, pre-approved envelope can ever be shared upstream**, and only if the caseworker "
        "explicitly chooses to. In production the DueCare anonymizer (a hard PII gate) redacts names, IDs, phone "
        "numbers, and addresses **before** anything is shareable.\n"
        "- **The caseworker controls every step** -- what is recorded, what is escalated, and whether anything is "
        "shared at all.\n\n"
        "The cell below shows the data-flow boundary explicitly."))
    c.append(code(BOUNDARY))

    # ---- Section 7: go to production ----
    c.append(md(
        '<a id="production"></a>\n## 7 - Go to production: the full DueCare harness\n\n'
        "This notebook is the friendly front door. The production system behind it is much larger:\n\n"
        "- **The full harness** -- 451 GREP indicator rules across 11 languages, a retrieval layer over an ILO / "
        "trafficking knowledge corpus, and **Gemma 4** doing the multi-step reasoning and drafting -- not the "
        "compact regex subset embedded here.\n"
        "- **Install it from source:** clone `gemma4_comp` and run `uv sync --all-packages`, then wire "
        "the chat harness into your own intake flow.\n"
        f"- **The data:** the published DueCare benchmark grades live on Kaggle (e.g. `{DATASET_ID}`), and the "
        "interactive workbench exposes a **/data** page over the knowledge surfaces.\n"
        f"- **The source:** the [repository]({REPO}) has the harness, the grader, the fine-tuning path, and the "
        "full evaluation sweep.\n\n"
        "**Honest boundary.** What runs here is a representative deterministic subset for triage support. It is not "
        "a substitute for a trained professional, not legal advice, and not a trafficking determination. Use it to "
        "triage faster and more consistently -- then apply human judgement, local law, and a real referral.\n\n"
        "License: MIT. Everything in this notebook is composite / synthetic -- no real people, no real PII.\n\n"
        "[Back to contents](#try)"))

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
    assert "DueCare NGO Case Triage".lower().replace(" ", "-") == "duecare-ngo-case-triage"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
