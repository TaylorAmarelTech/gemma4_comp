#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Knowledge Base Explorer Kaggle notebook.

A documentation-and-visualization tour of the DueCare *knowledge layer* -- the
grounded reference substrate the Gemma 4 harness reasons over. It documents and
draws:

  * the 11 ILO forced-labour indicators (2012) and the instrument controlling each,
  * the key ILO conventions and the regional / national anchors used alongside them,
  * the fee-camouflage taxonomy (the legitimate-sounding labels a worker-paid cost hides behind),
  * ~16 named migration corridors and the 7 sectors the harness reasons about,
  * the referral pathways (with the honest note that live numbers come from a versioned tool),
  * a small worked RAG retrieval (match indicators -> pull the ILO instrument -> cite),

and then assembles everything into a downloadable **facts pack** (`duecare_facts_pack.json`)
so a reader can take the facts.

The notebook is FULLY SELF-CONTAINED on Kaggle: no dataset, no model, no internet. The first code
cell embeds two builder-time toolkits -- the shared DueCare notebook visualization helpers
(scripts/_notebook_viz.py) AND the grounded DueCare indicator engine (scripts/_usecase_engine.py:
ILO_INDICATORS / ILO_REFS / FEE_CAMOUFLAGE / HOTLINES / PATTERNS + scan / risk_level). The reference
facts added here are STABLE (structure + citations), not volatile operational data (live hotline
numbers, current fee caps) which belong in a versioned tool call. It is a REPRESENTATIVE subset of
the production knowledge surfaces (as published: 451 GREP rules across 11 languages, 859 RAG docs,
16 ILO conventions, ...).

    python scripts/build_knowledge_base_explorer_notebook.py

ASCII-only (no Kaggle mojibake). No [:N] truncation of any displayed content.
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "knowledge_base_explorer"
KERNEL_ID = "taylorsamarel/duecare-knowledge-base-explorer"
TITLE = "DueCare Knowledge Base Explorer"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
DS = f"https://www.kaggle.com/datasets/{DATASET_ID}"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

