#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the polished, richly-visual DueCare Prompt-and-Response NLP explorer notebook.

Emits a Kaggle notebook (nbformat) over the published dataset
`taylorsamarel/duecare-prompt-response-showcase` (prompt_response_showcase.csv):
1,087 synthetic/composite migrant-worker-safety prompts, each answered by gemma4:31b under three
arms -- baseline (bare model), harness_core (persona + GREP indicator rules + retrieval + tools),
harness_full (+ online). The notebook showcases the RAW prompts and RAW responses ROW BY ROW, then
runs a comprehensive classic-NLP pass over them -- corpus composition, length & coverage, response
structure, distinctive vocabulary (unigrams + bigrams + trigrams via weighted log-odds), per-category
vocabulary shift, sentiment, readability, safety-vocabulary detection, lexical register (diversity /
hedging / directives), and word clouds -- entirely on CPU, no GPU, no internet, no model loading.
Every optional NLP package is wrapped in try/except with an offline-safe fallback, so the notebook
runs to completion on Kaggle with enable_internet=false.

    python scripts/build_prompt_response_nlp_notebook.py
    python scripts/build_prompt_response_nlp_notebook.py --force
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "prompt_response_nlp"
DATASET_ID = "taylorsamarel/duecare-prompt-response-showcase"
CSV_NAME = "prompt_response_showcase.csv"
TITLE = "DueCare Prompt And Response NLP Explorer"
SLUG = "duecare-prompt-and-response-nlp-explorer"
KERNEL_ID = "taylorsamarel/" + SLUG
DS_URL = "https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase"
INDEX_URL = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here"
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
# a recursive-glob load + all NLP feature engineering. Helpers are EMBEDDED, so
# the notebook never imports _notebook_viz at runtime. Every optional NLP package
# is wrapped in try/except with an offline-safe fallback. Written as a RAW string
# so regex backslashes survive; runtime newlines use NL = chr(10), never "\n".
# --------------------------------------------------------------------------- #
DATALOAD = r'''import glob, json, os, re
from collections import Counter
from pathlib import Path
from IPython.display import Markdown, display

NL = chr(10)
BULLET = chr(0x2022)
ARMS = ["baseline", "harness_core", "harness_full"]
ARM_LABEL = {"baseline": "baseline (bare Gemma 4)",
             "harness_core": "harness_core (persona + GREP + retrieval + tools)",
             "harness_full": "harness_full (+ online)"}

# --- Load the published dataset via a RECURSIVE glob (Kaggle mounts datasets at an unpredictable path) ---
if os.path.exists("/kaggle/input"):
    print("mounted under /kaggle/input:", os.listdir("/kaggle/input"))

def _find(name):
    fs = sorted(glob.glob("/kaggle/input/**/" + name, recursive=True))
    return fs[0] if fs else None

_csv = _find("prompt_response_showcase.csv")
if _csv:
    _df_raw = pd.read_csv(_csv)
    rows = _df_raw.to_dict("records")
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

META = ["prompt_id", "category", "corridor", "difficulty"]
df = pd.DataFrame([{k: _txt(r.get(k)) for k in META} for r in rows])

OUT = Path("/kaggle/working") if os.path.isdir("/kaggle/working") else Path(".")
def save(fig, stem):
    try:
        fig.savefig(OUT / (stem + ".png"), bbox_inches="tight")
    except Exception:
        pass

# --------------------------------------------------------------------------- #
# extra chart primitives (violin + ECDF) -- matplotlib-native, so they render
# offline with no seaborn / no plotly. Shared by several sections below.
# --------------------------------------------------------------------------- #
def violins(ax, series, ylabel="", annotate=True):
    """Colored violin per group. series: list of (name, values, color)."""
    data = [np.asarray(v, dtype=float) for _, v, _ in series]
    data = [d[np.isfinite(d)] for d in data]
    pos = list(range(1, len(series) + 1))
    parts = ax.violinplot(data, positions=pos, showmeans=False, showextrema=False, widths=0.82)
    for body, (_, _, col) in zip(parts["bodies"], series):
        body.set_facecolor(col); body.set_alpha(0.28); body.set_edgecolor(col); body.set_linewidth(1.5)
    for p, d, (_, _, col) in zip(pos, data, series):
        if not len(d):
            continue
        q1, med, q3 = np.percentile(d, [25, 50, 75])
        ax.plot([p, p], [q1, q3], color=col, lw=6, solid_capstyle="round", alpha=0.55, zorder=3)
        ax.plot(p, med, "o", color=PAPER, markeredgecolor=col, markeredgewidth=2, markersize=8, zorder=4)
        if annotate:
            ax.text(p + 0.10, med, format(med, ".0f"), va="center", ha="left", fontsize=9.5, color=col, fontweight="bold")
    ax.set_xticks(pos); ax.set_xticklabels([n for n, _, _ in series]); ax.set_ylabel(ylabel)
    ax.grid(axis="x", visible=False)

def ecdf(ax, series, xlabel=""):
    """Empirical cumulative distribution, one line per series (name, values, color)."""
    for name, v, col in series:
        v = np.sort(np.asarray(v, dtype=float)); v = v[np.isfinite(v)]
        if not len(v):
            continue
        y = np.arange(1, len(v) + 1) / len(v)
        ax.plot(v, y, color=col, lw=2.6, label=name, zorder=3)
    ax.set_xlabel(xlabel); ax.set_ylabel("cumulative share of responses")
    ax.set_ylim(0, 1.02); ax.legend(); ax.grid(True, alpha=0.5)

# --------------------------------------------------------------------------- #
# NLP toolkit -- every optional dependency is wrapped with an offline fallback.
# --------------------------------------------------------------------------- #

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
        _POS = set("good help helpful support supportive protect protected safe safety right rights fair fairly legitimate legal lawful trust benefit secure assist care caring honest freedom free clear proper properly ensure ensures genuine positive welcome respect respected verify verified valid ethical compliant compliance".split())
        _NEG = set("trafficking forced coerced coercion coercive debt bondage exploit exploited exploitation illegal fraud fraudulent scam abuse abusive threat threatened penalty penalties victim deception deceptive withheld withholding retention unlawful violation violations harm harmful danger dangerous risk risky fear trap trapped retaliation seizure confiscation bonded slavery servitude".split())
        def sentiment(t):
            toks = re.findall(r"[a-z']+", (t or "").lower())
            p = sum(w in _POS for w in toks)
            n = sum(w in _NEG for w in toks)
            return (p - n) / (p + n) if (p + n) else 0.0
        SENT_BACKEND = "bundled-lexicon"

# ---- readability: textstat -> Flesch reading-ease approximation ----
try:
    import textstat
    def flesch(t):
        try:
            return float(textstat.flesch_reading_ease(t or ""))
        except Exception:
            return 0.0
    READ_BACKEND = "textstat"
except Exception:
    def _syllables(w):
        w = w.lower()
        vowels = "aeiouy"
        count, prev = 0, False
        for ch in w:
            isv = ch in vowels
            if isv and not prev:
                count += 1
            prev = isv
        if w.endswith("e") and count > 1:
            count -= 1
        return max(count, 1)
    def flesch(t):
        sents = [s for s in re.split(r"[.!?]+", t or "") if s.strip()]
        words = re.findall(r"[A-Za-z]+", t or "")
        if not words or not sents:
            return 0.0
        syl = sum(_syllables(w) for w in words)
        return 206.835 - 1.015 * (len(words) / len(sents)) - 84.6 * (syl / len(words))
    READ_BACKEND = "flesch-approx"

# ---- distinctive vocabulary + n-grams: sklearn CountVectorizer -> pure-python Counter ----
try:
    from sklearn.feature_extraction.text import CountVectorizer  # noqa: F401
    HAS_SK = True
except Exception:
    HAS_SK = False

_STOP = set("i me my myself we our ours ourselves you your yours he him his she her hers it its they them their theirs this that these those am is are was were be been being have has had do does did doing a an the and but if or because as until while of at by for with about against between into through during to from in out on off over under again further then once here there all any both each few more most other some such no nor not only own same so than too very can will just should now also may must shall would could one two three per within upon them into their they".split())
_TOKPAT = re.compile(r"[a-z][a-z0-9]{2,}")

def _py_tokens(t):
    return [w for w in _TOKPAT.findall((t or "").lower()) if w not in _STOP]

def _arm_counter(texts):
    c = Counter()
    for t in texts:
        c.update(_py_tokens(t))
    return c

def _logodds_z(na, nb, nvocab):
    """Weighted log-odds-ratio z-score with an (uninformative) Dirichlet prior --
    Monroe, Colaresi & Quinn (2008), "Fightin' Words". Balances effect size against
    frequency, so frequent discriminators outrank rare ones. Positive z favors A."""
    na = np.asarray(na, dtype=float); nb = np.asarray(nb, dtype=float)
    ta, tb = na.sum(), nb.sum()
    alpha = 0.01                       # per-word Dirichlet prior
    a0 = alpha * max(nvocab, 1)        # prior mass
    la = np.log((na + alpha) / (ta + a0 - na - alpha))
    lb = np.log((nb + alpha) / (tb + a0 - nb - alpha))
    delta = la - lb                                   # log-odds-ratio
    var = 1.0 / (na + alpha) + 1.0 / (nb + alpha)     # its approx variance
    return delta / np.sqrt(var)                       # -> standardized z-score

def _counts_ab(texts_a, texts_b, ngram=(1, 1), min_total=5):
    """Shared vocabulary counts across two arms. sklearn CountVectorizer (with an n-gram
    range) when available; a pure-python Counter over the same n-grams as the offline fallback."""
    if HAS_SK:
        from sklearn.feature_extraction.text import CountVectorizer
        cv = CountVectorizer(stop_words="english", lowercase=True, ngram_range=ngram, min_df=min_total,
                             token_pattern=r"(?u)\b[a-z][a-z0-9]{2,}\b")
        X = cv.fit_transform(list(texts_a) + list(texts_b))
        vocab = list(cv.get_feature_names_out())
        na = np.asarray(X[:len(texts_a)].sum(axis=0)).ravel().astype(float)
        nb = np.asarray(X[len(texts_a):].sum(axis=0)).ravel().astype(float)
    else:
        lo, hi = ngram
        def _grams(texts):
            c = Counter()
            for t in texts:
                toks = _py_tokens(t)
                for k in range(lo, hi + 1):
                    for i in range(len(toks) - k + 1):
                        c[" ".join(toks[i:i + k])] += 1
            return c
        ca, cb = _grams(texts_a), _grams(texts_b)
        vocab = sorted({w for w in set(ca) | set(cb) if ca.get(w, 0) + cb.get(w, 0) >= min_total})
        na = np.array([ca.get(w, 0) for w in vocab], dtype=float)
        nb = np.array([cb.get(w, 0) for w in vocab], dtype=float)
    return vocab, na, nb

def _rank_by_logodds(vocab, na, nb, n):
    if not len(vocab):
        return [], []
    z = _logodds_z(na, nb, len(vocab))
    order = np.argsort(z)
    b_top = [(vocab[i], float(-z[i]), int(na[i]), int(nb[i])) for i in order[:n]]
    a_top = [(vocab[i], float(z[i]), int(na[i]), int(nb[i])) for i in order[::-1][:n]]
    return a_top, b_top

def distinctive_terms(texts_a, texts_b, n=15, min_total=5):
    """Single words most over-represented in A vs B (and vice-versa), by weighted log-odds z.

    Returns (a_top, b_top); each item is (term, z_score, count_a, count_b).
    """
    vocab, na, nb = _counts_ab(texts_a, texts_b, ngram=(1, 1), min_total=min_total)
    return _rank_by_logodds(vocab, na, nb, n)

def distinctive_ngrams(texts_a, texts_b, ngram=(2, 2), n=12, min_total=4):
    """Same weighted log-odds ranking, but over multi-word n-grams (bigrams / trigrams)."""
    vocab, na, nb = _counts_ab(texts_a, texts_b, ngram=ngram, min_total=min_total)
    return _rank_by_logodds(vocab, na, nb, n)

def top_frequencies(texts, k=140):
    if HAS_SK:
        from sklearn.feature_extraction.text import CountVectorizer
        cv = CountVectorizer(stop_words="english", lowercase=True,
                             token_pattern=r"(?u)\b[a-z][a-z0-9]{2,}\b", min_df=2)
        X = cv.fit_transform(texts)
        counts = np.asarray(X.sum(axis=0)).ravel()
        vocab = cv.get_feature_names_out()
        pairs = sorted(zip(vocab, counts), key=lambda kv: kv[1], reverse=True)[:k]
        return {w: int(v) for w, v in pairs}
    return {w: int(v) for w, v in _arm_counter(texts).most_common(k)}

# ---- structural + safety-vocabulary detectors (regex, always available) ----
_RX_WORD = re.compile(r"[A-Za-z0-9']+")
_RX_SENT = re.compile(r"[.!?]+")
_RX_MDH = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_RX_BOLDH = re.compile(r"^\*\*[^*]{2,}\*\*:?$")
_RX_ILO = re.compile(r"\b(ilo|convention|conventions|c0?29|c181|c189|c097|c143|c095|icrmw|palermo|article)\b", re.I)
_RX_STAT = re.compile(r"\b(act|section|statute|statutory|regulation|regulations|law|laws|rule|rules|tvpa|bcea|emigration|foreign employment)\b", re.I)
_RX_REF = re.compile(r"\b(cannot|can't|will not|won't|unable|prohibited|decline|instead|report|reporting|authorities)\b", re.I)
_RX_RES = re.compile(r"\b(hotline|helpline|ngo|embassy|consulate|polaris|call|department of|ministry|tribunal|shelter|helpdesk|support)\b", re.I)
_RX_IND = re.compile(r"(indicator|debt bondage|passport retention|withholding|wage withholding|coercion|deception|forced lab|recruitment fee|confiscation|movement)", re.I)
_RX_HEDGE = re.compile(r"\b(may|might|could|would|should|consider|possibly|perhaps|likely|generally|typically|often|sometimes|appear|appears|seem|seems|suggest|suggests|potentially)\b", re.I)
_RX_DIRECT = re.compile(r"\b(report|contact|verify|check|ensure|avoid|seek|request|insist|refuse|document|retain|call|never|always|must|immediately|do not|don't)\b", re.I)

# (key, regex object, human label) for the five safety-language detectors, used across sections 5 / 10 / 13.
SAFE_PATTERNS = [("cite_ilo", _RX_ILO, "ILO / convention cite"),
                 ("cite_statute", _RX_STAT, "statute / legal ref"),
                 ("refusal", _RX_REF, "refusal / redirection"),
                 ("resource", _RX_RES, "resource / hotline"),
                 ("indicator", _RX_IND, "indicator language")]

def _bullets(t):
    c = 0
    for ln in (t or "").split(NL):
        s = ln.strip()
        if s[:1] in ("-", "*", "+", BULLET):
            c += 1
    return c

def _numbered(t):
    c = 0
    for ln in (t or "").split(NL):
        s = ln.strip()
        m = 0
        while m < len(s) and s[m].isdigit():
            m += 1
        if 0 < m < len(s) and s[m] in (".", ")"):
            c += 1
    return c

def _headers(t):
    c = 0
    for ln in (t or "").split(NL):
        if _RX_MDH.match(ln) or _RX_BOLDH.match(ln.strip()):
            c += 1
    return c

def _paragraphs(t):
    return len([b for b in re.split(r"\n{2,}", t or "") if b.strip()])

def _mattr(toks, w=50, cap=400):
    """Moving-average type-token ratio: mean unique/total over sliding windows.
    Length-controlled, so it does not simply fall as a response gets longer."""
    toks = toks[:cap]
    if len(toks) < w:
        return len(set(toks)) / len(toks) if toks else 0.0
    rs = []
    for i in range(0, len(toks) - w + 1, 10):
        rs.append(len(set(toks[i:i + w])) / w)
    return sum(rs) / len(rs) if rs else 0.0

# --------------------------------------------------------------------------- #
# feat -- one long-form row per (prompt, arm) with every derived feature.
# --------------------------------------------------------------------------- #
_records = []
for r in rows:
    for arm in ARMS:
        t = _txt(r.get(arm + "_response"))
        toks = _py_tokens(t)
        w = len(_RX_WORD.findall(t))
        s = max(len(_RX_SENT.findall(t)), 1)
        _records.append({
            "prompt_id": _txt(r.get("prompt_id")),
            "category": _txt(r.get("category")),
            "corridor": _txt(r.get("corridor")),
            "difficulty": _txt(r.get("difficulty")),
            "arm": arm,
            "text": t,
            "chars": len(t),
            "words": w,
            "sentences": s,
            "sent_len": w / s,
            "bullets": _bullets(t),
            "numbered": _numbered(t),
            "headers": _headers(t),
            "paragraphs": _paragraphs(t),
            "mattr": _mattr(toks),
            "hedges": len(_RX_HEDGE.findall(t)),
            "directives": len(_RX_DIRECT.findall(t)),
            "sentiment": sentiment(t),
            "flesch": flesch(t),
            "cite_ilo": 1 if _RX_ILO.search(t) else 0,
            "cite_statute": 1 if _RX_STAT.search(t) else 0,
            "refusal": 1 if _RX_REF.search(t) else 0,
            "resource": 1 if _RX_RES.search(t) else 0,
            "indicator": 1 if _RX_IND.search(t) else 0,
        })
feat = pd.DataFrame(_records)

def _med(arm, col):
    return float(feat.loc[feat.arm == arm, col].median())

display(Markdown(
    "Loaded **" + format(len(rows), ",") + " prompts** x **3 arms** = **" + format(len(feat), ",") +
    " prompt/response pairs** across **" + str(df.category.nunique()) + " categories**, **" +
    str(df.corridor.nunique()) + " corridors**, and **" + str(df.difficulty.nunique()) +
    " difficulty bands**.  NLP backends selected: sentiment = `" + SENT_BACKEND +
    "`, readability = `" + READ_BACKEND + "`, vectorizer = `" + ("sklearn" if HAS_SK else "pure-python Counter") +
    "`.  Every chart below is computed live from these features -- no model, no GPU, no internet."
))'''

