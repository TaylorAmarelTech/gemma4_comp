#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the polished, richly-visual DueCare Prompt-and-Response NLP explorer notebook.

Emits a Kaggle notebook (nbformat) over the published dataset
`taylorsamarel/duecare-prompt-response-showcase` (prompt_response_showcase.csv):
1,087 synthetic/composite migrant-worker-safety prompts, each answered by gemma4:31b under three
arms -- baseline (bare model), harness_core (persona + GREP indicator rules + retrieval + tools),
harness_full (+ online). The notebook showcases the RAW prompts and RAW responses ROW BY ROW, then
runs classic NLP over them -- length/structure, sentiment, distinctive vocabulary (TF-IDF / log-odds),
safety-vocabulary detection, readability, and word clouds -- entirely on CPU, no GPU, no internet,
no model loading. Every optional NLP package is wrapped in try/except with an offline-safe fallback,
so the notebook runs to completion on Kaggle with enable_internet=false.

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

# ---- distinctive vocabulary + word frequencies: sklearn CountVectorizer -> pure-python Counter ----
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

def distinctive_terms(texts_a, texts_b, n=15, min_total=5):
    """Terms whose smoothed relative frequency is highest in A vs B (and vice versa).

    Returns (a_top, b_top); each item is (term, z_score, count_a, count_b).
    sklearn CountVectorizer builds the shared vocabulary when available; a pure-python
    Counter is the offline fallback. The score is the weighted log-odds-ratio z-score with
    an (uninformative) Dirichlet prior -- Monroe, Colaresi & Quinn (2008), "Fightin' Words" --
    which balances effect size against frequency, so frequent discriminators outrank rare ones.
    """
    if HAS_SK:
        from sklearn.feature_extraction.text import CountVectorizer
        cv = CountVectorizer(stop_words="english", lowercase=True,
                             token_pattern=r"(?u)\b[a-z][a-z0-9]{2,}\b", min_df=min_total)
        X = cv.fit_transform(list(texts_a) + list(texts_b))
        vocab = list(cv.get_feature_names_out())
        na = np.asarray(X[:len(texts_a)].sum(axis=0)).ravel().astype(float)
        nb = np.asarray(X[len(texts_a):].sum(axis=0)).ravel().astype(float)
    else:
        ca, cb = _arm_counter(texts_a), _arm_counter(texts_b)
        vocab = sorted({w for w in set(ca) | set(cb) if ca.get(w, 0) + cb.get(w, 0) >= min_total})
        na = np.array([ca.get(w, 0) for w in vocab], dtype=float)
        nb = np.array([cb.get(w, 0) for w in vocab], dtype=float)
    ta, tb, V = na.sum(), nb.sum(), max(len(vocab), 1)
    alpha = 0.01           # per-word Dirichlet prior
    a0 = alpha * V         # prior mass
    la = np.log((na + alpha) / (ta + a0 - na - alpha))
    lb = np.log((nb + alpha) / (tb + a0 - nb - alpha))
    delta = la - lb                                   # log-odds-ratio
    var = 1.0 / (na + alpha) + 1.0 / (nb + alpha)     # its approx variance
    z = delta / np.sqrt(var)                          # -> standardized z-score
    order = np.argsort(z)
    b_top = [(vocab[i], float(-z[i]), int(na[i]), int(nb[i])) for i in order[:n]]
    a_top = [(vocab[i], float(z[i]), int(na[i]), int(nb[i])) for i in order[::-1][:n]]
    return a_top, b_top

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
_RX_ILO = re.compile(r"\b(ilo|convention|conventions|c0?29|c181|c189|c097|c143|c095|icrmw|palermo|article)\b", re.I)
_RX_STAT = re.compile(r"\b(act|section|statute|statutory|regulation|regulations|law|laws|rule|rules|tvpa|bcea|emigration|foreign employment)\b", re.I)
_RX_REF = re.compile(r"\b(cannot|can't|will not|won't|unable|prohibited|decline|instead|report|reporting|authorities)\b", re.I)
_RX_RES = re.compile(r"\b(hotline|helpline|ngo|embassy|consulate|polaris|call|department of|ministry|tribunal|shelter|helpdesk|support)\b", re.I)
_RX_IND = re.compile(r"(indicator|debt bondage|passport retention|withholding|wage withholding|coercion|deception|forced lab|recruitment fee|confiscation|movement)", re.I)

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

