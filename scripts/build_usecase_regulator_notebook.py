#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Regulator Compliance use-case Kaggle notebook.

An applied, easy-to-use notebook for a labour ministry / regulator (BP2MI, POEA, a national labour
inspectorate). It batch-audits worker submissions or recruitment-agency filings and produces a
jurisdiction-level compliance report: the forced-labour indicators each filing contains, the risk
band, the controlling ILO instrument, a jurisdiction x risk rollup, an indicator-frequency profile,
a sector breakdown, and a risk-weighted enforcement queue so inspectors work the highest-risk
filings first.

The notebook is FULLY SELF-CONTAINED on Kaggle: no dataset, no model, no internet. The first code
cell embeds two builder-time toolkits -- the shared DueCare notebook visualization helpers
(scripts/_notebook_viz.py) AND the grounded DueCare indicator engine (scripts/_usecase_engine.py:
scan / risk_level / generate_chain plus the ILO knowledge maps). It is a REPRESENTATIVE,
deterministic subset of the real 451-rule GREP layer + ILO knowledge packs; production uses the full
harness with retrieval and Gemma 4 reasoning.

    python scripts/build_usecase_regulator_notebook.py

ASCII-only (no Kaggle mojibake). No [:N] truncation of any displayed filing or result.
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "usecase_regulator"
KERNEL_ID = "taylorsamarel/duecare-regulator-compliance"
TITLE = "DueCare Regulator Compliance"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

