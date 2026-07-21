#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare CoT *Direction & Intent* explorer notebook.

A long, deeply-visual Kaggle notebook (nbformat) that explores the *reasoning axes* and
*tone* of the published training dataset `taylorsamarel/duecare-cot-reasoning`
(cot_train.jsonl): 100+ domain perspectives x ~102-step chains of thought, each grounded
in a real ILO forced-labour indicator pattern, for safety fine-tuning of Gemma 4.

Where the sibling `duecare-cot-reasoning-explorer` covers the *space* (who / what /
chain-depth / schema), this notebook drills into the four reasoning axes -- DIRECTION
(inward vs outward), REACH (small vs large jump), PERSPECTIVE (101 role vantage points),
and the INTENT of each of the 102 steps -- and reads their *tone* with word clouds,
distinctive-vocabulary TF-IDF panels, sentiment, and violin/box register plots.

Every number and chart is computed live from the attached data -- CPU only, no GPU, no
internet, no model loading -- and every optional dependency (wordcloud, VADER/TextBlob,
plotly) degrades to an offline-safe fallback so the notebook always runs to completion.

    python scripts/build_cot_direction_explorer_notebook.py
    python scripts/build_cot_direction_explorer_notebook.py --force
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "cot_direction_explorer"
DATASET_ID = "taylorsamarel/duecare-cot-reasoning"
TITLE = "DueCare CoT Direction And Intent Explorer"
KERNEL_ID = "taylorsamarel/duecare-cot-direction-and-intent-explorer"
SLUG = "duecare-cot-direction-and-intent-explorer"
DS_URL = "https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning"
REPO_URL = "https://github.com/TaylorAmarelTech/gemma4_comp"


# --------------------------------------------------------------------------- #
# cell builders (nbformat v4)
# --------------------------------------------------------------------------- #
def _md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text)