# ---------------------------------------------------------------------------
# Cell 4 (SETUP 2): curated, grounded REFERENCE FACTS that extend the engine.
# All ASCII; every entry cites the controlling instrument.
# ---------------------------------------------------------------------------
REFERENCE_DEFS = '''# Curated, well-grounded REFERENCE FACTS that extend the embedded engine (all ASCII, every entry cites the
# controlling instrument). These are STABLE reference facts -- structure, scope, citations -- NOT volatile
# operational data (live phone numbers, current fee caps, fresh advisories) which belong in a versioned tool call.

# The canonical ILO 2012 set names 11 indicators; the engine adds recruitment_fee as an operational 12th cue
# grounded in ILO C181 Art.7 / Fair Recruitment. Keep the two clearly distinguished.
CANONICAL_11 = [k for k in ILO_INDICATORS if k != "recruitment_fee"]
OPERATIONAL_EXTRA = ["recruitment_fee"]

# Readable families the indicators fall into (a grouping aid, not an official ILO taxonomy).
INDICATOR_GROUPS = {
    "abuse_of_vulnerability": "Deception & vulnerability",
    "deception": "Deception & vulnerability",
    "restriction_of_movement": "Coercion & control",
    "isolation": "Coercion & control",
    "violence": "Coercion & control",
    "intimidation": "Coercion & control",
    "document_retention": "Documents & conditions",
    "abusive_conditions": "Documents & conditions",
    "excessive_overtime": "Documents & conditions",
    "wage_withholding": "Economic control",
    "debt_bondage": "Economic control",
    "recruitment_fee": "Economic control",
}

# Key ILO instruments (+ two UN / CoE anchors used alongside them), one-line scope each.
ILO_CONVENTIONS = {
    "C029": {"title": "Forced Labour Convention, 1930", "protects": "Prohibits all forms of forced or compulsory labour; the anchor instrument behind the 11 indicators."},
    "P029": {"title": "Protocol of 2014 to C029", "protects": "Modern update: prevention, protection, access to remedy, and compensation for victims of forced labour."},
    "C105": {"title": "Abolition of Forced Labour Convention, 1957", "protects": "Bars forced labour as political coercion, punishment, labour discipline, strike sanction, or discrimination."},
    "C095": {"title": "Protection of Wages Convention, 1949", "protects": "Wages paid regularly, in full, in legal tender; strict limits on deductions and truck systems."},
    "C181": {"title": "Private Employment Agencies Convention, 1997", "protects": "Regulates recruitment agencies; Art.7 bars charging recruitment fees or costs to workers."},
    "C097": {"title": "Migration for Employment Convention (Revised), 1949", "protects": "Equal treatment for regular migrant workers in pay, conditions, and social security."},
    "C143": {"title": "Migrant Workers (Supplementary Provisions) Convention, 1975", "protects": "Action against clandestine movement and abusive conditions; basic rights for irregular migrants."},
    "ICRMW": {"title": "UN Migrant Workers Convention, 1990", "protects": "Rights of all migrant workers and their families; Art.21 bars unauthorized confiscation of identity documents."},
    "C189": {"title": "Domestic Workers Convention, 2011", "protects": "Labour rights for domestic workers: written terms, hours, weekly rest, minimum wage, no document retention."},
    "C190": {"title": "Violence and Harassment Convention, 2019", "protects": "The right to a world of work free from violence and harassment, including gender-based."},
    "R203": {"title": "Forced Labour (Supplementary Measures) Recommendation, 2014", "protects": "Guidance accompanying P029: prevention, victim identification, protection, and access to remedy."},
    "R204": {"title": "Transition from the Informal to the Formal Economy Recommendation, 2015", "protects": "Formalization to reduce the informality that leaves workers exposed to forced-labour risk."},
}

# Regional / national anchors that operationalize the framework in specific jurisdictions.
REGIONAL_ANCHORS = {
    "US TVPA": {"jurisdiction": "United States", "protects": "Trafficking Victims Protection Act (2000): criminalizes trafficking, creates the T-visa, anchors the annual TIP Report tiers."},
    "UK Modern Slavery Act 2015": {"jurisdiction": "United Kingdom", "protects": "Consolidates slavery and trafficking offences; s.54 requires supply-chain transparency statements."},
    "AU Modern Slavery Act 2018": {"jurisdiction": "Australia", "protects": "Mandatory annual modern-slavery statements for large entities on risks in operations and supply chains."},
    "CA Supply Chains Act (S-211)": {"jurisdiction": "Canada", "protects": "Fighting Against Forced Labour and Child Labour in Supply Chains Act (2023): mandatory reporting."},
    "Kuwait DW Law No.68/2015": {"jurisdiction": "Kuwait", "protects": "First Gulf law giving domestic workers enforceable rights: weekly rest, paid leave, wage protection."},
    "CoE Warsaw Convention": {"jurisdiction": "Council of Europe", "protects": "Convention on Action against Trafficking in Human Beings (2005): victim-centred standards with GRETA monitoring."},
}

# Indicative mapping: which instrument(s) most directly speak to each forced-labour indicator.
CONVENTION_COLS = ["C029", "P029", "C095", "C181", "C097/C143", "ICRMW", "C189", "C190"]
INDICATOR_CONVENTION_MAP = {
    "abuse_of_vulnerability": ["C029", "C097/C143", "ICRMW"],
    "deception": ["C029", "C181", "C097/C143"],
    "restriction_of_movement": ["C029", "P029"],
    "isolation": ["C029"],
    "violence": ["C029", "C190"],
    "intimidation": ["C029", "C190"],
    "document_retention": ["C029", "ICRMW", "C189"],
    "wage_withholding": ["C095", "C189"],
    "debt_bondage": ["C029", "P029"],
    "abusive_conditions": ["C029", "C189"],
    "excessive_overtime": ["C189"],
    "recruitment_fee": ["C181"],
}

# The fee-camouflage taxonomy: legitimate-sounding label -> (plausible cover, what it really is, instrument).
FEE_TAXONOMY = {
    "training bond": ("repayable cost of job training", "a worker-paid recruitment cost that locks the worker in", "ILO C181 Art.7"),
    "mobilization fee": ("cost to mobilize / deploy the worker", "a worker-paid recruitment fee", "ILO C181 Art.7"),
    "processing fee": ("paperwork / visa processing", "a worker-paid recruitment cost", "ILO C181 Art.7"),
    "service charge": ("agency service", "a worker-paid recruitment fee", "ILO C181 Art.7"),
    "placement fee": ("cost of placing the worker", "a worker-paid recruitment fee (classic)", "ILO C181 Art.7"),
    "agency commission": ("the agency's commission", "a worker-paid recruitment fee", "ILO C181 Art.7"),
    "medical deposit": ("refundable medical-check deposit", "a withheld sum creating a financial hold", "ILO C095; C181"),
    "security deposit": ("refundable good-conduct deposit", "a withheld sum creating debt / a hold", "ILO C095; C181"),
    "e-wallet fee": ("digital wallet / payroll-card fee", "a wage-deduction rail that erodes take-home pay", "ILO C095"),
    "visa cost recovery": ("employer recovering the visa cost", "shifting an employer cost onto the worker", "ILO C181 Art.7"),
    "sustainability fee": ("a vague sustainability charge", "an invented deduction with no lawful basis", "ILO C095"),
    "retention incentive": ("a bonus you forfeit if you leave", "a penalty that restricts free exit", "ILO C029; C095"),
    "loyalty deduction": ("a deduction for a loyalty scheme", "an unlawful wage deduction", "ILO C095"),
}

# ~16 named migration corridors (origin -> destination) with the sectors each is known for.
CORRIDORS = [
    {"corridor": "Nepal -> Qatar", "origin": "Nepal", "destination": "Qatar", "sectors": ["construction", "hospitality"], "note": "Gulf sponsorship (kafala); construction and services; recruitment-fee debt is common."},
    {"corridor": "Nepal -> Malaysia", "origin": "Nepal", "destination": "Malaysia", "sectors": ["manufacturing", "construction"], "note": "Electronics and manufacturing; multi-tier recruitment agents raise fee-debt risk."},
    {"corridor": "Philippines -> Saudi Arabia", "origin": "Philippines", "destination": "Saudi Arabia", "sectors": ["domestic work", "care"], "note": "Household service work under sponsorship; document-retention and isolation risk."},
    {"corridor": "Philippines -> UAE", "origin": "Philippines", "destination": "UAE", "sectors": ["domestic work", "hospitality"], "note": "Domestic and service work; deployment via licensed agencies."},
    {"corridor": "Indonesia -> Saudi Arabia", "origin": "Indonesia", "destination": "Saudi Arabia", "sectors": ["domestic work"], "note": "Domestic work; periodic deployment moratoria; confinement and isolation risk."},
    {"corridor": "Indonesia -> Malaysia", "origin": "Indonesia", "destination": "Malaysia", "sectors": ["agriculture", "domestic work", "construction"], "note": "Palm-oil plantations and households; irregular crossings raise vulnerability."},
    {"corridor": "Bangladesh -> Saudi Arabia", "origin": "Bangladesh", "destination": "Saudi Arabia", "sectors": ["construction", "domestic work"], "note": "High recruitment costs; wage withholding on large projects."},
    {"corridor": "Bangladesh -> Malaysia", "origin": "Bangladesh", "destination": "Malaysia", "sectors": ["manufacturing", "construction", "agriculture"], "note": "Levy and agent fees; documented debt-bondage concerns."},
    {"corridor": "India -> UAE", "origin": "India", "destination": "UAE", "sectors": ["construction", "hospitality", "domestic work"], "note": "Large construction workforce; sponsor-tied visas."},
    {"corridor": "Myanmar -> Thailand", "origin": "Myanmar", "destination": "Thailand", "sectors": ["fishing", "manufacturing", "agriculture"], "note": "Seafood and fishing; documented forced labour at sea; document retention."},
    {"corridor": "Cambodia -> Thailand", "origin": "Cambodia", "destination": "Thailand", "sectors": ["fishing", "construction", "agriculture"], "note": "Cross-border brokers; debt and movement-restriction risk."},
    {"corridor": "Sri Lanka -> Kuwait", "origin": "Sri Lanka", "destination": "Kuwait", "sectors": ["domestic work"], "note": "Household work under sponsorship; Kuwait DW Law No.68/2015 applies."},
    {"corridor": "Ethiopia -> Lebanon", "origin": "Ethiopia", "destination": "Lebanon", "sectors": ["domestic work"], "note": "Kafala household work; passport-retention and confinement risk."},
    {"corridor": "Mexico -> United States", "origin": "Mexico", "destination": "United States", "sectors": ["agriculture", "hospitality", "construction"], "note": "H-2A / H-2B seasonal work; employer-tied visas; TVPA jurisdiction."},
    {"corridor": "Ukraine -> Poland", "origin": "Ukraine", "destination": "Poland", "sectors": ["agriculture", "construction", "care"], "note": "Seasonal and care work; EU labour standards; sub-agent risk."},
    {"corridor": "Vietnam -> Taiwan", "origin": "Vietnam", "destination": "Taiwan", "sectors": ["manufacturing", "fishing", "care"], "note": "Factory, distant-water fishing, and care; brokerage-fee debt."},
]

# The seven sectors the harness reasons about, with the indicators each most often surfaces.
SECTORS = {
    "domestic work": "Isolated household work; passport retention, wage withholding, confinement, no rest day (C189).",
    "construction": "Large sites; recruitment-fee debt, wage withholding, unsafe / abusive conditions, threats.",
    "agriculture": "Seasonal, piece-rate; deductions, deception on pay, excessive hours, contractor abuse.",
    "fishing": "Distant-water vessels; document retention, debt bondage, isolation at sea, violence.",
    "manufacturing": "Factories and dormitories; recruitment fees, overtime, restricted movement, retained documents.",
    "hospitality": "Hotels and services; wage deductions, long hours, sponsor-tied visas, deception on terms.",
    "care": "Care homes and in-home care; isolation, unpaid overtime, document control, dependency.",
}

# The knowledge-surface counts AS PUBLISHED by DueCare (stable reference prose; do not overclaim).
KNOWLEDGE_SURFACE = {
    "grep_indicator_rules": 451,
    "grep_languages": 11,
    "rag_documents": 859,
    "ilo_conventions": 16,
    "fee_camouflage_labels": 57,
    "corridor_fee_cap_entries": 38,
    "ngo_contact_bundles": 36,
    "trafficking_seed_prompts": 74640,
    "note": "As published in the DueCare knowledge-surface verification. This notebook embeds a REPRESENTATIVE subset for offline reproducibility.",
}

def retrieve_and_cite(text):
    """Worked RAG step: scan the text for indicators, pull the controlling instrument for each hit, and
    assemble the citation list. Deterministic + offline -- the same grounding the harness performs before
    Gemma 4 drafts an answer. Returns {indicators, citations, risk, risk_reason}."""
    hits = scan(text)
    citations, seen = [], set()
    for h in hits:
        ref = h["ilo_ref"]
        if ref not in seen:
            seen.add(ref)
            citations.append(ref)
    lvl, why = risk_level(hits)
    return {"indicators": [{"label": h["label"], "cue": h["snippet"], "instrument": h["ilo_ref"]} for h in hits],
            "citations": citations, "risk": lvl, "risk_reason": why}

print("reference layer loaded:",
      len(CANONICAL_11), "canonical ILO indicators +", len(OPERATIONAL_EXTRA), "operational cue |",
      len(ILO_CONVENTIONS), "ILO instruments |", len(REGIONAL_ANCHORS), "regional / national anchors |",
      len(CORRIDORS), "corridors |", len(SECTORS), "sectors |", len(FEE_TAXONOMY), "fee-camouflage entries.")
_demo = retrieve_and_cite("the agency charged a large placement fee and the employer took my passport")
print("retrieve_and_cite smoke -> risk:", _demo["risk"], "| citations:", _demo["citations"])'''