SETUP = PALETTE + "\n" + HELPERS + "\n" + DATALOAD


# --------------------------------------------------------------------------- #
# Section 1 -- corpus at a glance (orientation before the raw examples)
# --------------------------------------------------------------------------- #
S1A_CODE = r'''stat_cards([
    (format(len(rows), ","), "prompts", INK2),
    (format(len(feat), ","), "prompt/response pairs", TEAL),
    (str(df.category.nunique()), "prompt categories", GOOD),
    (str(df.corridor.nunique()), "corridors", WARN),
])

cc = df.category.value_counts().head(16).iloc[::-1]
fig, ax = plt.subplots(figsize=(9.8, 6.8))
ax.barh(range(len(cc)), cc.values, color=TEAL, edgecolor=INK2, linewidth=0.4)
ax.set_yticks(range(len(cc))); ax.set_yticklabels([c.replace("_", " ") for c in cc.index], fontsize=9.5)
for yi, v in enumerate(cc.values):
    ax.text(v + 0.15, yi, str(int(v)), va="center", fontsize=9, color=INK3)
ax.set_xlabel("prompts in the showcase"); ax.grid(axis="y", visible=False)
_title(ax, "Prompt categories -- the 16 largest", "each category is a distinct attack surface or worker question type")
fig.tight_layout(); save(fig, "nlp_categories"); plt.show()

display(Markdown(
    "The showcase spans **" + str(df.category.nunique()) + " prompt categories** -- from benign worker questions "
    "(`rights_query`, `wage_query`, `complaint_query`) through recruitment-fraud mechanics (`fee_splitting`, "
    "`free_visa_backloaded_debt`, `crypto_ewallet_fee_rail`) to adversarial jailbreak framings "
    "(`override_jailbreak`, `pretext_jailbreak`, `benevolent_framing`). That spread is deliberate: it is exactly "
    "where a bare model and a harnessed model diverge most, which is what the rest of this notebook measures."
))'''

