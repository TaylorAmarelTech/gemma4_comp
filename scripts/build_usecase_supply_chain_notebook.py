#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Supply Chain Compliance use-case Kaggle notebook.

An applied, easy-to-use notebook for a corporate compliance / ESG / procurement team that screens
supplier disclosures and worker-voice reports for forced-labour risk across a multi-tier supply chain
(UFLPA / modern-slavery-act territory). It defines a small supply-chain indicator extension on top of
the DueCare ILO engine -- tier-opacity, transshipment, recruitment-fee-to-worker, wage-anomaly,
movement-restriction, document-retention -- each mapped to the controlling framework (US UFLPA, US
WRO / CBP, UK/AU Modern Slavery Acts, ILO C029, OECD Due Diligence Guidance). `audit_supplier()` turns
a batch of supplier disclosures into a per-supplier risk table + controlling framework, then a
supplier x risk-indicator heatmap, a tier breakdown, a due-diligence summary (Kaggle-safe HTML), and a
risk-weighted escalation / remediation queue.

The notebook is FULLY SELF-CONTAINED on Kaggle: no dataset, no model, no internet. The first code
cell embeds two builder-time toolkits -- the shared DueCare notebook visualization helpers
(scripts/_notebook_viz.py) AND the grounded DueCare indicator engine (scripts/_usecase_engine.py:
scan / risk_level / generate_chain plus the ILO knowledge maps). It is a REPRESENTATIVE,
deterministic subset of the real 451-rule GREP layer + ILO knowledge packs; production uses the full
harness with retrieval and Gemma 4 reasoning.

    python scripts/build_usecase_supply_chain_notebook.py

ASCII-only (no Kaggle mojibake). No [:N] truncation of any displayed disclosure or result.
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "usecase_supply_chain"
KERNEL_ID = "taylorsamarel/duecare-supply-chain-compliance"
TITLE = "DueCare Supply Chain Compliance"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

