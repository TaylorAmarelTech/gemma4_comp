#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Prosecutor Case Building use-case Kaggle notebook.

An applied, easy-to-use notebook for a prosecutor, labour inspector, or anti-trafficking
investigator. Several workers come forward about the same employer or recruiter, each with a
partial account. `build_case()` pools those accounts into a structured case file: the forced-labour
indicators found across accounts (with the ILO / Palermo instrument each engages), the evidence
chain laid out along the recruitment-to-remedy lifecycle, the evidence GAPS still to corroborate
(with the record that would prove each), a grounded charge / referral framing, and a draft case
memo (Kaggle-safe HTML). It renders an indicator x account corroboration heatmap, a risk stat card,
and the memo.

The notebook is FULLY SELF-CONTAINED on Kaggle: no dataset, no model, no internet. The first code
cell embeds two builder-time toolkits -- the shared DueCare notebook visualization helpers
(scripts/_notebook_viz.py) AND the grounded DueCare indicator engine (scripts/_usecase_engine.py:
scan / risk_level / generate_chain plus the ILO knowledge maps). It is a REPRESENTATIVE,
deterministic subset of the real 451-rule GREP layer + ILO knowledge packs; production uses the full
harness with retrieval and Gemma 4 reasoning.

    python scripts/build_usecase_prosecutor_notebook.py

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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "usecase_prosecutor"
KERNEL_ID = "taylorsamarel/duecare-prosecutor-case-building"
TITLE = "DueCare Prosecutor Case Building"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