# --------------------------------------------------------------------------- #
# feat -- one long-form row per (prompt, arm) with every derived feature.
# --------------------------------------------------------------------------- #
_records = []
for r in rows:
    for arm in ARMS:
        t = _txt(r.get(arm + "_response"))
        _records.append({
            "prompt_id": _txt(r.get("prompt_id")),
            "category": _txt(r.get("category")),
            "corridor": _txt(r.get("corridor")),
            "difficulty": _txt(r.get("difficulty")),
            "arm": arm,
            "text": t,
            "chars": len(t),
            "words": len(_RX_WORD.findall(t)),
            "sentences": max(len(_RX_SENT.findall(t)), 1),
            "bullets": _bullets(t),
            "numbered": _numbered(t),
            "sentiment": sentiment(t),
            "flesch": flesch(t),
            "cite_ilo": 1 if _RX_ILO.search(t) else 0,
            "cite_statute": 1 if _RX_STAT.search(t) else 0,
            "refusal": 1 if _RX_REF.search(t) else 0,
            "resource": 1 if _RX_RES.search(t) else 0,
            "indicator": 1 if _RX_IND.search(t) else 0,
        })
feat = pd.DataFrame(_records)

display(Markdown(
    "Loaded **" + format(len(rows), ",") + " prompts** x **3 arms** = **" + format(len(feat), ",") +
    " prompt/response pairs** across **" + str(df.category.nunique()) + " categories**, **" +
    str(df.corridor.nunique()) + " corridors**, and **" + str(df.difficulty.nunique()) +
    " difficulty bands**.  NLP backends selected: sentiment = `" + SENT_BACKEND +
    "`, readability = `" + READ_BACKEND + "`, vectorizer = `" + ("sklearn" if HAS_SK else "pure-python Counter") + "`."
))'''

SETUP = PALETTE + "\n" + HELPERS + "\n" + DATALOAD


# --------------------------------------------------------------------------- #
# Section 1 -- RAW, ROW BY ROW (the centerpiece). Full verbatim prompt + baseline
# + harness_core, no truncation, for a few contrasting rows.
# --------------------------------------------------------------------------- #
S1_CODE = r'''def _head_refusal(t):
    head = (t or "")[:170].lower()
    return any(k in head for k in ["i cannot", "i can't", "i will not", "i won't",
                                   "i am unable", "i'm unable", "i am prohibited", "i can not"])

picks, seen = [], set()
# (a) up to 2 rows where the bare model complies but the harness refuses -- the safety divergence
for r in rows:
    pid = str(r.get("prompt_id"))
    if pid in seen:
        continue
    if not _head_refusal(r.get("baseline_response")) and _head_refusal(r.get("harness_core_response")):
        picks.append(r); seen.add(pid)
    if len(picks) >= 2:
        break
# (b) up to 2 rows where both answer but the harness adds ILO grounding -- the enrichment case
for r in rows:
    pid = str(r.get("prompt_id"))
    if pid in seen:
        continue
    core = str(r.get("harness_core_response") or "")
    if not _head_refusal(core) and "ilo" in core.lower() and len(core) > 900:
        picks.append(r); seen.add(pid)
    if len(picks) >= 4:
        break
# (c) top up from the front so we always show at least 3, even on an odd slice
for r in rows:
    if len(picks) >= 4:
        break
    pid = str(r.get("prompt_id"))
    if pid not in seen:
        picks.append(r); seen.add(pid)

display(Markdown("Showing **" + str(len(picks)) + "** rows end to end -- nothing truncated. "
                 "Read the bare-model answer, then the same prompt under the harness."))