# ---------------------------------------------------------------------------
# Cell 4: the supply-chain indicator extension + audit_supplier() + aggregates
# + due_diligence_summary() + renderers. Pure, offline. Runs in the same
# namespace as the embedded PALETTE/HELPERS/ENGINE cell (so `re`, `scan`,
# `risk_level`, `ILO_INDICATORS` etc. are all in scope).
# ---------------------------------------------------------------------------
SUPPLY_DEFS = '''from collections import Counter
try:                                     # IPython on Kaggle; a headless fallback so the notebook always runs
    from IPython.display import display, HTML, Markdown
except Exception:
    def display(*a, **k):
        for x in a: print(getattr(x, "data", x))
    def HTML(s): return s
    def Markdown(s): return s

# --- The six supply-chain forced-labour risk indicators (the corporate-diligence lens on the ILO set) ---
SUPPLY_INDICATORS = {
    "tier_opacity": "Tier opacity / undisclosed subcontracting",
    "transshipment": "Transshipment / origin obfuscation",
    "recruitment_fee_to_worker": "Recruitment fees charged to workers",
    "wage_anomaly": "Wage anomaly / unexplained deductions",
    "movement_restriction": "Restriction of worker movement",
    "document_retention": "Retention of worker identity documents",
}
# Controlling framework(s) per indicator -- the enforcement / disclosure regime a compliance team cites.
SUPPLY_FRAMEWORKS = {
    "transshipment": "US UFLPA (rebuttable presumption on region-linked goods); US Tariff Act s.307 / CBP Withhold Release Orders (WRO); OECD Due Diligence Guidance (traceability / chain of custody).",
    "document_retention": "ILO C029 + ICRMW (1990) Art. 21 (unlawful confiscation of ID/travel documents); UFLPA / CBP WRO forced-labour indicator (retention of identity documents).",
    "movement_restriction": "ILO C029 (forced labour); UFLPA / CBP WRO forced-labour indicator (restriction of movement); UK Modern Slavery Act 2015 + AU Modern Slavery Act 2018.",
    "recruitment_fee_to_worker": "ILO C181 Art. 7 + Fair Recruitment 2016 (Employer Pays Principle); ILO C029 debt-bondage indicator; UFLPA / CBP WRO forced-labour indicator (recruitment fees).",
    "wage_anomaly": "ILO C095 (Protection of Wages); UFLPA / CBP WRO forced-labour indicator (withholding of wages / abusive deductions); OECD Due Diligence Guidance.",
    "tier_opacity": "OECD Due Diligence Guidance for Responsible Supply Chains (map your chain); UK Modern Slavery Act 2015 s.54 + AU Modern Slavery Act 2018 (supply-chain transparency statements).",
}
# Short framework tag per indicator (for the compact audit table + heatmap legends).
SUPPLY_FRAMEWORK_TAG = {
    "transshipment": "UFLPA / CBP WRO",
    "document_retention": "ILO C029 / ICRMW Art.21",
    "movement_restriction": "ILO C029 / UFLPA",
    "recruitment_fee_to_worker": "ILO C181 / Employer Pays",
    "wage_anomaly": "ILO C095 / UFLPA",
    "tier_opacity": "OECD DDG / UK+AU MSA",
}
SUPPLY_SHORT = {
    "tier_opacity": "tier opacity", "transshipment": "transship", "recruitment_fee_to_worker": "recruit fee",
    "wage_anomaly": "wage anomaly", "movement_restriction": "movement", "document_retention": "doc retention",
}
# Priority order (most enforcement-acute first): drives which framework "controls" a multi-indicator supplier
# and the display sort. A triage heuristic, not a legal ranking.
SUPPLY_ORDER = ["transshipment", "document_retention", "movement_restriction",
                "recruitment_fee_to_worker", "wage_anomaly", "tier_opacity"]

# supply-chain-specific cues NOT already covered by the worker-voice ILO engine (tier opacity, origin
# obfuscation, and disclosure-level wage anomalies). Deliberately require a risk context so a clean
# disclosure ("we publish a full tier-2 map", "wages above the legal minimum") does NOT fire.
SUPPLY_PATTERNS = [
    ("tier_opacity", r"(declin\\w*|refus\\w*|unable|unwilling|will not|won'?t|cannot|can'?t|does not|do not|not able|no)\\s+(\\w+\\s+){0,3}(disclos\\w*|identif\\w*|name|map|provide|share|reveal|list|trace)\\s+(\\w+\\s+){0,4}(sub-?tier|subcontract\\w*|supplier|source|factor\\w*|facilit\\w*|mill|origin)"),
    ("tier_opacity", r"(no|zero|lack of|without|limited|little)\\s+(\\w+\\s+){0,3}(visibility|traceability|transparency|chain of custody|supplier (list|map))"),
    ("tier_opacity", r"(undisclosed|unauthoriz\\w*|unauthoris\\w*|hidden|unmapped|unregistered|unapproved)\\s+(\\w+\\s+){0,2}(subcontract\\w*|supplier|facilit\\w*|homework\\w*|workshop|factor\\w*)|(beyond|below|past|outside)\\s+tier\\s*1"),
    ("transshipment", r"(transship\\w*|trans-ship\\w*|re-?rout\\w*|re-?label\\w*|re-?packag\\w*|re-?export\\w*|commingl\\w*|co-mingl\\w*)"),
    ("transshipment", r"(country of origin|origin|provenance|source)\\s+(\\w+\\s+){0,3}(obscure\\w*|masked|hidden|unclear|changed|altered|misdeclared|falsif\\w*|cannot be verified|unverifiable)"),
    ("transshipment", r"(routed|shipped|moved|passed|channell?ed)\\s+(\\w+\\s+){0,3}(through|via)\\s+(\\w+\\s+){0,5}(before|then|to (obscure|hide|mask|change))|from\\s+(a\\s+)?(forced[- ]labou?r|sanctioned|high[- ]risk|restricted)\\s+region"),
    ("wage_anomaly", r"(wage|wages|pay|salary|piece[- ]rate|earnings)\\s+(\\w+\\s+){0,4}(below|under|less than|beneath)\\s+(\\w+\\s+){0,3}(minimum|legal|statutory|living)"),
    ("wage_anomaly", r"(unexplained|excessive|arbitrary|unlawful|undisclosed|illegal|improper)\\s+(\\w+\\s+){0,2}(deduction|deductions|withholding)|(no|missing|not provided|without)\\s+(\\w+\\s+){0,2}(pay ?slip|payslip|pay stub|wage record|wage slip)"),
    ("wage_anomaly", r"(cash[- ]only|cash in hand|off the books|unrecorded)\\s+(\\w+\\s+){0,2}(wage|wages|pay|payment)|(wage|pay|payroll)\\s+(\\w+\\s+){0,3}(discrepanc\\w*|inconsisten\\w*|irregular\\w*|anomal\\w*)"),
]
# Which ILO worker-voice indicators (from the base engine scan) map onto the supply-chain lens.
REMAP = {
    "document_retention": "document_retention",
    "recruitment_fee": "recruitment_fee_to_worker",
    "restriction_of_movement": "movement_restriction",
    "wage_withholding": "wage_anomaly",
}


def supply_scan(text):
    """Scan a supplier disclosure for the six supply-chain forced-labour risk indicators.

    Two match paths, de-duplicated (first match per indicator wins): (1) the supply-specific
    SUPPLY_PATTERNS (tier opacity, transshipment, disclosure-level wage anomalies) and (2) the base
    DueCare ILO engine `scan()`, remapped onto the supply-chain lens (passport retention, worker-paid
    recruitment fees, movement restriction, wage withholding). Each hit is a dict
    {indicator, label, snippet, framework}. Deterministic, offline, CPU-only.
    """
    t = (text or "").lower()
    hits, seen = [], set()
    for ind, pat in SUPPLY_PATTERNS:
        if ind in seen:
            continue
        m = re.search(pat, t)
        if m:
            seen.add(ind)
            hits.append({"indicator": ind, "label": SUPPLY_INDICATORS[ind],
                         "snippet": re.sub(r"\\s+", " ", m.group(0)), "framework": SUPPLY_FRAMEWORK_TAG[ind]})
    for h in scan(text):
        ind = REMAP.get(h["indicator"])
        if ind and ind not in seen:
            seen.add(ind)
            hits.append({"indicator": ind, "label": SUPPLY_INDICATORS[ind],
                         "snippet": h["snippet"], "framework": SUPPLY_FRAMEWORK_TAG[ind]})
    hits.sort(key=lambda h: SUPPLY_ORDER.index(h["indicator"]))
    return hits


def supply_risk(hits):
    """Map supply-chain hits to (LEVEL, why) with LEVEL in {HIGH, ELEVATED, WATCH, LOW} (count-based)."""
    n = len(hits)
    if n >= 4:
        return ("HIGH", "Multiple forced-labour / UFLPA-relevant indicators present")
    if n >= 2:
        return ("ELEVATED", "Several indicators present -- enhanced due diligence warranted")
    if n == 1:
        return ("WATCH", "One indicator present -- request clarification and records")
    return ("LOW", "No indicators surfaced (absence of indicators is not proof of compliance)")


def controlling_framework(hits):
    """The controlling framework text for the highest-priority indicator in the hit list (or '')."""
    return SUPPLY_FRAMEWORKS[hits[0]["indicator"]] if hits else ""


RISK_ORDER = ["HIGH", "ELEVATED", "WATCH", "LOW"]
RISK_COLOR = {"HIGH": EMBER, "ELEVATED": WARN, "WATCH": TEAL, "LOW": GOOD}
RISK_RANK = {"HIGH": 3, "ELEVATED": 2, "WATCH": 1, "LOW": 0}
RISK_FG = {"HIGH": "#7a2e12", "ELEVATED": "#7a5a1e", "WATCH": "#1f5a66", "LOW": "#2f5a3a"}
RISK_BG = {"HIGH": "#f0d8c8", "ELEVATED": "#efe3cf", "WATCH": "#cfe3e6", "LOW": "#d8e8dc"}
# Recommended due-diligence action per risk band (OECD DDG "cease / prevent / mitigate" logic).
DD_ACTION = {
    "HIGH": "Suspend / hold sourcing and open an investigation; require a time-bound corrective action plan (CAP) before resuming.",
    "ELEVATED": "Enhanced due diligence: request the sub-tier map, independent worker interviews, wage records, and a remediation plan.",
    "WATCH": "Request written clarification and documentary evidence; verify at the next audit cycle.",
    "LOW": "Proceed; keep the disclosure on file. Absence of indicators is not proof of compliance -- re-screen on change.",
}


def audit_supplier(disclosures):
    """Batch-screen supplier disclosures into a supply-chain compliance DataFrame.

    Each disclosure is a dict: {supplier, tier, country, text}. Returns one row per supplier -- supplier,
    tier, country, n_indicators, risk band, the detected supply-chain indicators, and the single
    controlling framework tag. Deterministic, offline, CPU-only -- a representative subset of the
    DueCare harness.
    """
    rows = []
    for d in disclosures:
        hits = supply_scan(d.get("text", ""))
        level, _why = supply_risk(hits)
        rows.append({
            "supplier": d.get("supplier", ""),
            "tier": d.get("tier", ""),
            "country": d.get("country", ""),
            "n_indicators": len(hits),
            "risk": level,
            "indicators": ", ".join(h["label"] for h in hits) or "(none)",
            "controlling_framework": (hits[0]["framework"] if hits else ""),
        })
    return pd.DataFrame(rows, columns=["supplier", "tier", "country", "n_indicators", "risk", "indicators", "controlling_framework"])


def color_risk(sty):
    """Tint the `risk` cells of a Styler by their risk color."""
    def _c(v): return "color:%s;font-weight:700" % RISK_COLOR.get(v, INK2)
    try:
        return sty.map(_c, subset=["risk"])
    except Exception:
        return sty.applymap(_c, subset=["risk"])


def supplier_indicator_matrix(disclosures):
    """Return (row_labels, col_labels, matrix) for a supplier x risk-indicator heatmap (1 = indicator present)."""
    inds = list(SUPPLY_INDICATORS.keys())
    col_labels = [SUPPLY_SHORT[k] for k in inds]
    row_labels, mat = [], []
    for d in disclosures:
        keys = {h["indicator"] for h in supply_scan(d.get("text", ""))}
        row_labels.append(str(d.get("supplier", "")) + " (T" + str(d.get("tier", "")) + ")")
        mat.append([1 if k in keys else 0 for k in inds])
    return row_labels, col_labels, mat


def tier_breakdown(df):
    """Per-tier risk mix + average indicator load, as a DataFrame (one row per tier)."""
    rows = []
    for t in sorted(df["tier"].unique()):
        sub = df[df.tier == t]
        row = {"tier": "Tier " + str(t), "suppliers": len(sub)}
        for lv in RISK_ORDER:
            row[lv] = int((sub.risk == lv).sum())
        row["avg indicators"] = round(float(sub.n_indicators.mean()), 2)
        rows.append(row)
    return pd.DataFrame(rows)


def escalation_queue(df):
    """Risk-weighted escalation / remediation queue: priority = risk_rank * 10 + n_indicators, highest first."""
    q = df.copy()
    q["priority"] = q["risk"].map(RISK_RANK) * 10 + q["n_indicators"]
    q["due_diligence_action"] = q["risk"].map(DD_ACTION)
    return q.sort_values("priority", ascending=False).reset_index(drop=True)


def due_diligence_summary(df):
    """Emit a per-supplier due-diligence summary as Kaggle-safe HTML (no flex / script / max-height).

    Riskiest suppliers first: each block shows the tier + country, a risk pill, the detected indicators,
    the controlling framework, and the recommended due-diligence action. Displays and returns the HTML.
    """
    RANK = df["risk"].map(RISK_RANK)
    ordered = df.assign(_r=RANK).sort_values(["_r", "n_indicators"], ascending=False).drop(columns="_r")
    blocks = []
    for _, r in ordered.iterrows():
        lv = r["risk"]
        pill = ("<span style='display:inline-block;background:" + RISK_BG[lv] + ";color:" + RISK_FG[lv] +
                ";border-radius:10px;padding:2px 12px;font-size:12px;font-weight:700'>" + lv + "</span>")
        action = DD_ACTION[lv]
        fw = r["controlling_framework"] or "(no controlling framework -- no indicator surfaced)"
        blocks.append(
            "<div style='background:#F7F6F1;border:1px solid #DDD8C9;border-left:6px solid " + RISK_COLOR[lv] +
            ";border-radius:10px;padding:13px 16px;margin:0 0 12px'>"
            "<div style='font-size:14px;font-weight:700;color:#14181B'>" + str(r["supplier"]) +
            " <span style='color:#5B5F68;font-weight:500'>(Tier " + str(r["tier"]) + ", " + str(r["country"]) +
            ")</span> &nbsp; " + pill + "</div>"
            "<div style='font-size:12.5px;color:#2A2D34;margin-top:7px'><b>Indicators:</b> " + str(r["indicators"]) + "</div>"
            "<div style='font-size:12.5px;color:#2A2D34;margin-top:4px'><b>Controlling framework:</b> " + fw + "</div>"
            "<div style='font-size:12.5px;color:#2A2D34;margin-top:4px'><b>Recommended due diligence:</b> " + action + "</div>"
            "</div>")
    n_high = int((df.risk == "HIGH").sum())
    header = ("<div style='font-family:Inter,-apple-system,system-ui,sans-serif;max-width:820px'>"
              "<div style='font-size:16px;font-weight:700;color:#14181B;margin-bottom:4px'>Due-diligence summary</div>"
              "<div style='font-size:12.5px;color:#5B5F68;margin-bottom:12px'>" + str(len(df)) +
              " suppliers screened across " + str(df.tier.nunique()) + " tiers; " + str(n_high) +
              " flagged HIGH. Composite / synthetic disclosures -- not a real supplier base, not an audit, not a legal determination.</div>")
    html = header + "".join(blocks) + "</div>"
    display(HTML(html))
    return html


print("audit_supplier() ready.", len(SUPPLY_INDICATORS), "supply-chain indicators;",
      len(SUPPLY_PATTERNS), "supply-specific rules +", len(PATTERNS), "base ILO rules;",
      len(FEE_CAMOUFLAGE), "fee-camouflage labels.")
_smoke = audit_supplier([{"supplier": "SMOKE-CO", "tier": 2, "country": "Country-X",
                          "text": "The mill retains workers passports, wages are below the legal minimum, and workers cannot leave the dormitory."}])
print("smoke ->", "risk:", _smoke.iloc[0]["risk"], "| indicators:", _smoke.iloc[0]["n_indicators"],
      "| framework:", _smoke.iloc[0]["controlling_framework"])'''