# ---------------------------------------------------------------------------
# Cell 4: build_case() + case knowledge maps + renderers. Pure, offline.
# Runs in the same namespace as the embedded PALETTE/HELPERS/ENGINE cell.
# ---------------------------------------------------------------------------
CASE_DEFS = '''from collections import OrderedDict
try:                                     # IPython on Kaggle; a headless fallback so the notebook always runs
    from IPython.display import display, HTML, Markdown
except Exception:
    def display(*a, **k):
        for x in a: print(getattr(x, "data", x))
    def HTML(s): return s
    def Markdown(s): return s

RISK_COLOR = {"HIGH": EMBER, "ELEVATED": WARN, "WATCH": TEAL, "LOW": GOOD}
_QMAP = dict(INDICATOR_QUESTIONS)        # indicator -> the follow-up question to ask

# Which lifecycle stage each ILO indicator most naturally belongs to (recruitment -> remedy). A
# defensible default so evidence can be laid out along the recruitment-to-remedy timeline.
STAGE_OF_INDICATOR = {
    "recruitment_fee": "recruitment",
    "deception": "recruitment",
    "abuse_of_vulnerability": "recruitment",
    "isolation": "transit",
    "document_retention": "arrival",
    "wage_withholding": "employment",
    "debt_bondage": "employment",
    "excessive_overtime": "employment",
    "abusive_conditions": "employment",
    "restriction_of_movement": "employment",
    "violence": "employment",
    "intimidation": "complaint",
}

# What corroborates each indicator -- the record a prosecutor / inspector would seek next.
EVIDENCE_SOURCE = {
    "document_retention": "physical custody check of the passport / ID; search of the employer safe or office; worker and witness testimony",
    "recruitment_fee": "receipts, loan agreements, agency ledgers, and remittance / bank records showing the worker-paid fee",
    "wage_withholding": "payroll records, bank statements, and the wage ledger (promised vs paid vs deducted)",
    "debt_bondage": "loan / advance contracts, deduction records, and the debt ledger tying wages to the debt",
    "restriction_of_movement": "accommodation inspection, locks / keys / gate records, CCTV or GPS, and witness testimony",
    "intimidation": "messages or recordings of threats, prior complaint / retaliation records, and witness testimony",
    "deception": "the signed contract compared to the advertised / promised terms; recruitment adverts and chat logs",
    "excessive_overtime": "time sheets, duty rosters, and biometric clock-in / clock-out logs",
    "isolation": "phone-custody evidence, call records, and witness testimony about blocked contact",
    "abuse_of_vulnerability": "immigration / visa status records, language needs, and first-time-abroad indicators",
    "violence": "medical records, photographs of injuries, any police report, and witness testimony",
    "abusive_conditions": "accommodation inspection photographs, an occupational-safety inspection, and medical records",
}

# The charge / referral angle each indicator supports, grounded in the cited instrument.
CHARGE_FRAMING = {
    "document_retention": "Retention of identity documents: an element of forced labour (ILO C029) and independently unlawful confiscation under ICRMW Art.21 (ILO C189 Art.9 for domestic workers).",
    "debt_bondage": "Debt bondage: forced labour under ILO C029 Art.2 + P029 and a servile status under the 1956 Supplementary Slavery Convention Art.1(a).",
    "recruitment_fee": "Worker-paid recruitment fees: breach of ILO C181 Art.7 and Fair Recruitment Principle 7; evidence of the debt that can underpin bondage.",
    "wage_withholding": "Withholding of wages: breach of ILO C095 Art.8/9/12 and a coercive means supporting a forced-labour charge.",
    "restriction_of_movement": "Restriction of movement / confinement: an element of forced labour (ILO C029) and a means of trafficking under Palermo Art.3.",
    "intimidation": "Threats (deportation, police, blacklisting): the menace-of-penalty element of forced labour (ILO C029) and a coercive means under Palermo Art.3.",
    "deception": "Deception about the job or terms: a means of trafficking under Palermo Art.3 and a breach of accurate-terms duties (ILO C181).",
    "excessive_overtime": "Excessive overtime / denied rest: breach of hours-of-work standards (ILO C001 / C030); corroborates abusive conditions.",
    "isolation": "Isolation (confiscated phone, blocked contact): an ILO 2012 forced-labour indicator and evidence of coercive control.",
    "abuse_of_vulnerability": "Abuse of vulnerability: a means under Palermo Art.3 (ICRMW Art.21); aggravating context for the coercion indicators.",
    "violence": "Physical or sexual violence: criminal assault and an element of forced labour (ILO C029; C190) -- refer to criminal enforcement immediately.",
    "abusive_conditions": "Abusive living / working conditions: an ILO 2012 indicator and occupational-safety breaches (ILO C155); corroborates the pattern.",
}
# Coercion indicators that speak to the two-part ILO C029 test (menace of penalty + involuntariness).
_COERCION = {"intimidation", "violence", "debt_bondage", "document_retention", "restriction_of_movement", "wage_withholding", "isolation"}

def build_case(accounts):
    """Pool several worker accounts of the same operation into a structured case file.

    accounts: a list of worker-account strings (one per witness / complainant). Returns a dict:
      per_account (each account scanned independently), indicators (every ILO indicator found across
      ALL accounts, with the controlling instrument, the corroborating account numbers, and the
      matched cues), case_risk (risk_level over the union of indicators), evidence_chain (the
      indicators arranged along the recruitment-to-remedy lifecycle), evidence_gaps (indicators NOT
      yet evidenced, each with what to corroborate and where to look), charge_summary + charge_framing
      (a referral framing grounded in the cited instruments), and referral_resources. Deterministic,
      offline, CPU-only -- a representative subset of the DueCare harness.
    """
    accounts = [a for a in accounts if str(a).strip()]
    per_account, union, cue_map = [], OrderedDict(), {}
    for i, acct in enumerate(accounts):
        hits = scan(acct)
        lvl, _why = risk_level(hits)
        per_account.append({"index": i, "label": "Account " + str(i + 1), "risk": lvl,
                            "n_indicators": len(hits), "indicator_keys": [h["indicator"] for h in hits],
                            "indicators": ", ".join(h["label"] for h in hits) or "(none)"})
        for h in hits:
            union.setdefault(h["indicator"], set()).add(i)
            cue_map.setdefault(h["indicator"], [])
            if h["snippet"] not in cue_map[h["indicator"]]:
                cue_map[h["indicator"]].append(h["snippet"])
    pooled = [{"indicator": k} for k in union]           # one per indicator -> an overall case band
    case_level, case_why = risk_level(pooled)
    indicators = [{
        "indicator": k, "label": ILO_INDICATORS[k],
        "accounts_corroborating": sorted(j + 1 for j in union[k]), "n_accounts": len(union[k]),
        "cues": cue_map.get(k, []), "ilo_ref": ILO_REFS.get(k, "ILO Indicators of Forced Labour (2012)"),
        "charge_framing": CHARGE_FRAMING.get(k, ""),
    } for k in union]
    evidence_chain = OrderedDict((s, []) for s in LIFECYCLE)
    for k in union:
        evidence_chain[STAGE_OF_INDICATOR.get(k, "employment")].append(
            {"label": ILO_INDICATORS[k], "n_accounts": len(union[k]), "ilo_ref": ILO_REFS.get(k, "ILO 2012")})
    gaps = [{"indicator": k, "label": ILO_INDICATORS[k], "corroborate": _QMAP[k],
             "evidence_source": EVIDENCE_SOURCE.get(k, "worker and witness testimony")}
            for k in ILO_INDICATORS if k not in union]
    present = set(union)
    coercion_present = sorted(present & _COERCION)
    if len(coercion_present) >= 2:
        summary = ("The accounts describe work exacted under menace of penalty and not offered voluntarily -- the "
                   "two-part test of forced labour under ILO C029 Art.2. Consider a forced-labour referral and, where "
                   "movement or harbouring for exploitation is present, a trafficking referral under Palermo Art.3.")
    elif present:
        summary = ("The accounts raise labour-exploitation concerns short of a clear forced-labour finding on this "
                   "record. Corroborate the gaps below before framing a charge; several indicators still point to "
                   "specific ILO breaches.")
    else:
        summary = "No forced-labour indicators were evidenced on this record. Absence of indicators is not proof of safety."
    return {
        "n_accounts": len(accounts), "per_account": per_account,
        "case_risk": case_level, "case_reason": case_why,
        "indicators": indicators, "evidence_chain": evidence_chain, "evidence_gaps": gaps,
        "charge_summary": summary, "charge_framing": [CHARGE_FRAMING[k] for k in union if k in CHARGE_FRAMING],
        "referral_resources": HOTLINES,
    }

# ---- renderers: a risk card, per-account table, corroboration heatmap, evidence chain, memo ----
def _case_card(case):
    stat_cards([(case["case_risk"], "pooled case risk", RISK_COLOR.get(case["case_risk"], INK2)),
                (len(case["indicators"]), "indicators evidenced", TEAL),
                (case["n_accounts"], "worker accounts", INK2),
                (len(case["evidence_gaps"]), "gaps to corroborate", WARN)])

def render_case_overview(case):
    """Risk stat card + per-account intake table + the pooled framing summary."""
    _case_card(case)
    rows = [{"account": p["label"], "risk": p["risk"], "indicators": p["n_indicators"],
             "what this account contains": p["indicators"]} for p in case["per_account"]]
    display(pretty_table(pd.DataFrame(rows), caption="Per-account intake -- each worker's account, scanned independently", bars=["indicators"]))
    print("POOLED CASE RISK:", case["case_risk"], "--", case["case_reason"])
    print("CHARGE / REFERRAL SUMMARY:", case["charge_summary"])

def case_heatmap(case):
    """Indicator x account corroboration matrix: which accounts corroborate each indicator."""
    keys = [d["indicator"] for d in case["indicators"]]
    if not keys:
        print("No indicators evidenced across the accounts -- nothing to chart. Absence is not proof of safety.")
        return
    labels = [ILO_INDICATORS[k] for k in keys]
    accts = [p["label"] for p in case["per_account"]]
    corr = {d["indicator"]: set(d["accounts_corroborating"]) for d in case["indicators"]}
    mat = [[1.0 if (j + 1) in corr[k] else 0.0 for j in range(len(accts))] for k in keys]
    heatmap(mat, labels, accts, title="Indicator x account corroboration matrix",
            subtitle="which worker accounts corroborate each forced-labour indicator",
            cmap="BuGn", fmt=".0f", cbar_label="present in account")

def render_evidence(case):
    """The evidence chain by lifecycle stage + the evidence-gap table (what to corroborate next)."""
    rows = []
    for stage in LIFECYCLE:
        items = case["evidence_chain"][stage]
        rows.append({"lifecycle stage": stage,
                     "indicators evidenced here": ", ".join(it["label"] + " (x" + str(it["n_accounts"]) + ")" for it in items)
                     or "(nothing yet -- a gap to fill)"})
    display(pretty_table(pd.DataFrame(rows), caption="Evidence chain -- indicators arranged along the recruitment-to-remedy lifecycle"))
    gaps = case["evidence_gaps"]
    if gaps:
        gdf = pd.DataFrame([{"indicator not yet evidenced": g["label"], "what to corroborate next": g["corroborate"],
                             "where to look": g["evidence_source"]} for g in gaps])
        display(pretty_table(gdf, caption="Evidence gaps -- what to corroborate next, and the record that would prove it"))
    else:
        print("Every tracked indicator is evidenced on this record.")

def case_memo(case, matter="MATTER (composite -- for review)"):
    """Render a Kaggle-safe HTML case memo (inline styles only -- no flex / script / max-height)."""
    ind_items = "".join(
        "<li style='margin:4px 0;color:#2A2D34;font-size:12.5px'><b>" + d["label"] + "</b> "
        "<span style='color:#5B5F68'>(corroborated by " + str(d["n_accounts"]) + " of " + str(case["n_accounts"]) +
        " accounts)</span> -- " + d["charge_framing"] + "</li>" for d in case["indicators"]) or \
        "<li style='color:#5B5F68'>No forced-labour indicators evidenced on this record.</li>"
    gap_items = "".join(
        "<li style='margin:3px 0;color:#2A2D34;font-size:12px'>" + g["label"] + ": " + g["corroborate"] +
        " <span style='color:#5B5F68'>(seek: " + g["evidence_source"] + ")</span></li>" for g in case["evidence_gaps"]) or \
        "<li style='color:#5B5F68'>None -- all tracked indicators evidenced.</li>"
    band = case["case_risk"]
    band_bg = {"HIGH": "#f0d8c8", "ELEVATED": "#efe3cf", "WATCH": "#cfe3e6", "LOW": "#d8e8dc"}.get(band, "#EFEDE4")
    band_fg = {"HIGH": "#7a2e12", "ELEVATED": "#7a5a1e", "WATCH": "#1f5a66", "LOW": "#2f5a3a"}.get(band, "#2A2D34")
    html = (
        "<div style='font-family:Inter,-apple-system,system-ui,sans-serif;max-width:820px;background:#F7F6F1;"
        "border:1px solid #DDD8C9;border-left:6px solid " + TEAL + ";border-radius:12px;padding:18px 22px'>"
        "<div style='font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#5B5F68'>Draft case memo -- composite, for review</div>"
        "<div style='font-size:17px;font-weight:800;color:#14181B;margin:2px 0 8px'>" + matter + "</div>"
        "<span style='display:inline-block;background:" + band_bg + ";color:" + band_fg +
        ";border-radius:10px;padding:3px 12px;font-size:12px;font-weight:700;margin-bottom:6px'>Pooled case risk: " + band + "</span>"
        "<div style='font-size:12.5px;color:#2A2D34;margin:12px 0 4px'><b>1. Basis.</b> " + str(case["n_accounts"]) +
        " worker account(s) reviewed. " + case["charge_summary"] + "</div>"
        "<div style='font-size:12.5px;color:#2A2D34;margin:10px 0 2px'><b>2. Indicators and instruments.</b></div>"
        "<ul style='margin:2px 0 8px 18px;padding:0'>" + ind_items + "</ul>"
        "<div style='font-size:12.5px;color:#2A2D34;margin:8px 0 2px'><b>3. Evidence still to corroborate.</b></div>"
        "<ul style='margin:2px 0 8px 18px;padding:0'>" + gap_items + "</ul>"
        "<div style='font-size:12px;color:#5B5F68;margin-top:10px;border-top:1px solid #E8E4D7;padding-top:8px'>"
        "This memo records indicators and citations for review only. It is not a charging decision, not legal advice, "
        "and not a trafficking or forced-labour determination. Verify every fact and apply the governing domestic law.</div>"
        "</div>")
    display(HTML(html))
    return html

def render_charge(case):
    """Suggested charge / referral framing table (one line per indicator) + the draft memo."""
    if case["indicators"]:
        cdf = pd.DataFrame([{"indicator": d["label"], "accounts": d["n_accounts"],
                             "charge / referral basis (grounded in the cited instrument)": d["charge_framing"]}
                            for d in case["indicators"]])
        display(pretty_table(cdf, caption="Suggested charge / referral framing -- one line per indicator, grounded in the ILO / Palermo instrument"))
    print("SUMMARY FRAMING:", case["charge_summary"])
    return case_memo(case)

print("build_case() ready. Tracking", len(ILO_INDICATORS), "ILO indicators;",
      len(PATTERNS), "demo indicator rules;", len(FEE_CAMOUFLAGE), "fee-camouflage labels;",
      len(LIFECYCLE), "lifecycle stages.")
_smoke = build_case(["the employer took my passport and I have not been paid for two months",
                     "they threatened to deport me if I complain and my phone was taken"])
print("smoke -> case risk:", _smoke["case_risk"], "| indicators:", [d["indicator"] for d in _smoke["indicators"]],
      "| gaps:", len(_smoke["evidence_gaps"]))'''