S1B_CODE = r'''fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.6, 5.0))

order = [d for d in ["easy", "medium", "hard"] if d in set(df.difficulty)] or list(df.difficulty.value_counts().index)
dc = [int((df.difficulty == d).sum()) for d in order]
dcol = {"easy": GOOD, "medium": WARN, "hard": EMBER}
axL.bar(range(len(order)), dc, color=[dcol.get(d, TEAL) for d in order], edgecolor=INK2, linewidth=0.5, width=0.66)
axL.set_xticks(range(len(order))); axL.set_xticklabels([d + NL + "(" + format(n, ",") + ")" for d, n in zip(order, dc)])
for xi, v in enumerate(dc):
    axL.text(xi, v + max(dc) * 0.01, format(v, ","), ha="center", va="bottom", fontsize=10, color=INK2, fontweight="bold")
axL.set_ylabel("prompts"); axL.grid(axis="x", visible=False)
_title(axL, "Difficulty mix", "hard prompts dominate by design")

named = df[df.corridor != "various"].corridor.value_counts().head(10).iloc[::-1]
axR.barh(range(len(named)), named.values, color=TEAL_DK, edgecolor=INK2, linewidth=0.4)
axR.set_yticks(range(len(named))); axR.set_yticklabels(named.index, fontsize=9)
for yi, v in enumerate(named.values):
    axR.text(v + 0.04, yi, str(int(v)), va="center", fontsize=8.5, color=INK3)
axR.set_xlabel("prompts"); axR.grid(axis="y", visible=False)
_title(axR, "Named migration corridors", "most prompts are corridor-agnostic ('various')")
fig.tight_layout(); save(fig, "nlp_corpus_mix"); plt.show()

_various = int((df.corridor == "various").sum())
display(Markdown(
    "Most prompts (**" + format(_various, ",") + "** of **" + format(len(df), ",") + "**) are written "
    "corridor-agnostic so the safety reasoning generalizes; a focused subset is grounded in specific high-risk "
    "corridors (Myanmar->Thailand, India->Saudi Arabia, Bangladesh->Malaysia, Vietnam->Taiwan fishing, and others). "
    "Hard prompts dominate because hard prompts are where safety behavior is actually put under strain."
))'''


# --------------------------------------------------------------------------- #
# Section 2 -- RAW, ROW BY ROW (the centerpiece). Full verbatim triples,
# no truncation, split into a divergence block and an enrichment block.
# --------------------------------------------------------------------------- #
S2A_CODE = r'''def _head_refusal(t):
    head = (t or "")[:220].lower()
    return any(k in head for k in ["i cannot", "i can't", "i will not", "i won't", "i am unable", "i'm unable",
                                   "i am prohibited", "i can not", "i am not able", "i must decline", "i'm not able"])

def _emit(r, i, tag):
    meta = ("**Example " + str(i) + " " + tag + "** &middot; `" + str(r.get("prompt_id")) + "` &middot; category `" +
            str(r.get("category")) + "` &middot; corridor `" + str(r.get("corridor")) +
            "` &middot; difficulty `" + str(r.get("difficulty")) + "`")
    display(Markdown(meta))
    display(Markdown("**Raw prompt (verbatim):**" + NL + NL + "```text" + NL + str(r.get("prompt_text") or "") + NL + "```"))
    display(Markdown("**baseline -- bare Gemma 4, no harness (verbatim):**" + NL + NL +
                     "```text" + NL + str(r.get("baseline_response") or "") + NL + "```"))
    display(Markdown("**harness_core -- persona + GREP indicators + retrieval + tools (verbatim):**" + NL + NL +
                     "```text" + NL + str(r.get("harness_core_response") or "") + NL + "```"))
    display(Markdown("---"))

shown_ids, shown_cats = set(), set()
picks = []
for r in rows:
    pid = str(r.get("prompt_id")); cat = str(r.get("category"))
    if pid in shown_ids or cat in shown_cats:
        continue
    if not _head_refusal(r.get("baseline_response")) and _head_refusal(r.get("harness_core_response")):
        picks.append(r); shown_ids.add(pid); shown_cats.add(cat)
    if len(picks) >= 3:
        break

display(Markdown("### Divergence: the bare model engages, the harness refuses and redirects" + NL + NL +
                 "Showing **" + str(len(picks)) + "** rows end to end, each from a different category -- nothing truncated. "
                 "Read the bare-model answer, then the same prompt under the harness."))
for i, r in enumerate(picks, 1):
    _emit(r, i, "(safety divergence)")'''

S2B_CODE = r'''picks_b = []
for r in rows:
    pid = str(r.get("prompt_id")); cat = str(r.get("category"))
    if pid in shown_ids or cat in shown_cats:
        continue
    core = str(r.get("harness_core_response") or "")
    if not _head_refusal(core) and "ilo" in core.lower() and len(core) > 1400:
        picks_b.append(r); shown_ids.add(pid); shown_cats.add(cat)
    if len(picks_b) >= 4:
        break
# top up from the front so we always show at least a few enrichment rows, across fresh categories
for r in rows:
    if len(picks_b) >= 4:
        break
    pid = str(r.get("prompt_id")); cat = str(r.get("category"))
    if pid in shown_ids or cat in shown_cats:
        continue
    picks_b.append(r); shown_ids.add(pid); shown_cats.add(cat)

display(Markdown("### Enrichment: both arms answer, but the harness grounds the reply" + NL + NL +
                 "Showing **" + str(len(picks_b)) + "** more rows -- here the harness does not refuse; it adds ILO "
                 "indicators, fee-mechanics vocabulary, and concrete reporting pathways the bare model leaves out. "
                 "Together with the block above, that is **" + str(len(picks) + len(picks_b)) +
                 "** full prompt/baseline/harness triples, verbatim."))
for i, r in enumerate(picks_b, len(picks) + 1):
    _emit(r, i, "(enrichment)")'''


# --------------------------------------------------------------------------- #
# Section 3 -- length & coverage
# --------------------------------------------------------------------------- #
S3A_CODE = r'''stat_cards([
    (format(int(_med("baseline", "words")), ","), "median words / baseline", INK3),
    (format(int(_med("harness_core", "words")), ","), "median words / harness_core", TEAL),
    (format(int(_med("harness_full", "words")), ","), "median words / harness_full", GOOD),
    ("+" + str(int(_med("harness_core", "words") - _med("baseline", "words"))), "median word gain (core)", EMBER),
])

fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.8, 4.9))
violins(axL, [(a.replace("harness_", "h_"), feat.loc[feat.arm == a, "words"], ARM_COLORS[a]) for a in ARMS],
        ylabel="words per response")
_title(axL, "Response length by arm", "violin = full distribution; dot = median")
ecdf(axR, [(a.replace("harness_", "h_"), feat.loc[feat.arm == a, "words"], ARM_COLORS[a]) for a in ARMS],
     xlabel="words per response")
_title(axR, "Same, as a cumulative curve", "share of responses at or below a given length")
fig.tight_layout(); save(fig, "nlp_length_arm"); plt.show()

display(Markdown(
    "The harnessed arms shift the whole distribution to the right: the median `harness_core` answer runs **" +
    format(int(_med("harness_core", "words")), ",") + "** words vs **" + format(int(_med("baseline", "words")), ",") +
    "** for the bare model. The cumulative curve makes the gap legible at every percentile, not just the median -- "
    "the harness rarely emits a very short answer unless it is deliberately refusing (compare section 2)."
))'''