# ---------------------------------------------------------------------------
# Cell 6: TRY YOUR OWN -- the paste cell, placed early so it is obvious.
# ---------------------------------------------------------------------------
TRY = '''# ============================================================================
#  TRY YOUR OWN -- edit the list of disclosures and run. Each disclosure is a
#  dict: {supplier, tier, country, text}. Composite / test data only, please --
#  no real supplier names, no real PII in a shared notebook.
# ============================================================================
my_disclosures = [
    {"supplier": "Northwind Textiles", "tier": 2, "country": "Country-B",
     "text": """Our tier-2 spinning mill declines to disclose its sub-tier cotton suppliers. Workers pay a
recruitment fee to the labour agent that is deducted from their wages, the facility keeps workers' passports
for safekeeping, and dormitory gates are locked at night so workers cannot leave."""},
    {"supplier": "Harbor Assembly", "tier": 1, "country": "Country-A",
     "text": """This tier-1 assembly supplier publishes a full tier-1 and tier-2 supplier map. Under an
employer-pays policy all recruitment and placement costs are borne by the factory and workers are never
billed. Passports remain with each worker. Wages are above the legal minimum with itemized payslips, and
workers are free to come and go outside shift hours."""},
]
my_audit = audit_supplier(my_disclosures)
display(color_risk(pretty_table(my_audit, caption="Your suppliers, screened by DueCare", bars=["n_indicators"])))
due_diligence_summary(my_audit)
print("Edit my_disclosures above and re-run. Risk banding: HIGH 4+, ELEVATED 2-3, WATCH 1, LOW 0 indicators.")'''