# ---------------------------------------------------------------------------
# Cell 6: TRY YOUR OWN -- the paste cell, placed early so it is obvious.
# ---------------------------------------------------------------------------
TRY = '''# ============================================================================
#  TRY YOUR OWN -- put one or more worker accounts (composite / test data only,
#  no real PII) in the list below and run. build_case() pools them into a case
#  file: indicators + instruments, the evidence chain, the gaps to corroborate,
#  a charge / referral framing, and a draft memo.
# ============================================================================
my_accounts = [
    """I was recruited to work in a private house abroad. When I arrived the employer took my passport and said
she would keep it safe. I have not been paid for two months, and I was told I must first work off the recruitment
fee. I am not allowed to leave the house on my own.""",
    """I work for the same family through the same agency. If I say I want to leave, they say they will call
immigration and have me deported. My phone is kept by the madam during the day, and I have had no rest day since
I arrived.""",
]
my_case = build_case(my_accounts)
render_case_overview(my_case)
case_heatmap(my_case)
render_evidence(my_case)
render_charge(my_case)
print("Edit my_accounts above and re-run. Each string is one worker's account of the same operation.")'''

# ---------------------------------------------------------------------------
# Cell 8: how case-building works -- layers, banding, the two-part C029 test.
# ---------------------------------------------------------------------------
HOWITWORKS = '''# build_case() is four small, transparent steps -- no black box.
stat_cards([(len(ILO_INDICATORS), "ILO indicators tracked", TEAL),
            (len(PATTERNS), "demo indicator rules", INK2),
            (len(LIFECYCLE), "lifecycle stages", WARN),
            ("451", "GREP rules in production", EMBER)])

layers = pd.DataFrame({
    "step": ["1. Indicator scan", "2. Instrument mapping", "3. Evidence chain", "4. Gaps + framing"],
    "what it does": [
        "match forced-labour cues in each worker's account (a representative subset of 451 GREP rules)",
        "map every indicator to the controlling ILO / Palermo instrument (C029, C095, C181, ICRMW, Palermo)",
        "arrange the evidenced indicators along the recruitment-to-remedy lifecycle, counting corroboration across accounts",
        "list what is NOT yet evidenced (with the record that would prove it) and frame a grounded charge / referral"],
    "engine call": ["scan(text)", "ILO_REFS / CHARGE_FRAMING", "STAGE_OF_INDICATOR / LIFECYCLE", "evidence gaps; build_case()"]})
display(pretty_table(layers, caption="How build_case() reaches a case file -- four transparent steps, all on-device"))

thr = pd.DataFrame({
    "indicators evidenced": ["4 or more", "2 - 3", "1", "0"],
    "pooled case risk": ["HIGH", "ELEVATED", "WATCH", "LOW"],
    "what it means for a case": ["multiple forced-labour indicators corroborated -- build the file now",
                                 "several indicators -- corroborate and review",
                                 "one indicator -- seek corroboration before acting",
                                 "nothing evidenced yet -- absence is not proof of safety"]})
display(pretty_table(thr, caption="Pooled case-risk banding (risk_level over the union of indicators across accounts)"))
print("The two-part ILO C029 test -- work exacted under menace of penalty AND not offered voluntarily -- is what the")
print("coercion indicators (threats, confinement, document retention, wage withholding, debt) speak to together.")'''

