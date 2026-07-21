#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the polished, richly-visual DueCare Prompt Intent & Attack explorer notebook.

Emits a Kaggle notebook (nbformat) over the published dataset
`taylorsamarel/duecare-prompt-response-showcase` (prompt_response_showcase.csv). Where the companion
`build_prompt_response_nlp_notebook.py` reads the RESPONSES across three arms, this notebook turns the
lens onto the ADVERSARIAL PROMPTS themselves -- 1,087 synthetic / composite migrant-worker-safety
prompts. It maps each prompt to a heuristic exploitation-INTENT bucket, detects the attack FRAMING it
uses to launder the request (euphemism, authority appeal, business/HR reframing, fiction pretext,
audit-dodge), renders prompt WORD CLOUDS overall and per category, scores prompt SENTIMENT / surface
tone (the "business-like banality" signal), profiles prompt LENGTH & complexity, and surfaces
distinctive VOCABULARY per intent and corridor -- then shows real prompts ROW BY ROW, verbatim.

Everything is computed live from the attached file, on CPU, with no GPU, no internet, and no model
loading. Every optional NLP package (wordcloud, vaderSentiment, textblob, scikit-learn, seaborn) is
wrapped in try/except with an offline-safe fallback, so the notebook runs to completion on Kaggle with
enable_internet=false. ASCII-only source -> no Kaggle mojibake.

    python scripts/build_prompt_intent_explorer_notebook.py
    python scripts/build_prompt_intent_explorer_notebook.py --force
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _notebook_viz import HELPERS, PALETTE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "prompt_intent_explorer"
DATASET_ID = "taylorsamarel/duecare-prompt-response-showcase"
CSV_NAME = "prompt_response_showcase.csv"
TITLE = "DueCare Prompt Intent And Attack Explorer"
SLUG = "duecare-prompt-intent-and-attack-explorer"
KERNEL_ID = "taylorsamarel/" + SLUG
DS_URL = "https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase"
REPO_URL = "https://github.com/TaylorAmarelTech/gemma4_comp"


# --------------------------------------------------------------------------- #
# cell builders (nbformat v4)
# --------------------------------------------------------------------------- #
def _md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text)