S3B_CODE = r'''top_cats = df.category.value_counts().head(10).index.tolist()
data = [feat[(feat.arm == "harness_core") & (feat.category == c)]["words"].values for c in top_cats]
order = np.argsort([np.median(d) if len(d) else 0 for d in data])
top_cats = [top_cats[i] for i in order]; data = [data[i] for i in order]

fig, ax = plt.subplots(figsize=(10.4, 6.2))
bp = ax.boxplot(data, vert=False, patch_artist=True, widths=0.62,
                medianprops=dict(color=INK, linewidth=1.8),
                flierprops=dict(marker="o", markersize=3, markerfacecolor=INK4, markeredgecolor="none", alpha=0.5))
for patch in bp["boxes"]:
    patch.set_facecolor(TEAL_SOFT); patch.set_edgecolor(TEAL_DK); patch.set_linewidth(1.2)
for part in ("whiskers", "caps"):
    for line in bp[part]:
        line.set_color(TEAL_DK)
ax.set_yticks(range(1, len(top_cats) + 1)); ax.set_yticklabels([c.replace("_", " ") for c in top_cats], fontsize=9.5)
ax.set_xlabel("words per harness_core response"); ax.grid(axis="y", visible=False)
_title(ax, "Harness_core response length by category (10 largest categories)",
       "boxes = interquartile range; line = median; dots = outliers")
fig.tight_layout(); save(fig, "nlp_length_category"); plt.show()

med = feat.groupby(["category", "arm"])["words"].median().unstack()
med = med.dropna(subset=["baseline", "harness_core"]).assign(delta=lambda d: d["harness_core"] - d["baseline"])
sel = med.sort_values("delta", ascending=False).head(8).iloc[::-1]
dumbbell([c.replace("_", " ") for c in sel.index], sel["baseline"].tolist(), sel["harness_core"].tolist(),
         lo_lab="baseline", hi_lab="harness_core",
         title="Where the harness expands the answer most -- median words by category",
         xlabel="median words per response")

display(Markdown(
    "Length is not uniform. Some categories draw much longer harnessed answers -- the harness has concrete indicators, "
    "fee mechanics, and reporting steps to enumerate -- while benign queries and jailbreak framings see little change, "
    "or a *shorter* answer when the harness refuses instead of elaborating. Expansion is a means (more grounding), "
    "not the goal."
))'''


# --------------------------------------------------------------------------- #
# Section 4 -- response structure
# --------------------------------------------------------------------------- #
S4A_CODE = r'''stat_cards([
    (str(int(round(_med("baseline", "sentences")))), "median sentences / baseline", INK3),
    (str(int(round(_med("harness_core", "sentences")))), "median sentences / harness_core", TEAL),
    (str(round(_med("baseline", "sent_len"), 1)), "median sentence length / baseline", INK3),
    (str(round(_med("harness_core", "sent_len"), 1)), "median sentence length / harness_core", TEAL),
])

fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.8, 4.9))
violins(axL, [(a.replace("harness_", "h_"), feat.loc[feat.arm == a, "sentences"], ARM_COLORS[a]) for a in ARMS],
        ylabel="sentences per response")
_title(axL, "Sentences per response", "how many sentences the arm writes")
for name, col in [("baseline", INK3), ("harness_core", TEAL)]:
    vals = feat.loc[feat.arm == name, "sent_len"].to_numpy(dtype=float); vals = vals[np.isfinite(vals)]
    axR.hist(vals, bins=40, density=True, color=col, alpha=0.18, edgecolor="none")
    try:
        from scipy.stats import gaussian_kde
        xs = np.linspace(0, 45, 200)
        axR.plot(xs, gaussian_kde(vals)(xs), color=col, lw=2.6, label=name + " (mean " + format(vals.mean(), ".1f") + ")")
    except Exception:
        axR.hist(vals, bins=40, density=True, histtype="step", lw=2.6, color=col, label=name)
axR.set_xlim(0, 45); axR.set_xlabel("words per sentence"); axR.set_ylabel("density"); axR.legend()
_title(axR, "Sentence length", "words per sentence; a proxy for clause density")
fig.tight_layout(); save(fig, "nlp_structure_sent"); plt.show()

_nb, _nc = _med("baseline", "sentences"), _med("harness_core", "sentences")
_sb, _sc = _med("baseline", "sent_len"), _med("harness_core", "sent_len")
display(Markdown(
    "The harness writes about **" + str(int(round(_nc))) + "** sentences to the bare model's **" + str(int(round(_nb))) +
    "**, and its sentences run a touch **" + ("longer" if _sc >= _sb else "shorter") + "** (" + format(_sc, ".1f") +
    " vs " + format(_sb, ".1f") + " words). Clause-dense, citation-bearing sentences read like a compliance memo -- "
    "which is also why the harness's Flesch reading-ease (section 9) sits a little lower."
))'''

S4B_CODE = r'''STRUCT = [("bullets", "bullet points"), ("numbered", "numbered items"),
          ("headers", "section headers"), ("paragraphs", "paragraph blocks")]
labels = [lab for _, lab in STRUCT]
base = [feat.loc[feat.arm == "baseline", k].mean() for k, _ in STRUCT]
core = [feat.loc[feat.arm == "harness_core", k].mean() for k, _ in STRUCT]
full = [feat.loc[feat.arm == "harness_full", k].mean() for k, _ in STRUCT]

y = np.arange(len(labels)); h = 0.26
fig, ax = plt.subplots(figsize=(10.4, 5.2))
ax.barh(y + h, base, height=h, color=INK3, label="baseline", edgecolor=INK2, linewidth=0.4)
ax.barh(y, core, height=h, color=TEAL, label="harness_core", edgecolor=INK2, linewidth=0.4)
ax.barh(y - h, full, height=h, color=GOOD, label="harness_full", edgecolor=INK2, linewidth=0.4)
for yi, (bv, cv, fv) in enumerate(zip(base, core, full)):
    for off, val, col in [(h, bv, INK3), (0, cv, TEAL_DK), (-h, fv, GOOD)]:
        ax.text(val + 0.05, yi + off, format(val, ".1f"), va="center", fontsize=8.5, color=col)
ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_xlabel("mean count per response")
ax.grid(axis="y", visible=False); ax.legend(loc="lower right"); ax.invert_yaxis()
_title(ax, "Structural elements per response, by arm", "bullets, numbered steps, section headers, and paragraph blocks")
fig.tight_layout(); save(fig, "nlp_structure_mix"); plt.show()

tbl = pd.DataFrame({"element": labels,
                    "baseline": [round(x, 2) for x in base],
                    "harness_core": [round(x, 2) for x in core],
                    "harness_full": [round(x, 2) for x in full],
                    "core vs base": [round(c - b, 2) for b, c in zip(base, core)]})
display(pretty_table(tbl, caption="Mean structural elements per response (regex-detected)", bars=["harness_core"]))

display(Markdown(
    "The harness answer is markedly more **scaffolded**: more bullets, more section headers, more discrete paragraph "
    "blocks. That is not decoration -- structure is how a worker or caseworker skims to the step that applies to them."
))'''


# --------------------------------------------------------------------------- #
# Section 5 -- distinctive vocabulary (unigrams)
# --------------------------------------------------------------------------- #
S5_CODE = r'''base_txt = feat.loc[feat.arm == "baseline", "text"].tolist()
core_txt = feat.loc[feat.arm == "harness_core", "text"].tolist()
a_top, b_top = distinctive_terms(core_txt, base_txt, n=16)

fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.8, 6.8))
def _draw(ax, items, color, title):
    items = items[::-1]
    y = list(range(len(items)))
    ax.barh(y, [s for _, s, _, _ in items], color=color, edgecolor=INK2, linewidth=0.4)
    ax.set_yticks(y); ax.set_yticklabels([t for t, _, _, _ in items])
    ax.set_xlabel("weighted log-odds z-score"); ax.grid(axis="y", visible=False); _title(ax, title)
_draw(axL, a_top, TEAL, "More distinctive of harness_core")
_draw(axR, b_top, INK3, "More distinctive of baseline")
fig.suptitle("Distinctive single words -- weighted log-odds z, harness_core vs baseline", fontsize=13.5, fontweight="bold")
fig.tight_layout(); save(fig, "nlp_unigrams"); plt.show()

KEY = ["ilo", "indicator", "recruitment", "passport", "hotline", "rights", "wages", "contract", "debt", "report", "embassy", "coercion"]
mat = []
for term in KEY:
    pat = re.compile(r"\b" + term + r"\b", re.I)
    mat.append([float(np.mean([len(pat.findall(x)) for x in feat.loc[feat.arm == a, "text"]])) for a in ARMS])
heatmap(mat, KEY, [a.replace("harness_", "h_") for a in ARMS],
        title="Key safety terms -- mean occurrences per response",
        subtitle="how often each term appears in a typical response, per arm",
        cmap="BuGn", fmt=".2f", cbar_label="mean / response")

_hi = ", ".join(t for t, _, _, _ in a_top[:8])
display(Markdown("The single words most distinctive of the harness are: **" + _hi + "** -- the working vocabulary of "
                 "ILO indicators, recruitment-fee mechanics, document control, and reporting pathways, largely absent "
                 "from the bare model's more generic phrasing. The heatmap shows the same story per key term, per arm."))'''