# ---------------------------------------------------------------------------
# Cell 8: how screening works -- the disclosure -> indicator -> framework -> risk flow.
# ---------------------------------------------------------------------------
FLOW = '''# The screen is a short, transparent pipeline: disclosure -> indicator -> framework -> risk -> action.
fig, ax = plt.subplots(figsize=(11.2, 2.3)); ax.axis("off"); ax.set_xlim(0, 11); ax.set_ylim(0, 2)
stages = [("disclosure", "supplier statement\\n+ worker voice", INK3),
          ("indicator", "6 supply-chain\\nrisk indicators", TEAL),
          ("framework", "UFLPA / WRO / MSA\\n/ ILO / OECD", GOOD),
          ("risk band", "LOW -> HIGH", WARN),
          ("action", "monitor -> suspend\\n+ remediate", EMBER)]
xs = [0.3, 2.5, 4.7, 6.9, 9.1]; w = 1.8
for (t, s, col), x in zip(stages, xs):
    ax.add_patch(FancyBboxPatch((x, 0.5), w, 1.0, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=PAPER2, edgecolor=col, linewidth=2.4))
    ax.text(x + w / 2, 1.16, t, ha="center", va="center", fontsize=11, fontweight="bold", color=INK)
    ax.text(x + w / 2, 0.79, s, ha="center", va="center", fontsize=7.6, color=INK3)
for i in range(len(xs) - 1):
    ax.annotate("", xy=(xs[i + 1] - 0.03, 1.0), xytext=(xs[i] + w + 0.03, 1.0),
                arrowprops=dict(arrowstyle="-|>", color=INK3, lw=1.8))
plt.tight_layout(); plt.show()

stat_cards([(len(SUPPLY_INDICATORS), "supply-chain indicators", TEAL),
            (len(SUPPLY_PATTERNS) + len(PATTERNS), "demo screening rules", INK2),
            ("5", "frameworks mapped", GOOD),
            ("451", "GREP rules in production", EMBER)])'''