# ---------------------------------------------------------------------------
# Cell 10: the composite accounts of one operation.
# ---------------------------------------------------------------------------
ACCOUNTS_DEF = '''# Four COMPOSITE / SYNTHETIC accounts from workers describing the SAME recruitment-and-employment
# operation. No real people, no real PII. Corroboration across accounts is the point.
CASE_ACCOUNTS = [
"""I answered an advertisement for well-paid hotel work abroad. The agency charged me a large placement fee,
which I borrowed, and promised a salary I have never actually received. When I arrived the job was not the hotel
job I was promised. My employer took my passport at the airport and still has it.""",
"""I came through the same agency. I have not been paid for three months -- they say the money is being kept for
me. I am not allowed to leave the accommodation without permission, and the gate is locked at night. When I asked
to go home they said I still owe the recruitment debt and cannot leave until it is paid off.""",
"""I work in the same place. The manager threatened to report us to immigration and cancel our visas if we
complain. Our phones are collected at the start of each shift, and we work every day with no rest day. The room
is crowded and there is often not enough food.""",
"""I am new and this is my first time abroad; I do not speak the local language. A recruiter told me the pay would
be one amount, but the contract they made me sign said something different. Money is deducted from my wages every
month for things I do not understand.""",
]
print("defined", len(CASE_ACCOUNTS), "composite accounts of one operation.")'''