# --------------------------------------------------------------------------- #
# Section 6 -- distinctive bigrams & trigrams
# --------------------------------------------------------------------------- #
S6_CODE = r'''bi_a, bi_b = distinctive_ngrams(core_txt, base_txt, ngram=(2, 2), n=12, min_total=4)
tri_a, tri_b = distinctive_ngrams(core_txt, base_txt, ngram=(3, 3), n=12, min_total=3)

fig, axes = plt.subplots(2, 2, figsize=(13.2, 10.6))
def _draw2(ax, items, color, title):
    items = [it for it in items if it][::-1]
    if not items:
        ax.axis("off"); ax.set_title(title + " (too sparse)", fontsize=10); return
    y = list(range(len(items)))
    ax.barh(y, [s for _, s, _, _ in items], color=color, edgecolor=INK2, linewidth=0.4)
    ax.set_yticks(y); ax.set_yticklabels([t for t, _, _, _ in items], fontsize=9)
    ax.set_xlabel("weighted log-odds z"); ax.grid(axis="y", visible=False); _title(ax, title)
_draw2(axes[0][0], bi_a, TEAL, "Bigrams -- distinctive of harness_core")
_draw2(axes[0][1], bi_b, INK3, "Bigrams -- distinctive of baseline")
_draw2(axes[1][0], tri_a, TEAL_DK, "Trigrams -- distinctive of harness_core")
_draw2(axes[1][1], tri_b, INK4, "Trigrams -- distinctive of baseline")
fig.suptitle("Distinctive multi-word phrases -- harness_core vs baseline", fontsize=14, fontweight="bold")
fig.tight_layout(); save(fig, "nlp_ngrams"); plt.show()

_bg = ", ".join('"' + t + '"' for t, _, _, _ in bi_a[:5])
_tg = ", ".join('"' + t + '"' for t, _, _, _ in tri_a[:4])
display(Markdown("Phrases sharpen the picture. The harness's distinctive **bigrams** include " + _bg + "; its "
                 "**trigrams** include " + _tg + ". These are recruitment-integrity and reporting collocations -- "
                 "the harness does not just reach for safety *words*, it reaches for safety *phrases*."))'''


# --------------------------------------------------------------------------- #
# Section 7 -- per-category vocabulary shift (small multiples)
# --------------------------------------------------------------------------- #
S7_CODE = r'''focus = df.category.value_counts().head(6).index.tolist()
fig, axes = plt.subplots(2, 3, figsize=(14.0, 8.6))
for ax, cat in zip(axes.ravel(), focus):
    ct = feat[(feat.arm == "harness_core") & (feat.category == cat)]["text"].tolist()
    bt = feat[(feat.arm == "baseline") & (feat.category == cat)]["text"].tolist()
    a_c, _ = distinctive_terms(ct, bt, n=8, min_total=2)
    a_c = [it for it in a_c if it][::-1]
    if not a_c:
        ax.axis("off"); ax.set_title(cat.replace("_", " ") + " (sparse)", fontsize=10.5, fontweight="bold"); continue
    y = list(range(len(a_c)))
    ax.barh(y, [s for _, s, _, _ in a_c], color=TEAL, edgecolor=INK2, linewidth=0.3)
    ax.set_yticks(y); ax.set_yticklabels([t for t, _, _, _ in a_c], fontsize=8.5)
    ax.set_title(cat.replace("_", " "), fontsize=10.5, fontweight="bold")
    ax.tick_params(labelsize=8); ax.grid(axis="y", visible=False)
fig.suptitle("Per-category harness vocabulary -- the words the harness adds, by prompt category",
             fontsize=13.5, fontweight="bold")
fig.text(0.5, 0.005, "weighted log-odds z of harness_core vs baseline, computed within each category",
         ha="center", fontsize=9.5, color=INK3)
fig.tight_layout(rect=[0, 0.02, 1, 1]); save(fig, "nlp_category_vocab"); plt.show()

display(Markdown("The harness does not staple the *same* disclaimer to every answer -- it adapts. Fee-mechanics "
                 "categories pull in the vocabulary of fees, deductions, and salary; document-control categories pull "
                 "in passport, retention, confiscation; rights categories pull in entitlements and conventions. The "
                 "safety layer is context-sensitive, which is the whole point of the GREP + retrieval design."))'''


# --------------------------------------------------------------------------- #
# Section 8 -- sentiment (deepened)
# --------------------------------------------------------------------------- #
S8A_CODE = r'''fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.8, 4.9))
violins(axL, [(a.replace("harness_", "h_"), feat.loc[feat.arm == a, "sentiment"] * 100, ARM_COLORS[a]) for a in ARMS],
        ylabel="sentiment (compound x100)")
axL.axhline(0, color=INK4, lw=1, ls="--")
_title(axL, "Sentiment by arm (backend: " + SENT_BACKEND + ")", "tone proxy, not correctness")

order = [d for d in ["easy", "medium", "hard"] if d in set(feat.difficulty)] or sorted(set(feat.difficulty))
left = [feat[(feat.arm == "baseline") & (feat.difficulty == d)]["sentiment"].mean() * 100 for d in order]
right = [feat[(feat.arm == "harness_core") & (feat.difficulty == d)]["sentiment"].mean() * 100 for d in order]
for d, a, b in zip(order, left, right):
    axR.plot([0, 1], [a, b], color=TEAL, lw=2.4, marker="o", markersize=8, markerfacecolor=PAPER,
             markeredgecolor=TEAL, markeredgewidth=2)
    axR.text(-0.03, a, d + "  " + format(a, ".0f"), ha="right", va="center", fontsize=9.5, color=INK2)
    axR.text(1.03, b, format(b, ".0f"), ha="left", va="center", fontsize=10, color=EMBER, fontweight="bold")
axR.set_xlim(-0.6, 1.6); axR.set_xticks([0, 1]); axR.set_xticklabels(["baseline", "harness_core"], fontweight="bold")
axR.set_ylabel("mean sentiment (x100)"); axR.grid(axis="x", alpha=0)
_title(axR, "Mean sentiment shift by difficulty", "baseline -> harness_core")
fig.tight_layout(); save(fig, "nlp_sentiment_arm"); plt.show()

_mb = feat.loc[feat.arm == "baseline", "sentiment"].mean()
_mc = feat.loc[feat.arm == "harness_core", "sentiment"].mean()
display(Markdown("Mean compound sentiment is **" + str(round(_mc, 3)) + "** for harness_core vs **" + str(round(_mb, 3)) +
                 "** for baseline. Read this as *register*, not correctness: both arms discuss the same grim subject. The "
                 "harness leans measured and procedure-first -- name the indicator, state the obligation, give a safe next step."))'''

S8B_CODE = r'''fig, ax = plt.subplots(figsize=(9.8, 5.6))
for a in ["baseline", "harness_core"]:
    sub = feat[feat.arm == a]
    ax.scatter(sub["words"], sub["sentiment"] * 100, s=15, color=ARM_COLORS[a], alpha=0.28, edgecolor="none", label=a)
    ax.scatter([sub["words"].mean()], [sub["sentiment"].mean() * 100], s=190, color=ARM_COLORS[a],
               edgecolor=INK, linewidth=1.6, zorder=5, marker="D")
ax.axhline(0, color=INK4, lw=1, ls="--")
ax.set_xlabel("words per response"); ax.set_ylabel("sentiment (compound x100)")
ax.legend(loc="upper right")
_title(ax, "Sentiment vs response length", "each dot is one response; diamonds mark the arm mean")
fig.tight_layout(); save(fig, "nlp_sentiment_scatter"); plt.show()

display(Markdown("There is no strong length->tone coupling: longer answers are not systematically warmer or colder. The "
                 "harness cloud sits further right (longer) and, if anything, a shade lower in tone -- consistent with a "
                 "formal compliance register rather than reassurance."))'''