FRAMEWORK_MAP = '''# Every indicator is tied to the framework a compliance team actually cites. This is the map.
fw = pd.DataFrame([{"supply-chain indicator": SUPPLY_INDICATORS[k],
                    "controlling framework(s)": SUPPLY_FRAMEWORKS[k]}
                   for k in SUPPLY_ORDER])
display(pretty_table(fw, caption="Supply-chain indicator -> controlling framework (UFLPA, US WRO/CBP, UK/AU Modern Slavery Acts, ILO C029/C095/C181, OECD Due Diligence)"))

thr = pd.DataFrame({
    "indicators found": ["4 or more", "2 - 3", "1", "0"],
    "risk band": RISK_ORDER,
    "due-diligence action it implies": [DD_ACTION["HIGH"], DD_ACTION["ELEVATED"], DD_ACTION["WATCH"], DD_ACTION["LOW"]]})
display(pretty_table(thr, caption="Risk banding and the due-diligence action each band implies (OECD cease / prevent / mitigate logic)"))
print("Two match paths feed the screen: supply-specific cues (tier opacity, transshipment, wage anomalies) and the")
print("base DueCare ILO engine (passport retention, worker-paid recruitment fees, movement restriction, wage withholding).")'''

# ---------------------------------------------------------------------------
# Cell 11: the synthetic supplier disclosures -- ~8 across 3 tiers.
# ---------------------------------------------------------------------------
SUPPLIERS_DEF = '''# 8 COMPOSITE / SYNTHETIC supplier disclosures across three tiers of one apparel/electronics chain.
# No real supplier names, no real people, no PII. Tiers: 1 = direct, 2 = sub-supplier, 3 = raw material.
DISCLOSURES = [
    {"supplier": "Harbor Assembly Ltd", "tier": 1, "country": "Country-A",
     "text": """This tier-1 assembly supplier publishes a full tier-1 and tier-2 supplier map for its buyers.
Under an employer-pays policy all recruitment and placement costs are borne by the factory and workers are
never billed. Passports remain with each worker. Monthly wages are above the legal minimum with itemized
payslips, and workers are free to come and go outside shift hours."""},
    {"supplier": "Meridian Electronics", "tier": 1, "country": "Country-B",
     "text": """The plant provides dormitory housing. Workers are not allowed to leave the compound on work
nights, and there are unexplained deductions from pay for accommodation and tools that workers cannot itemize."""},
    {"supplier": "Northwind Spinning Mill", "tier": 2, "country": "Country-B",
     "text": """This tier-2 mill holds the workers passports in the office safe. Workers paid a recruitment
fee of 2,000 to the labour agent that is still being deducted from their wages, the dormitory gates are
locked at night so workers cannot leave, and wages are below the legal minimum."""},
    {"supplier": "Delta Components Co", "tier": 2, "country": "Country-C",
     "text": """The component supplier declines to disclose its sub-tier subcontractors and says it has no
visibility below tier 1. Pay and hours are otherwise reported as normal."""},
    {"supplier": "Summit Dye House", "tier": 2, "country": "Country-A",
     "text": """A licensed processor with a written employer-pays recruitment policy, wages paid monthly on
time, and workers free to leave. It has asked us to verify its accreditation."""},
    {"supplier": "Riverbend Cotton Trading", "tier": 3, "country": "Country-D",
     "text": """The raw cotton is routed through a third country and relabeled before export, so the country
of origin is obscured. The trader will not disclose the originating farms, and there are no payslips for the
seasonal pickers."""},
    {"supplier": "Ivory Coast Ginning Coop", "tier": 3, "country": "Country-E",
     "text": """A farmer cooperative supplying raw fibre. It provides a supplier list and reports wages at the
legal minimum, but has asked for help improving its grievance channel."""},
    {"supplier": "Grayline Smelting", "tier": 3, "country": "Country-C",
     "text": """The refiner charges its workers a placement fee through a broker, keeps their identity
documents on site, and workers are not allowed to leave the camp. It cannot trace the origin of its input ore."""},
]
print("defined", len(DISCLOSURES), "composite disclosures across",
      len({d["tier"] for d in DISCLOSURES}), "tiers and",
      len({d["country"] for d in DISCLOSURES}), "sourcing countries.")'''

AUDIT_TABLE = '''# Screen the whole batch. AUD is reused by every rollup below.
AUD = audit_supplier(DISCLOSURES)
display(color_risk(pretty_table(AUD, bars=["n_indicators"],
        caption="Per-supplier screen -- indicators, risk band, and the controlling framework (full disclosure text preserved in DISCLOSURES)")))
print("risk mix:", {lv: int((AUD.risk == lv).sum()) for lv in RISK_ORDER})'''

# ---------------------------------------------------------------------------
# Cell 13-14: supplier x indicator heatmap.
# ---------------------------------------------------------------------------
HEATMAP = '''rows, cols, mat = supplier_indicator_matrix(DISCLOSURES)
heatmap(mat, rows, cols, title="Supplier x risk-indicator heatmap",
        subtitle="which forced-labour risk indicator each supplier trips (1 = present)", cmap="OrRd",
        fmt=".0f", cbar_label="indicator present")
tot = [sum(r[j] for r in mat) for j in range(len(cols))]
print("most common indicator across suppliers:", cols[max(range(len(cols)), key=lambda j: tot[j])],
      "(" + str(max(tot)) + " of " + str(len(rows)) + " suppliers)")'''