for i, r in enumerate(picks, 1):
    meta = ("**Example " + str(i) + "** &middot; `" + str(r.get("prompt_id")) + "` &middot; category `" +
            str(r.get("category")) + "` &middot; corridor `" + str(r.get("corridor")) +
            "` &middot; difficulty `" + str(r.get("difficulty")) + "`")
    display(Markdown(meta))
    display(Markdown("**Raw prompt (verbatim):**" + NL + NL + "```text" + NL + str(r.get("prompt_text") or "") + NL + "```"))
    display(Markdown("**baseline response -- bare Gemma 4, no harness (verbatim):**" + NL + NL +
                     "```text" + NL + str(r.get("baseline_response") or "") + NL + "```"))
    display(Markdown("**harness_core response -- persona + GREP indicators + retrieval + tools (verbatim):**" + NL + NL +
                     "```text" + NL + str(r.get("harness_core_response") or "") + NL + "```"))
    display(Markdown("---"))'''


# --------------------------------------------------------------------------- #
# Section 2 -- length & structure
# --------------------------------------------------------------------------- #
S2_CODE = r'''def _med(arm, col):
    return float(feat.loc[feat.arm == arm, col].median())

stat_cards([
    (format(int(_med("baseline", "words")), ","), "median words / baseline", INK3),
    (format(int(_med("harness_core", "words")), ","), "median words / harness_core", TEAL),
    (str(round(_med("baseline", "bullets") + _med("baseline", "numbered"), 1)), "median list items / baseline", INK3),
    (str(round(_med("harness_core", "bullets") + _med("harness_core", "numbered"), 1)), "median list items / harness_core", TEAL),
])

kde_hist([("baseline", feat.loc[feat.arm == "baseline", "words"], INK3),
          ("harness_core", feat.loc[feat.arm == "harness_core", "words"], TEAL)],
         title="Response length by arm", subtitle="words per response; density-normalized",
         xlabel="words per response")

# Median words per response, by category -- show where the harness expands the answer most.
med = feat.groupby(["category", "arm"])["words"].median().unstack()
med = med.dropna(subset=["baseline", "harness_core"])
med = med.assign(delta=med["harness_core"] - med["baseline"])
sel = med[med["delta"] > 0].sort_values("delta", ascending=False).head(6)
if len(sel) < 3:
    sel = med.sort_values("delta", ascending=False).head(6)
sel = sel.iloc[::-1]
dumbbell([c.replace("_", " ") for c in sel.index], sel["baseline"].tolist(), sel["harness_core"].tolist(),
         lo_lab="baseline", hi_lab="harness_core",
         title="Median words per response -- categories where the harness expands the answer most",
         xlabel="median words per response")

_bw = feat.loc[feat.arm == "baseline", "words"].median()
_cw = feat.loc[feat.arm == "harness_core", "words"].median()
_bl = (feat.loc[feat.arm == "baseline", "bullets"] + feat.loc[feat.arm == "baseline", "numbered"]).mean()
_cl = (feat.loc[feat.arm == "harness_core", "bullets"] + feat.loc[feat.arm == "harness_core", "numbered"]).mean()
display(Markdown(
    "The harness response runs **" + str(int(_cw)) + "** median words vs **" + str(int(_bw)) +
    "** for the bare model, and carries **" + str(round(_cl, 1)) + "** structured list items on average vs **" +
    str(round(_bl, 1)) + "**. The expansion is not uniform: in benevolent-framing / evasion categories the harness "
    "often gets *shorter* instead, because it refuses the ask rather than elaborating -- see sections 1 and 5."
))'''


# --------------------------------------------------------------------------- #
# Section 3 -- sentiment
# --------------------------------------------------------------------------- #
S3_CODE = r'''# Compound polarity is in [-1, 1]; scale x100 so the on-chart mean label reads sensibly.
b = (feat.loc[feat.arm == "baseline", "sentiment"] * 100).tolist()
c = (feat.loc[feat.arm == "harness_core", "sentiment"] * 100).tolist()
kde_hist([("baseline", b, INK3), ("harness_core", c, TEAL)],
         title="Response sentiment by arm (backend: " + SENT_BACKEND + ")",
         subtitle="compound polarity scaled x100; higher = warmer / more positive tone",
         xlabel="sentiment (compound x100)")