# ---------------------------------------------------------------------------
# Section 0: the knowledge layer at a glance + the three-layer pipeline.
# ---------------------------------------------------------------------------
PREVIEW_SURFACE = '''# The DueCare knowledge layer at a glance -- counts AS PUBLISHED (this notebook embeds a representative subset).
ks = KNOWLEDGE_SURFACE
stat_cards([(str(ks["grep_indicator_rules"]), "GREP indicator rules", TEAL),
            (str(ks["rag_documents"]), "RAG documents", EMBER),
            (str(ks["ilo_conventions"]), "ILO conventions", WARN),
            (str(ks["grep_languages"]), "languages", INK2)])

surface = pd.DataFrame([
    {"knowledge surface": "GREP indicator rules (across 11 languages)", "count (as published)": ks["grep_indicator_rules"]},
    {"knowledge surface": "RAG documents (trafficking / ILO corpus)", "count (as published)": ks["rag_documents"]},
    {"knowledge surface": "ILO conventions referenced", "count (as published)": ks["ilo_conventions"]},
    {"knowledge surface": "Fee-camouflage labels", "count (as published)": ks["fee_camouflage_labels"]},
    {"knowledge surface": "Corridor fee-cap entries", "count (as published)": ks["corridor_fee_cap_entries"]},
    {"knowledge surface": "NGO contact bundles", "count (as published)": ks["ngo_contact_bundles"]},
    {"knowledge surface": "Trafficking seed prompts", "count (as published)": ks["trafficking_seed_prompts"]},
])
display(pretty_table(surface, caption="DueCare knowledge surfaces -- counts as published (see note)"))
print("NOTE:", ks["note"])'''