# ---------------------------------------------------------------------------
# Cell 4: audit() + aggregates + compliance_report() + renderers. Pure, offline.
# Runs in the same namespace as the embedded PALETTE/HELPERS/ENGINE cell.
# ---------------------------------------------------------------------------
AUDIT_DEFS = '''from collections import Counter
try:                                     # IPython on Kaggle; a headless fallback so the notebook always runs
    from IPython.display import display, HTML, Markdown
except Exception:
    def display(*a, **k):
        for x in a: print(getattr(x, "data", x))
    def HTML(s): return s
    def Markdown(s): return s

RISK_ORDER = ["HIGH", "ELEVATED", "WATCH", "LOW"]
RISK_COLOR = {"HIGH": EMBER, "ELEVATED": WARN, "WATCH": TEAL, "LOW": GOOD}
RISK_RANK = {"HIGH": 3, "ELEVATED": 2, "WATCH": 1, "LOW": 0}
RISK_FG = {"HIGH": "#7a2e12", "ELEVATED": "#7a5a1e", "WATCH": "#1f5a66", "LOW": "#2f5a3a"}
RISK_BG = {"HIGH": "#f0d8c8", "ELEVATED": "#efe3cf", "WATCH": "#cfe3e6", "LOW": "#d8e8dc"}

# Which enforcement action a dominant indicator implies (a regulator's playbook, ILO-grounded).
ENFORCEMENT_FOCUS = {
    "document_retention": "Passport / ID-retention inspections at employer premises (retention of documents is an ILO C029 forced-labour indicator).",
    "recruitment_fee": "Audit licensed recruitment agencies' fee structures against the corridor cap; worker-paid recruitment fees breach ILO C181 Art.7.",
    "wage_withholding": "Wage-payment audits and back-pay orders (ILO C095, Protection of Wages).",
    "debt_bondage": "Investigate advance / loan-linked debt bondage and void unlawful wage deductions (ILO C029 Art.2; R203).",
    "restriction_of_movement": "Inspect for confinement and freedom-to-leave violations at worksites and accommodation.",
    "intimidation": "Anti-retaliation and whistleblower-protection enforcement (threats to report workers to immigration).",
    "deception": "Verify that written contracts match the terms workers were promised at recruitment (ILO C181).",
    "excessive_overtime": "Hours-of-work and weekly-rest-day compliance checks (ILO C001 / C030).",
    "isolation": "Inspect for confiscated phones and blocked communication in live-in and vessel-based work.",
    "abuse_of_vulnerability": "Targeted protection for first-time and non-local-language migrant workers (ICRMW Art.21).",
    "violence": "Immediate referral to criminal enforcement and victim protection (ILO C029; C190).",
    "abusive_conditions": "Housing, food, water, and occupational-safety inspections of worker accommodation.",
}
_LABEL2KEY = {v: k for k, v in ILO_INDICATORS.items()}
_LABEL2KEY["Recruitment fee charged to the worker (camouflaged)"] = "recruitment_fee"

def audit(submissions):
    """Batch-audit worker submissions or agency filings into a compliance DataFrame.

    Each submission is a dict: {id, jurisdiction, sector, text}. Returns one row per submission --
    id, jurisdiction, sector, n_indicators, risk band, the detected ILO indicators, and the top
    controlling ILO instrument. Deterministic, offline, CPU-only -- a representative subset of the
    DueCare harness.
    """
    rows = []
    for s in submissions:
        text = s.get("text", "")
        hits = scan(text)
        level, _why = risk_level(hits)
        rows.append({
            "id": s.get("id", ""),
            "jurisdiction": s.get("jurisdiction", ""),
            "sector": s.get("sector", ""),
            "n_indicators": len(hits),
            "risk": level,
            "indicators": ", ".join(h["label"] for h in hits) or "(none)",
            "top_ilo_ref": hits[0]["ilo_ref"] if hits else "",
        })
    return pd.DataFrame(rows, columns=["id", "jurisdiction", "sector", "n_indicators", "risk", "indicators", "top_ilo_ref"])

def color_risk(sty):
    """Tint the `risk` cells of a Styler by their risk color."""
    def _c(v): return "color:%s;font-weight:700" % RISK_COLOR.get(v, INK2)
    try:
        return sty.map(_c, subset=["risk"])
    except Exception:
        return sty.applymap(_c, subset=["risk"])

def jurisdiction_risk_matrix(df):
    """Return (jurisdictions, risk_order, counts) for a jurisdiction x risk-band rollup."""
    juris = sorted(df["jurisdiction"].unique())
    mat = [[int(((df.jurisdiction == j) & (df.risk == r)).sum()) for r in RISK_ORDER] for j in juris]
    return juris, RISK_ORDER, mat

def indicator_frequency(df):
    """Counter of ILO indicator label -> times it appears across the audited batch."""
    freq = Counter()
    for cell in df["indicators"]:
        if cell and cell != "(none)":
            for lab in cell.split(", "):
                freq[lab] += 1
    return freq

def enforcement_queue(df):
    """Risk-weighted enforcement queue: priority = risk_rank * 10 + n_indicators, highest first."""
    q = df.copy()
    q["priority"] = q["risk"].map(RISK_RANK) * 10 + q["n_indicators"]
    return q.sort_values("priority", ascending=False).reset_index(drop=True)

def compliance_report(df):
    """Emit a jurisdiction-level compliance summary as Kaggle-safe HTML (no flex / script / max-height).

    For every jurisdiction: counts by risk band, the most frequent forced-labour indicators, and a
    recommended enforcement focus derived from the dominant indicator. Displays and returns the HTML.
    """
    blocks = []
    for j in sorted(df["jurisdiction"].unique()):
        sub = df[df.jurisdiction == j]
        counts = {lv: int((sub.risk == lv).sum()) for lv in RISK_ORDER}
        cfreq = indicator_frequency(sub)
        top = cfreq.most_common(3)
        dom_key = _LABEL2KEY.get(top[0][0]) if top else None
        focus = ENFORCEMENT_FOCUS.get(dom_key, "No dominant indicator yet -- keep filings on file and monitor.")
        pills = "".join(
            "<span style='display:inline-block;background:" + RISK_BG[lv] + ";color:" + RISK_FG[lv] +
            ";border-radius:10px;padding:2px 10px;margin:2px 6px 2px 0;font-size:11.5px;font-weight:700'>" +
            lv + ": " + str(counts[lv]) + "</span>" for lv in RISK_ORDER)
        toph = ", ".join(lab + " (" + str(n) + ")" for lab, n in top) if top else "none detected"
        blocks.append(
            "<div style='background:#F7F6F1;border:1px solid #DDD8C9;border-left:6px solid " + TEAL +
            ";border-radius:10px;padding:13px 16px;margin:0 0 12px'>"
            "<div style='font-size:14px;font-weight:700;color:#14181B'>" + j +
            " <span style='color:#5B5F68;font-weight:500'>(" + str(len(sub)) + " submissions)</span></div>"
            "<div style='margin:8px 0'>" + pills + "</div>"
            "<div style='font-size:12.5px;color:#2A2D34'><b>Most frequent indicators:</b> " + toph + "</div>"
            "<div style='font-size:12.5px;color:#2A2D34;margin-top:5px'><b>Recommended enforcement focus:</b> " + focus + "</div>"
            "</div>")
    n_high = int((df.risk == "HIGH").sum())
    header = ("<div style='font-family:Inter,-apple-system,system-ui,sans-serif;max-width:780px'>"
              "<div style='font-size:16px;font-weight:700;color:#14181B;margin-bottom:4px'>Compliance report</div>"
              "<div style='font-size:12.5px;color:#5B5F68;margin-bottom:12px'>" + str(len(df)) +
              " submissions audited across " + str(df.jurisdiction.nunique()) + " jurisdictions; " +
              str(n_high) + " flagged HIGH. Composite / synthetic data -- not a real caseload, not a legal finding.</div>")
    html = header + "".join(blocks) + "</div>"
    display(HTML(html))
    return html

print("audit() ready. Tracking", len(ILO_INDICATORS), "ILO indicators;",
      len(PATTERNS), "demo indicator rules;", len(FEE_CAMOUFLAGE), "fee-camouflage labels.")
_smoke = audit([{"id": "SMOKE", "jurisdiction": "Destination-B", "sector": "domestic work",
                 "text": "The employer took my passport and I have not been paid for two months."}])
print("smoke ->", "risk:", _smoke.iloc[0]["risk"], "| indicators:", _smoke.iloc[0]["n_indicators"])'''