CASE_BUILD = '''# Pool the four accounts into one case file. CASE is reused by every view below.
CASE = build_case(CASE_ACCOUNTS)
render_case_overview(CASE)'''

HEATMAP = '''case_heatmap(CASE)
print("corroboration:", {d["label"]: d["n_accounts"] for d in CASE["indicators"]})'''

EVIDENCE = '''render_evidence(CASE)'''

CHARGE_MEMO = '''_ = render_charge(CASE)'''

# ---------------------------------------------------------------------------
# Cell 18: the reasoned chain (transparency layer).
# ---------------------------------------------------------------------------
CHAIN = '''# A prosecutor's finding must be defensible. generate_chain() exposes the reasoning behind a single
# account: restate neutrally, ask one question per ILO indicator (marking each PRESENT with its cue and
# instrument, or "not evident"), walk the recruitment-to-remedy lifecycle, then run counterfactual checks.
# This is the audit trail that can be attached to a case file.
anchor = CASE_ACCOUNTS[1]
chain = generate_chain(anchor)
cdf = pd.DataFrame(chain, columns=["step", "reasoning"])
display(pretty_table(cdf, caption="generate_chain() -- the reasoned audit trail behind one worker account (Account 2)"))
present = sum(1 for _, t in chain if "PRESENT" in t)
print("chain length:", len(chain), "steps |", present, "indicators marked PRESENT |",
      "lifecycle stages:", len(LIFECYCLE), "| counterfactual checks:", len(COUNTERFACTUALS))'''