LAYERS = '''# The three knowledge layers, and how a worker's text flows through them before Gemma 4 answers.
layers = pd.DataFrame([
    {"layer": "1. GREP indicators", "holds": "regex indicator rules (451 across 11 languages)",
     "answers": "which ILO forced-labour indicators are present in the text?", "example call": "scan(text)"},
    {"layer": "2. RAG law", "holds": "859 documents: ILO conventions, statutes, corridor / sector facts",
     "answers": "which controlling instrument governs each indicator?", "example call": "retrieve_and_cite(text)"},
    {"layer": "3. Tools", "holds": "versioned knowledge packs: hotlines, fee caps, current advisories",
     "answers": "what is the CURRENT number / cap / rule to route to?", "example call": "tool(corridor, sector)"},
])
display(pretty_table(layers, caption="GREP indicators -> RAG law -> tools: the three layers behind a grounded answer"))
print("Flow: raw text (stays local) -> GREP indicators -> RAG law -> tools -> Gemma 4 drafts a cited, grounded answer.")
print("Stable structure (indicators, instruments, refusal habits) is memorized; volatile facts come from tools.")'''

# ---------------------------------------------------------------------------
# Section 1: the 11 ILO indicators -> controlling convention.
# ---------------------------------------------------------------------------
INDICATOR_CARDS = '''# The forced-labour indicator set the harness tracks.
n_instr = len({r for refs in INDICATOR_CONVENTION_MAP.values() for r in refs})
stat_cards([(str(len(CANONICAL_11)), "canonical ILO 2012 indicators", TEAL),
            (str(len(OPERATIONAL_EXTRA)), "operational cue (recruitment fee)", EMBER),
            (str(len(CONVENTION_COLS)), "instruments in the map", WARN),
            (str(len(set(INDICATOR_GROUPS.values()))), "indicator families", INK2)])
print("The canonical ILO (2012) list names 11 indicators; DueCare adds recruitment_fee as an operational 12th")
print("cue grounded in ILO C181 Art.7 / Fair Recruitment. Both are shown below, clearly distinguished.")'''

INDICATOR_TABLE = '''# Each indicator -> its family, the controlling instrument, and whether it is in the canonical 2012 set.
rows = []
for ind, label in ILO_INDICATORS.items():
    rows.append({"ILO indicator": label,
                 "family": INDICATOR_GROUPS.get(ind, ""),
                 "controlling instrument": ILO_REFS.get(ind, "ILO Indicators of Forced Labour (2012)"),
                 "canonical 2012?": "yes" if ind in CANONICAL_11 else "operational (C181)"})
idf = pd.DataFrame(rows)
display(pretty_table(idf, caption="The forced-labour indicators -> the ILO instrument that controls each"))
print("Rows:", len(idf), "(", len(CANONICAL_11), "canonical +", len(OPERATIONAL_EXTRA), "operational ).")'''

INDICATOR_HEATMAP = '''# Indicator x convention: which instrument(s) most directly speak to each indicator (indicative mapping).
inds = list(ILO_INDICATORS.keys())
row_labels = [ILO_INDICATORS[i] for i in inds]
mat = [[1.0 if col in INDICATOR_CONVENTION_MAP.get(i, []) else 0.0 for col in CONVENTION_COLS] for i in inds]
heatmap(mat, row_labels, CONVENTION_COLS, cmap="BuGn", fmt=".0f", cbar_label="applies (1) / not (0)",
        title="Indicator x ILO convention: the controlling-instrument map",
        subtitle="indicative mapping -- a 1 marks an instrument that directly speaks to that indicator")
print("Read across a row for every instrument that speaks to an indicator; down a column for an instrument's reach.")
print("C029 (Forced Labour) is the anchor and lights up the most rows.")'''

# ---------------------------------------------------------------------------
# Section 2: ILO conventions & instruments.
# ---------------------------------------------------------------------------
CONV_TABLE = '''# The key ILO instruments, one-line scope each.
rows = [{"instrument": code, "title": v["title"], "what it protects": v["protects"]} for code, v in ILO_CONVENTIONS.items()]
cdf = pd.DataFrame(rows)
display(pretty_table(cdf, caption="Key ILO instruments behind the DueCare knowledge layer"))
print(len(ILO_CONVENTIONS), "ILO instruments documented here; DueCare references", KNOWLEDGE_SURFACE["ilo_conventions"], "conventions as published.")'''

ANCHOR_TABLE = '''# Regional / national anchors that operationalize the ILO framework in specific jurisdictions.
rows = [{"anchor": name, "jurisdiction": v["jurisdiction"], "what it does": v["protects"]} for name, v in REGIONAL_ANCHORS.items()]
adf = pd.DataFrame(rows)
display(pretty_table(adf, caption="Regional and national anchors (cited alongside the ILO instruments)"))
print("These are the jurisdiction-specific laws a corridor-aware answer cites next to the ILO instrument.")'''

CONV_REACH = '''# How many indicators each instrument in the map speaks to (column sums of the indicator x convention map).
counts = {col: sum(1 for i in ILO_INDICATORS if col in INDICATOR_CONVENTION_MAP.get(i, [])) for col in CONVENTION_COLS}
order = sorted(CONVENTION_COLS, key=lambda c: counts[c])
vals = [counts[c] for c in order]
y = np.arange(len(order)); fig, ax = plt.subplots(figsize=(9.0, 0.5 * len(order) + 1.6))
ax.barh(y, vals, color=TEAL, edgecolor=PAPER, linewidth=1.0)
for yi, v in zip(y, vals):
    ax.text(v + 0.04, yi, str(v), va="center", fontsize=10.5, color=INK2, fontweight="bold")
ax.set_yticks(y); ax.set_yticklabels(order); ax.set_xlabel("indicators the instrument speaks to")
ax.set_xlim(0, max(vals) + 1); ax.grid(axis="y", alpha=0)
_title(ax, "Reach of each instrument across the indicators", "column sums of the indicative indicator x convention map")
plt.tight_layout(); plt.show()
print("Instrument reach:", counts)'''