# ---------------------------------------------------------------------------
# Cell 6: TRY YOUR OWN -- the paste cell, placed early so it is obvious.
# ---------------------------------------------------------------------------
TRY = '''# ============================================================================
#  TRY YOUR OWN -- edit the list of submissions and run. Each submission is a
#  dict: {id, jurisdiction, sector, text}. Composite / test data only, please --
#  no real PII in a shared notebook.
# ============================================================================
my_submissions = [
    {"id": "A-1", "jurisdiction": "Destination-B", "sector": "domestic work",
     "text": """The employer took my passport when I arrived and I have not been paid for two months.
I must work off the recruitment fee first, and I am not allowed to leave the house."""},
    {"id": "A-2", "jurisdiction": "Origin-A", "sector": "construction",
     "text": """A licensed agency offered a construction job abroad with an employer-paid fee, a written
contract, and wages paid monthly on time. Please verify the agency is registered."""},
]
my_audit = audit(my_submissions)
display(color_risk(pretty_table(my_audit, caption="Your submissions, audited by DueCare", bars=["n_indicators"])))
compliance_report(my_audit)
print("Edit my_submissions above and re-run. Risk banding: HIGH 4+, ELEVATED 2-3, WATCH 1, LOW 0 indicators.")'''

# ---------------------------------------------------------------------------
# Cell 8: how enforcement prioritization works -- layers, banding, weighting.
# ---------------------------------------------------------------------------
HOWITWORKS = '''# audit() is three deterministic layers, then a risk band, then a priority weight.
stat_cards([(len(ILO_INDICATORS), "ILO indicators tracked", TEAL),
            (len(PATTERNS), "demo indicator rules", INK2),
            (len(FEE_CAMOUFLAGE), "fee-camouflage labels", WARN),
            ("451", "GREP rules in production", EMBER)])

layers = pd.DataFrame({
    "step": ["1. Indicator scan", "2. ILO knowledge", "3. Risk band", "4. Priority weight"],
    "what it does": [
        "match forced-labour cues in each submission (a representative subset of 451 GREP rules)",
        "map every hit to the controlling ILO instrument (C029, C095, C181, ICRMW, ...)",
        "count indicators -> HIGH / ELEVATED / WATCH / LOW (risk_level)",
        "rank the queue so the filings most likely to conceal forced labour are inspected first"],
    "engine call": ["scan(text)", "ILO_REFS / ILO_INDICATORS", "risk_level(hits)", "enforcement_queue(df)"]})
display(pretty_table(layers, caption="How audit() reaches a compliance decision -- four transparent steps, all on-device"))

thr = pd.DataFrame({
    "indicators found": ["4 or more", "2 - 3", "1", "0"],
    "risk band": RISK_ORDER,
    "enforcement action it implies": ["open an inspection now",
                                      "schedule a review / request records",
                                      "request clarification from the filer",
                                      "no action -- keep on file, absence is not proof of safety"]})
display(pretty_table(thr, caption="Risk banding and the enforcement action each band implies"))
print("A regulator's inspection capacity is finite. Risk weighting puts the highest-risk filings at the top of the queue,")
print("so scarce inspector time is spent where forced labour is most likely to be concealed.")'''