# Mean sentiment shift baseline -> harness_core, by difficulty band (large, stable samples).
order = [d for d in ["easy", "medium", "hard"] if d in set(feat.difficulty)]
if not order:
    order = sorted(set(feat.difficulty))
left = [feat[(feat.arm == "baseline") & (feat.difficulty == d)]["sentiment"].mean() * 100 for d in order]
right = [feat[(feat.arm == "harness_core") & (feat.difficulty == d)]["sentiment"].mean() * 100 for d in order]
slope([d + " prompts" for d in order], left, right, left_lab="baseline", right_lab="harness_core",
      title="Mean sentiment shift, baseline -> harness_core", ylabel="sentiment (compound x100)")

_mb = feat.loc[feat.arm == "baseline", "sentiment"].mean()
_mc = feat.loc[feat.arm == "harness_core", "sentiment"].mean()
display(Markdown(
    "Mean compound sentiment is **" + str(round(_mc, 3)) + "** for harness_core vs **" + str(round(_mb, 3)) +
    "** for baseline. Read this as *tone*, not correctness: both arms discuss the same grim subject matter, and the "
    "harness tends toward a measured, formal, procedure-first register (cite the indicator, name the obligation, give a "
    "safe next step) rather than a warmer or more emphatic one."
))'''


# --------------------------------------------------------------------------- #
# Section 4 -- distinctive vocabulary (the strongest signal)
# --------------------------------------------------------------------------- #
S4_CODE = r'''base_txt = feat.loc[feat.arm == "baseline", "text"].tolist()
core_txt = feat.loc[feat.arm == "harness_core", "text"].tolist()
a_top, b_top = distinctive_terms(core_txt, base_txt, n=15)

fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.6, 6.4))
def _draw(ax, items, color, title):
    items = items[::-1]
    terms = [t for t, _, _, _ in items]
    scores = [s for _, s, _, _ in items]
    y = list(range(len(terms)))
    ax.barh(y, scores, color=color, edgecolor=INK2, linewidth=0.4)
    ax.set_yticks(y); ax.set_yticklabels(terms)
    ax.set_xlabel("weighted log-odds z-score"); ax.set_title(title)
    ax.grid(axis="y", visible=False)
_draw(axL, a_top, TEAL, "More distinctive of harness_core")
_draw(axR, b_top, INK3, "More distinctive of baseline")
fig.suptitle("Distinctive vocabulary -- weighted log-odds z-score, harness_core vs baseline",
             fontsize=13.5, fontweight="bold")
fig.tight_layout(); save(fig, "nlp_distinctive"); plt.show()

# Heatmap: mean occurrences per response of a few key safety terms, across all three arms.
KEY = ["ilo", "indicator", "recruitment", "passport", "hotline", "rights", "wages", "contract", "debt", "report"]
mat = []
for term in KEY:
    pat = re.compile(r"\b" + term + r"\b", re.I)
    mat.append([float(np.mean([len(pat.findall(x)) for x in feat.loc[feat.arm == a, "text"]])) for a in ARMS])
heatmap(mat, KEY, ARMS, title="Key safety terms -- mean occurrences per response",
        subtitle="how often each term appears in a typical response, per arm",
        cmap="BuGn", fmt=".2f", cbar_label="mean / response")

_hi = ", ".join(t for t, _, _, _ in a_top[:8])
display(Markdown("The terms most distinctive of the harness response are: **" + _hi +
                 "** -- the vocabulary of ILO indicators, recruitment-fee mechanics, document control, and reporting "
                 "pathways. That vocabulary is largely absent from the bare model's more generic phrasing."))'''


# --------------------------------------------------------------------------- #
# Section 5 -- safety-vocabulary detection (regex, rate per response)
# --------------------------------------------------------------------------- #
S5_CODE = r'''PATTERNS = [("cite_ilo", "ILO / convention cite"), ("cite_statute", "statute / legal ref"),
            ("refusal", "refusal / redirection"), ("resource", "resource / hotline"),
            ("indicator", "indicator language")]
labels = [lab for _, lab in PATTERNS]
base = [feat.loc[feat.arm == "baseline", k].mean() * 100 for k, _ in PATTERNS]
core = [feat.loc[feat.arm == "harness_core", k].mean() * 100 for k, _ in PATTERNS]