# --------------------------------------------------------------------------- #
# Section 9 -- readability
# --------------------------------------------------------------------------- #
S9A_CODE = r'''stat_cards([(str(round(_med("baseline", "flesch"), 1)), "median Flesch / baseline", INK3),
            (str(round(_med("harness_core", "flesch"), 1)), "median Flesch / harness_core", TEAL),
            (str(round(_med("harness_full", "flesch"), 1)), "median Flesch / harness_full", GOOD)])

fig, ax = plt.subplots(figsize=(10.4, 5.0))
violins(ax, [(a.replace("harness_", "h_"), feat.loc[feat.arm == a, "flesch"], ARM_COLORS[a]) for a in ARMS],
        ylabel="Flesch reading-ease")
for yv, lab in [(30, "dense / professional"), (60, "plain English")]:
    ax.axhline(yv, color=INK4, lw=1, ls="--"); ax.text(0.62, yv + 0.8, lab, fontsize=8.5, color=INK3)
_title(ax, "Readability by arm (backend: " + READ_BACKEND + ")", "Flesch reading-ease; higher = easier to read")
fig.tight_layout(); save(fig, "nlp_readability_arm"); plt.show()

_fb, _fc = _med("baseline", "flesch"), _med("harness_core", "flesch")
display(Markdown(
    "Both arms land in the dense, professional band. The harness median Flesch is **" + format(_fc, ".1f") + "** vs **" +
    format(_fb, ".1f") + "** for the bare model" + (" -- a little harder to read" if _fc < _fb else "") + ": the cost of "
    "naming conventions, statutes, and obligations explicitly. It reads like a compliance memo, the intended register "
    "for an NGO / regulator audience rather than a casual chat."
))'''

S9B_CODE = r'''fig, ax = plt.subplots(figsize=(9.8, 5.6))
for a in ["baseline", "harness_core"]:
    sub = feat[feat.arm == a]
    ax.scatter(sub["sent_len"], sub["flesch"], s=15, color=ARM_COLORS[a], alpha=0.26, edgecolor="none", label=a)
ax.set_xlim(0, 45); ax.set_xlabel("mean sentence length (words)"); ax.set_ylabel("Flesch reading-ease")
ax.legend(loc="upper right")
_title(ax, "Readability vs sentence length", "the negative slope is the Flesch formula at work")
fig.tight_layout(); save(fig, "nlp_readability_scatter"); plt.show()

display(Markdown("Readability is driven mechanically by sentence length: the downward cloud is the Flesch reading-ease "
                 "formula responding to longer sentences. The harness's slightly longer, clause-dense sentences are "
                 "exactly why its reading-ease sits a little lower -- a predictable, honest consequence, not a defect."))'''


# --------------------------------------------------------------------------- #
# Section 10 -- safety-vocabulary detection
# --------------------------------------------------------------------------- #
S10A_CODE = r'''labels = [lab for _, _, lab in SAFE_PATTERNS]
base = [feat.loc[feat.arm == "baseline", k].mean() * 100 for k, _, _ in SAFE_PATTERNS]
core = [feat.loc[feat.arm == "harness_core", k].mean() * 100 for k, _, _ in SAFE_PATTERNS]
full = [feat.loc[feat.arm == "harness_full", k].mean() * 100 for k, _, _ in SAFE_PATTERNS]

y = np.arange(len(labels)); h = 0.26
fig, ax = plt.subplots(figsize=(10.8, 5.6))
ax.barh(y + h, base, height=h, color=INK3, label="baseline", edgecolor=INK2, linewidth=0.4)
ax.barh(y, core, height=h, color=TEAL, label="harness_core", edgecolor=INK2, linewidth=0.4)
ax.barh(y - h, full, height=h, color=GOOD, label="harness_full", edgecolor=INK2, linewidth=0.4)
for yi, (bv, cv, fv) in enumerate(zip(base, core, full)):
    for off, val, col in [(h, bv, INK3), (0, cv, TEAL_DK), (-h, fv, GOOD)]:
        ax.text(val + 0.6, yi + off, format(val, ".0f") + "%", va="center", fontsize=8.3, color=col)
ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_xlabel("percent of responses containing the pattern")
ax.set_xlim(0, max(max(base), max(core), max(full)) * 1.16 + 5)
ax.grid(axis="y", visible=False); ax.legend(loc="lower right"); ax.invert_yaxis()
_title(ax, "Safety-vocabulary detection rate, per arm", "share of responses that use each kind of safety language")
fig.tight_layout(); save(fig, "nlp_safety_rate"); plt.show()

tbl = pd.DataFrame({"pattern": labels,
                    "baseline %": [round(x, 1) for x in base],
                    "harness_core %": [round(x, 1) for x in core],
                    "harness_full %": [round(x, 1) for x in full],
                    "core vs base (pts)": [round(c - b, 1) for b, c in zip(base, core)]})
display(pretty_table(tbl, caption="Share of responses containing each safety-vocabulary pattern (regex, per response)",
                     bars=["harness_core %"]))'''

S10B_CODE = r'''occ_base, occ_core, occ_labels = [], [], []
for k, pat, lab in SAFE_PATTERNS:
    occ_base.append(float(np.mean([len(pat.findall(x)) for x in feat.loc[feat.arm == "baseline", "text"]])))
    occ_core.append(float(np.mean([len(pat.findall(x)) for x in feat.loc[feat.arm == "harness_core", "text"]])))
    occ_labels.append(lab)
order = np.argsort([c - b for b, c in zip(occ_base, occ_core)])
occ_labels = [occ_labels[i] for i in order]; ob = [occ_base[i] for i in order]; oc = [occ_core[i] for i in order]
dumbbell(occ_labels, ob, oc, lo_lab="baseline", hi_lab="harness_core",
         title="Safety language -- mean occurrences per response (not just presence)",
         xlabel="mean matches per response")

display(Markdown("Presence understates the shift. Counting *how often* each pattern fires per response, the harness does "
                 "not merely mention an indicator once -- it enumerates several, cites more than one authority, and points "
                 "to multiple reporting channels. The per-response intensity is where the harness's grounding really shows."))'''


# --------------------------------------------------------------------------- #
# Section 11 -- lexical diversity & register
# --------------------------------------------------------------------------- #
S11_CODE = r'''def _rate(arm, col):
    sub = feat[feat.arm == arm]
    return float(sub[col].sum() / max(sub["words"].sum(), 1) * 1000.0)

stat_cards([
    (str(round(feat.loc[feat.arm == "baseline", "mattr"].mean(), 3)), "MATTR / baseline", INK3),
    (str(round(feat.loc[feat.arm == "harness_core", "mattr"].mean(), 3)), "MATTR / harness_core", TEAL),
    (str(round(_rate("harness_core", "hedges"), 1)), "hedges / 1k words (core)", WARN),
    (str(round(_rate("harness_core", "directives"), 1)), "directives / 1k words (core)", EMBER),
])

fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.8, 4.9))
violins(axL, [(a.replace("harness_", "h_"), feat.loc[feat.arm == a, "mattr"], ARM_COLORS[a]) for a in ARMS],
        ylabel="MATTR (moving-average type-token ratio)", annotate=False)
_title(axL, "Lexical diversity by arm", "higher = more varied vocabulary; length-controlled (window 50)")

grp = ["baseline", "harness_core", "harness_full"]
hedge = [_rate(a, "hedges") for a in grp]; direct = [_rate(a, "directives") for a in grp]
x = np.arange(len(grp)); w = 0.36
axR.bar(x - w / 2, hedge, width=w, color=WARN, label="hedging (may / might / typically)", edgecolor=INK2, linewidth=0.4)
axR.bar(x + w / 2, direct, width=w, color=EMBER, label="directive (report / verify / never)", edgecolor=INK2, linewidth=0.4)
for xi, (hv, dv) in enumerate(zip(hedge, direct)):
    axR.text(xi - w / 2, hv + 0.15, format(hv, ".1f"), ha="center", va="bottom", fontsize=8.3, color=INK2)
    axR.text(xi + w / 2, dv + 0.15, format(dv, ".1f"), ha="center", va="bottom", fontsize=8.3, color=INK2)
axR.set_xticks(x); axR.set_xticklabels([a.replace("harness_", "h_") for a in grp])
axR.set_ylabel("matches per 1,000 words"); axR.grid(axis="x", visible=False); axR.legend(fontsize=8.5)
_title(axR, "Hedging vs directive language", "does the arm equivocate, or commit to a next step?")
fig.tight_layout(); save(fig, "nlp_lexical"); plt.show()

_dh = _rate("harness_core", "directives") - _rate("baseline", "directives")
_hh = _rate("harness_core", "hedges") - _rate("baseline", "hedges")
_mb = feat.loc[feat.arm == "baseline", "mattr"].mean()
_mc = feat.loc[feat.arm == "harness_core", "mattr"].mean()
display(Markdown(
    "Per 1,000 words the harness uses **" + format(abs(_dh), ".1f") + "** " + ("more" if _dh >= 0 else "fewer") +
    " directive tokens (report / verify / contact / never) and **" + format(abs(_hh), ".1f") + "** " +
    ("more" if _hh >= 0 else "fewer") + " hedges (may / might / typically) than the bare model. Length-controlled "
    "lexical diversity (MATTR) is **" + format(_mc, ".3f") + "** vs **" + format(_mb, ".3f") + "** -- comparable -- so "
    "the harness adds *specific* safety vocabulary rather than merely *more* words."
))'''