# ---------------------------------------------------------------------------
# Cell 10: the synthetic submissions -- ~10 across 3 jurisdictions + 3 sectors.
# ---------------------------------------------------------------------------
SUBMISSIONS_DEF = '''# ~10 COMPOSITE / SYNTHETIC submissions across 3 jurisdictions and 3 sectors. No real people, no PII.
# Jurisdictions: Origin-A (a labour-sending state), Destination-B and Destination-C (receiving states).
SUBMISSIONS = [
    {"id": "SUB-001", "jurisdiction": "Destination-B", "sector": "domestic work",
     "text": """The employer took my passport on arrival and I have not been paid for three months. I am told
I must work off the recruitment fee before I receive wages, I am not allowed to leave the house, and there is
no day off."""},
    {"id": "SUB-002", "jurisdiction": "Destination-B", "sector": "construction",
     "text": """The company has not paid our wages for two months and keeps saying the money will come later.
The foreman threatened to report us to immigration if we complain. We sleep in a crowded room."""},
    {"id": "SUB-003", "jurisdiction": "Destination-C", "sector": "fishing",
     "text": """The broker charged a large placement fee and I am still repaying the debt and cannot leave until
it is paid off. My phone was taken so I cannot contact my family, and the captain keeps our identity documents
on board."""},
    {"id": "SUB-004", "jurisdiction": "Origin-A", "sector": "construction",
     "text": """An agency offered me a construction job abroad and asked for a placement fee of 2,000 before I
leave. The pay and hours sound normal."""},
    {"id": "SUB-005", "jurisdiction": "Origin-A", "sector": "domestic work",
     "text": """The recruiter promised a salary that turned out to be different, and I was told I must pay a
training bond before departure. I do not speak the destination language."""},
    {"id": "SUB-006", "jurisdiction": "Destination-C", "sector": "domestic work",
     "text": """They keep my passport for safekeeping, no phone is allowed during work hours, I sleep on the
floor in a crowded room, and I work seven days a week with no rest."""},
    {"id": "SUB-007", "jurisdiction": "Destination-B", "sector": "fishing",
     "text": """The recruiter said it would be office work; actually it is fishing at sea for weeks. We cannot
contact our families, and the wages are deducted each month."""},
    {"id": "SUB-008", "jurisdiction": "Origin-A", "sector": "fishing",
     "text": """A licensed manning agency offered a fishing contract with employer-paid costs, a written
contract, and monthly wages paid on time. I would like to verify the agency is registered."""},
    {"id": "SUB-009", "jurisdiction": "Destination-C", "sector": "construction",
     "text": """Our pay is deducted for tools and transport, but the job is otherwise as described and we can
come and go freely."""},
    {"id": "SUB-010", "jurisdiction": "Destination-B", "sector": "domestic work",
     "text": """I am a first time abroad and do not speak the language. They took my documents, threatened to
deport me if I complain, and I have not been paid."""},
]
print("defined", len(SUBMISSIONS), "composite submissions across",
      len({s["jurisdiction"] for s in SUBMISSIONS}), "jurisdictions and",
      len({s["sector"] for s in SUBMISSIONS}), "sectors.")'''

AUDIT_TABLE = '''# Audit the whole batch. AUD is reused by every rollup below.
AUD = audit(SUBMISSIONS)
display(color_risk(pretty_table(AUD, bars=["n_indicators"],
        caption="Per-submission audit -- indicators, risk band, and the top controlling ILO instrument (full text preserved in SUBMISSIONS)")))
print("risk mix:", {lv: int((AUD.risk == lv).sum()) for lv in RISK_ORDER})'''