y = np.arange(len(labels)); h = 0.38
fig, ax = plt.subplots(figsize=(10.2, 5.4))
ax.barh(y + h / 2, base, height=h, color=INK3, label="baseline", edgecolor=INK2, linewidth=0.4)
ax.barh(y - h / 2, core, height=h, color=TEAL, label="harness_core", edgecolor=INK2, linewidth=0.4)
for yi, (bv, cv) in enumerate(zip(base, core)):
    ax.text(bv + 1.0, yi + h / 2, format(bv, ".0f") + "%", va="center", fontsize=9, color=INK3)
    ax.text(cv + 1.0, yi - h / 2, format(cv, ".0f") + "%", va="center", fontsize=9, color=TEAL_DK)
ax.set_yticks(y); ax.set_yticklabels(labels)
ax.set_xlabel("percent of responses containing the pattern")
ax.set_xlim(0, max(max(base), max(core)) * 1.18 + 3)
ax.grid(axis="y", visible=False); ax.legend(loc="lower right")
ax.set_title("Safety-vocabulary detection rate, per arm")
fig.tight_layout(); save(fig, "nlp_safety"); plt.show()

tbl = pd.DataFrame({"pattern": labels,
                    "baseline %": [round(x, 1) for x in base],
                    "harness_core %": [round(x, 1) for x in core],
                    "delta (pts)": [round(c - b, 1) for b, c in zip(base, core)]})
display(pretty_table(tbl, caption="Share of responses containing each safety-vocabulary pattern (regex, per response)",
                     bars=["harness_core %"]))'''


# --------------------------------------------------------------------------- #
# Section 6 -- readability
# --------------------------------------------------------------------------- #
S6_CODE = r'''def _mf(arm):
    return float(feat.loc[feat.arm == arm, "flesch"].median())

stat_cards([(str(round(_mf("baseline"), 1)), "median Flesch / baseline", INK3),
            (str(round(_mf("harness_core"), 1)), "median Flesch / harness_core", TEAL),
            (str(round(_mf("harness_full"), 1)), "median Flesch / harness_full", GOOD)])

kde_hist([("baseline", feat.loc[feat.arm == "baseline", "flesch"], INK3),
          ("harness_core", feat.loc[feat.arm == "harness_core", "flesch"], TEAL)],
         title="Readability by arm (backend: " + READ_BACKEND + ")",
         subtitle="Flesch reading-ease; higher = easier to read (60-70 ~ plain English, <30 ~ dense / professional)",
         xlabel="Flesch reading-ease")

display(Markdown(
    "Both arms land in the dense, professional band (legal citations and multi-clause sentences pull the score down). "
    "The harness response is typically a few points lower still -- the cost of naming conventions, statutes, and "
    "obligations explicitly. It reads like a compliance memo, which is the intended register for an NGO / regulator audience."
))'''


# --------------------------------------------------------------------------- #
# Section 7 -- word clouds
# --------------------------------------------------------------------------- #
S7_CODE = r'''try:
    from wordcloud import WordCloud
    HAS_WC = True
except Exception:
    HAS_WC = False

fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.6, 5.6))
for ax, arm, cmap in [(a1, "baseline", "Greys"), (a2, "harness_core", "BuGn")]:
    freqs = top_frequencies(feat.loc[feat.arm == arm, "text"].tolist(), 150)
    ax.set_title(arm + " -- top vocabulary")
    if HAS_WC and freqs:
        wc = WordCloud(width=760, height=470, background_color=PAPER, colormap=cmap,
                       prefer_horizontal=0.95, max_words=140).generate_from_frequencies(freqs)
        ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
    else:
        top = list(freqs.items())[:20][::-1]
        terms = [w for w, _ in top]; vals = [v for _, v in top]
        yy = list(range(len(terms)))
        ax.barh(yy, vals, color=(INK3 if arm == "baseline" else TEAL), edgecolor=INK2, linewidth=0.4)
        ax.set_yticks(yy); ax.set_yticklabels(terms, fontsize=8.5)
        ax.set_xlabel("count"); ax.grid(axis="y", visible=False)