# ---------------------------------------------------------------------------
# Cell 15-16: tier breakdown.
# ---------------------------------------------------------------------------
TIER = '''tb = tier_breakdown(AUD)
display(pretty_table(tb, caption="Tier breakdown -- risk mix and average indicator load per supply-chain tier",
                     bars=["avg indicators"], gradient=["HIGH"], cmap="OrRd"))

vals = list(tb["avg indicators"]); labels = list(tb["tier"])
fig, ax = plt.subplots(figsize=(7.6, 3.8))
bars = ax.bar(labels, vals, color=SEQ[:len(labels)], edgecolor=PAPER, linewidth=1.1, width=0.55)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=11, fontweight="bold", color=INK2)
ax.set_ylabel("avg forced-labour indicators"); ax.set_ylim(0, max(vals) + 0.6); ax.grid(axis="x", alpha=0)
_title(ax, "Average indicator load by tier", "risk usually deepens further from the buyer (tier 2-3)")
plt.tight_layout(); plt.show()
print("Deeper tiers (2-3) are where visibility is weakest and UFLPA / forced-labour risk concentrates.")'''

# ---------------------------------------------------------------------------
# Cell 18: the due-diligence summary.
# ---------------------------------------------------------------------------
SUMMARY = '''# The per-supplier due-diligence summary: riskiest first, with the controlling framework and the
# recommended action for each. Kaggle-safe HTML (inline styles only -- no flex / script / max-height).
_ = due_diligence_summary(AUD)'''

# ---------------------------------------------------------------------------
# Cell 19: the reasoned screen trail (defensible diligence) via generate_chain.
# ---------------------------------------------------------------------------
CHAIN = '''# A supplier finding has to be defensible. generate_chain() exposes the underlying ILO forced-labour
# reasoning behind a single supplier: restate neutrally, ask one question per ILO indicator, walk the
# recruitment-to-remedy lifecycle, then run counterfactual checks. This is the evidence trail a compliance
# officer can attach to a supplier file or a UFLPA applicability review.
top = escalation_queue(AUD).iloc[0]["supplier"]
top_text = next(d["text"] for d in DISCLOSURES if d["supplier"] == top)
chain = generate_chain(top_text)
cdf = pd.DataFrame(chain, columns=["step", "reasoning"])
display(pretty_table(cdf, caption="generate_chain() -- the ILO forced-labour reasoning trail behind the highest-priority supplier (" + top + ")"))
present = sum(1 for _, t in chain if "PRESENT" in t)
print("chain length:", len(chain), "steps |", present, "ILO indicators marked PRESENT |",
      "lifecycle stages:", len(LIFECYCLE), "| counterfactual checks:", len(COUNTERFACTUALS))'''

# ---------------------------------------------------------------------------
# Cell 20: the risk-weighted escalation / remediation queue.
# ---------------------------------------------------------------------------
QUEUE = '''# The escalation queue: risk-weighted so the compliance team works the highest-risk suppliers first.
Q = escalation_queue(AUD)
q_show = Q[["supplier", "tier", "country", "risk", "n_indicators", "priority", "due_diligence_action"]]
display(color_risk(pretty_table(q_show, bars=["priority"],
        caption="Risk-weighted escalation / remediation queue -- act from the top (priority = risk rank x 10 + indicators)")))

labs = [r.supplier + "  " + r.risk for r in Q.itertuples()]
vals = list(Q["priority"])
fig, ax = plt.subplots(figsize=(9.8, 0.46 * len(labs) + 1.5))
ax.barh(range(len(labs)), vals, color=[RISK_COLOR[r] for r in Q["risk"]], edgecolor=PAPER, linewidth=0.9)
for i, v in enumerate(vals):
    ax.text(v + 0.1, i, str(v), va="center", fontsize=9.5, color=INK3)
ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs); ax.invert_yaxis()
ax.set_xlabel("priority weight"); ax.set_xlim(0, max(vals) + 3); ax.grid(axis="y", alpha=0)
_title(ax, "Escalation queue by priority weight", "highest-risk suppliers first")
plt.tight_layout(); plt.show()
print("queue size:", len(Q), "| HIGH:", int((Q.risk == "HIGH").sum()), "| act first:", Q.iloc[0]["supplier"])'''

# ---------------------------------------------------------------------------
# Cell 22: trust boundary -- what stays in the company's environment.
# ---------------------------------------------------------------------------
BOUNDARY = '''# The data-flow boundary, made explicit. Nothing here calls out; audit_supplier() is pure local Python.
flow = pd.DataFrame({
    "data": ["raw supplier disclosures + worker-voice reports (may name people, sites, IDs)",
             "the structured screen (indicators, risk, framework)",
             "the due-diligence summary + escalation queue",
             "anonymized supplier-risk aggregate shared up the buyer chain"],
    "where it lives": ["the company's own environment only",
                       "the company's own environment only",
                       "the company's own environment only",
                       "shared with a buyer / auditor only after anonymization + human approval"],
    "leaves the environment?": ["never", "never", "never by default", "only aggregates, only after approval"]})
display(pretty_table(flow, caption="Trust boundary -- disclosures and worker reports stay in the company's environment"))

stat_cards([("0", "raw disclosures leave by default", GOOD),
            ("on-prem", "where the screen runs", TEAL),
            ("aggregates", "all that is shared upward", EMBER)])
print("Worker-voice reports are sensitive. In production the DueCare anonymizer (a hard PII gate) redacts names, IDs,")
print("and contact details before any supplier-risk aggregate is shared with a buyer, auditor, or regulator.")'''