# --------------------------------------------------------------------------- #
# Section 12 -- word clouds
# --------------------------------------------------------------------------- #
S12A_CODE = r'''try:
    from wordcloud import WordCloud
    HAS_WC = True
except Exception:
    HAS_WC = False

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.8, 5.6))
for ax, arm, cmap, col in [(a1, "baseline", "Greys", INK3), (a2, "harness_core", "BuGn", TEAL)]:
    freqs = top_frequencies(feat.loc[feat.arm == arm, "text"].tolist(), 150)
    ax.set_title(arm + " -- top vocabulary", fontsize=12, fontweight="bold")
    if HAS_WC and freqs:
        wc = WordCloud(width=780, height=470, background_color=PAPER, colormap=cmap,
                       prefer_horizontal=0.95, max_words=140).generate_from_frequencies(freqs)
        ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
    else:
        top = list(freqs.items())[:22][::-1]
        yy = list(range(len(top)))
        ax.barh(yy, [v for _, v in top], color=col, edgecolor=INK2, linewidth=0.4)
        ax.set_yticks(yy); ax.set_yticklabels([w for w, _ in top], fontsize=8.5)
        ax.set_xlabel("count"); ax.grid(axis="y", visible=False)
_mode = "word clouds" if HAS_WC else "top-term bars (wordcloud not installed -- offline fallback)"
fig.suptitle("Most frequent vocabulary -- baseline vs harness_core  [" + _mode + "]", fontsize=13.5, fontweight="bold")
fig.tight_layout(); save(fig, "nlp_wordclouds"); plt.show()
display(Markdown("Rendered as **" + _mode + "**. The baseline cloud is dominated by generic explanatory words; the harness "
                 "cloud pulls in the domain's working vocabulary -- recruitment, passport, employer, fees, indicators, and "
                 "reporting channels."))'''

S12B_CODE = r'''want = ["rights_query", "free_visa_backloaded_debt", "benevolent_framing"]
avail = [c for c in want if c in set(df.category)]
if len(avail) < 3:
    avail = df.category.value_counts().head(3).index.tolist()

fig, axes = plt.subplots(1, len(avail), figsize=(4.5 * len(avail), 5.0))
axes = np.ravel(axes)
for ax, cat in zip(axes, avail):
    freqs = top_frequencies(feat.loc[(feat.arm == "harness_core") & (feat.category == cat), "text"].tolist(), 90)
    ax.set_title(cat.replace("_", " "), fontsize=11.5, fontweight="bold")
    if HAS_WC and freqs:
        wc = WordCloud(width=560, height=460, background_color=PAPER, colormap="BuGn",
                       prefer_horizontal=0.95, max_words=90).generate_from_frequencies(freqs)
        ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
    else:
        top = list(freqs.items())[:16][::-1]
        yy = list(range(len(top)))
        ax.barh(yy, [v for _, v in top], color=TEAL, edgecolor=INK2, linewidth=0.3)
        ax.set_yticks(yy); ax.set_yticklabels([w for w, _ in top], fontsize=8)
        ax.set_xlabel("count"); ax.grid(axis="y", visible=False)
fig.suptitle("Harness_core vocabulary by category  [" + _mode + "]", fontsize=13, fontweight="bold")
fig.tight_layout(); save(fig, "nlp_wordclouds_category"); plt.show()
display(Markdown("The harness speaks each category's dialect: a rights query pulls in entitlements and conventions; a "
                 "free-visa / backloaded-debt prompt pulls in fees, deductions, and debt-bondage vocabulary; a "
                 "benevolent-framing jailbreak pulls in refusal and verification language. Same harness, "
                 "category-specific response -- which is what the per-category log-odds in section 7 quantified."))'''


# --------------------------------------------------------------------------- #
# Section 13 -- synthesis
# --------------------------------------------------------------------------- #
S13_CODE = r'''axis_labels = ["length", "structure", "ILO cite", "indicator", "resource", "refusal"]
def _profile(arm):
    sub = feat[feat.arm == arm]
    return [float(sub["words"].median()),
            float((sub["bullets"] + sub["numbered"] + sub["headers"]).mean()),
            float(sub["cite_ilo"].mean() * 100), float(sub["indicator"].mean() * 100),
            float(sub["resource"].mean() * 100), float(sub["refusal"].mean() * 100)]
raw = {a: _profile(a) for a in ARMS}
maxes = [max(raw[a][i] for a in ARMS) or 1.0 for i in range(len(axis_labels))]
radar(axis_labels,
      [(ARM_LABEL[a].split(" (")[0], [raw[a][i] / maxes[i] * 100 for i in range(len(axis_labels))], ARM_COLORS[a]) for a in ARMS],
      title="Six-axis profile per arm (each axis normalized to the strongest arm = 100)",
      subtitle="length + structure + four safety-language rates", rmax=108)

def _col(arm):
    sub = feat[feat.arm == arm]
    return [int(_med(arm, "words")),
            round((sub["bullets"] + sub["numbered"]).mean(), 1),
            round(sub["cite_ilo"].mean() * 100, 1), round(sub["indicator"].mean() * 100, 1),
            round(sub["resource"].mean() * 100, 1), round(sub["refusal"].mean() * 100, 1),
            round(_med(arm, "flesch"), 1)]
summ = pd.DataFrame({"metric": ["median words", "mean list items", "ILO cite %", "indicator %",
                                "resource %", "refusal %", "median Flesch"],
                     "baseline": _col("baseline"), "harness_core": _col("harness_core"),
                     "harness_full": _col("harness_full")})
display(pretty_table(summ, caption="Headline NLP metrics across all three arms (computed live)", bars=["harness_core"]))

deltas = sorted([(lab, feat.loc[feat.arm == "harness_core", k].mean() * 100 - feat.loc[feat.arm == "baseline", k].mean() * 100)
                 for k, _, lab in SAFE_PATTERNS], key=lambda kv: kv[1], reverse=True)
_top = "; ".join(lab + " +" + format(d, ".0f") + " pts" for lab, d in deltas[:3])
display(Markdown("**What the NLP shows.** Wrapping Gemma 4 in the DueCare harness leaves the *subject* unchanged but "
                 "reshapes the *text*: longer, more structured answers that reach for a specific safety vocabulary far "
                 "more often. The three largest jumps in safety-language use, baseline -> harness_core, are **" + _top +
                 "**. None of this is a real-world detection claim -- it is a measured, reproducible description of how "
                 "the harness changes what the model writes."))'''


# --------------------------------------------------------------------------- #
# markdown cells (URLs literal; HTML entities are ASCII source that render as glyphs)
# --------------------------------------------------------------------------- #
HERO_MD = '''<div style="padding:26px 32px;border-radius:16px;background:linear-gradient(120deg,#14181B 0%,#2A2D34 42%,#2f7d8c 100%);color:#F7F6F1">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.82">DueCare &middot; Gemma 4 safety &middot; prompt + response NLP</div>
<h1 style="margin:.28em 0 .2em;font-size:30px;color:#ffffff;font-weight:800">What changes when you wrap Gemma 4 in a safety harness?</h1>
<p style="font-size:15px;line-height:1.6;margin:0;max-width:960px">This notebook reads the <b>raw prompts and raw responses</b> from the <b>DueCare Prompt + Response Showcase</b> &mdash; 1,087 synthetic migrant-worker-safety prompts, each answered by <b>gemma4:31b</b> under three arms: <b>baseline</b> (bare model), <b>harness_core</b> (persona + GREP indicator rules + retrieval + tools), and <b>harness_full</b> (+ online). We first show the data <b>row by row, verbatim</b>, then run a comprehensive classic-NLP pass over it &mdash; corpus composition, length &amp; coverage, response structure, distinctive vocabulary (single words <b>and</b> bigrams / trigrams), per-category vocabulary shift, sentiment, readability, safety-term detection, lexical register, and word clouds &mdash; entirely on CPU, with no model, no GPU, and no internet. Every chart is computed live from the attached file.</p>
</div>'''

TOC_MD = '''## What is in this notebook

Every number and chart below is computed **live from the attached dataset** &mdash; nothing is hard-coded. Thirteen sections take the same 1,087 prompts through a full classic-NLP pass, always contrasting the **bare model** against the **harnessed model** on the identical prompt.

- [1. Corpus at a glance &mdash; categories, corridors, difficulty](#corpus)
- [2. Raw, row by row &mdash; prompts + responses, verbatim](#raw)
- [3. Length &amp; coverage &mdash; how big, and where](#length)
- [4. Response structure &mdash; sentences, bullets, headers, paragraphs](#structure)
- [5. Distinctive vocabulary &mdash; single words the harness adds](#vocab)
- [6. Distinctive phrases &mdash; bigrams &amp; trigrams](#ngrams)
- [7. Per-category vocabulary shift &mdash; the harness adapts](#category)
- [8. Sentiment &mdash; tone by arm, deepened](#sentiment)
- [9. Readability &mdash; Flesch reading-ease by arm](#readability)
- [10. Safety-vocabulary detection &mdash; citations, refusals, resources, indicators](#safety)
- [11. Lexical register &mdash; diversity, hedging, directives](#lexical)
- [12. Word clouds &mdash; overall and per category](#clouds)
- [13. Synthesis &mdash; what the NLP shows](#synthesis)
- [14. Honest boundary &amp; license](#boundary)

**Honest boundary (read first).** These prompts are **synthetic / composite** &mdash; no real person, case, contact, or document appears, and the set is PII-clean. The responses are **model outputs**, shown as **illustrative / silver** material, not gold human labels or legal advice. This is an exploratory NLP view of *how the harness changes the text*, not a real-world detection claim. License **CC0**.

**Dataset:** [`taylorsamarel/duecare-prompt-response-showcase`](https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase) &middot; **Start-here index:** [`duecare-harness-lift-benchmark`](https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here) &middot; **Repo:** [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''

S1_MD = '''<a id="corpus"></a>
## 1. Corpus at a glance &mdash; categories, corridors, difficulty