# ---------------------------------------------------------------------------
# Cell 20: trust boundary -- what stays in the case system.
# ---------------------------------------------------------------------------
BOUNDARY = '''# The data-flow boundary, made explicit. Nothing here calls out; build_case() is pure local Python.
flow = pd.DataFrame({
    "data": ["raw worker / witness accounts (names, IDs, contact details)",
             "uploaded evidence (documents, photos, records)",
             "the structured case file (indicators, chain, gaps, framing)",
             "an anonymized cross-border request (MLAT / mutual legal assistance)"],
    "where it lives": ["the investigating authority's case system only",
                       "the investigating authority's case system only",
                       "the investigating authority's case system only",
                       "shared with another jurisdiction only after anonymization + human approval"],
    "leaves the case system?": ["never", "never", "never by default", "only anonymized, only after approval"]})
display(pretty_table(flow, caption="Trust boundary -- evidence stays in the case system"))

stat_cards([("0", "raw evidence leaves by default", GOOD),
            ("on-prem", "where build_case() runs", TEAL),
            ("anonymized", "all that crosses a border (MLAT)", EMBER)])
print("Cross-border cooperation (mutual legal assistance) shares only anonymized, pre-approved material -- never raw")
print("witness text. In production the DueCare anonymizer (a hard PII gate) redacts names, IDs, and phone numbers first.")'''