# ---------------------------------------------------------------------------
# Section 3: fee-camouflage taxonomy.
# ---------------------------------------------------------------------------
FEE_BAR = '''# What the fee-camouflage labels really are: group each label by the unlawful thing it hides.
from collections import Counter
def _fee_family(instr):
    if "C181" in instr: return "worker-paid recruitment fee (C181 Art.7)"
    if "C029" in instr: return "exit penalty / hold (C029)"
    return "unlawful wage deduction / withholding (C095)"
fam = Counter(_fee_family(v[2]) for v in FEE_TAXONOMY.values())
order = sorted(fam, key=lambda k: fam[k])
vals = [fam[k] for k in order]
cols = [TEAL, WARN, EMBER][:len(order)]
y = np.arange(len(order)); fig, ax = plt.subplots(figsize=(9.8, 0.75 * len(order) + 1.8))
ax.barh(y, vals, color=cols, edgecolor=PAPER, linewidth=1.0)
for yi, v in zip(y, vals):
    ax.text(v + 0.05, yi, str(v), va="center", fontsize=11, color=INK2, fontweight="bold")
ax.set_yticks(y); ax.set_yticklabels(order); ax.set_xlabel("number of camouflage labels")
ax.set_xlim(0, max(vals) + 1); ax.grid(axis="y", alpha=0)
_title(ax, "Fee-camouflage labels by what they really are",
       str(len(FEE_TAXONOMY)) + " legitimate-sounding labels -- most are worker-paid recruitment fees banned by ILO C181 Art.7")
plt.tight_layout(); plt.show()
print("Families:", dict(fam))'''

FEE_TABLE = '''# The full taxonomy: the label, its plausible cover story, what it really is, and the instrument it engages.
rows = [{"camouflage label": k, "plausible cover": v[0], "what it really is": v[1], "instrument": v[2]}
        for k, v in FEE_TAXONOMY.items()]
fdf = pd.DataFrame(rows)
display(pretty_table(fdf, caption="Fee-camouflage taxonomy -- the legitimate-sounding label vs the worker-paid cost it hides"))
print(len(fdf), "labels here; DueCare publishes", KNOWLEDGE_SURFACE["fee_camouflage_labels"], "fee-camouflage labels in production.")'''

# ---------------------------------------------------------------------------
# Section 4: corridors & sectors.
# ---------------------------------------------------------------------------
CORRIDOR_TABLE = '''# Named migration corridors (origin -> destination) with the sectors each is known for.
rows = [{"corridor": c["corridor"], "origin": c["origin"], "destination": c["destination"],
         "sectors": ", ".join(c["sectors"]), "note": c["note"]} for c in CORRIDORS]
codf = pd.DataFrame(rows)
display(pretty_table(codf, caption="Named migration corridors in the reference layer"))
print(len(CORRIDORS), "corridors; DueCare publishes", KNOWLEDGE_SURFACE["corridor_fee_cap_entries"],
      "corridor fee-cap entries (volatile -> tool call, not hard-coded here).")'''

SECTOR_TABLE = '''# The seven sectors the harness reasons about, and the indicators each most often surfaces.
rows = [{"sector": s, "what to watch for": note} for s, note in SECTORS.items()]
sdf = pd.DataFrame(rows)
display(pretty_table(sdf, caption="Sectors and their characteristic forced-labour indicators"))
print(len(SECTORS), "sectors covered:", ", ".join(SECTORS.keys()))'''

CORRIDOR_SECTOR_HEAT = '''# Corridor x sector: an ILLUSTRATIVE emphasis grid drawn from each corridor's sector profile above
# (2 = the corridor's primary sector, 1 = also noted, 0 = not in the profile). This is a coverage map derived
# from the corridor notes, NOT measured incidence.
sector_cols = list(SECTORS.keys())
def _emph(corr, sec):
    secs = corr["sectors"]
    if not secs: return 0.0
    if sec == secs[0]: return 2.0
    return 1.0 if sec in secs else 0.0
row_labels = [c["corridor"] for c in CORRIDORS]
mat = [[_emph(c, sec) for sec in sector_cols] for c in CORRIDORS]
heatmap(mat, row_labels, sector_cols, cmap="BuGn", fmt=".0f", cbar_label="emphasis (2 primary / 1 noted / 0 none)",
        title="Corridor x sector: illustrative emphasis from each corridor's profile",
        subtitle="2 = the corridor's primary sector, 1 = also noted, 0 = not in the profile -- coverage, not measured incidence")
print("Illustrative only: this grid reflects which sectors each corridor's profile emphasizes, drawn from the notes above.")'''

# ---------------------------------------------------------------------------
# Section 5: referral pathways.
# ---------------------------------------------------------------------------
HOTLINE_TABLE = '''# Referral pathways -- where a worker or caseworker is routed. Documented, with the honest caveat.
rows = [{"region": k, "referral pathway": v} for k, v in HOTLINES.items() if k != "note"]
hdf = pd.DataFrame(rows)
display(pretty_table(hdf, caption="Referral pathways in the reference layer (verify the current number before use)"))
print("NOTE:", HOTLINES["note"])
print()
stat_cards([(str(len([k for k in HOTLINES if k != "note"])), "referral regions", TEAL),
            (str(KNOWLEDGE_SURFACE["ngo_contact_bundles"]), "NGO contact bundles (published)", EMBER),
            ("tool", "where live numbers live", WARN)])'''