# ---------------------------------------------------------------------------
# Cell 12-13: jurisdiction x risk heatmap.
# ---------------------------------------------------------------------------
HEATMAP = '''juris, order, mat = jurisdiction_risk_matrix(AUD)
heatmap(mat, juris, order, title="Submissions by jurisdiction x risk band",
        subtitle="where the highest-risk filings concentrate", cmap="OrRd", fmt=".0f", cbar_label="submissions")
print("jurisdiction x risk rollup:")
for j, row in zip(juris, mat):
    print("   " + j + ": " + ", ".join("%s=%d" % (lv, n) for lv, n in zip(order, row)))'''

# ---------------------------------------------------------------------------
# Cell 14-15: indicator-frequency bar.
# ---------------------------------------------------------------------------
FREQ = '''freq = indicator_frequency(AUD)
if freq:
    pairs = sorted(freq.items(), key=lambda kv: kv[1])
    labs = [p[0] for p in pairs]; vals = [p[1] for p in pairs]
    fig, ax = plt.subplots(figsize=(9.8, 0.5 * len(labs) + 1.7))
    ax.barh(range(len(labs)), vals, color=TEAL, edgecolor=PAPER, linewidth=0.9)
    for i, v in enumerate(vals):
        ax.text(v + 0.05, i, str(v), va="center", fontsize=10, color=INK3)
    ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs)
    ax.set_xlabel("times detected across the batch"); ax.set_xlim(0, max(vals) + 1); ax.grid(axis="y", alpha=0)
    _title(ax, "Which forced-labour indicators show up most",
           "ILO 2012 indicators the scan flagged across the audited filings")
    plt.tight_layout(); plt.show()
    print("most frequent:", freq.most_common(3))
else:
    print("no indicators detected in the batch")'''

# ---------------------------------------------------------------------------
# Cell 16-17: sector breakdown.
# ---------------------------------------------------------------------------
SECTOR = '''sectors = sorted(AUD["sector"].unique())
rows = []
for s in sectors:
    sub = AUD[AUD.sector == s]
    row = {"sector": s, "submissions": len(sub)}
    for lv in RISK_ORDER:
        row[lv] = int((sub.risk == lv).sum())
    row["avg indicators"] = round(float(sub.n_indicators.mean()), 2)
    rows.append(row)
sec = pd.DataFrame(rows)
display(pretty_table(sec, caption="Sector breakdown -- risk mix and average indicator load per sector",
                     bars=["avg indicators"], gradient=["HIGH"], cmap="OrRd"))

vals = list(sec["avg indicators"])
fig, ax = plt.subplots(figsize=(8.4, 3.9))
bars = ax.bar(sectors, vals, color=SEQ[:len(sectors)], edgecolor=PAPER, linewidth=1.1, width=0.6)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom", fontsize=11, fontweight="bold", color=INK2)
ax.set_ylabel("avg forced-labour indicators"); ax.set_ylim(0, max(vals) + 0.6); ax.grid(axis="x", alpha=0)
_title(ax, "Average indicator load by sector", "which sectors carry the most risk in this batch")
plt.tight_layout(); plt.show()'''

# ---------------------------------------------------------------------------
# Cell 19: the compliance report.
# ---------------------------------------------------------------------------
REPORT = '''# The jurisdiction-level compliance report: counts by risk, top indicators, and the recommended
# enforcement focus for each jurisdiction. Kaggle-safe HTML (inline styles only -- no flex / script).
_ = compliance_report(AUD)'''

# ---------------------------------------------------------------------------
# Cell 20: the reasoned audit trail (defensible enforcement).
# ---------------------------------------------------------------------------
CHAIN = '''# A regulator's finding has to be defensible. generate_chain() exposes the reasoning behind a single
# audit: restate neutrally, ask one question per ILO indicator, walk the recruitment-to-remedy lifecycle,
# then run counterfactual checks. This is the audit trail an inspector can attach to a case file.
top_id = enforcement_queue(AUD).iloc[0]["id"]
top_text = next(s["text"] for s in SUBMISSIONS if s["id"] == top_id)
chain = generate_chain(top_text)
cdf = pd.DataFrame(chain, columns=["step", "reasoning"])
display(pretty_table(cdf, caption="generate_chain() -- the audit trail behind the highest-priority filing (" + top_id + ")"))
present = sum(1 for _, t in chain if "PRESENT" in t)
print("chain length:", len(chain), "steps |", present, "indicators marked PRESENT |",
      "lifecycle stages:", len(LIFECYCLE), "| counterfactual checks:", len(COUNTERFACTUALS))'''