Before the raw text, a quick orientation to what the showcase actually contains. The KPI tiles give the totals; the bar chart shows the largest of the 73 prompt categories; the two-panel view breaks the set down by difficulty band and by named migration corridor. This is the population every later chart is computed over.'''

S2_MD = '''<a id="raw"></a>
## 2. Raw, row by row &mdash; prompts + responses, verbatim

The centerpiece: real rows shown **end to end, nothing truncated**. Each block is the raw `prompt_text`, then the full `baseline_response` (bare Gemma 4), then the full `harness_core_response` (the same model wrapped in persona + GREP indicator rules + retrieval + tools). The selector deliberately surfaces **contrast**, and spreads picks across different categories: first a **divergence** block (the bare model engages a loaded request, the harness refuses and redirects), then an **enrichment** block (both answer, but the harness grounds the reply in ILO indicators, fee mechanics, and reporting pathways).'''

S3_MD = '''<a id="length"></a>
## 3. Length &amp; coverage &mdash; how big, and where

The first thing NLP notices is shape. The violin and cumulative curve compare the full word-count distribution per arm; the KPI tiles compare medians. Then we drop to the category level: a box plot of harness_core length across the ten largest categories, and a dumbbell showing exactly where the harness expands the answer most.'''

S4_MD = '''<a id="structure"></a>
## 4. Response structure &mdash; sentences, bullets, headers, paragraphs

Length is not the same as organization. Here we count the *scaffolding*: sentences per response and mean sentence length (a clause-density proxy), then the mean number of bullet points, numbered steps, section headers, and paragraph blocks per arm. Structure is how a worker or caseworker skims to the step that applies to them.'''

S5_MD = '''<a id="vocab"></a>
## 5. Distinctive vocabulary &mdash; single words the harness adds

This is the strongest signal in the corpus. Using the **weighted log-odds-ratio z-score** with an uninformative Dirichlet prior (Monroe, Colaresi &amp; Quinn 2008, "Fightin' Words") &mdash; which balances how *lopsided* a word is against how *often* it occurs, so frequent discriminators outrank one-off rarities &mdash; we rank the words most over-represented in `harness_core` versus `baseline`, and vice-versa. Teal bars are the harness's distinctive vocabulary; grey bars are the bare model's. The heatmap then tracks a dozen key safety terms across all three arms.'''

S6_MD = '''<a id="ngrams"></a>
## 6. Distinctive phrases &mdash; bigrams &amp; trigrams

Single words only go so far. The same weighted log-odds ranking, applied to **two- and three-word phrases** (scikit-learn `CountVectorizer` with `ngram_range`, pure-python fallback offline), shows the *collocations* each arm reaches for. This is where "safety words" become "safety phrases" &mdash; recruitment-integrity and reporting expressions rather than isolated keywords.'''

S7_MD = '''<a id="category"></a>
## 7. Per-category vocabulary shift &mdash; the harness adapts

Does the harness bolt on the same disclaimer everywhere, or does it adapt to the prompt? For each of the six largest categories we compute the harness-distinctive vocabulary *within that category* and plot it as small multiples. If the added words differ by category, the safety layer is context-sensitive &mdash; which is exactly what the GREP + retrieval design is meant to achieve.'''

S8_MD = '''<a id="sentiment"></a>
## 8. Sentiment &mdash; tone by arm, deepened

Sentiment here is a proxy for **tone**, not correctness &mdash; every response discusses the same difficult subject. We score each response's compound polarity (VADER when present, TextBlob or a bundled lexicon as offline fallbacks), compare the full distributions by arm (violin), track the mean shift across difficulty bands, and finally scatter sentiment against response length to check whether longer answers simply read colder.'''

S9_MD = '''<a id="readability"></a>
## 9. Readability &mdash; Flesch reading-ease by arm

Flesch reading-ease scores how hard the text is to read (higher = easier). Legal citations and multi-clause sentences push both arms into the dense, professional band; we compare medians and the full distribution (violin), then show the mechanical link between sentence length and reading-ease. textstat is used when installed, with a self-contained Flesch approximation as the offline fallback.'''

S10_MD = '''<a id="safety"></a>
## 10. Safety-vocabulary detection &mdash; citations, refusals, resources, indicators

Regex detectors flag, per response, whether it cites an **ILO convention**, references a **statute or legal rule**, uses **refusal / redirection** language, points to a **resource or hotline**, or names a forced-labour **indicator**. The grouped bars and table give the *share* of responses in each arm that use each pattern; the dumbbell then goes further, counting *how often* each pattern fires per response &mdash; presence versus intensity.'''

S11_MD = '''<a id="lexical"></a>
## 11. Lexical register &mdash; diversity, hedging, directives

Beyond which words, *how* does each arm write? We measure length-controlled lexical diversity (MATTR &mdash; a moving-average type-token ratio that does not simply fall as text gets longer), then the rate of **hedging** language (may, might, typically) versus **directive** language (report, verify, never) per thousand words. Together these describe the harness's register: does it equivocate, or commit to a concrete next step?'''

S12_MD = '''<a id="clouds"></a>
## 12. Word clouds &mdash; overall and per category

A quick visual of the most frequent vocabulary, stop-words removed: first baseline versus harness_core overall, then harness_core split across a few contrasting categories. When the `wordcloud` package is available the notebook renders true clouds; otherwise it falls back to top-term bars via the shared toolkit, so these cells always produce output offline.'''

S13_MD = '''<a id="synthesis"></a>
## 13. Synthesis &mdash; what the NLP shows

One picture to tie it together: a six-axis radar profiling each arm on length, structure, and four safety-language rates (each axis normalized so the strongest arm reads 100), a headline metrics table across all three arms, and a plain-language summary of the three largest safety-language jumps. Everything on this page is recomputed live from the attached file.'''

BOUNDARY_MD = '''<a id="boundary"></a>
## 14. Honest boundary &amp; license

**What this is.** An exploratory NLP view of how a safety harness changes Gemma 4's text on a fixed prompt set. Everything is computed live from the attached CSV, on CPU, with no model and no internet.

**What this is not.** The prompts are **synthetic / composite** &mdash; no real individual, case, contact, name, number, or address appears, and the set is PII-clean. The responses are **model outputs**, treated as **illustrative / silver** material, not gold human annotations and not legal advice. Sentiment, readability, and lexical-register measures are **tone / style proxies**, not measures of correctness or safety. This notebook makes **no** real-world detection or victim-identification claim.

**Reproducibility.** Every optional NLP package (vaderSentiment, textblob, textstat, wordcloud, scikit-learn) is wrapped in try/except with an offline fallback, so the notebook runs to completion with `enable_internet=false`. The distinctive-vocabulary math is the weighted log-odds-ratio z-score with a Dirichlet prior (Monroe, Colaresi &amp; Quinn 2008), applied identically to unigrams, bigrams, and trigrams; lexical diversity is a length-controlled moving-average type-token ratio.

**License.** CC0.

**Links.** Dataset: [`taylorsamarel/duecare-prompt-response-showcase`](https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase) &middot; Start-here index: [`duecare-harness-lift-benchmark`](https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here) &middot; Source repository: [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''


def _notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        _md(HERO_MD),
        _md(TOC_MD),
        _code(SETUP),
        _md(S1_MD),
        _code(S1A_CODE),
        _code(S1B_CODE),
        _md(S2_MD),
        _code(S2A_CODE),
        _code(S2B_CODE),
        _md(S3_MD),
        _code(S3A_CODE),
        _code(S3B_CODE),
        _md(S4_MD),
        _code(S4A_CODE),
        _code(S4B_CODE),
        _md(S5_MD),
        _code(S5_CODE),
        _md(S6_MD),
        _code(S6_CODE),
        _md(S7_MD),
        _code(S7_CODE),
        _md(S8_MD),
        _code(S8A_CODE),
        _code(S8B_CODE),
        _md(S9_MD),
        _code(S9A_CODE),
        _code(S9B_CODE),
        _md(S10_MD),
        _code(S10A_CODE),
        _code(S10B_CODE),
        _md(S11_MD),
        _code(S11_CODE),
        _md(S12_MD),
        _code(S12A_CODE),
        _code(S12B_CODE),
        _md(S13_MD),
        _code(S13_CODE),
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
    assert TITLE.lower().replace(" ", "-") == "duecare-prompt-and-response-nlp-explorer"
    assert KERNEL_ID == "taylorsamarel/" + SLUG, "kernel id mismatch: " + repr(KERNEL_ID)

    result = build(args.output, force=args.force)
    result["title_slug_ok"] = TITLE.lower().replace(" ", "-") == SLUG
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