# ---------------------------------------------------------------------------
# Section 6: how RAG works here -- worked retrieval.
# ---------------------------------------------------------------------------
RETRIEVE_ONE = '''# Worked retrieval on a single example: scan for indicators, pull the controlling instrument for each, cite.
example = ("I paid a large placement fee to the agency and I am still repaying it. On arrival the employer took "
           "my passport for safekeeping, and I have not been paid for two months.")
print("EXAMPLE TEXT:"); print(example); print()
res = retrieve_and_cite(example)
det = pd.DataFrame([{"indicator": d["label"], "matched cue": d["cue"], "controlling instrument": d["instrument"]}
                   for d in res["indicators"]])
display(pretty_table(det, caption="Matched indicators -> the ILO instrument each engages (the RAG retrieval step)"))
print("Risk:", res["risk"], "--", res["risk_reason"])
print("Citations the model would ground its answer in:")
for cite in res["citations"]:
    print("   -", cite)'''

RETRIEVE_BATCH = '''# The same retrieval over a small batch of short probes -- the layer cites the instrument every time,
# and stays quiet on the benign one.
probes = [
    "the recruiter charged a training bond I must work off before I get paid",
    "I have a stable factory job, paid on time, with one rest day a week",
    "my phone was taken and I am not allowed to leave the compound",
]
rows = []
for p in probes:
    r = retrieve_and_cite(p)
    rows.append({"probe": p,
                 "indicators found": ", ".join(d["label"] for d in r["indicators"]) or "(none)",
                 "cited instruments": " | ".join(r["citations"]) or "(none)",
                 "risk": r["risk"]})
bdf = pd.DataFrame(rows)
display(pretty_table(bdf, caption="Batch retrieval -- indicators found and the instruments cited for each probe"))
print("The benign probe returns no indicators and no citation -- the layer stays quiet when the text supports it.")'''

# ---------------------------------------------------------------------------
# Section 7: the downloadable facts pack.
# ---------------------------------------------------------------------------
FACTS_PACK = '''# Assemble everything into a single downloadable facts pack so a reader can take the facts.
import os, json, datetime

# Choose an output directory. An explicit DUECARE_FACTS_DIR override wins (used for offline validation so
# nothing is written to /kaggle/working); otherwise /kaggle/working on Kaggle; otherwise the current dir.
if os.environ.get("DUECARE_FACTS_DIR"):
    OUT_DIR = os.environ["DUECARE_FACTS_DIR"]
elif os.path.isdir("/kaggle/working"):
    OUT_DIR = "/kaggle/working"
else:
    OUT_DIR = os.getcwd()
os.makedirs(OUT_DIR, exist_ok=True)

facts_pack = {
    "meta": {
        "name": "DueCare Knowledge Base facts pack",
        "description": ("A grounded, ASCII, offline reference bundle: the ILO forced-labour indicators and the "
                        "instrument controlling each, key ILO conventions and regional / national anchors, the "
                        "fee-camouflage taxonomy, named migration corridors and sectors, and referral pathways."),
        "license": "MIT",
        "generated_by": "DueCare Knowledge Base Explorer (Kaggle notebook)",
        "source_repo": "https://github.com/TaylorAmarelTech/gemma4_comp",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "boundary": ("Stable reference facts (structure + citations). Volatile facts -- live hotline numbers, "
                     "current fee caps, fresh advisories -- come from a versioned tool call, not this pack."),
    },
    "knowledge_surface_as_published": KNOWLEDGE_SURFACE,
    "ilo_indicators": {
        "canonical_2012_set": {k: ILO_INDICATORS[k] for k in CANONICAL_11},
        "operational_extra": {k: ILO_INDICATORS[k] for k in OPERATIONAL_EXTRA},
        "controlling_instrument": ILO_REFS,
        "family": INDICATOR_GROUPS,
        "indicative_convention_map": INDICATOR_CONVENTION_MAP,
    },
    "ilo_conventions": ILO_CONVENTIONS,
    "regional_national_anchors": REGIONAL_ANCHORS,
    "fee_camouflage": {
        "labels": FEE_CAMOUFLAGE,
        "taxonomy": {k: {"plausible_cover": v[0], "what_it_really_is": v[1], "instrument": v[2]}
                     for k, v in FEE_TAXONOMY.items()},
    },
    "corridors": CORRIDORS,
    "sectors": SECTORS,
    "referral_pathways": HOTLINES,
}

blob = json.dumps(facts_pack, indent=2, ensure_ascii=True)
path = os.path.join(OUT_DIR, "duecare_facts_pack.json")
with open(path, "w", encoding="utf-8") as fh:
    fh.write(blob)

# Manifest: each top-level section and its entry count -- a non-lossy overview (no truncation).
manifest = pd.DataFrame([
    {"section": "meta", "entries": len(facts_pack["meta"])},
    {"section": "knowledge_surface_as_published", "entries": len(KNOWLEDGE_SURFACE)},
    {"section": "ilo_indicators.canonical_2012_set", "entries": len(CANONICAL_11)},
    {"section": "ilo_indicators.operational_extra", "entries": len(OPERATIONAL_EXTRA)},
    {"section": "ilo_conventions", "entries": len(ILO_CONVENTIONS)},
    {"section": "regional_national_anchors", "entries": len(REGIONAL_ANCHORS)},
    {"section": "fee_camouflage.taxonomy", "entries": len(FEE_TAXONOMY)},
    {"section": "corridors", "entries": len(CORRIDORS)},
    {"section": "sectors", "entries": len(SECTORS)},
    {"section": "referral_pathways", "entries": len([k for k in HOTLINES if k != "note"])},
])
display(pretty_table(manifest, caption="Facts pack contents -- each section and its entry count", bars=["entries"]))
print("wrote facts pack ->", path)
print("size:", len(blob), "bytes |", blob.count(chr(10)) + 1, "lines")
print()
print("PREVIEW -- the meta + knowledge_surface sections in full (the rest of the pack is on disk at the path above):")
print(json.dumps({"meta": facts_pack["meta"],
                  "knowledge_surface_as_published": facts_pack["knowledge_surface_as_published"]}, indent=2))'''