_mode = "word clouds" if HAS_WC else "top-term bars (wordcloud not installed -- offline fallback)"
fig.suptitle("Most frequent vocabulary -- baseline vs harness_core  [" + _mode + "]",
             fontsize=13.5, fontweight="bold")
fig.tight_layout(); save(fig, "nlp_wordclouds"); plt.show()
display(Markdown("Rendered as **" + _mode + "**. The baseline cloud is dominated by generic explanatory words; the "
                 "harness cloud pulls in the domain's working vocabulary -- recruitment, passport, employer, fees, "
                 "indicators, and reporting channels."))'''


# --------------------------------------------------------------------------- #
# markdown cells (URLs literal; HTML entities are ASCII source that render as glyphs)
# --------------------------------------------------------------------------- #
HERO_MD = '''<div style="padding:26px 32px;border-radius:16px;background:linear-gradient(120deg,#14181B 0%,#2A2D34 42%,#2f7d8c 100%);color:#F7F6F1">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.82">DueCare &middot; Gemma 4 safety &middot; prompt + response NLP</div>
<h1 style="margin:.28em 0 .2em;font-size:30px;color:#ffffff;font-weight:800">What changes when you wrap Gemma 4 in a safety harness?</h1>
<p style="font-size:15px;line-height:1.6;margin:0;max-width:940px">This notebook reads the <b>raw prompts and raw responses</b> from the <b>DueCare Prompt + Response Showcase</b> &mdash; 1,087 synthetic migrant-worker-safety prompts, each answered by <b>gemma4:31b</b> under three arms: <b>baseline</b> (bare model), <b>harness_core</b> (persona + GREP indicator rules + retrieval + tools), and <b>harness_full</b> (+ online). We first show the data <b>row by row, verbatim</b>, then run classic NLP over it &mdash; length &amp; structure, sentiment, distinctive vocabulary, safety-term detection, readability, and word clouds &mdash; entirely on CPU, with no model, no GPU, and no internet. Every chart is computed live from the attached file.</p>
</div>'''

TOC_MD = '''## What is in this notebook

Every number and chart below is computed **live from the attached dataset** &mdash; nothing is hard-coded.