def _toc() -> str:
    items = [
        ("1", "Try your own case", "try"),
        ("2", "How case-building works", "how"),
        ("3", "A worked case: four corroborating accounts", "case"),
        ("4", "The reasoned audit trail (transparency layer)", "chain"),
        ("5", "Trust boundary: evidence stays in the case system", "boundary"),
        ("6", "Go to production: the full DueCare harness", "production"),
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
        "# DueCare Prosecutor Case Building\n\n"
        "**For a prosecutor, labour inspector, or anti-trafficking investigator.** Several workers come forward "
        "about the same employer or recruiter, each with a partial account. This notebook pools those accounts into "
        "a **structured case file** in seconds: the forced-labour indicators they contain, the exact ILO / Palermo "
        "instrument each one engages, the evidence laid out along the recruitment-to-remedy lifecycle, the **gaps "
        "still to corroborate** (with the record that would prove each one), a grounded **charge / referral "
        "framing**, and a **draft case memo** you can edit -- all inside your own case system, with no model, no "
        "internet, and nothing leaving the machine.\n\n"
        "**The problem it helps with.** Building a labour-exploitation or trafficking case means turning many "
        "partial worker accounts into one coherent, corroborated picture, mapped to the right instrument, with the "
        "evidence gaps made explicit. Doing that by hand is slow and uneven. `build_case()` gives every account the "
        "same structured, ILO-grounded reading, shows where the accounts corroborate one another, names exactly what "
        "still needs corroborating, and drafts a memo an investigator can edit.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** This notebook runs a **representative, deterministic subset** of the "
        "DueCare harness -- a compact indicator scanner plus the ILO knowledge map -- so it is fully reproducible "
        "offline. It is **decision-support**: a way to organize accounts, citations, and evidence gaps. It is "
        "**not** legal advice, **not** a charging decision, and **not** a trafficking or forced-labour "
        "determination. Every account here is composite / synthetic (no real people, no real PII). Production "
        "DueCare uses the full 451-rule GREP layer, retrieval, and Gemma 4 reasoning (see the final section)."))

    # ---- Setup ----
    c.append(md(
        "## Setup -- run these two cells once\n\n"
        "The first cell embeds the DueCare notebook visualization toolkit **and** the grounded indicator engine "
        "(the ILO indicators, the `scan()` / `risk_level()` / `generate_chain()` logic, and the knowledge maps). "
        "The second defines `build_case()`, the case knowledge maps, and the renderers. After both run, everything "
        "else is self-contained: **no dataset, no model, no internet.**"))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + ENGINE))
    c.append(code(CASE_DEFS))

    # ---- Section 1: TRY YOUR OWN ----
    c.append(md(
        '<a id="try"></a>\n## 1 - Try your own case\n\n'
        "**Edit the `my_accounts` list in the next cell** -- put one or more worker accounts (composite or test "
        "data, please: no real PII in a shared notebook) -- and run it. `build_case()` pools them and the renderers "
        "print the full case view: the risk card and per-account intake, the indicator-by-account corroboration "
        "heatmap, the evidence chain and gaps, the charge / referral framing, and a draft memo. Everything runs "
        "locally.\n\n"
        "*(Run the two setup cells above first -- they embed the visualization toolkit and the DueCare indicator "
        "engine so the notebook is completely self-contained.)*"))
    c.append(code(TRY))

    # ---- Section 2: how it works ----
    c.append(md(
        '<a id="how"></a>\n## 2 - How case-building works: indicators -> instrument -> evidence chain -> gaps\n\n'
        "`build_case()` is four small, transparent steps -- no black box:\n\n"
        "```\n"
        "several worker accounts (raw text, stays in the case system)\n"
        "        |\n"
        "  [1] indicator scan     regex cues for the ILO forced-labour indicators, per account\n"
        "        |                (a representative subset of the 451-rule DueCare GREP layer)\n"
        "  [2] instrument map     map each indicator to its controlling ILO / Palermo instrument\n"
        "        |\n"
        "  [3] evidence chain     lay the indicators along recruitment -> transit -> arrival -> employment\n"
        "        |                -> complaint -> exit -> remedy, counting corroboration across accounts\n"
        "  [4] gaps + framing     what is NOT yet evidenced (and the record that would prove it) + a grounded\n"
        "        |                charge / referral framing\n"
        "  structured case file + draft memo (reviewable, no raw text leaves)\n"
        "```\n\n"
        "The next cell shows the coverage, the four-step map, and the pooled case-risk banding, with the two-part "
        "ILO C029 test that the coercion indicators speak to together."))
    c.append(code(HOWITWORKS))

    # ---- Section 3: worked case ----
    c.append(md(
        '<a id="case"></a>\n## 3 - A worked case: four corroborating accounts\n\n'
        "Four **composite / synthetic** accounts from workers describing the **same** recruitment-and-employment "
        "operation -- a placement-fee debt and a switched job, months of unpaid wages and a locked gate, threats and "
        "confiscated phones, and a misleading contract with unexplained deductions. Pooled through `build_case()`, "
        "they show how partial accounts corroborate one another into a coherent case. No account describes a real "
        "person, and full account text is preserved -- nothing is truncated."))
    c.append(code(ACCOUNTS_DEF))
    c.append(code(CASE_BUILD))
    c.append(md(
        "### 3A - Indicator x account corroboration matrix\n"
        "Where do the accounts agree? The heatmap marks which worker accounts corroborate each forced-labour "
        "indicator, so a reviewer can see at a glance which elements are supported by more than one witness."))
    c.append(code(HEATMAP))
    c.append(md(
        "### 3B - The evidence chain and the gaps\n"
        "The evidenced indicators arranged along the recruitment-to-remedy lifecycle, then the **evidence gaps**: "
        "the indicators not yet evidenced, each paired with what to corroborate next and the specific record -- "
        "payroll, contracts, custody checks, inspection photos -- that would prove it."))
    c.append(code(EVIDENCE))
    c.append(md(
        "### 3C - The charge / referral framing and the draft memo\n"
        "A suggested charge / referral framing, one line per indicator, each grounded in the ILO or Palermo "
        "instrument it engages -- then a **draft case memo** (Kaggle-safe inline-styled HTML) that an investigator "
        "can edit. The memo states indicators and citations for review only; it is not a charging decision."))
    c.append(code(CHARGE_MEMO))

    # ---- Section 4: the reasoned chain ----
    c.append(md(
        '<a id="chain"></a>\n## 4 - The reasoned audit trail (the transparency layer)\n\n'
        "A prosecutorial or inspection finding has to be defensible. `generate_chain()` exposes the reasoning behind "
        "a single account: it restates the situation neutrally, asks one structured question per ILO indicator "
        "(marking each PRESENT with its cue and instrument, or 'not evident'), walks the recruitment-to-remedy "
        "lifecycle, and runs a set of counterfactual checks (could a lawful arrangement explain this?). This is the "
        "step-by-step record an investigator can attach to a case file."))
    c.append(code(CHAIN))

    # ---- Section 5: trust boundary ----
    c.append(md(
        '<a id="boundary"></a>\n## 5 - Trust boundary: evidence stays in the case system\n\n'
        "Worker and witness accounts are among the most sensitive records an investigation holds. This tool is built "
        "so the raw text **never has to leave the case system**:\n\n"
        "- **Raw accounts and uploaded evidence stay on-prem.** `build_case()` is pure Python running in this "
        "notebook -- no request goes anywhere.\n"
        "- **Only anonymized material ever crosses a border.** Mutual legal assistance (MLAT) shares pre-approved, "
        "anonymized material, never raw witness text, and only after human approval. In production the DueCare "
        "anonymizer (a hard PII gate) redacts names, IDs, and phone numbers **before** anything is shareable.\n"
        "- **The investigating authority controls every step** -- what is recorded, what is corroborated, and "
        "whether anything is shared at all.\n\n"
        "The cell below shows the data-flow boundary explicitly."))
    c.append(code(BOUNDARY))

    # ---- Section 6: go to production ----
    c.append(md(
        '<a id="production"></a>\n## 6 - Go to production: the full DueCare harness\n\n'
        "This notebook is the friendly front door. The production system behind it is much larger:\n\n"
        "- **Fine-tune on your own law.** The harness can be fine-tuned on a jurisdiction's specific forced-labour "
        "and trafficking statutes, so the charge framing reflects **your** domestic law, not a generic template.\n"
        "- **The full harness** -- 451 GREP indicator rules across 11 languages, retrieval over an ILO / statute / "
        "case-law corpus, and **Gemma 4** doing the multi-step reasoning and drafting -- not the compact regex "
        "subset embedded here.\n"
        "- **Install it:** `pip install duecare-llm-core duecare-llm-chat` (the `duecare-llm-*` family), then wire "
        "`build_case()` into your case-management workflow.\n"
        f"- **The data:** the published DueCare benchmark grades live on Kaggle (e.g. `{DATASET_ID}`), and the "
        "interactive workbench exposes a **/data** page over the knowledge surfaces.\n"
        f"- **The source:** the [repository]({REPO}) has the harness, the grader, the fine-tuning path, and the "
        "full evaluation sweep.\n\n"
        "**Honest boundary.** What runs here is a representative deterministic subset for case-building support. It "
        "is decision-support, **not** a substitute for a trained investigator or prosecutor, **not** legal advice, "
        "and **not** a trafficking or forced-labour determination. Use it to organize accounts, citations, and "
        "evidence gaps consistently -- then apply human judgement, the governing domestic law, and due process.\n\n"
        "License: MIT. Everything in this notebook is composite / synthetic -- no real people, no real PII.\n\n"
        "[Back to contents](#try)"))

    nb = nbf.v4.new_notebook()
    nb["cells"] = c
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                      "language_info": {"name": "python"}}
    nbf.validate(nb)
    nbf.write(nb, str(nb_dir / "notebook.ipynb"))

    meta = {"id": KERNEL_ID, "title": TITLE, "code_file": "notebook.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": False, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    raw = (nb_dir / "notebook.ipynb").read_text(encoding="utf-8")
    non_ascii = sorted({ch for ch in raw if ord(ch) > 127})
    return {"kernel_id": KERNEL_ID, "title": TITLE, "cells": len(c),
            "code_cells": sum(1 for x in c if x.cell_type == "code"), "notebook_dir": str(nb_dir),
            "non_ascii_chars": "".join(non_ascii)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    summary = build(args.output, force=args.force)
    slug = summary["kernel_id"].split("/", 1)[1]
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    assert TITLE.lower().replace(" ", "-") == "duecare-prosecutor-case-building"
    assert not summary["non_ascii_chars"], f"non-ASCII leaked into the notebook: {summary['non_ascii_chars']!r}"
    summary["title_slug_ok"] = True
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