# ---------------------------------------------------------------------------
# Cell 22: the risk-weighted enforcement queue.
# ---------------------------------------------------------------------------
QUEUE = '''# The enforcement queue: risk-weighted so inspectors work the highest-risk filings first.
Q = enforcement_queue(AUD)
q_show = Q[["id", "jurisdiction", "sector", "risk", "n_indicators", "priority", "indicators"]]
display(color_risk(pretty_table(q_show, bars=["priority"],
        caption="Risk-weighted enforcement queue -- inspect from the top (priority = risk rank x 10 + indicators)")))

labs = [r.id + "  " + r.risk for r in Q.itertuples()]
vals = list(Q["priority"])
fig, ax = plt.subplots(figsize=(9.8, 0.42 * len(labs) + 1.5))
ax.barh(range(len(labs)), vals, color=[RISK_COLOR[r] for r in Q["risk"]], edgecolor=PAPER, linewidth=0.9)
for i, v in enumerate(vals):
    ax.text(v + 0.1, i, str(v), va="center", fontsize=9.5, color=INK3)
ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs); ax.invert_yaxis()
ax.set_xlabel("priority weight"); ax.set_xlim(0, max(vals) + 3); ax.grid(axis="y", alpha=0)
_title(ax, "Enforcement queue by priority weight", "highest-risk filings first")
plt.tight_layout(); plt.show()
print("queue size:", len(Q), "| HIGH:", int((Q.risk == "HIGH").sum()), "| inspect first:", Q.iloc[0]["id"])'''

# ---------------------------------------------------------------------------
# Cell 24: trust boundary -- what stays in the regulator's environment.
# ---------------------------------------------------------------------------
BOUNDARY = '''# The data-flow boundary, made explicit. Nothing here calls out; audit() is pure local Python.
flow = pd.DataFrame({
    "data": ["raw worker submissions / agency filings (names, IDs, contact details)",
             "the structured audit() result (indicators, risk, citations)",
             "the jurisdiction-level compliance report",
             "anonymized cross-border aggregate (counts by risk / indicator)"],
    "where it lives": ["the regulator's own environment only",
                       "the regulator's own environment only",
                       "the regulator's own environment only",
                       "shared with another authority only after anonymization + human approval"],
    "leaves the environment?": ["never", "never", "never by default", "only aggregates, only after approval"]})
display(pretty_table(flow, caption="Trust boundary -- submissions stay in the regulator's environment"))

stat_cards([("0", "raw submissions leave by default", GOOD),
            ("on-prem", "where audit() runs", TEAL),
            ("aggregates", "all that crosses a border", EMBER)])
print("Cross-border cooperation shares only anonymized aggregates -- counts by risk and indicator -- never raw case text.")
print("In production the DueCare anonymizer (a hard PII gate) redacts names, IDs, and phone numbers before any share.")'''