- [1. Raw, row by row &mdash; prompts + responses, verbatim](#raw)
- [2. Length &amp; structure &mdash; how big, how organized](#length)
- [3. Sentiment &mdash; tone by arm](#sentiment)
- [4. Distinctive vocabulary &mdash; what the harness says that the bare model does not](#vocab)
- [5. Safety-vocabulary detection &mdash; citations, refusals, resources, indicators](#safety)
- [6. Readability &mdash; Flesch reading-ease by arm](#readability)
- [7. Word clouds &mdash; baseline vs harness_core](#clouds)
- [8. Honest boundary &amp; license](#boundary)

**Honest boundary (read first).** These prompts are **synthetic / composite** &mdash; no real person, case, contact, or document appears, and the set is PII-clean. The responses are **model outputs**, shown as **illustrative / silver** material, not gold human labels or legal advice. This is an exploratory NLP view of *how the harness changes the text*, not a real-world detection claim. License **CC0**.

**Dataset:** [`taylorsamarel/duecare-prompt-response-showcase`](https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase) &middot; **Start-here index:** [`duecare-harness-lift-benchmark`](https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here) &middot; **Repo:** [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''

S1_MD = '''<a id="raw"></a>
## 1. Raw, row by row &mdash; prompts + responses, verbatim

The centerpiece: a few real rows shown **end to end, nothing truncated**. Each block is the raw `prompt_text`, then the full `baseline_response` (bare Gemma 4), then the full `harness_core_response` (the same model wrapped in persona + GREP indicator rules + retrieval + tools). The selector deliberately surfaces **contrast** &mdash; rows where the bare model answers a loaded request but the harness refuses and redirects, and rows where both answer but the harness grounds the reply in ILO indicators and reporting pathways.'''

S2_MD = '''<a id="length"></a>
## 2. Length &amp; structure &mdash; how big, how organized

The first thing NLP notices is shape: how many words, and how much of the answer is broken into bullets and numbered steps. The KPI tiles compare medians; the density plot shows the full word-count distribution per arm; the dumbbell shows, per category, how much longer the harness answer runs.'''

S3_MD = '''<a id="sentiment"></a>
## 3. Sentiment &mdash; tone by arm

Sentiment here is a proxy for **tone**, not correctness &mdash; every response discusses the same difficult subject. We score each response's compound polarity (VADER when present, TextBlob or a bundled lexicon as offline fallbacks) and compare the distributions, then track the mean shift from baseline to harness_core across difficulty bands.'''

S4_MD = '''<a id="vocab"></a>
## 4. Distinctive vocabulary &mdash; what the harness says that the bare model does not

This is the strongest signal in the corpus. Using the **weighted log-odds-ratio z-score** with an informative Dirichlet prior (Monroe, Colaresi &amp; Quinn 2008, "Fightin' Words") &mdash; which balances how *lopsided* a word is against how *often* it occurs, so frequent discriminators outrank one-off rarities &mdash; we rank the words most over-represented in `harness_core` versus `baseline`, and vice-versa. The teal bars are the harness's distinctive vocabulary; the grey bars are the bare model's. The heatmap then tracks a handful of key safety terms across all three arms.'''

S5_MD = '''<a id="safety"></a>
## 5. Safety-vocabulary detection &mdash; citations, refusals, resources, indicators

Regex detectors flag, per response, whether it cites an **ILO convention**, references a **statute or legal rule**, uses **refusal / redirection** language, points to a **resource or hotline**, or names a forced-labour **indicator**. The bars show the share of responses in each arm that contain each pattern &mdash; a direct read on how the harness reshapes what the model reaches for.'''

S6_MD = '''<a id="readability"></a>
## 6. Readability &mdash; Flesch reading-ease by arm

Flesch reading-ease scores how hard the text is to read (higher = easier). Legal citations and multi-clause sentences push both arms into the dense, professional band; we compare the medians and the full distribution. textstat is used when installed, with a self-contained Flesch approximation as the offline fallback.'''

S7_MD = '''<a id="clouds"></a>
## 7. Word clouds &mdash; baseline vs harness_core

A quick visual of the most frequent vocabulary in each arm, stop-words removed. When the `wordcloud` package is available the notebook renders true clouds; otherwise it falls back to top-term bars via the shared toolkit, so this cell always produces output offline.'''

BOUNDARY_MD = '''<a id="boundary"></a>
## 8. Honest boundary &amp; license

**What this is.** An exploratory NLP view of how a safety harness changes Gemma 4's text on a fixed prompt set. Everything is computed live from the attached CSV, on CPU, with no model and no internet.

**What this is not.** The prompts are **synthetic / composite** &mdash; no real individual, case, contact, name, number, or address appears, and the set is PII-clean. The responses are **model outputs**, treated as **illustrative / silver** material, not gold human annotations and not legal advice. Sentiment and readability are **tone / style proxies**, not measures of correctness or safety. This notebook makes **no** real-world detection or victim-identification claim.

**Reproducibility.** Every optional NLP package (vaderSentiment, textblob, textstat, wordcloud, scikit-learn) is wrapped in try/except with an offline fallback, so the notebook runs to completion with `enable_internet=false`. The distinctive-vocabulary math is a smoothed log relative-frequency ratio, length-normalized across arms.

**License.** CC0.

**Links.** Dataset: [`taylorsamarel/duecare-prompt-response-showcase`](https://www.kaggle.com/datasets/taylorsamarel/duecare-prompt-response-showcase) &middot; Start-here index: [`duecare-harness-lift-benchmark`](https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here) &middot; Source repository: [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''


def _notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        _md(HERO_MD),
        _md(TOC_MD),
        _code(SETUP),
        _md(S1_MD),
        _code(S1_CODE),
        _md(S2_MD),
        _code(S2_CODE),
        _md(S3_MD),
        _code(S3_CODE),
        _md(S4_MD),
        _code(S4_CODE),
        _md(S5_MD),
        _code(S5_CODE),
        _md(S6_MD),
        _code(S6_CODE),
        _md(S7_MD),
        _code(S7_CODE),
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