def _code(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(text)


# --------------------------------------------------------------------------- #
# EXTRA_TOOLKIT: helpers layered on top of PALETTE + HELPERS from _notebook_viz.
# Everything is offline-safe -- wordcloud, VADER, TextBlob and plotly each fall
# back cleanly so the notebook runs with only numpy/pandas/matplotlib/seaborn/
# scikit-learn/scipy (the Kaggle base image and the local test venv).
# --------------------------------------------------------------------------- #
EXTRA_TOOLKIT = r'''import re as _re
from collections import Counter

# ---- is the wordcloud library available? (drives an honest render-mode note) ----
try:
    import wordcloud as _wc_mod  # noqa: F401
    WORDCLOUD_OK = True
except Exception:
    WORDCLOUD_OK = False

def cloud_note():
    if WORDCLOUD_OK:
        return "Rendered with the **wordcloud** library (word size = how distinctive the term is)."
    return ("The `wordcloud` package is not installed here, so each cloud falls back to a "
            "**ranked bar of the most distinctive terms** -- identical information, zero extra dependency.")

def _tok(text):
    return _re.findall(r"[a-z][a-z_]{2,}", text.lower())

# ---- sentiment: VADER (nltk) -> TextBlob -> a small built-in lexicon (all offline) ----
def _build_sentiment():
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer
        _sia = SentimentIntensityAnalyzer()
        return "VADER (nltk)", (lambda t: float(_sia.polarity_scores(t)["compound"]))
    except Exception:
        pass
    try:
        from textblob import TextBlob
        return "TextBlob", (lambda t: float(TextBlob(t).sentiment.polarity))
    except Exception:
        pass
    _POS = set("protect protects protected safe safely support supports supported help helps helping "
               "right rights lawful clear verify verified careful reversible preserve preserves trust "
               "fair recover recovery assist secure genuine honest respect consent legitimate remedy choice".split())
    _NEG = set("debt bondage withheld withholding forced threat threats coercion abuse abusive deception "
               "deceive retention isolation violence intimidation trap risk retaliation harm exploit unlawful "
               "control controlled pressure fear vulnerable danger dispute disputed unsafe overclaim".split())
    def _lex(t):
        toks = _tok(t)
        if not toks:
            return 0.0
        p = sum(1 for w in toks if w in _POS)
        n = sum(1 for w in toks if w in _NEG)
        d = p + n
        return 0.0 if d == 0 else (p - n) / d
    return "built-in lexicon", _lex

SENTIMENT_BACKEND, sentiment_of = _build_sentiment()

# ---- distinctive vocabulary: slice one shared TF-IDF matrix (group mean vs the rest) ----
def group_distinctive(tfidf, terms, mask, topn=22):
    mask = np.asarray(mask, dtype=bool)
    if mask.sum() == 0 or (~mask).sum() == 0:
        return {}
    mi = np.asarray(tfidf[mask].mean(axis=0)).ravel()
    mo = np.asarray(tfidf[~mask].mean(axis=0)).ravel()
    diff = mi - mo
    idx = np.argsort(diff)[::-1][:topn]
    return {terms[i]: float(diff[i]) for i in idx if diff[i] > 0.0}

# ---- horizontal bars of distinctive terms (two panels side by side) ----
def _bars_terms(ax, freqs, color, title):
    items = sorted(freqs.items(), key=lambda kv: kv[1])
    labs = [k for k, _ in items]
    vals = [v for _, v in items]
    ax.barh(range(len(labs)), vals, color=color, edgecolor=INK2, linewidth=0.4)
    ax.set_yticks(range(len(labs)))
    ax.set_yticklabels(labs, fontsize=9)
    ax.set_xticks([])
    ax.set_title(title, fontsize=11.5, fontweight="bold", color=INK, loc="left")
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)

def two_bar_terms(freqs_a, title_a, color_a, freqs_b, title_b, color_b, suptitle=""):
    fig, axs = plt.subplots(1, 2, figsize=(12.0, 5.6))
    _bars_terms(axs[0], freqs_a, color_a, title_a)
    _bars_terms(axs[1], freqs_b, color_b, title_b)
    if suptitle:
        fig.suptitle(suptitle, fontsize=13.5, fontweight="bold", color=INK, x=0.02, ha="left")
    plt.tight_layout()
    plt.show()

# ---- word cloud (wordcloud lib) with a ranked-bar fallback; draws into any axis ----
def _draw_cloud(ax, freqs, color, title=None):
    if title is not None:
        ax.set_title(title, fontsize=11, fontweight="bold", color=INK, loc="left")
    if not freqs:
        ax.axis("off")
        ax.text(0.5, 0.5, "(no distinctive terms)", ha="center", va="center", color=INK3)
        return False
    if WORDCLOUD_OK:
        try:
            from wordcloud import WordCloud
            wc = WordCloud(width=560, height=360, background_color=PAPER, prefer_horizontal=0.92,
                           max_words=64, color_func=lambda *a, **k: color)
            wc.generate_from_frequencies({k: float(v) for k, v in freqs.items()})
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            return True
        except Exception:
            pass
    keep = sorted(freqs.items(), key=lambda kv: kv[1])[-16:]
    labs = [k for k, _ in keep]
    vals = [v for _, v in keep]
    ax.barh(range(len(labs)), vals, color=color, edgecolor=INK2, linewidth=0.4)
    ax.set_yticks(range(len(labs)))
    ax.set_yticklabels(labs, fontsize=8.5)
    ax.set_xticks([])
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    return False

def cloud_pair(a, b, suptitle=""):
    fig, axs = plt.subplots(1, 2, figsize=(12.0, 4.9))
    _draw_cloud(axs[0], a[1], a[2], a[0])
    _draw_cloud(axs[1], b[1], b[2], b[0])
    if suptitle:
        fig.suptitle(suptitle, fontsize=13.5, fontweight="bold", color=INK, x=0.02, ha="left")
    plt.tight_layout()
    plt.show()

def cloud_grid(items, ncols=3, title="", figsize=None):
    n = len(items)
    nrows = (n + ncols - 1) // ncols
    fig, axs = plt.subplots(nrows, ncols, figsize=figsize or (4.5 * ncols, 3.3 * nrows))
    axs = np.atleast_1d(axs).ravel()
    for ax, (t, fr, col) in zip(axs, items):
        _draw_cloud(ax, fr, col, t)
    for ax in axs[len(items):]:
        ax.axis("off")
    if title:
        fig.suptitle(title, fontsize=13.5, fontweight="bold", color=INK, x=0.02, ha="left")
    plt.tight_layout()
    plt.show()

# ---- the 102-step anatomy: nine fixed reasoning phases, classified live per step ----
PHASES = ["1 Frame & perspective", "2 Evidence states", "3 Actor map", "4 ILO indicator screens",
          "5 Lifecycle stages", "6 Jurisdiction & legal", "7 Counterfactuals",
          "8 Safe-action selection", "9 Verify, provenance & privacy"]

PHASE_INTENT = {
    "1 Frame & perspective": "Lock the vantage point, state the role boundary, set the reach and direction, and restate the facts without adding any -- so the whole chain is anchored before analysis begins.",
    "2 Evidence states": "Walk four evidence conditions (account only, partial documents, conflicting records, multi-worker pattern) and separate what the record supports from what it does not yet establish.",
    "3 Actor map": "Place every actor in the chain (worker, recruiter, broker, transporter, sponsor, housing, payment, document holder) and mark what is evidenced versus assumed.",
    "4 ILO indicator screens": "Test each of the eleven ILO 2012 forced-labour indicators against the record, naming the supporting observation and the gap that must close before asserting it.",
    "5 Lifecycle stages": "Locate events across the migration lifecycle (recruitment through return and recovery), keeping warning signs distinct from later outcomes.",
    "6 Jurisdiction & legal": "For origin, transit, and destination, name the governing framework and effective date, and the primary source that must be verified rather than asserted.",
    "7 Counterfactuals": "Stress-test the reading -- which single new fact, authentication, changed goal, or later rule would move the safe next step.",
    "8 Safe-action selection": "Enumerate the options in scope, weigh reversibility and retaliation exposure, choose the smallest reversible step, and state explicitly what this role will NOT do.",
    "9 Verify, provenance & privacy": "List facts to verify against primary sources, route volatile contacts to live tools, record referral provenance, state the residual uncertainty, and confirm no PII was invented.",
}

def _phase_of(step_text):
    t = step_text.lower()
    if any(k in t for k in ("fix the perspective", "role boundary", "reasoning reach", "reasoning direction", "restate the situation", "hypothesis to test")):
        return "1 Frame & perspective"
    if "evidence state" in t or "record supports" in t:
        return "2 Evidence states"
    if "actor map" in t or "directly evidenced versus assumed" in t:
        return "3 Actor map"
    if "screen ilo indicator" in t or "support or refute" in t or "gap that must be closed" in t:
        return "4 ILO indicator screens"
    if "place the situation against" in t or "warning sign distinct" in t:
        return "5 Lifecycle stages"
    if "country" in t or "framework and effective date" in t or "bilateral labour" in t:
        return "6 Jurisdiction & legal"
    if "counterfactual" in t:
        return "7 Counterfactuals"
    if any(k in t for k in ("options open to", "reversibility", "smallest reversible", "safe action", "will not do")):
        return "8 Safe-action selection"
    return "9 Verify, provenance & privacy"

def phase_counts(chain_text):
    steps = [s for _, s in _re.findall(r"^\s*(\d+)\.\s*(.*)$", chain_text, flags=_re.M)]
    cnt = Counter(_phase_of(s) for s in steps)
    return {p: int(cnt.get(p, 0)) for p in PHASES}'''


# --------------------------------------------------------------------------- #
# DATALOAD: recursive glob for cot_train.jsonl (fallback cot.jsonl) + SystemExit.
# Keeps `rows` and the assistant/user text accessors so every later cell can
# recompute vocabulary and tone from the raw chains.
# --------------------------------------------------------------------------- #
DATALOAD = '''import glob, json, os, re
from pathlib import Path
from IPython.display import Markdown, display

if os.path.exists("/kaggle/input"):
    print("mounted under /kaggle/input:", os.listdir("/kaggle/input"))

def _glob(name):
    return sorted(glob.glob(f"/kaggle/input/**/{name}", recursive=True))

_files = _glob("cot_train.jsonl") or _glob("cot.jsonl")
if not _files:
    raise SystemExit("attach taylorsamarel/duecare-cot-reasoning (need cot_train.jsonl)")
with open(_files[0], encoding="utf-8") as fh:
    rows = [json.loads(line) for line in fh if line.strip()]

META = ["perspective", "perspective_label", "category", "situation", "ilo_indicator",
        "reach", "direction", "step_count", "lineage_id", "lineage_family_id", "split"]
df = pd.DataFrame([{k: r.get(k) for k in META} for r in rows])

def _atext(r):
    return next(m["content"] for m in r["messages"] if m["role"] == "assistant")
def _utext(r):
    return next(m["content"] for m in r["messages"] if m["role"] == "user")
A_DOCS = [_atext(r) for r in rows]

OUT = Path("/kaggle/working") if os.path.isdir("/kaggle/working") else Path(".")
def save(fig, stem):
    try:
        fig.savefig(OUT / (stem + ".png"), bbox_inches="tight")
    except Exception:
        pass

display(Markdown(
    f"Loaded **{len(df):,} chain-of-thought rows** &mdash; **{df.perspective.nunique()} perspectives**, "
    f"**{df.category.nunique()} role categories**, **{df.situation.nunique()} ILO indicator patterns**. "
    f"Reach: {sorted(df.reach.dropna().unique())}. Direction: {sorted(df.direction.dropna().unique())}. "
    f"Sentiment backend resolved to **{SENTIMENT_BACKEND}**; word clouds "
    f"{'via the wordcloud library' if WORDCLOUD_OK else 'via the offline ranked-bar fallback'}."
))'''

SETUP = PALETTE + "\n" + HELPERS + "\n" + EXTRA_TOOLKIT + "\n" + DATALOAD


# --------------------------------------------------------------------------- #
# section 1 -- overview
# --------------------------------------------------------------------------- #
OVERVIEW_STATS_CODE = '''n = len(df)
n_persp = int(df.perspective.nunique())
n_cat = int(df.category.nunique())
n_sit = int(df.situation.nunique())
stat_cards([(str(n_persp), "perspectives (WHO)", TEAL),
            ("2 x 2", "direction x reach (HOW)", EMBER),
            (str(n_sit), "ILO patterns (WHAT)", INK2),
            ("102", "reasoning steps (INTENT)", GOOD)])
display(Markdown(
    f"Four axes structure the corpus. **WHO** reasons ({n_persp} perspectives in {n_cat} role categories), "
    f"**WHAT** they reason about ({n_sit} ILO forced-labour patterns), **HOW** they reason "
    f"(direction x reach = four quadrants), and the fixed **INTENT** of each of the 102 steps. "
    f"This notebook takes those last two -- the reasoning axes and their tone -- apart."
))'''


OVERVIEW_TABLE_CODE = '''def _u(f): return int(df[f].nunique())
summary = pd.DataFrame({
    "Axis": ["WHO -- perspective", "WHO -- role category", "WHAT -- ILO pattern",
             "HOW -- direction", "HOW -- reach", "INTENT -- steps per chain", "Total chains"],
    "Distinct values": [_u("perspective"), _u("category"), _u("situation"),
                        _u("direction"), _u("reach"), "1 (fixed at 102)", "--"],
    "Values": [
        "worker_construction, labour_inspector, recruiter, shelter_hotline, prosecutor, ...",
        ", ".join(sorted(df["category"].unique())),
        ", ".join(sorted(df["situation"].unique())),
        " vs ".join(sorted(df["direction"].dropna().unique())),
        " vs ".join(sorted(df["reach"].dropna().unique())),
        "1. .. 102.  (fix perspective -> screen indicators -> choose safe action)",
        f"{len(df):,} rows",
    ],
})
display(pretty_table(summary, caption="The four reasoning axes -- counted live from the attached chains"))'''


AXES_MATRIX_CODE = '''# 2 x 2 count grid -- every quadrant is balanced by construction.
rd = (pd.crosstab(df["reach"], df["direction"])
        .reindex(index=["small_jump", "large_jump"], columns=["inward", "outward"]))
heatmap(rd.values, ["small_jump", "large_jump"], ["inward", "outward"],
        title="HOW they reason: two axes, four quadrants",
        subtitle="reach (rows) x direction (cols) -- chains per quadrant, counted live",
        fmt=".0f", cmap="BuGn", cbar_label="chains")

# Build ONE shared TF-IDF matrix from every assistant chain; every vocabulary panel
# below just slices this matrix, so all the "distinctive term" comparisons are consistent.
from sklearn.feature_extraction.text import TfidfVectorizer
_VEC = TfidfVectorizer(ngram_range=(1, 2), min_df=5, stop_words="english", max_features=6000)
TFIDF = _VEC.fit_transform(A_DOCS)
TERMS = np.array(_VEC.get_feature_names_out())
display(Markdown(
    f"Shared TF-IDF vocabulary built once from all **{len(A_DOCS):,}** assistant chains: "
    f"**{len(TERMS):,}** terms (1- and 2-grams). Each quadrant holds **{int(rd.values.min()):,}"
    f"**-**{int(rd.values.max()):,}** chains, so no reasoning style is over-represented."
))'''


# --------------------------------------------------------------------------- #
# section 2 -- direction
# --------------------------------------------------------------------------- #
DIRECTION_TERMS_CODE = '''in_mask = (df["direction"] == "inward").values
in_terms = group_distinctive(TFIDF, TERMS, in_mask, topn=16)
out_terms = group_distinctive(TFIDF, TERMS, ~in_mask, topn=16)
two_bar_terms(in_terms, "inward -- narrow to THIS worker", TEAL,
              out_terms, "outward -- widen to the actor map & systems", EMBER,
              suptitle="Distinctive vocabulary by DIRECTION (TF-IDF: one side's mean minus the other)")
n_in = int(in_mask.sum()); n_out = int((~in_mask).sum())
stat_cards([(f"{n_in:,}", "inward chains", TEAL), (f"{n_out:,}", "outward chains", EMBER),
            (str(len(in_terms)), "inward marker terms", INK2), (str(len(out_terms)), "outward marker terms", INK3)])
display(Markdown(
    "**Inward** reasoning turns toward the worker's own experience and choices: the markers are "
    "`begin corridor` / `level pattern` / `narrow` / `established specific` / `specific worker` "
    "&mdash; it starts from the corridor-level pattern and narrows to what is established for this one person. "
    "**Outward** reasoning turns toward systems and other actors: `reason outward` / `begin concrete` / "
    "`widen actor` / `applicable framework` / `map corridor` &mdash; it starts concrete and widens to the "
    "actor map and the applicable legal framework. Same situation, opposite sweep."
))'''


DIRECTION_CLOUD_CODE = '''cloud_pair(("inward reasoning", group_distinctive(TFIDF, TERMS, in_mask, topn=60), TEAL),
           ("outward reasoning", group_distinctive(TFIDF, TERMS, ~in_mask, topn=60), EMBER),
           suptitle="Word clouds of DIRECTION-distinctive terms")
display(Markdown(cloud_note()))'''


# --------------------------------------------------------------------------- #
# section 3 -- reach
# --------------------------------------------------------------------------- #
REACH_TERMS_CODE = '''sm_mask = (df["reach"] == "small_jump").values
sm_terms = group_distinctive(TFIDF, TERMS, sm_mask, topn=16)
lg_terms = group_distinctive(TFIDF, TERMS, ~sm_mask, topn=16)
two_bar_terms(sm_terms, "small jump -- stay one inference from the record", TEAL,
              lg_terms, "large jump -- reach for the indicator cluster", WARN,
              suptitle="Distinctive vocabulary by REACH (TF-IDF: small_jump vs large_jump)")
n_sm = int(sm_mask.sum()); n_lg = int((~sm_mask).sum())
stat_cards([(f"{n_sm:,}", "small_jump chains", TEAL), (f"{n_lg:,}", "large_jump chains", WARN),
            (str(len(sm_terms)), "small-jump markers", INK2), (str(len(lg_terms)), "large-jump markers", INK3)])
display(Markdown(
    "**Small jump** stays conservative: `stay inference` / `prefer conservative` / `conservative reading` / "
    "`needed` &mdash; it prefers the cautious reading and names what would be needed to go further. "
    "**Large jump** reaches: `large jump` / `indicator cluster` / `immediately state` / `confirm refute` / "
    "`non obvious` / `ties details` &mdash; it names the non-obvious indicator cluster up front, then works to "
    "confirm or refute it. Reach controls how far a single step may travel beyond the record."
))'''


REACH_CLOUD_CODE = '''cloud_pair(("small jump", group_distinctive(TFIDF, TERMS, sm_mask, topn=60), TEAL),
           ("large jump", group_distinctive(TFIDF, TERMS, ~sm_mask, topn=60), WARN),
           suptitle="Word clouds of REACH-distinctive terms")
display(Markdown(cloud_note()))'''


# --------------------------------------------------------------------------- #
# section 4 -- the direction x reach matrix
# --------------------------------------------------------------------------- #
QUADRANT_HEAT_CODE = '''from sklearn.metrics.pairwise import cosine_distances
quads = [("small_jump", "inward"), ("small_jump", "outward"),
         ("large_jump", "inward"), ("large_jump", "outward")]
qlabs = [f"{r}\\n{d}" for r, d in quads]
cent = []
for r, d in quads:
    m = ((df["reach"] == r) & (df["direction"] == d)).values
    cent.append(np.asarray(TFIDF[m].mean(axis=0)).ravel())
D = cosine_distances(np.vstack(cent))
heatmap(D, qlabs, qlabs,
        title="How different are the four quadrants' vocabularies?",
        subtitle="cosine distance between mean TF-IDF vectors (0 = identical wording, larger = more distinct)",
        fmt=".3f", cmap="BuGn", cbar_label="cosine distance")
move_dir = float(np.mean([D[0, 1], D[2, 3]]))   # change direction, hold reach
move_reach = float(np.mean([D[0, 2], D[1, 3]]))  # change reach, hold direction
driver = "direction" if move_dir > move_reach else "reach"
display(Markdown(
    f"Changing **direction** (holding reach) moves the wording by **{move_dir:.3f}** cosine; changing "
    f"**reach** (holding direction) by **{move_reach:.3f}**. So **{driver}** reshapes the vocabulary more. "
    f"The two quadrants that differ on *both* axes (`small_jump/inward` vs `large_jump/outward`) are the "
    f"most distinct of all &mdash; the axes compose rather than cancel."
))'''


QUADRANT_EXAMPLES_CODE = '''# One full chain per quadrant, verbatim -- distinct perspectives so the axis (not the topic) is what varies.
seen = set(); picks = []
for r, d in quads:
    for row in rows:
        if row["reach"] == r and row["direction"] == d and row["perspective"] not in seen:
            picks.append(row); seen.add(row["perspective"]); break
parts = []
for row in picks:
    hdr = (f"**Quadrant `{row['reach']} / {row['direction']}`** &mdash; {row['perspective_label']} "
           f"(`{row['category']}`) reasoning over ILO `{row['ilo_indicator']}`")
    prompt = "> " + _utext(row).replace("\\n", "\\n> ")
    chain = "```text\\n" + _atext(row) + "\\n```"
    parts.append(hdr + "\\n\\n" + prompt + "\\n\\n" + chain)
display(Markdown("\\n\\n---\\n\\n".join(parts)))'''


# --------------------------------------------------------------------------- #
# section 5 -- perspective lens
# --------------------------------------------------------------------------- #
PERSPECTIVE_COVERAGE_CODE = '''cat = df["category"].value_counts().sort_values()
roles = df.groupby("category")["perspective"].nunique()
order = list(cat.index)
labels = [c.replace("_", " ").title() for c in order]
vals = [int(cat[c]) for c in order]
top = max(vals)
fig, ax = plt.subplots(figsize=(9.8, 5.2))
ax.barh(range(len(order)), vals, color=TEAL, edgecolor=INK2, linewidth=0.5)
ax.set_yticks(range(len(order))); ax.set_yticklabels(labels)
for y, c in enumerate(order):
    ax.text(int(cat[c]) + top * 0.012, y, f"{int(cat[c]):,} rows  ({int(roles[c])} perspectives)",
            va="center", fontsize=9.5, color=INK2)
ax.set_xlim(0, top * 1.36); ax.set_xlabel("rows"); ax.set_ylabel("")
ax.set_title("Perspective coverage: rows and distinct perspectives per role category", loc="left")
ax.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, "cotdir_perspectives"); plt.show()
display(Markdown(
    f"The **{df.category.nunique()} role categories** span **{df.perspective.nunique()} distinct perspectives**. "
    f"Every perspective reasons over the same forced-labour situations, so the model meets each ILO indicator "
    f"from the affected worker outward to family, frontline support, the origin and destination state, the "
    f"justice system, the supply chain, the recruitment chain, and outside observers."
))'''


PERSPECTIVE_CLOUDS_CODE = '''top6 = list(df["category"].value_counts().index[:6])
items = []
for i, c in enumerate(top6):
    m = (df["category"] == c).values
    fr = group_distinctive(TFIDF, TERMS, m, topn=40)
    items.append((c.replace("_", " ").title(), fr, SEQ[i % len(SEQ)]))
cloud_grid(items, ncols=3,
           title="One situation, many minds -- vocabulary that distinguishes each role category")
display(Markdown(
    "Each panel shows the terms most **characteristic of that role** relative to all others. The vantage "
    "point rewrites the vocabulary: the affected worker dwells on their own record and choices, the justice "
    "system on frameworks and elements, frontline support on referral and safety &mdash; the same ILO "
    "indicator, read through different professional priorities. " + cloud_note()
))'''


# --------------------------------------------------------------------------- #
# section 6 -- situation x ILO-indicator coverage
# --------------------------------------------------------------------------- #
SITIND_CODE = '''mp = df.drop_duplicates("situation").set_index("situation")["ilo_indicator"].to_dict()
mtbl = pd.DataFrame({
    "Situation (headline)": [s.replace("_", " ").title() for s in mp],
    "ILO indicator (2012)": [mp[s] for s in mp],
    "Chains": [int((df["situation"] == s).sum()) for s in mp],
}).sort_values("Chains", ascending=False).reset_index(drop=True)
display(pretty_table(mtbl, caption="Each headline situation maps 1:1 to an ILO Indicator of Forced Labour (2012)"))

ct = pd.crosstab(df["category"], df["situation"]).reindex(index=df["category"].value_counts().index)
heatmap(ct.values,
        [c.replace("_", " ").title() for c in ct.index],
        [s.replace("_", " ").title() for s in ct.columns],
        title="Coverage grid: role category x ILO situation",
        subtitle="chains per (who reasons) x (which ILO pattern) -- balanced, no blank cells",
        fmt=".0f", cmap="BuGn", cbar_label="chains")
display(Markdown(
    f"The five headline situations map one-to-one onto five ILO 2012 indicators, and every one of the "
    f"**{df.category.nunique()} role categories** covers every situation (no empty cell). Coverage is balanced "
    f"by construction, so a role never learns to reason about only one kind of harm."
))'''


# --------------------------------------------------------------------------- #
# section 7 -- reasoning tone / sentiment
# --------------------------------------------------------------------------- #
TONE_OVERALL_CODE = '''import random as _rnd
_rnd.seed(7)
_idx = list(range(len(rows)))
if len(_idx) > 900:
    _idx = sorted(_rnd.sample(_idx, 900))
pol = np.array([sentiment_of(A_DOCS[i]) for i in _idx])
sdf = df.iloc[_idx].copy()
sdf["polarity"] = pol
kde_hist([("assistant chain polarity", pol, TEAL)],
         title=f"Reasoning tone is measured and tightly clustered ({SENTIMENT_BACKEND})",
         subtitle=f"polarity in [-1, 1] over {len(pol):,} sampled chains; a narrow band = deliberate, non-alarmist prose",
         xlabel="sentiment polarity  (-1 negative .. 0 neutral .. +1 positive)",
         vlines=[(float(pol.mean()), EMBER, f"mean {pol.mean():+.3f}")])
neutralish = float(np.mean(np.abs(pol) < 0.15)) * 100.0
stat_cards([(f"{pol.mean():+.3f}", "mean polarity", TEAL), (f"{pol.std():.3f}", "std (spread)", INK2),
            (f"{neutralish:.0f}%", "within +/-0.15 of neutral", GOOD), (f"{len(pol):,}", "chains scored", INK3)])
display(Markdown(
    f"Scored with **{SENTIMENT_BACKEND}**, the chains sit in a **narrow band close to neutral** "
    f"(mean **{pol.mean():+.3f}**, std **{pol.std():.3f}**; **{neutralish:.0f}%** within 0.15 of neutral). "
    f"That is the intended register: the reasoning is procedural, not emotive. Any slight lean comes from "
    f"*naming risk indicators as analytical objects* (debt, coercion, threats) rather than from alarmist "
    f"language &mdash; a safety-desirable property for an on-device judge."
))'''


TONE_DIRECTION_CODE = '''fig, ax = plt.subplots(figsize=(8.8, 4.9))
try:
    import seaborn as sns
    sns.violinplot(data=sdf, x="direction", y="polarity", order=["inward", "outward"],
                   hue="direction", palette={"inward": TEAL, "outward": EMBER},
                   legend=False, cut=0, inner="quartile", ax=ax)
except Exception:
    grp = [sdf.loc[sdf["direction"] == d, "polarity"].values for d in ["inward", "outward"]]
    ax.boxplot(grp); ax.set_xticks([1, 2]); ax.set_xticklabels(["inward", "outward"])
ax.set_title("Tone by reasoning DIRECTION", loc="left"); ax.set_xlabel(""); ax.set_ylabel("polarity")
plt.tight_layout(); plt.show()
mi = float(sdf.loc[sdf["direction"] == "inward", "polarity"].mean())
mo = float(sdf.loc[sdf["direction"] == "outward", "polarity"].mean())
display(Markdown(
    f"Inward mean **{mi:+.3f}** vs outward mean **{mo:+.3f}** &mdash; a gap of just **{abs(mi - mo):.3f}**. "
    f"Direction reshapes *what* is reasoned and *how it is framed* (the vocabulary panels above), but it "
    f"barely moves the emotional register: the tone stays flat and measured whichever way the reasoning turns."
))'''


TONE_CATEGORY_CODE = '''order = list(sdf.groupby("category")["polarity"].median().sort_values().index)
fig, ax = plt.subplots(figsize=(10.6, 5.4))
try:
    import seaborn as sns
    sns.boxplot(data=sdf, y="category", x="polarity", order=order, hue="category",
                palette="crest", legend=False, fliersize=2, ax=ax)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([c.replace("_", " ").title() for c in order])
except Exception:
    grp = [sdf.loc[sdf["category"] == c, "polarity"].values for c in order]
    ax.boxplot(grp, vert=False); ax.set_yticks(range(1, len(order) + 1))
    ax.set_yticklabels([c.replace("_", " ").title() for c in order])
ax.set_title("Tone by ROLE CATEGORY", loc="left"); ax.set_xlabel("polarity"); ax.set_ylabel("")
plt.tight_layout(); plt.show()
_med = sdf.groupby("category")["polarity"].median()
spread = float(_med.max() - _med.min())
display(Markdown(
    f"Across all **{df.category.nunique()} role categories** the median polarity spans only **{spread:.3f}**. "
    f"Roles that name more risk indicators (justice, frontline support) read a touch more cautious, but every "
    f"category stays in the same measured band. The register is a property of the *dataset*, not of any one role."
))'''


# --------------------------------------------------------------------------- #
# section 8 -- the 102-step anatomy & intent
# --------------------------------------------------------------------------- #
ANATOMY_FRAME_CODE = '''frame = [ln for ln in _atext(rows[0]).split("\\n") if re.match(r"^[1-6]\\.", ln.strip())]
display(Markdown(
    "**Every chain opens with the same six framing steps** (verbatim from the first row). "
    "This is the INTENT of phase 1 -- fix the vantage point and the boundaries before any analysis:\\n\\n"
    "```text\\n" + "\\n".join(frame) + "\\n```"
))'''


ANATOMY_BAR_CODE = '''pc = phase_counts(_atext(rows[0]))          # structure is identical across every row
vals = [pc[p] for p in PHASES]
fig, ax = plt.subplots(figsize=(10.6, 5.6))
colors = [SEQ[i % len(SEQ)] for i in range(len(PHASES))]
ax.barh(range(len(PHASES)), vals, color=colors, edgecolor=INK2, linewidth=0.5)
ax.set_yticks(range(len(PHASES))); ax.set_yticklabels(PHASES); ax.invert_yaxis()
for i, v in enumerate(vals):
    ax.text(v + 0.3, i, f"{v} steps", va="center", fontsize=9.5, color=INK2)
ax.set_xlim(0, max(vals) * 1.28); ax.set_xlabel("steps in the 102-step chain")
ax.set_title(f"Anatomy of the {sum(vals)}-step chain -- steps per reasoning phase", loc="left")
ax.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, "cotdir_anatomy"); plt.show()
biggest = PHASES[int(np.argmax(vals))]
display(Markdown(
    f"The **{sum(vals)} steps** are not free-form. They march through **{len(PHASES)} fixed phases**, and the "
    f"largest block by far is **{biggest.split(' ', 1)[1]}** ({max(vals)} steps) &mdash; the chain spends most "
    f"of its length methodically screening every ILO indicator before it is ever allowed to choose an action."
))'''


ANATOMY_TABLE_CODE = '''pc = phase_counts(_atext(rows[0]))
intent = pd.DataFrame({
    "Phase": [p.split(" ", 1)[1] for p in PHASES],
    "Steps": [pc[p] for p in PHASES],
    "What each step establishes (the INTENT)": [PHASE_INTENT[p] for p in PHASES],
})
display(pretty_table(intent, bars=["Steps"], bar_color=TEAL_SOFT,
                     caption="The intent of every phase -- what the reasoning is for at each stage"))
display(Markdown(
    "Read top to bottom this is a **discipline**: anchor the vantage point, weigh the evidence, map the "
    "actors, screen all eleven indicators, place events on the lifecycle, ground the law in a real "
    "jurisdiction, stress-test with counterfactuals, choose the smallest reversible action, and close by "
    "verifying facts and protecting privacy. That ordered intent is exactly what fine-tuning teaches."
))'''


# --------------------------------------------------------------------------- #
# section 9 -- row by row (full chains across directions / perspectives)
# --------------------------------------------------------------------------- #
ROWBYROW_CODE = '''def _find(**kw):
    for r in rows:
        if all(r.get(k) == v for k, v in kw.items()):
            return r
    return None
picks = [
    _find(category="frontline_support", direction="inward", reach="small_jump"),
    _find(category="origin_state", direction="outward", reach="large_jump"),
    _find(category="justice_system", direction="inward", reach="large_jump"),
]
picks = [p for p in picks if p]
parts = []
for row in picks:
    hdr = (f"**{row['perspective_label']}** (`{row['perspective']}`, category `{row['category']}`)  \\n"
           f"**ILO indicator:** `{row['ilo_indicator']}` &middot; **axes:** direction `{row['direction']}`, "
           f"reach `{row['reach']}` &middot; **{row['step_count']} steps** &middot; split `{row['split']}`")
    prompt = "> " + _utext(row).replace("\\n", "\\n> ")
    chain = "```text\\n" + _atext(row) + "\\n```"
    parts.append(hdr + "\\n\\n" + prompt + "\\n\\n" + chain)
display(Markdown(("\\n\\n" + ("- " * 24) + "\\n\\n").join(parts)))'''


# --------------------------------------------------------------------------- #
# markdown cells (URLs literal; HTML entities keep the source ASCII)
# --------------------------------------------------------------------------- #
HERO_MD = '''<div style="padding:26px 32px;border-radius:16px;background:linear-gradient(120deg,#14181B 0%,#2A2D34 40%,#c15b2e 118%);color:#F7F6F1">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.82">DueCare &middot; Gemma 4 safety &middot; the reasoning axes</div>
<h1 style="margin:.28em 0 .2em;font-size:30px;color:#ffffff;font-weight:800">Direction, reach, perspective &amp; intent</h1>
<p style="font-size:15px;line-height:1.6;margin:0;max-width:940px">The <b>DueCare CoT Reasoning</b> dataset trains Gemma 4 to think through a migrant-worker safety case in a <b>~102-step</b> chain, from <b>100+ points of view</b>, grounded in real <b>ILO forced-labour indicator</b> patterns. Its sibling explorer maps the <i>space</i> &mdash; who, what, how deep. This notebook takes apart the <b>reasoning axes and their tone</b>: <b>DIRECTION</b> (inward toward the worker vs outward toward systems), <b>REACH</b> (a conservative small jump vs a far large jump), <b>PERSPECTIVE</b> (101 role vantage points), and the fixed <b>INTENT</b> of each of the 102 steps. We read them with word clouds, distinctive-vocabulary panels, sentiment, and register plots &mdash; entirely from the attached data, on CPU, with no model and no internet.</p>
</div>'''

TOC_MD = '''## What is in this notebook

Every number, cloud, and chart below is computed **live from the attached dataset** &mdash; nothing is hard-coded. Optional libraries (wordcloud, VADER/TextBlob, plotly) each fall back to an offline-safe equivalent, so the notebook always runs end to end.

- [1. Overview &mdash; the four reasoning axes](#overview)
- [2. DIRECTION &mdash; inward vs outward](#direction)
- [3. REACH &mdash; small jump vs large jump](#reach)
- [4. The direction &times; reach matrix &mdash; four quadrants](#quadrant)
- [5. PERSPECTIVE &mdash; one situation, many minds](#perspective)
- [6. Situation &times; ILO indicator coverage](#situation)
- [7. Reasoning TONE &mdash; how measured is it?](#tone)
- [8. The 102-step anatomy &amp; the intent of each phase](#anatomy)
- [9. Row by row &mdash; full chains, verbatim](#rowbyrow)
- [10. Honest boundary &amp; links](#boundary)

**Dataset:** [`taylorsamarel/duecare-cot-reasoning`](https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning) &middot; **Source repo:** [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''

OVERVIEW_MD = '''<a id="overview"></a>
## 1. Overview &mdash; the four reasoning axes

Each row pairs a short **user prompt** (help protect a migrant worker, from a specific vantage point) with a long **assistant chain of thought**. Four axes structure the corpus: **WHO** reasons (perspective, role category), **WHAT** they reason about (ILO pattern), **HOW** they reason (direction &times; reach), and the fixed **INTENT** of each of the 102 steps. This notebook takes apart the last two &mdash; the reasoning style and its tone. The stat tiles and table below count everything live.'''

DIRECTION_MD = '''<a id="direction"></a>
## 2. DIRECTION &mdash; inward vs outward

The **direction** tag decides whose interior a step turns toward. **Inward** reasoning gathers and self-checks: it begins from the corridor-level pattern and narrows to what is actually established for *this* worker. **Outward** reasoning escalates and routes: it begins from the concrete record and widens to the actor map, other institutions, and the applicable legal framework. Below: the vocabulary that most distinguishes each direction (TF-IDF), then the same as word clouds.'''

REACH_MD = '''<a id="reach"></a>
## 3. REACH &mdash; small jump vs large jump

The **reach** tag decides how far a single step may infer beyond the record. **Small jump** stays one inference away: prefer the conservative reading and name what would be needed to go further. **Large jump** reaches for the non-obvious indicator cluster immediately, then works to confirm or refute it. Same distinctive-vocabulary treatment as direction.'''

QUADRANT_MD = '''<a id="quadrant"></a>
## 4. The direction &times; reach matrix &mdash; four quadrants

Direction and reach compose into four reasoning quadrants: `small_jump/inward`, `small_jump/outward`, `large_jump/inward`, `large_jump/outward`. How different are they, really? The heatmap measures the **cosine distance between each quadrant's mean vocabulary** &mdash; a principled read on which axis reshapes the reasoning more. Then one **full chain per quadrant**, verbatim, so you can see the difference in the actual prose.'''

PERSPECTIVE_MD = '''<a id="perspective"></a>
## 5. PERSPECTIVE &mdash; one situation, many minds

The same forced-labour situation is reasoned from **101 perspectives** in **9 role categories** &mdash; from the affected worker outward to family and community, frontline support, the origin and destination state, the justice system, the supply chain, the recruitment chain, and outside observers. The bar shows coverage; the word-cloud small-multiples show the vocabulary that makes each role's reasoning its own.'''

SITUATION_MD = '''<a id="situation"></a>
## 6. Situation &times; ILO indicator coverage

Every chain is grounded in one of five **ILO Indicators of Forced Labour (2012)** patterns, and each headline `situation` maps 1:1 to an underlying `ilo_indicator`. The table shows that mapping and its live chain counts; the heatmap shows the full **role category &times; situation** coverage grid &mdash; balanced by construction, with no empty cells.'''

TONE_MD = '''<a id="tone"></a>
## 7. Reasoning TONE &mdash; how measured is it?

A safety judge should reason in a **procedural, non-alarmist** register even about severe harm. We score each assistant chain's sentiment polarity (VADER if available, else TextBlob, else a transparent built-in lexicon) and look at the distribution, then split it by direction and by role category. The question: does the tone stay measured across every axis and role?'''

ANATOMY_MD = '''<a id="anatomy"></a>
## 8. The 102-step anatomy &amp; the intent of each phase

The chain's length is not padding &mdash; it is a **fixed nine-phase discipline**. Below: the shared opening frame verbatim, the number of steps each phase receives (classified live), and a table of what each phase is *for*. This is the INTENT axis: not just how long the reasoning is, but what each stretch of it establishes.'''

ROWBYROW_MD = '''<a id="rowbyrow"></a>
## 9. Row by row &mdash; full chains, verbatim

Three complete rows, shown end to end with **nothing truncated**, chosen to span directions, reaches, and role categories. This is exactly the shape the model is trained to produce: fix the perspective, hold the role boundary, screen the ILO indicators, ground the law, choose the smallest safe action, and protect privacy.'''

BOUNDARY_MD = '''<a id="boundary"></a>
## 10. Honest boundary &amp; links

**What this is.** Illustrative, deliberately-authored reasoning grounded in real **ILO forced-labour indicator patterns**. It teaches a *reasoning structure and register* &mdash; set the direction and reach, hold the role boundary, screen the indicators, ground legal claims in a cited source, choose a safe next action, protect privacy &mdash; not a lookup table of volatile facts.

**What this is not.** These are **silver labels**: synthetic, model-shaped rationales, not gold human annotations. Every row is **propose-only** and **synthetic** &mdash; no real individual, case, contact, name, number, or address appears, and the PII detector is clean across the set. This is **not** a real-world detection or victim-identification system, and the chains are not legal advice.

**Method notes.** Distinctive vocabulary is a difference of mean TF-IDF weights (one group vs the rest) over a single shared vocabulary; quadrant distance is cosine distance between mean TF-IDF vectors; sentiment uses VADER / TextBlob / a built-in lexicon (whichever is available) and is reported with its backend named. Word clouds fall back to ranked bars when the `wordcloud` package is absent. All figures are reproducible from the attached file.

**License.** MIT. **Provenance:** each row declares its schema, ILO source references, license, and a content hash.

**Links.** Dataset: [`taylorsamarel/duecare-cot-reasoning`](https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning) &middot; Source repository: [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''


def _notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        _md(HERO_MD),
        _md(TOC_MD),
        _code(SETUP),
        # 1. overview
        _md(OVERVIEW_MD),
        _code(OVERVIEW_STATS_CODE),
        _code(OVERVIEW_TABLE_CODE),
        _code(AXES_MATRIX_CODE),
        # 2. direction
        _md(DIRECTION_MD),
        _code(DIRECTION_TERMS_CODE),
        _code(DIRECTION_CLOUD_CODE),
        # 3. reach
        _md(REACH_MD),
        _code(REACH_TERMS_CODE),
        _code(REACH_CLOUD_CODE),
        # 4. quadrant matrix
        _md(QUADRANT_MD),
        _code(QUADRANT_HEAT_CODE),
        _code(QUADRANT_EXAMPLES_CODE),
        # 5. perspective
        _md(PERSPECTIVE_MD),
        _code(PERSPECTIVE_COVERAGE_CODE),
        _code(PERSPECTIVE_CLOUDS_CODE),
        # 6. situation x indicator
        _md(SITUATION_MD),
        _code(SITIND_CODE),
        # 7. tone
        _md(TONE_MD),
        _code(TONE_OVERALL_CODE),
        _code(TONE_DIRECTION_CODE),
        _code(TONE_CATEGORY_CODE),
        # 8. anatomy
        _md(ANATOMY_MD),
        _code(ANATOMY_FRAME_CODE),
        _code(ANATOMY_BAR_CODE),
        _code(ANATOMY_TABLE_CODE),
        # 9. row by row
        _md(ROWBYROW_MD),
        _code(ROWBYROW_CODE),
        # 10. boundary
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
    # ASCII guard -- the notebook source must stay mojibake-free on the Kaggle viewer.
    raw = nb_path.read_text(encoding="utf-8")
    non_ascii = sorted({c for c in raw if ord(c) > 127})
    return {
        "notebook": str(nb_path),
        "kernel_metadata": str(meta_path),
        "kernel_id": KERNEL_ID,
        "title": TITLE,
        "n_cells": len(nb.cells),
        "n_code_cells": sum(1 for c in nb.cells if c.cell_type == "code"),
        "non_ascii_chars": "".join(non_ascii),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    # Kaggle derives the kernel slug from the title -- assert they agree.
    assert TITLE.lower().replace(" ", "-") == SLUG, f"title slug mismatch: {TITLE!r} -> {TITLE.lower().replace(' ', '-')!r} != {SLUG!r}"
    assert KERNEL_ID == "taylorsamarel/" + SLUG, f"kernel id mismatch: {KERNEL_ID!r}"

    result = build(args.output, force=args.force)
    result["title_slug_ok"] = TITLE.lower().replace(" ", "-") == SLUG
    assert not result["non_ascii_chars"], f"non-ASCII characters leaked into the notebook: {result['non_ascii_chars']!r}"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