def _toc() -> str:
    items = [
        ("0", "How the knowledge layer feeds the harness", "overview"),
        ("1", "The 11 ILO indicators -> controlling convention", "indicators"),
        ("2", "ILO conventions and instruments", "conventions"),
        ("3", "Fee-camouflage taxonomy", "fees"),
        ("4", "Corridors and sectors", "corridors"),
        ("5", "Referral pathways", "referrals"),
        ("6", "How RAG works here (worked retrieval)", "rag"),
        ("7", "Downloadable facts pack", "factspack"),
        ("8", "Boundary and how to extend the knowledge base", "extend"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c: list = []

    # ---- Section 0: hero + what the layer is + TOC + boundary ----
    c.append(md(
        "# DueCare Knowledge Base Explorer\n\n"
        "**The grounded reference layer behind the Gemma 4 safety harness -- documented, visualized, and "
        "downloadable.** Before DueCare's model drafts a single word, it reasons over a *knowledge layer*: the "
        "ILO forced-labour indicators, the conventions that control them, the fee-camouflage labels a worker-paid "
        "cost hides behind, the migration corridors and sectors where the risk lives, and the referral pathways a "
        "worker is routed to. This notebook opens that layer up -- the **documents, the RAG facts, the indicator "
        "rules, the whole DueCare database** -- as readable tables and figures, and then writes it all out as a "
        "single **facts pack** you can take with you.\n\n"
        "**What the knowledge layer is.** Three stacked layers: **GREP indicators** (regex rules that spot the "
        "forced-labour cues), **RAG law** (a corpus that maps each cue to the controlling ILO instrument), and "
        "**tools** (versioned packs for the volatile facts -- live hotline numbers, current fee caps). The harness "
        "runs text through indicators, grounds each hit in the law, and calls tools for anything that changes over "
        "time -- so the model *reasons* with stable structure and *looks up* the volatile specifics.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** This notebook embeds a **representative, deterministic subset** of "
        "the DueCare knowledge surfaces so it runs fully offline (no dataset, no model, no internet). The counts it "
        "quotes for the full surfaces (451 GREP rules across 11 languages, 859 RAG documents, 16 ILO conventions, "
        "...) are stated **as published**. The reference facts here are **stable** (structure + citations); volatile "
        "operational data -- live hotline numbers, current fee caps, fresh advisories -- is deliberately **not** "
        "hard-coded and comes from a versioned tool call in production. Nothing here is legal advice or a "
        "trafficking determination."))

    # ---- Setup ----
    c.append(md(
        "## Setup -- run these two cells once\n\n"
        "The first cell embeds the DueCare notebook visualization toolkit **and** the grounded indicator engine "
        "(the ILO indicators, `ILO_REFS`, `FEE_CAMOUFLAGE`, `HOTLINES`, and the `scan()` / `risk_level()` logic). "
        "The second adds the curated reference facts this explorer documents -- `ILO_CONVENTIONS`, "
        "`REGIONAL_ANCHORS`, the fee-camouflage taxonomy, `CORRIDORS`, `SECTORS`, and the published surface counts. "
        "After both run, everything else is self-contained: **no dataset, no model, no internet.**"))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + ENGINE))
    c.append(code(REFERENCE_DEFS))

    # ---- Section 0 body ----
    c.append(md(
        '<a id="overview"></a>\n## 0 - How the knowledge layer feeds the harness\n\n'
        "A grounded answer is not one model call -- it is text flowing through three layers, each answering a "
        "different question:\n\n"
        "```\n"
        "worker text (stays local)\n"
        "      |\n"
        "  [1] GREP indicators   which ILO forced-labour indicators are present?      scan(text)\n"
        "      |                 (451 regex rules across 11 languages in production)\n"
        "  [2] RAG law           which instrument controls each hit? (C029, C095, ...) retrieve_and_cite(text)\n"
        "      |                 (859 documents: conventions, statutes, corridor facts)\n"
        "  [3] tools             the CURRENT number / fee cap / advisory to route to    tool(corridor, sector)\n"
        "      |                 (versioned knowledge packs -- volatile facts)\n"
        "  Gemma 4 drafts a cited, grounded answer\n"
        "```\n\n"
        "The stat tiles and table below show the surface counts (as published) and the three layers side by side."))
    c.append(code(PREVIEW_SURFACE))
    c.append(code(LAYERS))

    # ---- Section 1: indicators ----
    c.append(md(
        '<a id="indicators"></a>\n## 1 - The 11 ILO indicators -> controlling convention\n\n'
        "The backbone of the knowledge layer is the ILO's **2012 set of 11 forced-labour indicators**. DueCare "
        "tracks all 11 and adds `recruitment_fee` as an operational 12th cue (worker-paid recruitment fees, banned "
        "by **ILO C181 Art.7**). Every indicator maps to the instrument that controls it -- that mapping is what "
        "lets the model cite the *law*, not just flag a concern. Below: coverage tiles, the full "
        "indicator -> instrument table, and an indicator x convention heatmap."))
    c.append(code(INDICATOR_CARDS))
    c.append(code(INDICATOR_TABLE))
    c.append(code(INDICATOR_HEATMAP))

    # ---- Section 2: conventions ----
    c.append(md(
        '<a id="conventions"></a>\n## 2 - ILO conventions and instruments\n\n'
        "The instruments themselves, documented with a one-line scope each: the forced-labour anchors "
        "(**C029** + its **P029** protocol, **C105**), wage protection (**C095**), fair recruitment (**C181**), the "
        "migrant-worker instruments (**C097**, **C143**, **ICRMW**), domestic work (**C189**), violence and "
        "harassment (**C190**), and the accompanying recommendations (**R203**, **R204**) -- plus the regional and "
        "national anchors (**US TVPA**, **UK / AU / CA** modern-slavery and supply-chain acts, **Kuwait's** domestic "
        "worker law, the **CoE Warsaw Convention**) that operationalize them in a jurisdiction. The bar shows how "
        "far each instrument reaches across the indicators."))
    c.append(code(CONV_TABLE))
    c.append(code(ANCHOR_TABLE))
    c.append(code(CONV_REACH))

    # ---- Section 3: fee camouflage ----
    c.append(md(
        '<a id="fees"></a>\n## 3 - Fee-camouflage taxonomy\n\n'
        "Worker-paid recruitment fees are illegal under **ILO C181 Art.7**, so they are rarely called a "
        '"recruitment fee." They wear a legitimate-sounding label instead -- a *training bond*, a *mobilization '
        "fee*, a *sustainability fee*. This is the **relabel / camouflage** detection knowledge: each label paired "
        "with the cover story it uses, what it really is, and the instrument it breaches. The bar groups the labels "
        "by the unlawful thing they hide; the table is the full taxonomy."))
    c.append(code(FEE_BAR))
    c.append(code(FEE_TABLE))

    # ---- Section 4: corridors & sectors ----
    c.append(md(
        '<a id="corridors"></a>\n## 4 - Corridors and sectors\n\n'
        "Risk is not evenly spread -- it concentrates in specific **migration corridors** (Nepal -> Qatar, "
        "Myanmar -> Thailand, Ethiopia -> Lebanon, ...) and **sectors** (domestic work, construction, agriculture, "
        "fishing, manufacturing, hospitality, care). Below: the corridor table (origin -> destination + the sectors "
        "each is known for), the sector table (what to watch for in each), and an **illustrative** corridor x sector "
        "emphasis grid derived from the corridor profiles -- a coverage map, not measured incidence."))
    c.append(code(CORRIDOR_TABLE))
    c.append(code(SECTOR_TABLE))
    c.append(code(CORRIDOR_SECTOR_HEAT))

    # ---- Section 5: referral pathways ----
    c.append(md(
        '<a id="referrals"></a>\n## 5 - Referral pathways\n\n'
        "Detection is only useful if it ends in **help**. The referral layer routes a worker or caseworker to the "
        "right resource by region. The honest part: the specific phone numbers are **volatile** -- they change, and "
        'getting one wrong is worse than saying "verify the current number." So in production the live numbers '
        "come from a **versioned knowledge pack / tool call**, never from the model's memory. The table documents "
        "the pathways; the note states the caveat plainly."))
    c.append(code(HOTLINE_TABLE))

    # ---- Section 6: how RAG works ----
    c.append(md(
        '<a id="rag"></a>\n## 6 - How RAG works here (a worked retrieval)\n\n'
        "Retrieval, made concrete. `retrieve_and_cite()` runs the same two steps the harness does before Gemma 4 "
        "answers: **scan** the text for indicators, then **pull** the controlling ILO instrument for each hit and "
        "assemble the citation list. The single example shows the full retrieval on one account; the batch shows it "
        "over several short probes -- and shows the layer staying **quiet** on a benign one (no indicator, no "
        "citation)."))
    c.append(code(RETRIEVE_ONE))
    c.append(code(RETRIEVE_BATCH))

    # ---- Section 7: facts pack ----
    c.append(md(
        '<a id="factspack"></a>\n## 7 - Downloadable facts pack\n\n'
        "Everything above, assembled into one JSON **facts pack** and written to `duecare_facts_pack.json` (in "
        "`/kaggle/working` on Kaggle) so a reader can take the facts: the indicators and their instruments, the "
        "conventions and anchors, the fee-camouflage taxonomy, the corridors and sectors, and the referral "
        "pathways. The cell prints the path, the size, a section-by-section manifest, and a full (non-truncated) "
        "preview of the `meta` and `knowledge_surface` sections."))
    c.append(code(FACTS_PACK))

    # ---- Section 8: boundary + how to extend + links ----
    c.append(md(
        '<a id="extend"></a>\n## 8 - Boundary and how to extend the knowledge base\n\n'
        "**How to extend it.** The knowledge layer is meant to grow. To add coverage:\n\n"
        "1. **Add an indicator** -- append it to `ILO_INDICATORS` with a clear label, add a `PATTERNS` regex that "
        "spots it, and (critically) **attach its instrument** in `ILO_REFS` so every hit can cite the law.\n"
        "2. **Add a convention / anchor** -- add an entry to `ILO_CONVENTIONS` (or `REGIONAL_ANCHORS`) with its "
        "one-line scope, and wire it into `INDICATOR_CONVENTION_MAP` for the indicators it governs.\n"
        "3. **Add a corridor** -- append to `CORRIDORS` with `origin`, `destination`, the `sectors` it is known for, "
        "and a one-line note; the corridor x sector grid picks it up automatically.\n"
        "4. **Keep volatile facts out of the model** -- a new hotline number or fee cap goes in a **versioned tool "
        "pack**, not a training target, so it can be updated without retraining.\n\n"
        "**Boundary.** This is a representative, offline subset for documentation and reuse. It is **not** legal "
        "advice, **not** a trafficking determination, and **not** the full production harness -- which uses the "
        "complete GREP layer (451 rules across 11 languages), retrieval over the full corpus, and **Gemma 4** for "
        "the reasoning. Every worker example here is composite / synthetic (no real people, no real PII).\n\n"
        "### Use the data\n"
        f"- **Take the facts:** download `duecare_facts_pack.json` from this notebook's output.\n"
        f"- **Explore the grades:** the public [`{DATASET_ID.split('/')[1]}`]({DS}) dataset carries the DueCare "
        "harness-lift benchmark grades; the interactive workbench exposes a **/data** page over these knowledge "
        "surfaces.\n"
        f"- **Go to source:** the [repository]({REPO}) has the full harness, the knowledge packs, the grader, and "
        "the fine-tuning path.\n\n"
        "License: MIT. Reference facts and citations only -- no PII.\n\n"
        "[Back to contents](#overview)"))

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
    assert "DueCare Knowledge Base Explorer".lower().replace(" ", "-") == "duecare-knowledge-base-explorer"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