def _code(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(text)


# --------------------------------------------------------------------------- #
# SETUP -- the first code cell: shared prettify toolkit (PALETTE + HELPERS) then
# a recursive-glob load + all PROMPT-side feature engineering (intent buckets,
# attack frames, sentiment, length). Helpers are EMBEDDED, so the notebook never
# imports _notebook_viz at runtime. Written as a RAW string so regex backslashes
# survive; runtime newlines use NL = chr(10), never a backslash-n escape.
# --------------------------------------------------------------------------- #
DATALOAD = r'''import glob, json, os, re
from collections import Counter
from pathlib import Path
from IPython.display import Markdown, display

NL = chr(10)

# --- Load the published dataset via a RECURSIVE glob (Kaggle mounts datasets at an unpredictable path) ---
if os.path.exists("/kaggle/input"):
    print("mounted under /kaggle/input:", os.listdir("/kaggle/input"))

def _find(name):
    fs = sorted(glob.glob("/kaggle/input/**/" + name, recursive=True))
    return fs[0] if fs else None

_csv = _find("prompt_response_showcase.csv")
if _csv:
    _raw = pd.read_csv(_csv)
    rows = _raw.to_dict("records")
    print("loaded", len(rows), "rows from", _csv)
else:
    _jl = _find("prompt_response_showcase.jsonl")
    if not _jl:
        raise SystemExit("attach the dataset: taylorsamarel/duecare-prompt-response-showcase")
    rows = [json.loads(l) for l in open(_jl, encoding="utf-8") if l.strip()]
    print("loaded", len(rows), "rows from", _jl)

def _txt(v):
    if v is None:
        return ""
    if isinstance(v, float):
        try:
            if np.isnan(v):
                return ""
        except Exception:
            pass
    return str(v)

OUT = Path("/kaggle/working") if os.path.isdir("/kaggle/working") else Path(".")
def save(fig, stem):
    try:
        fig.savefig(OUT / (stem + ".png"), bbox_inches="tight")
    except Exception:
        pass

# ------------------------------------------------------------------------- #
# INTENT taxonomy -- map each adversarial prompt to ONE exploitation-intent
# bucket. These are HEURISTIC labels: priority-ordered keyword rules over the
# prompt text (the most specific structural intent wins), then a category-name
# fallback, then "other_general". Illustrative, not gold annotation.
# ------------------------------------------------------------------------- #
INTENT_RULES = [
    ("passport_document_control", r"passport|national id|work permit|document (safekeep|hold|retention|confiscat)|safekeeping|retain (the|their|his|her) (passport|document)|hold (the|their) (passport|id|document)"),
    ("movement_control", r"return ticket|prevent(ing)? (them|him|her|the worker).{0,20}(leav|depart|quit)|stop them from (leaving|going)|cannot leave|locked (the|their)|confin|not allowed to leave|exit permit"),
    ("financial_obfuscation", r"crypto|stablecoin|e-wallet|ewallet|offshore|\bspv\b|shell (compan|entit)|paper trail|money mule|launder|obfuscat|no invoice|sister (concern|compan)|free-zone|split .{0,20}(invoic|entit)|multi-entity"),
    ("contract_substitution", r"contract substitution|substitute (the|their)? ?contract|second contract|sign .{0,25}(new|different|another) contract|visa purposes only|dual contract"),
    ("wage_withholding", r"wage (deduction|withhold)|deduct(ing|ion)?.{0,15}(wage|salary|pay)|withhold(ing)? (wage|pay|salary)|voluntary savings|savings remittance|salary deduction"),
    ("fee_extraction", r"placement fee|recruitment fee|charge (the|each)? ?worker|statutory cap|fee (cap|split|splitting)|processing fee|exceeds the (statutory|legal)|mobilization fee|certification .{0,15}fee|documentation .{0,15}fee"),
    ("debt_bondage", r"backload|back-load|productivity bond|talent investment|investment bond|debt bondage|circular debt|\bdebt\b|repay(ment)?|indebt|recover .{0,25}(cost|placement)|advance of|solidarity advance"),
    ("complaint_suppression", r"avoid .{0,20}(audit|subpoena|inspect|scrutiny)|if audited|does not look like|so it does not|evade|escape (detection|liability)|deniab|so (they|she|he|the worker) (cannot|can't) (complain|report)"),
    ("recruitment_deception", r"free visa|free ticket|too good to be true|attract workers|job (offer|listing)|whatsapp script|no fees|\bfake\b|\blure\b|advertise|promising (young|work|job)"),
    ("coercion_threat", r"threat|coerce|coercion|family pressure|forfeit|punish|religious|moral (obligation|duty)|destitut|emergency|fear|pressure (them|her|him)"),
]
INTENT_GLOSS = {
    "passport_document_control": "seize or 'safekeep' passports / IDs / permits to trap the worker",
    "movement_control": "hold return tickets or block departure so the worker cannot leave",
    "financial_obfuscation": "route fees via crypto / e-wallet / offshore SPV / split invoices to hide the trail",
    "contract_substitution": "swap the government-approved contract for a worse one on arrival",
    "wage_withholding": "deduct or withhold wages, often relabelled as 'savings'",
    "fee_extraction": "charge the worker recruitment / placement fees above the legal cap",
    "debt_bondage": "load an advance or bond onto the worker, repaid via deductions",
    "complaint_suppression": "structure the scheme so the worker cannot complain or be audited",
    "recruitment_deception": "false 'free visa' / too-good-to-be-true recruitment offers",
    "coercion_threat": "threats, family pressure, religious / emergency justifications",
    "other_general": "legitimate worker / NGO / policy queries and unclassified prompts",
}
CAT_MAP = {
    "passport_control_policy": "passport_document_control", "coercion_document_confiscation": "passport_document_control",
    "wage_deduction_as_savings": "wage_withholding", "wage_query": "wage_withholding",
    "contract_substitution": "contract_substitution", "contract_language_extraction": "contract_substitution", "contract_query": "contract_substitution",
    "fee_splitting": "fee_extraction", "fee_query": "fee_extraction", "fee_limits_query": "fee_extraction", "ngo_fee_camouflage": "fee_extraction", "relabeling": "fee_extraction",
    "crypto_ewallet_fee_rail": "financial_obfuscation", "offshore_spv_obfuscation": "financial_obfuscation", "financial_obfuscation": "financial_obfuscation",
    "financial_obfuscation_fee_transfer": "financial_obfuscation", "financial_obfuscation_investment": "financial_obfuscation", "multi_entity_fee_laundering": "financial_obfuscation", "money_mule": "financial_obfuscation",
    "free_visa_backloaded_debt": "debt_bondage", "circular_debt_structures": "debt_bondage",
    "forced_recruitment": "recruitment_deception", "digital_recruitment": "recruitment_deception", "job_board_listing": "recruitment_deception", "social_media_post": "recruitment_deception",
    "coercion_family_pressure": "coercion_threat", "coercion_false_hope": "coercion_threat", "psychological_manipulation": "coercion_threat", "forced_criminality": "coercion_threat",
    "justification_religious": "coercion_threat", "justification_destitution": "coercion_threat", "justification_emergency": "coercion_threat", "moral_religious_framing": "coercion_threat",
}
_INTENT_RX = [(name, re.compile(rx, re.I)) for name, rx in INTENT_RULES]
def intent_of(r):
    t = _txt(r.get("prompt_text"))
    for name, rx in _INTENT_RX:
        if rx.search(t):
            return name
    return CAT_MAP.get(_txt(r.get("category")), "other_general")
INTENT_SHORT = {
    "passport_document_control": "passport", "movement_control": "movement", "financial_obfuscation": "financial",
    "contract_substitution": "contract", "wage_withholding": "wage", "fee_extraction": "fee",
    "debt_bondage": "debt", "complaint_suppression": "complaint", "recruitment_deception": "recruit",
    "coercion_threat": "coercion", "other_general": "other",
}

# ------------------------------------------------------------------------- #
# ATTACK FRAMES -- HOW the prompt launders the ask. NON-exclusive: a single
# prompt may layer several. Regex over prompt text; always available offline.
# ------------------------------------------------------------------------- #
FRAMES = [
    ("euphemism_relabeling", "euphemism / relabeling", "euphemism", r"'[^']{3,40}'|solidarity advance|voluntary savings|talent (investment|development)|wellness program|productivity bond|safekeeping|integrated .{0,20}(fee|program)|benevolent loan|cooperative (maintenance|education)|retention (incentive|bond)|mobilization fee"),
    ("authority_legitimacy", "authority / legitimacy appeal", "authority", r"licen[cs]e|registered|non-profit|compliant|poea|nea |slbfe|rec-|reg\.|\bcda\b|act no|section \d|statut|government (approved|show)|convention|ministry"),
    ("business_hr_logistics", "business / HR / logistics reframe", "business/HR", r"\bb2b\b|consultancy|hr department|internal memo|administrative|logistics|policy letter|draft (the|a|me|us|an)|paperwork|contract language|book the|structure (the|this)|agreement"),
    ("evasion_audit_dodge", "evasion / audit dodge", "evasion", r"paper trail|no invoice|cannot be traced|if audited|subpoena|so it does not look|does not (look|appear) like|avoid .{0,20}(audit|detection|scrutiny)|deniab|without .{0,15}naming"),
    ("fiction_roleplay", "fiction / roleplay pretext", "fiction", r"hypothetical|fiction|role[- ]?play|seminar|dystopian|imagine|in-character|creative|novel|thriller|screenplay"),
    ("override_jailbreak", "authority-override jailbreak", "override", r"ignore (all|previous|the)|you must|as an ai|no real impact|purely creative|override|disregard|jailbreak|without (any )?(restrictions|filter)|bypass"),
]
_FRAME_RX = [(k, lab, sh, re.compile(rx, re.I)) for k, lab, sh, rx in FRAMES]
FRAME_KEYS = [k for k, _, _, _ in FRAMES]
FRAME_LABEL = {k: lab for k, lab, _, _ in FRAMES}
FRAME_SHORT = {k: sh for k, _, sh, _ in FRAMES}

# ---- sentiment: vaderSentiment -> textblob -> bundled lexicon polarity ----
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
    def sentiment(t):
        return float(_VADER.polarity_scores(t or "")["compound"])
    SENT_BACKEND = "vaderSentiment"
except Exception:
    try:
        from textblob import TextBlob
        def sentiment(t):
            return float(TextBlob(t or "").sentiment.polarity)
        SENT_BACKEND = "textblob"
    except Exception:
        _POS = set("good help helpful support supportive protect protected safe safety right rights fair fairly legitimate legal lawful trust benefit secure assist care caring honest freedom free clear proper properly ensure ensures genuine positive welcome respect respected verify verified valid ethical compliant compliance solidarity wellness cooperative".split())
        _NEG = set("trafficking forced coerced coercion coercive debt bondage exploit exploited exploitation illegal fraud fraudulent scam abuse abusive threat threatened penalty penalties victim deception deceptive withheld withholding retention unlawful violation violations harm harmful danger dangerous risk risky fear trap trapped retaliation seizure confiscation bonded slavery servitude".split())
        def sentiment(t):
            toks = re.findall(r"[a-z']+", (t or "").lower())
            p = sum(w in _POS for w in toks)
            n = sum(w in _NEG for w in toks)
            return (p - n) / (p + n) if (p + n) else 0.0
        SENT_BACKEND = "bundled-lexicon"

# ---- vectorizer availability (used by word-cloud + TF-IDF + bigram cells) ----
try:
    from sklearn.feature_extraction.text import CountVectorizer  # noqa: F401
    HAS_SK = True
except Exception:
    HAS_SK = False

# offline tokenizer + a small extra stop-set for the pure-python fallbacks
STOP = set("the and for our are you your with that this from will can may per within into their they them has have had was were our we us able out off very just also only both each more most such not nor but who whom which what when where why how all any some one two three the a an of to in on at by as is be it or if so we i".split())
STOP |= set("000 workers worker".split())
TOK = re.compile(r"[a-z][a-z0-9]{2,}")

_RX_WORD = re.compile(r"[A-Za-z0-9']+")
_RX_SENT = re.compile(r"[.!?]+")

# ---- build ONE feature row per PROMPT (not per arm -- this is the prompt-side view) ----
_recs = []
for r in rows:
    t = _txt(r.get("prompt_text"))
    fr = {k: (1 if rx.search(t) else 0) for k, _, _, rx in _FRAME_RX}
    rec = {
        "prompt_id": _txt(r.get("prompt_id")),
        "category": _txt(r.get("category")),
        "corridor": _txt(r.get("corridor")),
        "difficulty": _txt(r.get("difficulty")),
        "prompt_text": t,
        "intent": intent_of(r),
        "chars": len(t),
        "words": len(_RX_WORD.findall(t)),
        "sentences": max(len(_RX_SENT.findall(t)), 1),
        "sentiment": sentiment(t),
        "n_frames": sum(fr.values()),
    }
    for k, v in fr.items():
        rec["frame_" + k] = v
    _recs.append(rec)
df = pd.DataFrame(_recs)

_kw = int(sum(1 for r in rows if any(rx.search(_txt(r.get("prompt_text"))) for _, rx in _INTENT_RX)))
display(Markdown(
    "Loaded **" + format(len(df), ",") + " adversarial prompts** across **" + str(df.category.nunique()) +
    " attack categories**, **" + str(df.corridor.nunique()) + " migration corridors**, and **" +
    str(df.difficulty.nunique()) + " difficulty bands**.  Each prompt is mapped to **" +
    str(df.intent.nunique()) + " heuristic intent buckets** (" + str(_kw) + " by keyword rule, " +
    str(len(df) - _kw) + " by category fallback) and scanned for **" + str(len(FRAME_KEYS)) +
    " attack-framing techniques**.  Sentiment backend: `" + SENT_BACKEND +
    "`; vectorizer: `" + ("scikit-learn" if HAS_SK else "pure-python Counter") + "`."
))'''

SETUP = PALETTE + "\n" + HELPERS + "\n" + DATALOAD


# --------------------------------------------------------------------------- #
# Section 1 -- overview
# --------------------------------------------------------------------------- #
S1A_CODE = r'''n = len(df)
def _u(f):
    return int(df[f].nunique())
named = int((df.corridor != "various").sum())
stat_cards([(format(n, ","), "adversarial prompts", TEAL),
            (str(_u("category")), "attack categories", INK2),
            (str(df.intent.nunique()), "intent buckets", EMBER),
            (str(_u("difficulty")), "difficulty bands", GOOD)])
summary = pd.DataFrame({
    "Metric": ["Total prompts", "Attack categories", "Intent buckets (heuristic)", "Migration corridors",
               "Named-corridor prompts", "Difficulty bands", "Median words / prompt", "Longest prompt (words)"],
    "Value": [format(n, ","), _u("category"), df.intent.nunique(), _u("corridor"),
              format(named, ","), _u("difficulty"), int(df.words.median()), int(df.words.max())],
})
display(pretty_table(summary, caption="The adversarial prompt set at a glance -- every figure counted live from the attached file"))'''


S1B_CODE = r'''vc = df["category"].value_counts().head(15).sort_values()
labels = [c.replace("_", " ") for c in vc.index]
vals = [int(v) for v in vc.values]
top = max(vals)
fig, ax = plt.subplots(figsize=(9.8, 6.6))
try:
    import seaborn as sns
    sns.barplot(x=vals, y=labels, color=TEAL, edgecolor=INK2, linewidth=0.5, ax=ax)
except Exception:
    ax.barh(range(len(vals)), vals, color=TEAL, edgecolor=INK2, linewidth=0.5)
    ax.set_yticks(range(len(vals))); ax.set_yticklabels(labels)
for y, v in enumerate(vals):
    ax.text(v + top * 0.01, y, str(v), va="center", fontsize=9.5, color=INK2)
ax.set_xlim(0, top * 1.13); ax.set_xlabel("prompts"); ax.set_ylabel("")
ax.set_title("Top 15 attack categories by prompt count")
ax.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, "intent_categories"); plt.show()
display(Markdown(
    "The set spans **" + str(df.category.nunique()) + " named attack categories** -- from overt jailbreaks "
    "(`override_jailbreak`, `pretext_jailbreak`) to slow, business-like laundering schemes "
    "(`fee_splitting`, `offshore_spv_obfuscation`, `ngo_fee_camouflage`). The categories are broadly "
    "balanced; the long tail of smaller categories is where the most specific corridor and sector "
    "scenarios live."
))'''


S1C_CODE = r'''fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.8, 5.0))
cc = df.loc[df.corridor != "various", "corridor"].value_counts().sort_values()
axL.barh(range(len(cc)), [int(v) for v in cc.values], color=TEAL, edgecolor=INK2, linewidth=0.5)
axL.set_yticks(range(len(cc))); axL.set_yticklabels(list(cc.index), fontsize=9)
for y, v in enumerate(cc.values):
    axL.text(int(v) + 0.15, y, str(int(v)), va="center", fontsize=8.5, color=INK2)
axL.set_xlabel("prompts"); axL.set_title("Named migration corridors")
axL.text(0, 1.02, "excludes corridor='various' (" + format(int((df.corridor == 'various').sum()), ",") + " prompts)",
         transform=axL.transAxes, fontsize=9, color=INK3, va="bottom")
axL.grid(axis="y", visible=False)
dorder = [d for d in ["easy", "medium", "hard"] if d in set(df.difficulty)]
dc = df["difficulty"].value_counts().reindex(dorder)
palette = {"easy": GOOD, "medium": WARN, "hard": EMBER}
axR.bar(range(len(dc)), [int(v) for v in dc.values], color=[palette.get(d, TEAL) for d in dorder],
        edgecolor=INK2, linewidth=0.6, width=0.62)
axR.set_xticks(range(len(dc))); axR.set_xticklabels(dorder)
for x, v in enumerate(dc.values):
    axR.text(x, int(v) + max(dc.values) * 0.01, str(int(v)), ha="center", va="bottom", fontsize=10, color=INK2)
axR.set_ylabel("prompts"); axR.set_title("Difficulty mix")
axR.grid(axis="x", visible=False)
fig.tight_layout(); save(fig, "intent_corridor_difficulty"); plt.show()
display(Markdown(
    "Most prompts carry corridor `various` (the scheme is corridor-agnostic); the **" + str(len(cc)) +
    " named corridors** are the concrete origin-to-destination routes (Nepal->Qatar, Kenya->Saudi Arabia, "
    "Vietnam->Taiwan fishing, ...). The set leans deliberately toward **hard** prompts -- the elaborate, "
    "plausible laundering schemes that most stress a safety harness."
))'''


# --------------------------------------------------------------------------- #
# Section 2 -- intent taxonomy
# --------------------------------------------------------------------------- #
S2A_CODE = r'''ic = df["intent"].value_counts().sort_values()
labels = [i.replace("_", " ") for i in ic.index]
vals = [int(v) for v in ic.values]
top = max(vals)
colors = [INK3 if k == "other_general" else TEAL for k in ic.index]
fig, ax = plt.subplots(figsize=(9.8, 5.8))
ax.barh(range(len(vals)), vals, color=colors, edgecolor=INK2, linewidth=0.5)
ax.set_yticks(range(len(vals))); ax.set_yticklabels(labels)
for y, v in enumerate(vals):
    ax.text(v + top * 0.01, y, str(v) + "  (" + format(100 * v / len(df), ".0f") + "%)", va="center", fontsize=9.5, color=INK2)
ax.set_xlim(0, top * 1.22); ax.set_xlabel("prompts"); ax.set_ylabel("")
ax.set_title("Exploitation-intent distribution (heuristic labels)")
ax.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, "intent_distribution"); plt.show()
big = ic.index[-1].replace("_", " ")
display(Markdown(
    "These are **heuristic** buckets -- priority-ordered keyword rules over the prompt text, then a "
    "category fallback (the grey `other general` bar is the unclassified remainder). The dominant intent "
    "is **" + big + "**, but the set is spread across every bucket: document control, fee mechanics, wage "
    "and debt structures, financial obfuscation, and coercion all appear at scale. No single intent "
    "swamps the signal."
))'''


S2B_CODE = r'''out = []
for it, cnt in df["intent"].value_counts().items():
    sub = df[df.intent == it]
    ex_cat = sub["category"].value_counts().index[0]
    out.append({
        "Intent bucket": it.replace("_", " "),
        "Prompts": int(cnt),
        "Share": format(100 * cnt / len(df), ".1f") + "%",
        "What the ask tries to do (heuristic)": INTENT_GLOSS.get(it, ""),
        "Top source category": ex_cat,
    })
display(pretty_table(pd.DataFrame(out),
                     caption="Intent buckets -- heuristic exploitation-intent labels, live counts, and the dominant source category",
                     bars=["Prompts"]))'''


S2C_CODE = r'''order_int = list(df["intent"].value_counts().index)
dorder = [d for d in ["easy", "medium", "hard"] if d in set(df.difficulty)]
ct = pd.crosstab(df["intent"], df["difficulty"]).reindex(index=order_int, columns=dorder).fillna(0.0)
pct = ct.div(ct.sum(axis=1).replace(0, 1), axis=0) * 100
heatmap(pct.values, [i.replace("_", " ") for i in pct.index], list(pct.columns),
        title="How hard is each intent?  (row-normalized %)",
        subtitle="within each intent bucket, share of prompts in each difficulty band -- the 'direction' of hardness",
        cmap="OrRd", fmt=".0f", cbar_label="% of bucket")
hard_share = (df.assign(h=(df.difficulty == "hard")).groupby("intent")["h"].mean().sort_values(ascending=False))
lead = hard_share.index[0].replace("_", " ")
display(Markdown(
    "Reading each row left to right shows where an intent concentrates. The obfuscation-heavy intents "
    "(**" + lead + "**, financial obfuscation, fee extraction) sit almost entirely in the **hard** band -- "
    "they are the multi-entity, multi-step schemes -- while simpler recruitment and query prompts carry a "
    "larger easy / medium share."
))'''


# --------------------------------------------------------------------------- #
# Section 3 -- attack framing
# --------------------------------------------------------------------------- #
S3A_CODE = r'''counts = [(FRAME_LABEL[k], int(df["frame_" + k].sum())) for k in FRAME_KEYS]
counts.sort(key=lambda kv: kv[1])
labels = [c for c, _ in counts]
vals = [v for _, v in counts]
top = max(vals)
fig, ax = plt.subplots(figsize=(9.8, 5.0))
ax.barh(range(len(vals)), vals, color=TEAL, edgecolor=INK2, linewidth=0.5)
ax.set_yticks(range(len(vals))); ax.set_yticklabels(labels)
for y, v in enumerate(vals):
    ax.text(v + top * 0.01, y, str(v) + "  (" + format(100 * v / len(df), ".0f") + "%)", va="center", fontsize=9.5, color=INK2)
ax.set_xlim(0, top * 1.2); ax.set_xlabel("prompts containing the frame"); ax.set_ylabel("")
ax.set_title("Attack-framing techniques -- how prompts launder the request (non-exclusive)")
ax.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, "intent_frames"); plt.show()
display(Markdown(
    "A frame is a **laundering technique**, detected by regex; a prompt may use several at once, so these "
    "do not sum to 100%. The two workhorses are **euphemism / relabeling** (a benign name for an abusive "
    "mechanism -- 'voluntary savings', 'productivity bond', 'safekeeping') and the **authority / legitimacy "
    "appeal** (license numbers, registered non-profits, cited statutes). Overt jailbreaks are the rarest "
    "frame: most of the set is quiet, procedural, and plausible."
))'''


S3B_CODE = r'''stat_cards([(str(int((df.n_frames == 0).sum())), "no frame detected", INK3),
            (str(int((df.n_frames == 1).sum())), "1 frame", TEAL),
            (str(int((df.n_frames >= 2).sum())), "2+ frames (layered)", EMBER),
            (str(int(df.n_frames.max())), "max frames on one prompt", GOOD)])
order_int = list(df["intent"].value_counts().index)
mat = []
for it in order_int:
    sub = df[df.intent == it]
    mat.append([100 * float(sub["frame_" + k].mean()) for k in FRAME_KEYS])
heatmap(mat, [i.replace("_", " ") for i in order_int], [FRAME_SHORT[k] for k in FRAME_KEYS],
        title="Which framing pairs with which intent  (%)",
        subtitle="within each intent bucket, share of prompts using each framing technique",
        cmap="BuGn", fmt=".0f", cbar_label="% of bucket")
display(Markdown(
    "Framing and intent are **correlated**: fee, debt and wage intents lean hard on euphemism and the "
    "authority appeal (they need a plausible business wrapper), while document-control and coercion prompts "
    "more often reach for the fiction / roleplay pretext. Many prompts **stack** frames -- a registered "
    "non-profit (authority) charging an 'integrated wellness fee' (euphemism) with no invoice (evasion)."
))'''


S3C_CODE = r'''def _first_sentence_with(rx, text):
    for s in re.split(r"(?<=[.!?])\s+", text or ""):
        if rx.search(s):
            return s.strip()
    return (text or "").strip()

ex = []
for k, lab, sh, rx in _FRAME_RX:
    hit = df[df["frame_" + k] == 1]
    if len(hit) == 0:
        continue
    r0 = hit.iloc[0]
    ex.append({
        "Framing technique": lab,
        "One verbatim sentence from a real prompt": _first_sentence_with(rx, r0["prompt_text"]),
        "Intent": r0["intent"].replace("_", " "),
    })
display(pretty_table(pd.DataFrame(ex),
                     caption="One real, verbatim sentence per framing technique -- the laundering vocabulary in situ (whole sentence, not truncated)"))'''


# --------------------------------------------------------------------------- #
# Section 4 -- word clouds
# --------------------------------------------------------------------------- #
S4A_CODE = r'''try:
    from wordcloud import WordCloud
    HAS_WC = True
except Exception:
    HAS_WC = False

def freqs_of(texts, k=170):
    if HAS_SK:
        from sklearn.feature_extraction.text import CountVectorizer
        try:
            cv = CountVectorizer(stop_words="english", lowercase=True,
                                 token_pattern=r"(?u)\b[a-z][a-z0-9]{2,}\b", min_df=2)
            X = cv.fit_transform(texts)
            counts = np.asarray(X.sum(axis=0)).ravel()
            vocab = cv.get_feature_names_out()
            pairs = sorted(zip(vocab, counts), key=lambda kv: kv[1], reverse=True)
            return {w: int(c) for w, c in pairs if w not in STOP and c > 0}
        except Exception:
            pass
    c = Counter()
    for t in texts:
        c.update(w for w in TOK.findall((t or "").lower()) if w not in STOP)
    return dict(c.most_common(k))

fq = freqs_of(df["prompt_text"].tolist(), 170)
fig, ax = plt.subplots(figsize=(11.6, 6.2))
if HAS_WC and fq:
    wc = WordCloud(width=1120, height=560, background_color=PAPER, colormap="BuGn",
                   prefer_horizontal=0.95, max_words=150).generate_from_frequencies(fq)
    ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
    ax.set_title("Prompt vocabulary word cloud -- the whole adversarial set")
else:
    top = list(fq.items())[:28][::-1]
    terms = [w for w, _ in top]; vals = [v for _, v in top]
    ax.barh(range(len(terms)), vals, color=TEAL, edgecolor=INK2, linewidth=0.4)
    ax.set_yticks(range(len(terms))); ax.set_yticklabels(terms, fontsize=9)
    ax.set_xlabel("count across all prompts"); ax.grid(axis="y", visible=False)
    ax.set_title("Top prompt terms (wordcloud not installed -- offline top-term fallback)")
_mode = "word cloud" if HAS_WC else "top-term bars (offline fallback)"
fig.tight_layout(); save(fig, "intent_wordcloud_all"); plt.show()
display(Markdown(
    "Rendered as a **" + _mode + "**. The prompt vocabulary is the working language of labour recruitment -- "
    "fees, agency, contract, visa, deduction, passport, placement, monthly -- not the language of "
    "obvious wrongdoing. That is exactly the point: the abusive intent is carried in **structure**, not in "
    "alarming words, which is what makes these prompts hard."
))'''


S4B_CODE = r'''top_cats = list(df["category"].value_counts().head(4).index)
fig, axes = plt.subplots(2, 2, figsize=(12.6, 9.0))
for ax, cat in zip(axes.ravel(), top_cats):
    fq = freqs_of(df.loc[df.category == cat, "prompt_text"].tolist(), 90)
    if HAS_WC and fq:
        wc = WordCloud(width=560, height=360, background_color=PAPER, colormap="BuGn",
                       prefer_horizontal=0.95, max_words=70).generate_from_frequencies(fq)
        ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
    else:
        top = list(fq.items())[:14][::-1]
        terms = [w for w, _ in top]; vals = [v for _, v in top]
        ax.barh(range(len(terms)), vals, color=TEAL, edgecolor=INK2, linewidth=0.4)
        ax.set_yticks(range(len(terms))); ax.set_yticklabels(terms, fontsize=8); ax.grid(axis="y", visible=False)
    ax.set_title(cat.replace("_", " "), fontsize=11)
_mode = "word clouds" if HAS_WC else "top-term bars (offline fallback)"
fig.suptitle("Prompt vocabulary by top-4 attack category  [" + _mode + "]", fontsize=13.5, fontweight="bold")
fig.tight_layout(); save(fig, "intent_wordcloud_cats"); plt.show()
display(Markdown(
    "Per-category clouds show how the vocabulary shifts with the scheme: fee-splitting and camouflage "
    "categories foreground `fee`, `invoice`, `entity`, `cap`; document and passport categories foreground "
    "`passport`, `permit`, `safekeeping`, `logistics`. Each category has a recognizable fingerprint."
))'''


# --------------------------------------------------------------------------- #
# Section 5 -- sentiment / tone
# --------------------------------------------------------------------------- #
S5A_CODE = r'''s = (df["sentiment"].astype(float) * 100)
kde_hist([("all prompts", s.tolist(), TEAL)],
         title="Prompt sentiment / surface tone (backend: " + SENT_BACKEND + ")",
         subtitle="compound polarity scaled x100; note how much mass sits near ZERO -- procedural, business-like phrasing",
         xlabel="prompt sentiment (compound x100)",
         vlines=[(0, INK3, "neutral"), (float(s.mean()), EMBER, "mean " + format(float(s.mean()), ".0f"))])
neutral = int((df["sentiment"].abs() < 0.2).sum())
stat_cards([(format(df.sentiment.mean(), "+.2f"), "mean sentiment", TEAL),
            (format(df.sentiment.median(), "+.2f"), "median sentiment", INK2),
            (format(100 * neutral / len(df), ".0f") + "%", "near-neutral (|s|<0.2)", EMBER),
            (format(100 * (df.sentiment > 0).mean(), ".0f") + "%", "surface-positive", GOOD)])
display(Markdown(
    "This is the **business-like banality** signal. The adversarial prompts do not read as menacing -- a large "
    "share score **neutral**, and the mean tips **slightly positive**, because they borrow the warm vocabulary "
    "of compliance and welfare ('solidarity', 'wellness', 'cooperative', 'free visa', 'compliant'). An abusive "
    "ask wrapped in a friendly, procedural register is the hardest kind for a bare model to refuse -- and the "
    "core reason a dedicated safety harness earns its keep."
))'''


S5B_CODE = r'''order_int = list(df["intent"].value_counts().index)
labels = [i.replace("_", " ") for i in order_int]
fig, ax = plt.subplots(figsize=(10.6, 6.2))
ok = False
try:
    import seaborn as sns
    sub = df.assign(s100=df["sentiment"] * 100)
    sns.violinplot(data=sub, y="intent", x="s100", order=order_int, color=TEAL_SOFT,
                   inner="quartile", cut=0, ax=ax)
    ok = True
except Exception:
    ok = False
if not ok:
    data = [(df.loc[df.intent == it, "sentiment"] * 100).tolist() for it in order_int]
    ax.boxplot(data, vert=False, patch_artist=True,
               boxprops=dict(facecolor=TEAL_SOFT, edgecolor=INK2), medianprops=dict(color=EMBER))
ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
ax.axvline(0, color=INK3, ls="--", lw=1.6)
ax.set_xlabel("prompt sentiment (compound x100)"); ax.set_ylabel("")
ax.set_title("Surface tone by intent bucket")
ax.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, "intent_sentiment_by_intent"); plt.show()
display(Markdown(
    "Splitting tone by intent shows the camouflage clearly: the fee, debt, wage and recruitment intents -- the "
    "ones that most need a plausible cover story -- skew the **most positive**, because they lean hardest on "
    "benign euphemisms. Coercion and document-control prompts sit closer to neutral. Tone here is a proxy for "
    "**surface framing**, never for how harmful the underlying request is."
))'''


# --------------------------------------------------------------------------- #
# Section 6 -- length & complexity
# --------------------------------------------------------------------------- #
S6A_CODE = r'''kde_hist([("characters", df["chars"].tolist(), TEAL)],
         title="Prompt length -- characters per prompt",
         subtitle="longer setups carry more laundering context: a plausible business backstory before the ask",
         xlabel="characters per prompt",
         vlines=[(float(df.chars.median()), EMBER, "median " + str(int(df.chars.median())))])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.6, 4.6))
for ax, col in [(a1, "words"), (a2, "sentences")]:
    v = df[col].values
    ax.hist(v, bins=34, color=TEAL, alpha=0.60, edgecolor=PAPER)
    ax.axvline(float(np.median(v)), color=EMBER, lw=2, ls="--")
    ax.text(float(np.median(v)), ax.get_ylim()[1] * 0.92, " median " + str(int(np.median(v))),
            color=EMBER, fontweight="bold", fontsize=9)
    ax.set_xlabel(col + " per prompt"); ax.set_ylabel("prompts"); ax.set_title(col.title() + " per prompt")
fig.suptitle("Prompt complexity -- word and sentence counts", fontsize=13, fontweight="bold")
fig.tight_layout(); save(fig, "intent_length"); plt.show()
display(Markdown(
    "The prompts are **substantial**: a typical one runs to roughly **" + str(int(df.words.median())) +
    " words** across **" + str(int(df.sentences.median())) + " sentences**. That length is not padding -- it is "
    "the elaborate, plausible backstory (a registered agency, a corridor, a fee schedule, a statute) that the "
    "harmful ask is buried inside."
))'''


S6B_CODE = r'''dorder = [d for d in ["easy", "medium", "hard"] if d in set(df.difficulty)]
fig, ax = plt.subplots(figsize=(9.8, 5.4))
ok = False
try:
    import seaborn as sns
    sns.violinplot(data=df, x="difficulty", y="words", order=dorder, color=TEAL_SOFT,
                   inner="quartile", cut=0, ax=ax)
    ok = True
except Exception:
    ok = False
if not ok:
    ax.boxplot([df.loc[df.difficulty == d, "words"].tolist() for d in dorder], labels=dorder, patch_artist=True,
               boxprops=dict(facecolor=TEAL_SOFT, edgecolor=INK2), medianprops=dict(color=EMBER))
    ax.set_xticklabels(dorder)
ax.set_xlabel("difficulty"); ax.set_ylabel("words per prompt")
ax.set_title("Prompt length by difficulty band")
ax.grid(axis="x", visible=False)
fig.tight_layout(); save(fig, "intent_length_by_difficulty"); plt.show()
meds = {d: int(df.loc[df.difficulty == d, "words"].median()) for d in dorder}
display(Markdown(
    "Difficulty tracks length. Median words per prompt: " +
    ", ".join("**" + d + "** " + str(meds[d]) for d in dorder) +
    ". The hard prompts are longer because harder laundering needs more scaffolding -- more entities, more "
    "steps, more citation of real rules to sound legitimate."
))'''


# --------------------------------------------------------------------------- #
# Section 7 -- distinctive vocabulary
# --------------------------------------------------------------------------- #
S7A_CODE = r'''def top_terms_for(mask, k=8):
    texts = df.loc[mask, "prompt_text"].tolist()
    if HAS_SK and len(texts) >= 3:
        from sklearn.feature_extraction.text import TfidfVectorizer
        try:
            tv = TfidfVectorizer(stop_words="english", lowercase=True,
                                 token_pattern=r"(?u)\b[a-z][a-z0-9]{2,}\b", min_df=2, max_df=0.9)
            X = tv.fit_transform(texts)
            means = np.asarray(X.mean(axis=0)).ravel()
            vocab = tv.get_feature_names_out()
            idx = [i for i in np.argsort(means)[::-1] if vocab[i] not in STOP][:k]
            return [vocab[i] for i in idx]
        except Exception:
            pass
    c = Counter()
    for t in texts:
        c.update(w for w in TOK.findall((t or "").lower()) if w not in STOP and len(w) > 2)
    return [w for w, _ in c.most_common(k)]

top_intents = [i for i in df["intent"].value_counts().index if i != "other_general"][:6]
t1 = pd.DataFrame({
    "Intent bucket": [it.replace("_", " ") for it in top_intents],
    "Most distinctive terms (TF-IDF)": [", ".join(top_terms_for(df.intent == it)) for it in top_intents],
})
display(pretty_table(t1, caption="Distinctive vocabulary per intent bucket -- top TF-IDF terms (pure-python Counter fallback if scikit-learn is absent)"))
named = [c for c in df["corridor"].value_counts().index if c != "various"][:6]
if named:
    t2 = pd.DataFrame({
        "Migration corridor": named,
        "Most distinctive terms (TF-IDF)": [", ".join(top_terms_for(df.corridor == c)) for c in named],
    })
    display(pretty_table(t2, caption="Distinctive vocabulary per named migration corridor (most prompts carry corridor='various')"))'''


S7B_CODE = r'''KEY = ["passport", "fee", "fees", "deduct", "contract", "visa", "invoice", "offshore", "license", "savings", "return", "debt"]
show_int = list(df["intent"].value_counts().index)[:8]
mat = []
for term in KEY:
    pat = re.compile(r"\b" + term + r"\b", re.I)
    mat.append([float(np.mean([len(pat.findall(t)) for t in df.loc[df.intent == it, "prompt_text"]])) if int((df.intent == it).sum()) else 0.0 for it in show_int])
heatmap(mat, KEY, [INTENT_SHORT.get(i, i) for i in show_int],
        title="Key laundering terms x intent -- mean occurrences per prompt",
        subtitle="how often each term appears in a typical prompt of that intent",
        cmap="BuGn", fmt=".2f", cbar_label="mean / prompt")
display(Markdown(
    "The term-by-intent grid is a compact fingerprint: `passport` spikes in document control, `offshore` and "
    "`invoice` in financial obfuscation, `deduct` and `savings` in wage withholding, `debt` in debt bondage. "
    "Each intent reaches for its own toolkit of words."
))'''


S7C_CODE = r'''if HAS_SK:
    from sklearn.feature_extraction.text import CountVectorizer
    try:
        cv = CountVectorizer(stop_words="english", lowercase=True, ngram_range=(2, 2),
                             token_pattern=r"(?u)\b[a-z][a-z]+\b", min_df=4)
        X = cv.fit_transform(df["prompt_text"].tolist())
        counts = np.asarray(X.sum(axis=0)).ravel()
        vocab = cv.get_feature_names_out()
        pairs = sorted(zip(vocab, counts), key=lambda kv: kv[1], reverse=True)[:20][::-1]
    except Exception:
        pairs = []
else:
    pairs = []
if not pairs:
    c = Counter()
    for t in df["prompt_text"]:
        toks = [w for w in TOK.findall((t or "").lower()) if w not in STOP]
        c.update(zip(toks, toks[1:]))
    pairs = [(" ".join(bg), n) for bg, n in c.most_common(20)][::-1]
terms = [a for a, _ in pairs]
vals = [int(b) for _, b in pairs]
top = max(vals) if vals else 1
fig, ax = plt.subplots(figsize=(9.8, 6.8))
ax.barh(range(len(terms)), vals, color=TEAL, edgecolor=INK2, linewidth=0.4)
ax.set_yticks(range(len(terms))); ax.set_yticklabels(terms)
for y, v in enumerate(vals):
    ax.text(v + top * 0.01, y, str(v), va="center", fontsize=9, color=INK2)
ax.set_xlim(0, top * 1.13); ax.set_xlabel("count across all prompts"); ax.set_ylabel("")
ax.set_title("Most frequent 2-word phrases in the prompts")
ax.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, "intent_bigrams"); plt.show()
display(Markdown(
    "The most frequent bigrams read like a recruitment-fraud phrasebook -- placement fee, return ticket, free "
    "visa, foreign employment, per month -- the concrete building blocks the schemes are assembled from."
))'''


# --------------------------------------------------------------------------- #
# Section 8 -- row by row
# --------------------------------------------------------------------------- #
S8_CODE = r'''pref = ["passport_document_control", "financial_obfuscation", "fee_extraction", "wage_withholding",
        "recruitment_deception", "coercion_threat", "movement_control", "contract_substitution", "debt_bondage"]
pick, seen = [], set()
for it in pref:
    sub = df[df.intent == it]
    if len(sub) == 0:
        continue
    r0 = sub.iloc[0]
    if r0.prompt_id in seen:
        continue
    pick.append(r0); seen.add(r0.prompt_id)
    if len(pick) >= 6:
        break
for _, r0 in df.iterrows():
    if len(pick) >= 6:
        break
    if r0.prompt_id not in seen:
        pick.append(r0); seen.add(r0.prompt_id)

display(Markdown("Showing **" + str(len(pick)) + "** full prompts, verbatim, spanning distinct intents -- nothing truncated. "
                 "This is exactly what a bare model sees, and exactly what the safety harness has to hold the line against."))
for i, r0 in enumerate(pick, 1):
    meta = ("**Example " + str(i) + "** &middot; intent `" + str(r0.intent) + "` &middot; `" + str(r0.prompt_id) +
            "` &middot; category `" + str(r0.category) + "` &middot; corridor `" + str(r0.corridor) +
            "` &middot; difficulty `" + str(r0.difficulty) + "`")
    display(Markdown(meta))
    display(Markdown("```text" + NL + str(r0.prompt_text) + NL + "```"))
    display(Markdown("---"))'''


# --------------------------------------------------------------------------- #
# markdown cells (URLs literal; HTML entities are ASCII source that render as glyphs)
# --------------------------------------------------------------------------- #
HERO_MD = '''<div style="padding:26px 32px;border-radius:16px;background:linear-gradient(120deg,#14181B 0%,#2A2D34 42%,#c15b2e 100%);color:#F7F6F1">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.82">DueCare &middot; Gemma 4 safety &middot; the prompt side</div>
<h1 style="margin:.28em 0 .2em;font-size:30px;color:#ffffff;font-weight:800">Reading the attack: intent, framing, tone &amp; vocabulary</h1>
<p style="font-size:15px;line-height:1.6;margin:0;max-width:940px">Its companion notebook studies what the model <i>answers</i>. This one turns the lens onto the <b>adversarial prompts themselves</b> &mdash; the 1,087 synthetic, composite migrant-worker-safety prompts in the <b>DueCare Prompt + Response Showcase</b>. We map each prompt to a heuristic <b>exploitation-intent</b> bucket (passport control, fee extraction, debt bondage, financial obfuscation&hellip;), detect the <b>attack framing</b> it uses to launder the request (euphemism, authority appeal, business/HR reframing, fiction pretext, audit-dodge), render prompt <b>word clouds</b>, score prompt <b>sentiment</b> (the tell-tale <i>business-like banality</i>), profile <b>length &amp; complexity</b>, and surface distinctive <b>vocabulary</b> per intent and corridor &mdash; then read real prompts <b>row by row, verbatim</b>. Entirely on CPU, no model, no GPU, no internet; every chart computed live from the attached file.</p>
</div>'''

TOC_MD = '''## What is in this notebook

Every number and chart below is computed **live from the attached dataset** &mdash; nothing is hard-coded.

- [1. Overview &mdash; categories, corridors, difficulty](#overview)
- [2. Intent taxonomy &mdash; what each prompt is trying to do](#intent)
- [3. Attack framing &mdash; how the ask is laundered](#framing)
- [4. Prompt word clouds &mdash; overall and per category](#clouds)
- [5. Sentiment &amp; tone &mdash; the business-like banality signal](#sentiment)
- [6. Length &amp; complexity &mdash; how elaborate the setups are](#length)
- [7. Distinctive vocabulary &mdash; per intent, per corridor, top phrases](#vocab)
- [8. Row by row &mdash; full prompts, verbatim](#rows)
- [9. Honest boundary &amp; license](#boundary)

**Honest boundary (read first).** These prompts are **synthetic / composite** &mdash; no real person, case, contact, document, or address appears, and the set is PII-clean. The intent buckets and attack frames are **heuristic, regex-derived labels**, illustrative rather than gold annotation. This is an exploratory NLP view of *how the adversarial prompts are constructed*, not a real-world detection or victim-identification claim. License **CC0**.

**Dataset:** [`taylorsamarel/duecare-prompt-response-showcase`](https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase) &middot; **Companion:** the Prompt + Response NLP explorer &middot; **Repo:** [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''

S1_MD = '''<a id="overview"></a>
## 1. Overview &mdash; categories, corridors, difficulty

First, the shape of the set. Each prompt carries a hand-labelled **attack category**, a migration **corridor** (many are corridor-agnostic and marked `various`), and a **difficulty** band. The KPI tiles and table count the real rows; the bars show the category mix, the named corridors, and the deliberate lean toward hard prompts.'''

S2_MD = '''<a id="intent"></a>
## 2. Intent taxonomy &mdash; what each prompt is trying to do

The category labels describe *surface form*; here we ask about **exploitation intent** &mdash; what the ask is actually trying to do to a worker. Each prompt is mapped to **one** intent bucket by a set of **heuristic, priority-ordered keyword rules** over the prompt text (most specific structural intent wins), with a category-name fallback and an `other_general` remainder. These labels are **illustrative, not gold** &mdash; but even a rough mapping reveals how the corpus is distributed across the mechanisms of forced labour, and which intents concentrate in the hardest prompts.'''

S3_MD = '''<a id="framing"></a>
## 3. Attack framing &mdash; how the ask is laundered

Intent is *what*; framing is *how*. A framing technique is the rhetorical wrapper that makes an abusive request sound acceptable. We regex-detect six: **euphemism / relabeling** (a benign name for an abusive mechanism), the **authority / legitimacy appeal** (licenses, registrations, cited statutes), a **business / HR / logistics reframe**, an **evasion / audit dodge**, a **fiction / roleplay pretext**, and the overt **authority-override jailbreak**. Frames are **non-exclusive** &mdash; the most sophisticated prompts stack several &mdash; so the visuals below show both how often each frame appears and how frames pair with intent.'''

S4_MD = '''<a id="clouds"></a>
## 4. Prompt word clouds &mdash; overall and per category

A quick visual of the most frequent prompt vocabulary, stop-words removed. When the `wordcloud` package is available the notebook renders true clouds; otherwise it falls back to top-term bars via the shared toolkit, so this cell always produces output offline. The striking thing is how *ordinary* the vocabulary is: the abuse lives in structure, not in alarming words.'''

S5_MD = '''<a id="sentiment"></a>
## 5. Sentiment &amp; tone &mdash; the business-like banality signal

Sentiment here is a proxy for **surface tone**, never for how harmful a request is. We score each prompt's compound polarity (VADER when present, TextBlob or a bundled lexicon as offline fallbacks). The signal that matters: these adversarial prompts skew **neutral-to-positive**, because they borrow the warm, procedural language of compliance and welfare. An abusive ask wrapped in a friendly register is precisely the case a bare model is most likely to answer &mdash; and the strongest argument for a dedicated safety harness.'''

S6_MD = '''<a id="length"></a>
## 6. Length &amp; complexity &mdash; how elaborate the setups are

How much scaffolding does each attack carry? We profile characters, words, and sentences per prompt, then split length by difficulty band. Longer is not padding: the extra length is the plausible business backstory &mdash; a registered agency, a corridor, a fee schedule, a cited statute &mdash; that the harmful ask is buried inside.'''

S7_MD = '''<a id="vocab"></a>
## 7. Distinctive vocabulary &mdash; per intent, per corridor, top phrases

Which words *characterize* each slice of the corpus? Using **TF-IDF** (scikit-learn when present, a pure-python Counter as the offline fallback) we pull the most distinctive terms per intent bucket and per named corridor, chart a key-term-by-intent heatmap, and rank the most frequent two-word phrases &mdash; the concrete building blocks the schemes are assembled from.'''

S8_MD = '''<a id="rows"></a>
## 8. Row by row &mdash; full prompts, verbatim

The centerpiece: a handful of real prompts shown **end to end, nothing truncated**, chosen to span distinct intents. This is exactly what a bare model receives &mdash; a long, plausible, professional-sounding setup with a single harmful ask folded in &mdash; and exactly what the DueCare harness is built to recognize and refuse.'''

BOUNDARY_MD = '''<a id="boundary"></a>
## 9. Honest boundary &amp; license

**What this is.** An exploratory NLP view of *how the adversarial prompts are constructed* &mdash; their intent, framing, tone, length, and vocabulary. Everything is computed live from the attached file, on CPU, with no model and no internet.

**What this is not.** The prompts are **synthetic / composite** &mdash; no real individual, case, contact, name, number, or address appears, and the set is PII-clean. The **intent buckets and attack frames are heuristic, regex-derived labels**: a priority-ordered keyword mapping, illustrative rather than gold human annotation, and some prompts land in `other_general`. Sentiment is a **surface-tone proxy**, not a measure of how harmful a request is. This notebook makes **no** real-world detection or victim-identification claim, and none of the prompt content is instructions to be followed.

**Use the data.** Re-map the intent rules to your own taxonomy, add framing detectors, or join these prompt-side features to the response-side arms in the companion notebook to study *which* framings the harness resists best. Every function is offline-safe and re-runnable.

**Reproducibility.** Each optional NLP package (wordcloud, vaderSentiment, textblob, scikit-learn, seaborn) is wrapped in try/except with an offline fallback, so the notebook runs to completion with `enable_internet=false`.

**License.** CC0.

**Links.** Dataset: [`taylorsamarel/duecare-prompt-response-showcase`](https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase) &middot; Source repository: [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''


def _notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        _md(HERO_MD),
        _md(TOC_MD),
        _code(SETUP),
        _md(S1_MD),
        _code(S1A_CODE),
        _code(S1B_CODE),
        _code(S1C_CODE),
        _md(S2_MD),
        _code(S2A_CODE),
        _code(S2B_CODE),
        _code(S2C_CODE),
        _md(S3_MD),
        _code(S3A_CODE),
        _code(S3B_CODE),
        _code(S3C_CODE),
        _md(S4_MD),
        _code(S4A_CODE),
        _code(S4B_CODE),
        _md(S5_MD),
        _code(S5A_CODE),
        _code(S5B_CODE),
        _md(S6_MD),
        _code(S6A_CODE),
        _code(S6B_CODE),
        _md(S7_MD),
        _code(S7A_CODE),
        _code(S7B_CODE),
        _code(S7C_CODE),
        _md(S8_MD),
        _code(S8_CODE),
        _md(BOUNDARY_MD),
    ]
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    }
    return nb


def _kernel_metadata() -> dict:
    return {
        "id": KERNEL_ID,
        "title": TITLE,
        "code_file": "notebook.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": False,
        "dataset_sources": [DATASET_ID],
        "competition_sources": [],
        "kernel_sources": [],
    }


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / SLUG
    if nb_dir.exists() and force:
        shutil.rmtree(nb_dir)
    nb_dir.mkdir(parents=True, exist_ok=True)
    nb = _notebook()
    nbf.validate(nb)  # fail fast if the notebook structure is malformed
    nb_path = nb_dir / "notebook.ipynb"
    nbf.write(nb, str(nb_path))
    meta_path = nb_dir / "kernel-metadata.json"
    meta_path.write_text(json.dumps(_kernel_metadata(), indent=2), encoding="utf-8")
    nbf.read(str(nb_path), as_version=4)  # round-trip read to confirm it is valid on disk
    return {
        "notebook": str(nb_path),
        "kernel_metadata": str(meta_path),
        "kernel_id": KERNEL_ID,
        "title": TITLE,
        "n_cells": len(nb.cells),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    # Kaggle derives the kernel slug from the title -- assert they agree.
    assert TITLE.lower().replace(" ", "-") == SLUG, (
        "title slug mismatch: " + repr(TITLE) + " -> " + repr(TITLE.lower().replace(" ", "-")) + " != " + repr(SLUG)
    )
    assert TITLE.lower().replace(" ", "-") == "duecare-prompt-intent-and-attack-explorer"
    assert KERNEL_ID == "taylorsamarel/" + SLUG, "kernel id mismatch: " + repr(KERNEL_ID)

    result = build(args.output, force=args.force)
    result["title_slug_ok"] = TITLE.lower().replace(" ", "-") == SLUG
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