def _toc() -> str:
    items = [
        ("1", "Try your own supplier disclosures", "try"),
        ("2", "How the screen works: disclosure -> indicator -> framework -> risk", "how"),
        ("3", "A worked batch: screen, heatmap, and tier breakdown", "batch"),
        ("4", "The due-diligence summary", "summary"),
        ("5", "Escalation + remediation prioritization", "queue"),
        ("6", "Trust boundary: disclosures stay in your environment", "boundary"),
        ("7", "Honest boundary + go to production", "boundary2"),
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
        "# DueCare Supply Chain Compliance\n\n"
        "**For a corporate compliance, ESG, or responsible-procurement team** -- the office that has to answer "
        "\"is there forced labour anywhere in our supply chain?\" to a customs authority, an investor, or an "
        "auditor. Supplier disclosures and worker-voice reports arrive faster than anyone can read them, and the "
        "risky suppliers look almost exactly like the compliant ones. This notebook screens a batch of supplier "
        "disclosures for **six supply-chain forced-labour risk indicators** -- tier opacity, transshipment / origin "
        "obfuscation, recruitment fees charged to workers, wage anomalies, restriction of worker movement, and "
        "retention of identity documents -- maps each one to the **controlling framework** (US UFLPA, US WRO / CBP, "
        "the UK and Australian Modern Slavery Acts, ILO C029 / C095 / C181, and the OECD Due Diligence Guidance), "
        "and turns it into a per-supplier risk table, a supplier-by-indicator heatmap, a tier breakdown, a "
        "**due-diligence summary**, and a **risk-weighted escalation / remediation queue** -- all inside your own "
        "environment, with no model, no internet, and nothing leaving the machine.\n\n"
        "**The problem it helps with.** UFLPA and the modern-slavery statutes put the burden of proof on the buyer, "
        "but diligence capacity is finite and the highest risk hides deep in tiers 2 and 3. `audit_supplier()` gives "
        "every disclosure the same structured, framework-grounded first pass, so nothing obvious is missed, the "
        "pattern across a supply chain becomes visible, and the suppliers that need investigation rise to the top of "
        "the queue.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** This notebook runs a **representative, deterministic subset** of the "
        "DueCare harness -- a compact indicator scanner plus the framework map -- so it is fully reproducible "
        "offline. It is a **screening and prioritization aid**: it flags *indicators* and points at the *controlling "
        "framework*. It is **not** a supply-chain audit, **not** a UFLPA admissibility determination, **not** legal "
        "advice, and **not** a substitute for on-the-ground human due diligence and worker engagement. Every "
        "disclosure here is composite / synthetic (no real suppliers, no real people, no real PII). Production "
        "DueCare uses the full 451-rule GREP layer, retrieval, and Gemma 4 reasoning (see the final section)."))

    # ---- Setup ----
    c.append(md(
        "## Setup -- run these two cells once\n\n"
        "The first cell embeds the DueCare notebook visualization toolkit **and** the grounded indicator engine "
        "(the ILO indicators, the `scan()` / `risk_level()` logic, and the knowledge maps). The second defines the "
        "**supply-chain extension**: the six indicators, the framework map, `audit_supplier()`, the aggregates, and "
        "`due_diligence_summary()`. After both run, everything else is self-contained: **no dataset, no model, no "
        "internet.**"))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + ENGINE))
    c.append(code(SUPPLY_DEFS))

    # ---- Section 1: TRY YOUR OWN ----
    c.append(md(
        '<a id="try"></a>\n## 1 - Try your own supplier disclosures\n\n'
        "**Edit the `my_disclosures` list in the next cell** -- each entry is a dict with `supplier`, `tier`, "
        "`country`, and `text` (composite or test data, please: no real supplier names or PII in a shared notebook) "
        "-- and run it. `audit_supplier()` returns a compliance DataFrame and `due_diligence_summary()` renders the "
        "per-supplier summary with the controlling framework and recommended action. Everything runs locally.\n\n"
        "*(Run the two setup cells above first -- they embed the visualization toolkit and the DueCare indicator "
        "engine plus the supply-chain extension so the notebook is completely self-contained.)*"))
    c.append(code(TRY))

    # ---- Section 2: how the screen works ----
    c.append(md(
        '<a id="how"></a>\n## 2 - How the screen works: disclosure -> indicator -> framework -> risk\n\n'
        "The screen is a short, transparent pipeline -- no black box. A supplier disclosure (and any worker-voice "
        "report attached to it) is scanned for the six supply-chain indicators; each hit is mapped to the framework "
        "that controls it; the indicator count sets a risk band; and the band implies a due-diligence action. The "
        "diagram and the two tables below show the flow, the full indicator-to-framework map, and the banding."))
    c.append(code(FLOW))
    c.append(code(FRAMEWORK_MAP))

    # ---- Section 3: worked batch ----
    c.append(md(
        '<a id="batch"></a>\n## 3 - A worked batch: screen, heatmap, and tier breakdown\n\n'
        "Eight **composite / synthetic** supplier disclosures across three tiers of one apparel / electronics chain "
        "(tier 1 direct assembly, tier 2 sub-suppliers, tier 3 raw material). `audit_supplier()` produces the "
        "per-supplier screen; then a supplier-by-indicator heatmap and a tier breakdown show where the risk "
        "concentrates. Full disclosure text is preserved in `DISCLOSURES` -- nothing is truncated."))
    c.append(code(SUPPLIERS_DEF))
    c.append(code(AUDIT_TABLE))
    c.append(md(
        "### 3A - Supplier x risk-indicator heatmap\n"
        "Which indicator does each supplier trip? The heatmap puts suppliers on the rows and the six indicators on "
        "the columns, so a reviewer can see at a glance which suppliers cluster risk and which single indicator "
        "(passport retention, worker-paid fees, transshipment) is most common across the chain."))
    c.append(code(HEATMAP))
    c.append(md(
        "### 3B - Tier breakdown\n"
        "Risk is rarely spread evenly across tiers. This breakdown shows the risk mix and the average indicator load "
        "per tier, which almost always deepens further from the buyer -- tier 2 and tier 3, where visibility is "
        "weakest, are where UFLPA and forced-labour risk concentrate."))
    c.append(code(TIER))

    # ---- Section 4: the due-diligence summary ----
    c.append(md(
        '<a id="summary"></a>\n## 4 - The due-diligence summary\n\n'
        "`due_diligence_summary()` rolls the screen up to the level a compliance team acts on: for each supplier, "
        "riskiest first, the risk band, the detected indicators, the **controlling framework**, and the "
        "**recommended due-diligence action** (the OECD cease / prevent / mitigate logic -- suspend and open a "
        "corrective action plan for HIGH, enhanced diligence for ELEVATED, clarification for WATCH). It is rendered "
        "as Kaggle-safe inline-styled HTML."))
    c.append(code(SUMMARY))
    c.append(md(
        "### 4A - The reasoned screen trail\n"
        "A supplier finding has to survive scrutiny. `generate_chain()` exposes the underlying ILO "
        "forced-labour reasoning behind the highest-priority supplier -- restate the situation neutrally, ask "
        "one question per ILO indicator, walk the recruitment-to-remedy lifecycle, then run counterfactual "
        "checks. It is the evidence trail a compliance officer can attach to a supplier file or a UFLPA "
        "applicability review."))
    c.append(code(CHAIN))

    # ---- Section 5: escalation / remediation queue ----
    c.append(md(
        '<a id="queue"></a>\n## 5 - Escalation + remediation prioritization\n\n'
        "Diligence capacity is finite, so the order matters. `escalation_queue()` assigns each supplier a priority "
        "weight (`risk rank x 10 + indicators`) and sorts descending, so a HIGH-risk supplier with many indicators "
        "always outranks a WATCH-risk supplier with one -- and each row carries the recommended remediation action. "
        "The compliant and single-indicator suppliers still matter (a tool that flagged everyone would be useless), "
        "so the queue also says **LOW** and **WATCH** when that is what the disclosure supports."))
    c.append(code(QUEUE))

    # ---- Section 6: trust boundary ----
    c.append(md(
        '<a id="boundary"></a>\n## 6 - Trust boundary: disclosures stay in your environment\n\n'
        "Supplier disclosures and worker-voice reports are sensitive records -- they can name people, sites, and "
        "identity numbers. This tool is built so the raw text **never has to leave the company's environment**:\n\n"
        "- **Raw disclosures and worker reports stay on-prem.** `audit_supplier()` is pure Python running in this "
        "notebook -- no request goes anywhere.\n"
        "- **Only anonymized aggregates ever move up the chain.** A supplier-risk aggregate shared with a buyer, "
        "auditor, or regulator carries counts by risk and indicator, never raw worker text, and only after human "
        "approval. In production the DueCare anonymizer (a hard PII gate) redacts names, IDs, and contact details "
        "**before** anything is shareable.\n"
        "- **The company controls every step** -- what is screened, what is escalated, and whether any aggregate is "
        "shared at all.\n\n"
        "The cell below shows the data-flow boundary explicitly."))
    c.append(code(BOUNDARY))

    # ---- Section 7: honest boundary + go to production ----
    c.append(md(
        '<a id="boundary2"></a>\n## 7 - Honest boundary + go to production\n\n'
        "This notebook is the friendly front door. The production system behind it is much larger:\n\n"
        "- **Fine-tune on your own supplier code and program.** The harness can be fine-tuned on your specific "
        "supplier code of conduct, audit protocol, and the corridors you source from, so the risk bands and "
        "framework citations reflect **your** program, not a generic template.\n"
        "- **The full harness** -- 451 GREP indicator rules across 11 languages, retrieval over an ILO / UFLPA / "
        "modern-slavery corpus, and **Gemma 4** doing the multi-step reasoning and drafting -- not the compact regex "
        "subset embedded here.\n"
        "- **Install it from source:** clone `gemma4_comp` and run `uv sync --all-packages`, then wire "
        "`audit_supplier()` into your supplier-onboarding and monitoring pipeline.\n"
        f"- **The data + source:** the published DueCare benchmark grades live on Kaggle (e.g. `{DATASET_ID}`), and "
        f"the [repository]({REPO}) has the harness, the grader, and the full evaluation sweep.\n\n"
        "**Honest boundary.** What runs here is a representative deterministic subset for compliance screening. It is "
        "**not** a supply-chain audit, **not** a UFLPA admissibility or legal determination, and **not** a substitute "
        "for on-the-ground human due diligence and worker engagement. Use it to screen and prioritize consistently -- "
        "then apply human judgement, independent verification, and local law.\n\n"
        "License: MIT. Everything in this notebook is composite / synthetic -- no real suppliers, no real people, no "
        "real PII.\n\n"
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
    assert TITLE.lower().replace(" ", "-") == "duecare-supply-chain-compliance"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