def _toc() -> str:
    items = [
        ("1", "Try your own submissions", "try"),
        ("2", "How enforcement prioritization works", "how"),
        ("3", "A worked batch: audit, rollups, and the report", "batch"),
        ("4", "The compliance report + audit trail", "report"),
        ("5", "The risk-weighted enforcement queue", "queue"),
        ("6", "Trust boundary: submissions stay in your environment", "boundary"),
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
        "# DueCare Regulator Compliance\n\n"
        "**For a labour ministry, migrant-worker authority, or labour inspectorate** -- the kind of office that "
        "runs a BP2MI, a POEA, or a national labour inspection service. Recruitment agencies file, workers submit "
        "complaints, and the pile grows faster than inspectors can read it. This notebook turns a batch of "
        "submissions or agency filings into a **jurisdiction-level compliance report** in seconds: the forced-labour "
        "indicators each filing contains, the risk band, the exact ILO instrument each indicator engages, a "
        "jurisdiction-by-risk rollup, an indicator-frequency profile, a sector breakdown, and a **risk-weighted "
        "enforcement queue** so scarce inspector time goes to the filings most likely to conceal forced labour -- "
        "all **inside your own environment**, with no model, no internet, and nothing leaving the machine.\n\n"
        "**The problem it helps with.** A regulator cannot inspect every filing, and the dangerous ones look almost "
        "exactly like compliant ones. `audit()` gives every submission the same structured, ILO-grounded first pass, "
        "so nothing obvious is missed, patterns across a jurisdiction become visible, and the urgent cases rise to "
        "the top of the queue.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** This notebook runs a **representative, deterministic subset** of the "
        "DueCare harness -- a compact indicator scanner plus the ILO knowledge map -- so it is fully reproducible "
        "offline. It is a triage and prioritization aid: **not** a trafficking determination, **not** a legal "
        "finding, and **not** a substitute for a trained inspector or due process. Every submission here is "
        "composite / synthetic (no real people, no real PII). Production DueCare uses the full 451-rule GREP layer, "
        "retrieval, and Gemma 4 reasoning (see the final section)."))

    # ---- Setup ----
    c.append(md(
        "## Setup -- run these two cells once\n\n"
        "The first cell embeds the DueCare notebook visualization toolkit **and** the grounded indicator engine "
        "(the ILO indicators, the `scan()` / `risk_level()` / `generate_chain()` logic, and the knowledge maps). "
        "The second defines `audit()`, the aggregates, and `compliance_report()`. After both run, everything else "
        "is self-contained: **no dataset, no model, no internet.**"))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + ENGINE))
    c.append(code(AUDIT_DEFS))

    # ---- Section 1: TRY YOUR OWN ----
    c.append(md(
        '<a id="try"></a>\n## 1 - Try your own submissions\n\n'
        "**Edit the `my_submissions` list in the next cell** -- each entry is a dict with `id`, `jurisdiction`, "
        "`sector`, and `text` (composite or test data, please: no real PII in a shared notebook) -- and run it. "
        "`audit()` returns a compliance DataFrame and `compliance_report()` prints the jurisdiction-level summary. "
        "Everything runs locally.\n\n"
        "*(Run the two setup cells above first -- they embed the visualization toolkit and the DueCare indicator "
        "engine so the notebook is completely self-contained.)*"))
    c.append(code(TRY))

    # ---- Section 2: how prioritization works ----
    c.append(md(
        '<a id="how"></a>\n## 2 - How enforcement prioritization works\n\n'
        "`audit()` is four small, transparent steps -- no black box:\n\n"
        "```\n"
        "worker submissions / agency filings (raw text, stays in your environment)\n"
        "        |\n"
        "  [1] indicator scan   regex cues for the ILO forced-labour indicators\n"
        "        |              (a representative subset of the 451-rule DueCare GREP layer)\n"
        "  [2] ILO knowledge    map each hit to its controlling instrument (C029, C095, C181, ICRMW, ...)\n"
        "        |\n"
        "  [3] risk band        count indicators -> HIGH / ELEVATED / WATCH / LOW\n"
        "        |\n"
        "  [4] priority weight  rank the queue so the highest-risk filings are inspected first\n"
        "        |\n"
        "  compliance report + enforcement queue (structured, reviewable, no raw text leaves)\n"
        "```\n\n"
        "The next cell shows the coverage, the four-step map, and the risk banding with the enforcement action each "
        "band implies."))
    c.append(code(HOWITWORKS))

    # ---- Section 3: worked batch ----
    c.append(md(
        '<a id="batch"></a>\n## 3 - A worked batch: audit, rollups, and the report\n\n'
        "Ten **composite / synthetic** submissions across three jurisdictions (an origin state and two destination "
        "states) and three sectors (domestic work, construction, fishing). `audit()` produces the per-submission "
        "compliance table; then a jurisdiction-by-risk heatmap, an indicator-frequency profile, and a sector "
        "breakdown show the patterns a regulator actually acts on. Full submission text is preserved -- nothing is "
        "truncated."))
    c.append(code(SUBMISSIONS_DEF))
    c.append(code(AUDIT_TABLE))
    c.append(md(
        "### 3A - Jurisdiction x risk rollup\n"
        "Where do the highest-risk filings concentrate? The heatmap counts submissions in each jurisdiction by risk "
        "band, so a supervisor can see at a glance which corridor needs attention."))
    c.append(code(HEATMAP))
    c.append(md(
        "### 3B - Indicator frequency\n"
        "Which forced-labour indicators drive the flags across the whole batch? Frequency tells a regulator which "
        "abuse pattern -- passport retention, worker-paid fees, wage withholding -- is most common in this caseload."))
    c.append(code(FREQ))
    c.append(md(
        "### 3C - Sector breakdown\n"
        "Risk is not spread evenly across sectors. This breakdown shows the risk mix and the average indicator load "
        "per sector, so inspection resources can be steered to the sectors carrying the most risk."))
    c.append(code(SECTOR))

    # ---- Section 4: the compliance report + audit trail ----
    c.append(md(
        '<a id="report"></a>\n## 4 - The compliance report + audit trail\n\n'
        "`compliance_report()` rolls the audit up to the level a regulator reports and acts on: for each "
        "jurisdiction, the counts by risk band, the most frequent indicators, and a **recommended enforcement "
        "focus** derived from the dominant indicator (each tied to the controlling ILO instrument). It is rendered "
        "as Kaggle-safe inline-styled HTML. The second cell shows the **reasoned audit trail** behind the "
        "highest-priority filing -- the defensible, step-by-step record an inspector can attach to a case file."))
    c.append(code(REPORT))
    c.append(code(CHAIN))

    # ---- Section 5: the enforcement queue ----
    c.append(md(
        '<a id="queue"></a>\n## 5 - The risk-weighted enforcement queue\n\n'
        "Inspection capacity is finite, so the order matters. `enforcement_queue()` assigns each filing a priority "
        "weight (`risk rank x 10 + indicators`) and sorts descending, so a HIGH-risk filing with many indicators "
        "always outranks a WATCH-risk filing with one. The benign and single-indicator filings still matter -- a "
        "tool that cried wolf on every filing would be useless -- so the queue also says **LOW** and **WATCH** when "
        "that is what the text supports."))
    c.append(code(QUEUE))

    # ---- Section 6: trust boundary ----
    c.append(md(
        '<a id="boundary"></a>\n## 6 - Trust boundary: submissions stay in your environment\n\n'
        "Worker submissions and agency filings are sensitive records. This tool is built so the raw text **never "
        "has to leave the regulator's environment**:\n\n"
        "- **Raw submissions and filings stay on-prem.** `audit()` is pure Python running in this notebook -- no "
        "request goes anywhere.\n"
        "- **Only anonymized aggregates ever cross a border.** Cross-border cooperation shares counts by risk and "
        "indicator, never raw case text, and only after human approval. In production the DueCare anonymizer (a "
        "hard PII gate) redacts names, IDs, and phone numbers **before** anything is shareable.\n"
        "- **The regulator controls every step** -- what is inspected, what is escalated, and whether any aggregate "
        "is shared at all.\n\n"
        "The cell below shows the data-flow boundary explicitly."))
    c.append(code(BOUNDARY))

    # ---- Section 7: go to production ----
    c.append(md(
        '<a id="production"></a>\n## 7 - Go to production: the full DueCare harness\n\n'
        "This notebook is the friendly front door. The production system behind it is much larger:\n\n"
        "- **Fine-tune on your own regulations.** The harness can be fine-tuned on a jurisdiction's specific "
        "labour law and recruitment rules, so the risk bands and enforcement focus reflect **your** statutes, not "
        "a generic template.\n"
        "- **The full harness** -- 451 GREP indicator rules across 11 languages, retrieval over an ILO / statute "
        "corpus, and **Gemma 4** doing the multi-step reasoning and drafting -- not the compact regex subset "
        "embedded here.\n"
        "- **Install it from source:** clone `gemma4_comp` and run `uv sync --all-packages`, then wire "
        "`audit()` into your intake pipeline.\n"
        f"- **The data:** the published DueCare benchmark grades live on Kaggle (e.g. `{DATASET_ID}`), and the "
        "interactive workbench exposes a **/data** page over the knowledge surfaces.\n"
        f"- **The source:** the [repository]({REPO}) has the harness, the grader, the fine-tuning path, and the "
        "full evaluation sweep.\n\n"
        "**Honest boundary.** What runs here is a representative deterministic subset for compliance triage. It is "
        "not a substitute for a trained inspector, not legal advice, and not a trafficking determination. Use it to "
        "prioritize inspections consistently -- then apply human judgement, local law, and due process.\n\n"
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
    assert TITLE.lower().replace(" ", "-") == "duecare-regulator-compliance"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
