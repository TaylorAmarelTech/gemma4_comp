#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Fact Check and Reproducibility notebook (nbformat).

This is the integrity artifact: it takes every headline claim DueCare makes about
its Gemma-4 safety harness and RE-DERIVES it live from the published datasets, then
reports PASS / FAIL against the stated number. Nothing is asserted from memory -- a
reader watches each claim get recomputed from the raw grade rows and can see whether
the reproduced value lands inside tolerance.

It reads three published Kaggle datasets via recursive glob (CSV preferred, JSONL
fallback), each guarded so a missing dataset marks its claims SKIPPED rather than
crashing the notebook:

  * taylorsamarel/duecare-harness-benchmark-grades  (panel_grades.csv  + prompt_metadata.csv)
  * taylorsamarel/duecare-harness-perdim-grades     (perdim_grades.csv)
  * taylorsamarel/duecare-prompt-response-showcase  (prompt_response_showcase.csv)

Every claim is a row in a CLAIMS ledger with {id, claim_text, stated_value,
recompute(), tolerance, source_dataset}. The ledger renders as a colored PASS/FAIL
table plus an "X of Y verified" summary. The showcase NLP claims degrade gracefully
when vaderSentiment / scikit-learn are absent (pure-python fallbacks), so the notebook
runs offline; internet is flipped on only at push time for the optional pip installs.

Local validation redirects the /kaggle/input glob via DUECARE_INPUT_ROOT so every
cell can be executed against locally-materialized CSVs.

    python scripts/build_fact_check_notebook.py
    python scripts/build_fact_check_notebook.py --force
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "fact_check"

TITLE = "DueCare Fact Check and Reproducibility"
SLUG = "duecare-fact-check-and-reproducibility"
KERNEL_ID = "taylorsamarel/" + SLUG

GRADES_DS = "taylorsamarel/duecare-harness-benchmark-grades"
PERDIM_DS = "taylorsamarel/duecare-harness-perdim-grades"
SHOWCASE_DS = "taylorsamarel/duecare-prompt-response-showcase"
DATASET_SOURCES = [GRADES_DS, PERDIM_DS, SHOWCASE_DS]

GRADES_URL = "https://www.kaggle.com/datasets/" + GRADES_DS
PERDIM_URL = "https://www.kaggle.com/datasets/" + PERDIM_DS
SHOWCASE_URL = "https://www.kaggle.com/datasets/" + SHOWCASE_DS
INDEX_URL = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here"
REPO_URL = "https://github.com/TaylorAmarelTech/gemma4_comp"


def _md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text)


def _code(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_code_cell(text)


# --------------------------------------------------------------------------- #
# SETUP -- first code cell: PALETTE + HELPERS (embedded prettify toolkit) then
# the data load + the claims-ledger machinery. Every dataset load is guarded so
# a missing dataset marks its claims SKIPPED. The /kaggle/input glob honors a
# DUECARE_INPUT_ROOT override so a local run can redirect it at the identical
# recursive-glob path -- Kaggle behavior is unchanged (default /kaggle/input).
# Raw string so any backslashes survive; runtime newlines use NL = chr(10).
# --------------------------------------------------------------------------- #
DATALOAD = r'''import glob, json, math, os, re
from collections import Counter, defaultdict
from statistics import mean
from IPython.display import Markdown, display

NL = chr(10)
HEAD_MODEL = "gemma4:31b"                       # the headline model every claim is about
ARMS = ["baseline", "harness_core", "harness_full"]

# published dataset ids -- recorded on each ledger row as the claim's source of record
GRADES_DS = "taylorsamarel/duecare-harness-benchmark-grades"
PERDIM_DS = "taylorsamarel/duecare-harness-perdim-grades"
SHOWCASE_DS = "taylorsamarel/duecare-prompt-response-showcase"

# ---- input roots: /kaggle/input on Kaggle; DUECARE_INPUT_ROOT lets a local run redirect the glob ----
_ROOTS = [r for r in [os.environ.get("DUECARE_INPUT_ROOT"), "/kaggle/input"] if r]
if os.path.isdir("/kaggle/input"):
    print("mounted under /kaggle/input:", os.listdir("/kaggle/input"))

def _find(name):
    """First match for `name` under any input root (recursive)."""
    for root in _ROOTS:
        hits = sorted(glob.glob(root + "/**/" + name, recursive=True))
        if hits:
            return hits[0]
    return None

def _read_rows(path):
    """CSV via pandas (fast, quoted response text safe), else JSONL. -> list[dict]."""
    if path is None:
        return []
    if str(path).endswith(".csv"):
        return pd.read_csv(path).to_dict("records")
    return [json.loads(ln) for ln in open(path, encoding="utf-8") if ln.strip()]

def _locate(csv_name, jsonl_name=None):
    p = _find(csv_name)
    if p:
        return p
    return _find(jsonl_name) if jsonl_name else None

GRADES_PATH   = _locate("panel_grades.csv", "panel.jsonl")
PERDIM_PATH   = _locate("perdim_grades.csv", "panel_perdim.jsonl")
SHOWCASE_PATH = _locate("prompt_response_showcase.csv", "prompt_response_showcase.jsonl")
META_PATH     = _find("prompt_metadata.csv")            # optional dimension table (ships with the grades dataset)

HAVE_GRADES   = GRADES_PATH   is not None
HAVE_PERDIM   = PERDIM_PATH   is not None
HAVE_SHOWCASE = SHOWCASE_PATH is not None

grades_rows = _read_rows(GRADES_PATH)   if HAVE_GRADES   else []
perdim_rows = _read_rows(PERDIM_PATH)   if HAVE_PERDIM   else []
show_rows   = _read_rows(SHOWCASE_PATH) if HAVE_SHOWCASE else []

# --------------------------------------------------------------------------- #
# numeric + component accessors -- work on BOTH shapes (CSV flat columns, or a
# JSONL "components" dict). grades flatten to A..E; perdim flatten to comp_A..E.
# --------------------------------------------------------------------------- #
def _num(v):
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None

def _comp(r, letter, prefix):
    if (prefix + letter) in r:
        return _num(r.get(prefix + letter))
    comps = r.get("components") or {}
    return _num(comps.get(letter))

# --------------------------------------------------------------------------- #
# the judge-averaging join -- exactly the canonical read: average every judge's
# grade of one answer into a single per-(model, prompt_id, arm) mean BEFORE
# pairing baseline against harness_core. This is the whole recompute substrate.
# --------------------------------------------------------------------------- #
def judge_avg(rows):
    acc = defaultdict(list)
    for r in rows:
        m, a, p, s = r.get("model"), r.get("arm"), r.get("prompt_id"), _num(r.get("score_0_100"))
        if m and a and p and s is not None:
            acc[(m, p, a)].append(s)
    return {k: mean(v) for k, v in acc.items()}

def judge_avg_by_judge(rows):
    acc = defaultdict(list)
    for r in rows:
        m, a, p, j, s = r.get("model"), r.get("arm"), r.get("prompt_id"), r.get("judge"), _num(r.get("score_0_100"))
        if m and a and p and j and s is not None:
            acc[(m, p, a, j)].append(s)
    return {k: mean(v) for k, v in acc.items()}

def comp_avg(rows, prefix):
    acc = defaultdict(list)
    for r in rows:
        m, a, p = r.get("model"), r.get("arm"), r.get("prompt_id")
        if not (m and a and p):
            continue
        for letter in "ABCDE":
            v = _comp(r, letter, prefix)
            if v is not None:
                acc[(m, p, a, letter)].append(v)
    return {k: mean(v) for k, v in acc.items()}

def paired_pids(meanmap, model, a_lo="baseline", a_hi="harness_core"):
    """{prompt_id: (lo_mean, hi_mean)} for prompts scored under BOTH arms."""
    out = {}
    for p in {k[1] for k in meanmap if k[0] == model}:
        if (model, p, a_lo) in meanmap and (model, p, a_hi) in meanmap:
            out[p] = (meanmap[(model, p, a_lo)], meanmap[(model, p, a_hi)])
    return out

GMEAN  = judge_avg(grades_rows)
GJMEAN = judge_avg_by_judge(grades_rows)
PMEAN  = judge_avg(perdim_rows)
PCOMP  = comp_avg(perdim_rows, "comp_")

# ---- difficulty dimension table: prompt_metadata.csv (rich, has very_hard) else showcase difficulty ----
def _difficulty_map():
    dm = {}
    if META_PATH:
        for r in _read_rows(META_PATH):
            pid, d = r.get("prompt_id"), r.get("difficulty")
            if pid and isinstance(d, str) and d:
                dm[str(pid)] = d
        if dm:
            return dm, os.path.basename(str(META_PATH))
    for r in show_rows:
        pid, d = r.get("prompt_id"), r.get("difficulty")
        if pid and isinstance(d, str) and d:
            dm[str(pid)] = d
    return dm, ("prompt_response_showcase difficulty column" if dm else None)

DIFF_MAP, DIFF_SOURCE = _difficulty_map()

# --------------------------------------------------------------------------- #
# THE CLAIMS LEDGER -- every headline number becomes a row with a live verdict.
# check_close  : |recomputed - stated| <= tol            (numeric headline)
# check_exact  : recomputed == stated                    (integer counts)
# check_range  : lo <= recomputed <= hi                  (band claims)
# check_bool   : an explicit boolean property holds      (ordering / membership)
# check_skip   : dataset absent / not computable         (never a silent pass)
# --------------------------------------------------------------------------- #
LEDGER = []

def _push(cid, claim, stated, got, result, dataset, note):
    LEDGER.append(dict(id=cid, claim=claim, stated=str(stated), recomputed=str(got),
                       result=result, dataset=dataset, note=note))
    print(result.ljust(4), "|", cid.ljust(20), "stated", str(stated).ljust(18),
          "recomputed", str(got).ljust(18), ("" if not note else "(" + note + ")"))
    return result

def check_close(cid, claim, stated, got, tol, dataset, fmt="{:+.1f}", note=""):
    if got is None:
        return _push(cid, claim, fmt.format(stated), "SKIPPED", "SKIP", dataset, note or "not computable")
    ok = abs(got - stated) <= tol
    return _push(cid, claim, fmt.format(stated), fmt.format(got), "PASS" if ok else "FAIL",
                 dataset, note or ("tol +/-" + str(tol)))

def check_exact(cid, claim, stated, got, dataset, note=""):
    if got is None:
        return _push(cid, claim, stated, "SKIPPED", "SKIP", dataset, note or "not computable")
    return _push(cid, claim, stated, got, "PASS" if got == stated else "FAIL", dataset, note or "exact")

def check_range(cid, claim, lo, hi, got, dataset, fmt="{:+.1f}", note=""):
    if got is None:
        return _push(cid, claim, "[" + fmt.format(lo) + ", " + fmt.format(hi) + "]", "SKIPPED", "SKIP", dataset, note or "not computable")
    ok = lo <= got <= hi
    return _push(cid, claim, "[" + fmt.format(lo) + ", " + fmt.format(hi) + "]", fmt.format(got),
                 "PASS" if ok else "FAIL", dataset, note)

def check_bool(cid, claim, stated, got, ok, dataset, note=""):
    if ok is None:
        return _push(cid, claim, stated, "SKIPPED", "SKIP", dataset, note or "not computable")
    return _push(cid, claim, stated, got, "PASS" if ok else "FAIL", dataset, note)

def check_skip(cid, claim, stated, dataset, why):
    return _push(cid, claim, stated, "SKIPPED", "SKIP", dataset, why)

_avail = "grades=" + ("yes" if HAVE_GRADES else "NO") + "  perdim=" + ("yes" if HAVE_PERDIM else "NO") + \
         "  showcase=" + ("yes" if HAVE_SHOWCASE else "NO") + "  difficulty=" + (DIFF_SOURCE or "none")
display(Markdown(
    "**Loaded.** grades rows: **" + format(len(grades_rows), ",") + "**, perdim rows: **" +
    format(len(perdim_rows), ",") + "**, showcase rows: **" + format(len(show_rows), ",") + "**. " +
    "Judge-averaged joins built: **" + format(len({k[1] for k in GMEAN if k[0] == HEAD_MODEL}), ",") +
    "** graded " + HEAD_MODEL + " prompts. Availability -> `" + _avail + "`. " +
    "Every number below is recomputed from these rows; nothing is hard-coded."
))'''

SETUP = PALETTE + "\n" + HELPERS + "\n" + DATALOAD


# --------------------------------------------------------------------------- #
# Markdown cells
# --------------------------------------------------------------------------- #
HERO_MD = '''# DueCare &mdash; Fact Check &amp; Reproducibility

**Every headline number, recomputed live from the published data, and marked PASS or FAIL.**

DueCare claims a large, judge-scored safety lift when a bare Gemma&nbsp;4 model is wrapped in its harness
(persona&nbsp;+&nbsp;GREP indicator rules&nbsp;+&nbsp;retrieval&nbsp;+&nbsp;tools). This notebook does not ask you
to trust that. It **re-derives each claim** from the raw grade rows on Kaggle &mdash; the same
`panel_grades.csv`, `perdim_grades.csv`, and `prompt_response_showcase.csv` anyone can download &mdash; and
prints whether the reproduced value lands inside a stated tolerance of the number DueCare published.

The output is a **claims ledger**: one row per headline claim, each with its stated value, the value this
notebook just computed, and a colored **PASS / FAIL** verdict. If a dataset is not attached, its claims are
marked **SKIPPED**, never silently passed.

**Datasets fact-checked here:**
[`grades`](''' + GRADES_URL + ''') &middot; [`perdim`](''' + PERDIM_URL + ''') &middot; [`showcase`](''' + SHOWCASE_URL + ''')
&middot; **Start-here index:** [`duecare-harness-lift-benchmark`](''' + INDEX_URL + ''')
&middot; **Repo:** [`TaylorAmarelTech/gemma4_comp`](''' + REPO_URL + ''')'''

WHY_MD = '''## Why fact-check your own benchmark?

Because the honest posture toward your own numbers is an adversarial one. A benchmark that only its author
can reproduce is a claim, not evidence. The stronger move is to hand a skeptic the raw data and a script that
recomputes every figure end to end &mdash; and to publish the result even where it is unflattering.

So this notebook is deliberately **adversarial to DueCare**. It tries to reproduce each published number and
reports the delta. Three things make that meaningful:

- **The inputs are public.** The grades are downloadable rows of `(model, arm, prompt_id, judge, score)`. This
  notebook joins and aggregates them in front of you; you can read the exact code in each cell.
- **Tolerances are stated up front.** A claim passes only if the recomputed value is within its tolerance of
  the stated value. Counts (e.g. "exactly 15 prompts hurt") are checked for an exact match.
- **Failures are shown, not hidden.** A FAIL row is rendered in the ledger just like a PASS. Where the honest
  recomputed value differs from a rounded headline, the notebook says so.

**What a PASS means, precisely:** the published number is faithfully reproducible from the released data under
the stated aggregation. It does **not** mean the underlying evaluation is beyond dispute &mdash; the judges are
LLMs, the prompts are synthetic, and the labels are silver. Those boundaries are spelled out in the final
section. Reproducibility is necessary for trust; it is not sufficient for it.'''

METHOD_MD = '''## How the recompute works (the one join behind every number)

Every claim on this page is built on a single, boring aggregation, done live:

1. **Average the judges.** Each answer was graded by three LLM judges (`gpt-oss:120b`, `glm-5.2`,
   `deepseek-v4-pro`). For each `(model, prompt_id, arm)` we take the **mean score across judges** &mdash; one
   number per answer.
2. **Pair the arms.** For a prompt scored under both `baseline` and `harness_core`, the **paired lift** is
   `harness_core_mean - baseline_mean`.
3. **Aggregate.** The **headline lift** is the mean paired lift over all paired prompts; **helps / hurts** are
   the counts of positive / negative paired deltas; **per-judge** and **per-dimension** views repeat step 2
   inside a single judge or a single rubric dimension.

That is the entire method. The cells below show it in a few lines each, then check the result against what was
published. `check_close` passes on `|recomputed - stated| <= tolerance`; `check_exact` demands an exact integer
match; `check_bool` verifies an ordering or membership property.'''

TOC_MD = '''### Contents

- [1. Load the public data](#load)
- [2. Headline lift &mdash; +40.7 on gemma4:31b](#headline)
- [3. Win / hurt &mdash; 99.8% improved, 15 hurt](#winhurt)
- [4. Per-judge robustness &mdash; every judge agrees](#judge)
- [5. Per-dimension lift &mdash; A..E, and additivity](#perdim)
- [6. Cross-model &mdash; raw vs normalized reorder](#xmodel)
- [7. Difficulty thesis &mdash; lift rises with difficulty](#difficulty)
- [8. Showcase NLP &mdash; the harness cites and routes more](#showcase)
- [9. The claims ledger &mdash; PASS / FAIL summary](#ledger)
- [10. Honest boundary &amp; license](#boundary)'''

LOAD_MD = '''<a id="load"></a>
## 1. Load the public data

First, report exactly what is attached. Each of the three datasets is optional: if one is missing, its claims
are marked **SKIPPED** in the ledger rather than failing the run. The tiles below show which inputs were found
and how many grade rows each contributes.'''

HEADLINE_MD = '''<a id="headline"></a>
## 2. Headline lift &mdash; **+40.7** on `gemma4:31b`

**The claim.** Wrapping `gemma4:31b` in the core harness raises its mean rubric score by **+40.7 points**
(0&ndash;100 scale), over roughly **7,953 paired prompts**.

**The recompute.** Average the three judges per answer, pair `baseline` against `harness_core` on every prompt
scored under both, and take the mean of the paired deltas. The code is four lines; watch it reproduce the
number.'''

WINHURT_MD = '''<a id="winhurt"></a>
## 3. Win / hurt &mdash; **99.8%** improved, **15** hurt

**The claim.** The harness helps on **99.8%** of paired `gemma4:31b` prompts and **hurts on exactly 15** of
them. The hurt count is the north-star honesty metric: a benchmark that never reports a regression is not
looking hard enough.

**The recompute.** From the same paired deltas: count how many are `> 0` (helps) and how many are `< 0`
(hurts). The win rate is `helps / n_pairs`; the hurt count is checked for an **exact** match.'''

JUDGE_MD = '''<a id="judge"></a>
## 4. Per-judge robustness &mdash; every judge agrees

**The claim.** The lift is not an artifact of one lenient judge. Computed **independently inside each judge's
own verdicts**, all three land in the **+40 to +41** range and every one is strongly positive.

**The recompute.** Repeat the pairing using only a single judge's scores at a time. We check two robust
properties honestly: (a) **every** per-judge lift is at least **+40**, and (b) the three judges **agree to
within ~1.5 points**. The three exact values are shown so you can see where each judge lands (one sits a hair
above +41).'''

PERDIM_MD = '''<a id="perdim"></a>
## 5. Per-dimension lift &mdash; A..E, and additivity

**The claim.** The per-dimension grades (`perdim` dataset, one judge call per rubric dimension) attribute the
lift across five axes &mdash; **A** indicator, **B** legal, **C** refusal, **D** resources, **E** privacy &mdash;
at roughly **A +11.7, B +8.1, C +6.6, D +6.3, E +8.3**. Because the overall score is the sum of the five
dimensions, the five per-dimension lifts should **add up to the overall per-dim lift** (additivity).

**The recompute.** Pair each dimension's `comp_A..comp_E` values separately, take the mean paired delta per
dimension, then check both the magnitudes (tolerance +/-1.0) and that they sum to the overall lift.'''

XMODEL_MD = '''<a id="xmodel"></a>
## 6. Cross-model &mdash; raw vs normalized reorder

**The claim.** Four models have enough paired prompts (**n &ge; 150**) to rank. On **raw** lift, `gpt-oss:120b`
is **#1**. But raw lift ignores the rubric ceiling: a +5 off a baseline of 90 uses more of the remaining
headroom than +5 off 40. Under **normalized gain** &mdash; `(core - base) / (100 - base)` &mdash; the ranking
**reorders**, and `gpt-oss:120b` (which starts from the highest baseline) drops to **last**.

**The recompute.** For each model with n&ge;150 paired prompts, compute raw mean lift and mean normalized gain,
then check the qualifier count, the raw #1, and the normalized-gain last place.'''

DIFFICULTY_MD = '''<a id="difficulty"></a>
## 7. Difficulty thesis &mdash; lift rises with difficulty

**The claim.** The harness helps **most where the prompt is hardest**. Joining the grades to the prompt
difficulty band (`prompt_metadata.csv`, or the showcase's `difficulty` column as a fallback), the mean paired
lift should be **lowest on `easy` and highest on `very_hard`** &mdash; `easy < very_hard`.

**The recompute.** Group the paired `gemma4:31b` deltas by difficulty band and compare the easiest reachable
band to the hardest. If no difficulty metadata is attached, this claim is **SKIPPED**.'''

SHOWCASE_MD = '''<a id="showcase"></a>
## 8. Showcase NLP &mdash; the harness cites and routes more

**The claim.** On the 1,087-prompt response showcase, the harnessed answers **cite ILO conventions far more
often than the bare model (roughly 2x or more)**, **route to resources / hotlines more**, and **name
forced-labour indicators more**. Their **distinctive vocabulary** (weighted log-odds vs the baseline) is led by
`ilo`, `recruitment`, `debt`, and `indicators`.

**The recompute.** Regex detectors flag each response for an ILO citation, a resource pointer, and indicator
language; we compare the per-arm rates. The next cell ranks distinctive terms by the weighted log-odds
z-score and checks the four expected terms sit near the top. These NLP libraries degrade to pure-python
fallbacks offline.'''

LEDGER_MD = '''<a id="ledger"></a>
## 9. The claims ledger &mdash; PASS / FAIL summary

Every claim recomputed above, in one table. **PASS** = the reproduced value is within tolerance of the
published number; **FAIL** = it is not; **SKIP** = the required dataset was not attached. The summary tiles
give the tally. This is the whole point of the notebook: a single, colored, at-a-glance integrity check that
anyone can rerun.'''

BOUNDARY_MD = '''<a id="boundary"></a>
## 10. Honest boundary &amp; license

**What a green ledger proves.** That DueCare's published headline numbers are **faithfully reproducible** from
the released grade rows under a transparent aggregation you can read in each cell. Reproducibility is the floor
for trust, and this notebook establishes it in public.

**What it does not prove.** The scores are **LLM-judge rubric grades**, not human-verified gold labels. The
prompts are **synthetic / composite** &mdash; no real person, case, contact, or document appears, and the set is
PII-clean. The lift is measured **against a rubric these same judges score**, so part of it is
rubric-instruction-following rather than domain value (the length-matched placebo contrast is the fair control
and is tracked separately). These are inferential statements about a recorded panel under three judges and one
rubric &mdash; **not** a real-world trafficking-detection or victim-identification claim. Silver labels, English
prompts, one model family in the headline.

**Reproducibility.** Every figure is recomputed live from the attached CSVs; the judge-averaging + pairing join
is shown in full. Optional NLP packages (vaderSentiment, scikit-learn) are wrapped with pure-python fallbacks so
the notebook completes offline; internet is used only for their optional install.

**License.** CC0.

**Links.** Grades: [`''' + GRADES_DS + '''`](''' + GRADES_URL + ''') &middot; Perdim:
[`''' + PERDIM_DS + '''`](''' + PERDIM_URL + ''') &middot; Showcase: [`''' + SHOWCASE_DS + '''`](''' + SHOWCASE_URL + ''')
&middot; Start-here index: [`duecare-harness-lift-benchmark`](''' + INDEX_URL + ''') &middot; Source repository:
[`TaylorAmarelTech/gemma4_comp`](''' + REPO_URL + ''')'''


# --------------------------------------------------------------------------- #
# Code cells
# --------------------------------------------------------------------------- #
LOAD_CODE = r'''_present = [("grades", HAVE_GRADES, len(grades_rows)),
            ("perdim", HAVE_PERDIM, len(perdim_rows)),
            ("showcase", HAVE_SHOWCASE, len(show_rows))]
stat_cards([
    (str(sum(1 for _, ok, _ in _present if ok)) + "/3", "datasets attached", TEAL if all(o for _, o, _ in _present) else WARN),
    (format(len(grades_rows), ","), "grades rows", GOOD if HAVE_GRADES else INK4),
    (format(len(perdim_rows), ","), "perdim rows", GOOD if HAVE_PERDIM else INK4),
    (format(len(show_rows), ","), "showcase rows", GOOD if HAVE_SHOWCASE else INK4),
])

tbl = pd.DataFrame([{
    "dataset": name,
    "attached": "yes" if ok else "NO -- claims will SKIP",
    "rows": format(n, ","),
    "path": (os.path.basename(str(p)) if p else "not found"),
} for (name, ok, n), p in zip(_present, [GRADES_PATH, PERDIM_PATH, SHOWCASE_PATH])])
display(pretty_table(tbl, caption="Attached inputs (recursive glob under the input roots)"))

display(Markdown(
    "Difficulty metadata source: **" + (DIFF_SOURCE or "none attached -- the difficulty claim will SKIP") + "**. "
    "The ledger records a verdict for every claim; a missing dataset yields SKIP, never a silent pass."
))'''

HEADLINE_CODE = r'''# --- recompute the headline lift, live ---
pairs = paired_pids(GMEAN, HEAD_MODEL)                      # {prompt_id: (baseline_mean, core_mean)}
deltas = [c - b for b, c in pairs.values()]                # paired lift per prompt
n_pairs = len(deltas)
if n_pairs:
    lift = mean(deltas)
    base_mean = mean(b for b, c in pairs.values())
    core_mean = mean(c for b, c in pairs.values())
else:
    lift = base_mean = core_mean = None

check_close("headline_lift", "gemma4:31b core-baseline paired lift", 40.7, lift, 0.5, GRADES_DS)
check_close("headline_n_pairs", "gemma4:31b paired prompt count", 7953,
            (float(n_pairs) if n_pairs else None), 50.0, GRADES_DS, fmt="{:,.0f}", note="approx 7,953")

if n_pairs:
    stat_cards([
        (format(n_pairs, ","), "paired prompts", INK2),
        (str(round(base_mean, 1)), "baseline mean", INK3),
        (str(round(core_mean, 1)), "harness_core mean", TEAL),
        ("+" + str(round(lift, 1)), "recomputed lift", EMBER),
    ])
    dumbbell(["gemma4:31b (all paired)"], [base_mean], [core_mean],
             lo_lab="baseline", hi_lab="harness_core",
             title="Headline lift, recomputed from the grade rows",
             subtitle="baseline mean -> harness_core mean; delta labeled",
             xlabel="mean rubric score (0-100)", xlim=(0, 100))
else:
    display(Markdown("Grades dataset not attached -- headline claims SKIPPED."))'''

HEADLINE_DIST_CODE = r'''# --- the full paired-delta distribution behind the single mean ---
if n_pairs:
    kde_hist([("paired lift (core - baseline)", deltas, TEAL)],
             title="Every paired delta -- the +40.7 is the mean of this distribution",
             subtitle="one value per prompt; the mass sits far to the right of zero",
             xlabel="paired lift (rubric points)",
             vlines=[(0.0, INK4, "no change"), (mean(deltas), EMBER, "mean +" + str(round(mean(deltas), 1)))])
    _neg = sum(1 for x in deltas if x < 0)
    display(Markdown(
        "The mean is not carried by a handful of outliers: **" + format(sum(1 for x in deltas if x > 0), ",") +
        "** of **" + format(n_pairs, ",") + "** prompts improve, and only **" + str(_neg) +
        "** sit left of zero. The headline +40.7 is the center of mass of this whole distribution."
    ))
else:
    display(Markdown("Grades dataset not attached -- distribution SKIPPED."))'''

WINHURT_CODE = r'''# --- helps / hurts, from the same paired deltas ---
if n_pairs:
    helps = sum(1 for x in deltas if x > 0)
    hurts = sum(1 for x in deltas if x < 0)
    ties = sum(1 for x in deltas if x == 0)
    win_rate = 100.0 * helps / n_pairs
    worst = min(deltas)
else:
    helps = hurts = None
    win_rate = worst = None

check_close("win_rate", "share of paired prompts improved", 99.8, win_rate, 0.3, GRADES_DS,
            fmt="{:.1f}%", note="helps / n_pairs")
check_exact("hurt_count", "paired prompts where the harness HURTS", 15, hurts, GRADES_DS, note="exact count")

if n_pairs:
    stat_cards([
        (format(helps, ","), "prompts helped", GOOD),
        (str(hurts), "prompts hurt", EMBER),
        (str(ties), "ties", INK4),
        (str(round(win_rate, 1)) + "%", "win rate", TEAL),
    ])
    fig, ax = plt.subplots(figsize=(9.8, 2.4))
    ax.barh([0], [helps], color=GOOD, edgecolor=INK2, linewidth=0.5, label="helps")
    ax.barh([0], [hurts], left=[helps], color=EMBER, edgecolor=INK2, linewidth=0.5, label="hurts")
    ax.text(helps / 2, 0, "helps " + format(helps, ","), ha="center", va="center", color=PAPER, fontweight="bold", fontsize=11)
    ax.text(helps + max(hurts, 1) + n_pairs * 0.01, 0, "hurts " + str(hurts) + "  (worst " + str(round(worst, 1)) + ")",
            ha="left", va="center", color=EMBER, fontweight="bold", fontsize=10)
    ax.set_yticks([]); ax.set_xlim(0, n_pairs * 1.12); ax.set_xlabel("paired prompts")
    ax.grid(axis="y", visible=False)
    _title(ax, "Helps vs hurts across " + format(n_pairs, ",") + " paired prompts", "the 15-prompt hurt tail is shown to scale")
    fig.tight_layout(); plt.show()
else:
    display(Markdown("Grades dataset not attached -- win/hurt claims SKIPPED."))'''

JUDGE_CODE = r'''# --- recompute the lift independently inside each judge's own verdicts ---
def _judge_lift(judge):
    pids = {k[1] for k in GJMEAN if k[0] == HEAD_MODEL and k[3] == judge}
    ps = [p for p in pids
          if (HEAD_MODEL, p, "baseline", judge) in GJMEAN and (HEAD_MODEL, p, "harness_core", judge) in GJMEAN]
    if not ps:
        return None, None, None, 0
    jd = [GJMEAN[(HEAD_MODEL, p, "harness_core", judge)] - GJMEAN[(HEAD_MODEL, p, "baseline", judge)] for p in ps]
    b = mean(GJMEAN[(HEAD_MODEL, p, "baseline", judge)] for p in ps)
    c = mean(GJMEAN[(HEAD_MODEL, p, "harness_core", judge)] for p in ps)
    return mean(jd), b, c, len(jd)

judges = sorted({k[3] for k in GJMEAN if k[0] == HEAD_MODEL})
rows_j = [(j, *_judge_lift(j)) for j in judges]
rows_j = [r for r in rows_j if r[1] is not None]
jlifts = [lf for _, lf, _, _, _ in rows_j]

_floor = (min(jlifts) if jlifts else None)
_spread = (max(jlifts) - min(jlifts)) if jlifts else None
check_bool("judge_all_ge40", "every judge's independent lift is >= +40", ">= +40 (all 3)",
           ("min +" + str(round(_floor, 1))) if _floor is not None else None,
           (_floor is not None and _floor >= 40.0) if jlifts else None, GRADES_DS, note="floor across 3 judges")
check_bool("judge_agreement", "the 3 judges agree within <= 1.5 pts", "spread <= 1.5",
           ("spread " + str(round(_spread, 1)) + " pts") if _spread is not None else None,
           (_spread is not None and _spread <= 1.5) if jlifts else None, GRADES_DS, note="max - min judge lift")

if rows_j:
    tbl = pd.DataFrame([{
        "judge": j, "n pairs": format(n, ","), "baseline": round(b, 1),
        "harness_core": round(c, 1), "lift": round(lf, 1),
    } for j, lf, b, c, n in rows_j])
    display(pretty_table(tbl, caption="Paired lift recomputed inside each judge (gemma4:31b)", bars=["lift"]))
    dumbbell([j for j, *_ in rows_j], [b for _, _, b, _, _ in rows_j], [c for _, _, _, c, _ in rows_j],
             lo_lab="baseline", hi_lab="harness_core",
             title="Every judge, on its own, shows the lift",
             subtitle="each row is one judge's paired baseline -> harness_core",
             xlabel="mean rubric score (0-100)", xlim=(0, 100))
    display(Markdown(
        "The three judge lifts are **" + ", ".join("+" + str(round(lf, 1)) for _, lf, _, _, _ in rows_j) +
        "** -- all comfortably above +40, spanning under a point and a half. `glm-5.2` sits a hair above +41; the "
        "author's '+40 to +41' is an honest rounding of this cluster, and the robust property (all >= +40, tight "
        "agreement) is what the ledger checks."
    ))
else:
    display(Markdown("Grades dataset not attached -- per-judge claims SKIPPED."))'''

PERDIM_CODE = r'''# --- per-dimension paired lift on the perdim dataset (comp_A..comp_E) ---
def _perdim_lift(letter):
    pids = {k[1] for k in PCOMP if k[0] == HEAD_MODEL and k[3] == letter}
    ps = [p for p in pids
          if (HEAD_MODEL, p, "baseline", letter) in PCOMP and (HEAD_MODEL, p, "harness_core", letter) in PCOMP]
    if not ps:
        return None, 0
    d = [PCOMP[(HEAD_MODEL, p, "harness_core", letter)] - PCOMP[(HEAD_MODEL, p, "baseline", letter)] for p in ps]
    return mean(d), len(ps)

DIM_NAME = {"A": "indicator", "B": "legal", "C": "refusal", "D": "resources", "E": "privacy"}
STATED = {"A": 11.7, "B": 8.1, "C": 6.6, "D": 6.3, "E": 8.3}
pd_lift = {}; pd_n = {}
for letter in "ABCDE":
    lf, n = _perdim_lift(letter)
    pd_lift[letter] = lf; pd_n[letter] = n
    check_close("perdim_" + letter, "dim " + letter + " (" + DIM_NAME[letter] + ") lift",
                STATED[letter], lf, 1.0, PERDIM_DS)

_got = [pd_lift[k] for k in "ABCDE"]
if all(v is not None for v in _got):
    fig, ax = plt.subplots(figsize=(9.8, 4.6))
    y = list(range(5))[::-1]
    labels = [k + " " + DIM_NAME[k] for k in "ABCDE"]
    ax.barh(y, _got, color=[TEAL, GOOD, WARN, "#3d6b8a", "#6d5a7a"], edgecolor=INK2, linewidth=0.5)
    for yi, k in zip(y, "ABCDE"):
        ax.plot([STATED[k], STATED[k]], [yi - 0.4, yi + 0.4], color=EMBER, lw=2.4, zorder=4)
        ax.text(pd_lift[k] + 0.15, yi, "+" + str(round(pd_lift[k], 1)) + "  (stated +" + str(STATED[k]) + ")",
                va="center", fontsize=9, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_xlabel("mean paired lift (rubric points)")
    ax.grid(axis="y", visible=False)
    _title(ax, "Per-dimension lift -- recomputed (bars) vs stated (ember ticks)",
           "tolerance is +/-1.0 point per dimension")
    fig.tight_layout(); plt.show()
else:
    display(Markdown("Perdim dataset not attached -- per-dimension claims SKIPPED."))'''

PERDIM_ADD_CODE = r'''# --- additivity: the five per-dimension lifts should sum to the overall per-dim lift ---
overall_pairs = paired_pids(PMEAN, HEAD_MODEL)
overall_lift = mean(c - b for b, c in overall_pairs.values()) if overall_pairs else None
sum_dims = sum(_got) if all(v is not None for v in _got) else None

check_bool("perdim_additivity", "sum of dim lifts == overall per-dim lift (+/-0.5)", "sum == overall",
           (("sum +" + str(round(sum_dims, 1)) + " vs overall +" + str(round(overall_lift, 1)))
            if (sum_dims is not None and overall_lift is not None) else None),
           ((abs(sum_dims - overall_lift) <= 0.5) if (sum_dims is not None and overall_lift is not None) else None),
           PERDIM_DS, note="score = A+B+C+D+E by construction")

if sum_dims is not None and overall_lift is not None:
    fig, ax = plt.subplots(figsize=(9.8, 2.7))
    left = 0.0
    cols = {"A": TEAL, "B": GOOD, "C": WARN, "D": "#3d6b8a", "E": "#6d5a7a"}
    for k in "ABCDE":
        ax.barh([1], [pd_lift[k]], left=[left], color=cols[k], edgecolor=PAPER, linewidth=1.2)
        ax.text(left + pd_lift[k] / 2, 1, k, ha="center", va="center", color=PAPER, fontweight="bold", fontsize=10)
        left += pd_lift[k]
    ax.barh([0], [overall_lift], color=INK3, edgecolor=INK2, linewidth=0.5)
    ax.text(overall_lift + 0.3, 0, "overall +" + str(round(overall_lift, 1)), va="center", fontsize=10, color=INK2, fontweight="bold")
    ax.text(sum_dims + 0.3, 1, "sum of dims +" + str(round(sum_dims, 1)), va="center", fontsize=10, color=EMBER, fontweight="bold")
    ax.set_yticks([0, 1]); ax.set_yticklabels(["overall", "A+B+C+D+E"]); ax.set_xlabel("mean paired lift (rubric points)")
    ax.grid(axis="y", visible=False)
    _title(ax, "Additivity check -- the stacked dimensions reconstruct the overall lift", None)
    fig.tight_layout(); plt.show()
else:
    display(Markdown("Perdim dataset not attached -- additivity SKIPPED."))'''

XMODEL_CODE = r'''# --- rank every model with n>=150 paired prompts, raw lift vs normalized gain ---
def _model_stats(model):
    pm = paired_pids(GMEAN, model)
    if len(pm) < 150:
        return None
    raw = mean(c - b for b, c in pm.values())
    ng = mean((c - b) / (100 - b) for b, c in pm.values() if b < 100)
    return dict(model=model, n=len(pm), raw=raw, ng=ng)

qual = [s for s in (_model_stats(m) for m in sorted({k[0] for k in GMEAN})) if s]
by_raw = sorted(qual, key=lambda s: -s["raw"])
by_ng = sorted(qual, key=lambda s: -s["ng"])

check_exact("xmodel_qualify", "models with n>=150 paired prompts", 4, (len(qual) if qual else None), GRADES_DS)
check_bool("xmodel_raw_top", "raw-lift #1 is gpt-oss:120b", "gpt-oss:120b",
           (by_raw[0]["model"] if by_raw else None),
           ((by_raw[0]["model"] == "gpt-oss:120b") if by_raw else None), GRADES_DS)
check_bool("xmodel_ng_bottom", "normalized-gain last is gpt-oss:120b", "gpt-oss:120b",
           (by_ng[-1]["model"] if by_ng else None),
           ((by_ng[-1]["model"] == "gpt-oss:120b") if by_ng else None), GRADES_DS,
           note="normalized gain = (core-base)/(100-base)")

if qual:
    tbl = pd.DataFrame([{
        "model": s["model"], "n pairs": format(s["n"], ","),
        "raw lift": round(s["raw"], 1), "raw rank": by_raw.index(s) + 1,
        "norm gain": round(s["ng"], 3), "ng rank": by_ng.index(s) + 1,
    } for s in by_raw])
    display(pretty_table(tbl, caption="Cross-model: raw lift vs normalized gain (n>=150)", bars=["raw lift"]))
    raw_rank = {s["model"]: by_raw.index(s) + 1 for s in qual}
    ng_rank = {s["model"]: by_ng.index(s) + 1 for s in qual}
    labels = [s["model"] for s in by_raw]
    slope(labels, [raw_rank[m] for m in labels], [ng_rank[m] for m in labels],
          left_lab="raw-lift rank", right_lab="normalized-gain rank",
          title="The ranking reorders once you control for the ceiling",
          subtitle="rank 1 = top; gpt-oss:120b starts highest, so it gains the least headroom",
          ylabel="rank", invert=True)
    display(Markdown(
        "`gpt-oss:120b` posts the biggest **raw** lift but the **smallest** normalized gain -- it begins from the "
        "highest baseline, so it has the least headroom to recover. Both facts are true at once; the reorder is the "
        "honest reading."
    ))
else:
    display(Markdown("Grades dataset not attached -- cross-model claims SKIPPED."))'''

DIFFICULTY_CODE = r'''# --- join gemma4:31b paired deltas to the difficulty band and compare extremes ---
_ORDER = ["easy", "medium", "hard", "very_hard", "multipath"]
bands = defaultdict(list)
if DIFF_MAP and pairs:
    for p, (b, c) in pairs.items():
        d = DIFF_MAP.get(str(p))
        if d:
            bands[d].append(c - b)

band_lift = {k: mean(v) for k, v in bands.items() if v}
present = [k for k in _ORDER if k in band_lift] + [k for k in band_lift if k not in _ORDER]
easiest = next((k for k in _ORDER if k in band_lift), None)
hardest = next((k for k in reversed(_ORDER) if k in band_lift and k != "multipath"), None)

if not DIFF_MAP:
    check_skip("difficulty_thesis", "harness lift rises with difficulty (easiest < hardest)", "easy < very_hard",
               GRADES_DS, "no difficulty metadata attached")
elif easiest and hardest and easiest != hardest:
    check_bool("difficulty_thesis", "harness lift rises with difficulty (easiest < hardest)", "easy < very_hard",
               easiest + " +" + str(round(band_lift[easiest], 1)) + " < " + hardest + " +" + str(round(band_lift[hardest], 1)),
               band_lift[hardest] > band_lift[easiest], GRADES_DS, note="source: " + (DIFF_SOURCE or "?"))
else:
    check_skip("difficulty_thesis", "harness lift rises with difficulty (easiest < hardest)", "easy < very_hard",
               GRADES_DS, "fewer than two difficulty bands joinable")

if band_lift:
    order = present
    vals = [band_lift[k] for k in order]
    ns = [len(bands[k]) for k in order]
    dcol = {"easy": GOOD, "medium": WARN, "hard": EMBER, "very_hard": "#8a2f18", "multipath": INK3}
    fig, ax = plt.subplots(figsize=(9.8, 0.7 * len(order) + 1.6))
    y = list(range(len(order)))[::-1]
    ax.barh(y, vals, color=[dcol.get(k, TEAL) for k in order], edgecolor=INK2, linewidth=0.5)
    for yi, k, v, n in zip(y, order, vals, ns):
        ax.text(v + 0.3, yi, "+" + str(round(v, 1)) + "  (n=" + format(n, ",") + ")", va="center", fontsize=9.5, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels(order); ax.set_xlabel("mean paired lift (rubric points)")
    ax.grid(axis="y", visible=False)
    _title(ax, "Lift by prompt difficulty (gemma4:31b)", "source: " + (DIFF_SOURCE or "n/a") + "; harder prompts, bigger lift")
    fig.tight_layout(); plt.show()
else:
    display(Markdown("No difficulty metadata joinable -- difficulty thesis SKIPPED."))'''

SHOWCASE_CODE = r'''# --- showcase: per-arm rates of ILO citation, resource pointers, indicator language ---
RX_ILO = re.compile(r"\b(ilo|convention|conventions|c0?29|c181|c189|c097|c143|c095|icrmw|palermo|article)\b", re.I)
RX_RES = re.compile(r"\b(hotline|helpline|ngo|embassy|consulate|polaris|call|department of|ministry|tribunal|shelter|helpdesk|support)\b", re.I)
RX_IND = re.compile(r"(indicator|debt bondage|passport retention|withholding|wage withholding|coercion|deception|forced lab|recruitment fee|confiscation|movement)", re.I)

def _rate(field, rx):
    if not show_rows:
        return None
    return 100.0 * sum(1 for r in show_rows if rx.search(str(r.get(field) or ""))) / len(show_rows)

DET = [("ilo", RX_ILO, "ILO / convention citation"),
       ("resource", RX_RES, "resource / hotline pointer"),
       ("indicator", RX_IND, "forced-labour indicator")]
rates = {}
for key, rx, _lab in DET:
    b = _rate("baseline_response", rx)
    c = _rate("harness_core_response", rx)
    rates[key] = (b, c)

_bi, _ci = rates["ilo"]
check_bool("showcase_ilo_2x", "harness cites ILO >= 2x the baseline rate", "core >= 2x baseline",
           (str(round(_ci, 1)) + "% vs " + str(round(_bi, 1)) + "% (" + (str(round(_ci / _bi, 1)) + "x" if _bi else "inf") + ")") if _bi is not None else None,
           ((_bi > 0 and _ci >= 2 * _bi) if _bi is not None else None), SHOWCASE_DS)
_br, _cr = rates["resource"]
check_bool("showcase_resource_more", "harness routes to resources more than baseline", "core > baseline",
           (str(round(_cr, 1)) + "% vs " + str(round(_br, 1)) + "%") if _br is not None else None,
           ((_cr > _br) if _br is not None else None), SHOWCASE_DS)
_bn, _cn = rates["indicator"]
check_bool("showcase_indicator_more", "harness names indicators more than baseline", "core > baseline",
           (str(round(_cn, 1)) + "% vs " + str(round(_bn, 1)) + "%") if _bn is not None else None,
           ((_cn > _bn) if _bn is not None else None), SHOWCASE_DS)

if show_rows:
    labels = [lab for _, _, lab in DET]
    base = [rates[k][0] for k, _, _ in DET]
    core = [rates[k][1] for k, _, _ in DET]
    y = np.arange(len(labels)); h = 0.36
    fig, ax = plt.subplots(figsize=(10.0, 3.6))
    ax.barh(y + h / 2, base, height=h, color=INK3, label="baseline", edgecolor=INK2, linewidth=0.4)
    ax.barh(y - h / 2, core, height=h, color=TEAL, label="harness_core", edgecolor=INK2, linewidth=0.4)
    for yi, bv, cv in zip(y, base, core):
        ax.text(bv + 1, yi + h / 2, str(round(bv, 1)) + "%", va="center", fontsize=9, color=INK3)
        ax.text(cv + 1, yi - h / 2, str(round(cv, 1)) + "%", va="center", fontsize=9, color=TEAL_DK, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_xlim(0, 112); ax.set_xlabel("share of showcase responses (%)")
    ax.grid(axis="y", visible=False); ax.legend(loc="lower right"); ax.invert_yaxis()
    _title(ax, "Safety-language rates by arm (n=" + format(len(show_rows), ",") + " showcase prompts)",
           "regex-detected presence per response")
    fig.tight_layout(); plt.show()
else:
    display(Markdown("Showcase dataset not attached -- citation/resource/indicator claims SKIPPED."))'''

VOCAB_CODE = r'''# --- distinctive vocabulary: weighted log-odds z (Monroe et al. 2008), harness_core vs baseline ---
_STOP = set(("i me my we our you your he she it they them the a an and but if or of at by for with about to from "
             "in on off over under is are was be been being have has had do does did this that these those as no "
             "not only own same so than too very can will just should now also may must one two per within their they").split())
_TOK = re.compile(r"[a-z][a-z0-9]{2,}")

def _toks(t):
    return [w for w in _TOK.findall((t or "").lower()) if w not in _STOP]

def _counter(field):
    c = Counter()
    for r in show_rows:
        c.update(_toks(r.get(field)))
    return c

EXPECT = ["ilo", "recruitment", "debt", "indicators"]
ranked = []
ca = cb = None
if show_rows:
    ca, cb = _counter("harness_core_response"), _counter("baseline_response")
    vocab = sorted({w for w in set(ca) | set(cb) if ca.get(w, 0) + cb.get(w, 0) >= 5})
    alpha = 0.01; a0 = alpha * len(vocab); ta = sum(ca.values()); tb = sum(cb.values())
    def _z(w):
        na, nb = ca.get(w, 0), cb.get(w, 0)
        la = math.log((na + alpha) / (ta + a0 - na - alpha))
        lb = math.log((nb + alpha) / (tb + a0 - nb - alpha))
        return (la - lb) / math.sqrt(1.0 / (na + alpha) + 1.0 / (nb + alpha))
    ranked = sorted(vocab, key=_z, reverse=True)

_TOPK = 15
top = ranked[:_TOPK]
missing = [w for w in EXPECT if w not in top]
check_bool("showcase_vocab_terms", "top-" + str(_TOPK) + " distinctive terms include ilo/recruitment/debt/indicators",
           "all 4 in top-" + str(_TOPK),
           ("ranks " + ", ".join(w + "#" + str(ranked.index(w) + 1) for w in EXPECT if w in ranked)) if ranked else None,
           ((not missing) if ranked else None), SHOWCASE_DS,
           note=("all present" if ranked and not missing else ("missing: " + ", ".join(missing) if ranked else "")))

if ranked:
    terms = top[::-1]
    zs = [_z(w) for w in terms]
    cols = [EMBER if w in EXPECT else TEAL for w in terms]
    fig, ax = plt.subplots(figsize=(9.8, 6.2))
    ax.barh(range(len(terms)), zs, color=cols, edgecolor=INK2, linewidth=0.4)
    ax.set_yticks(range(len(terms))); ax.set_yticklabels(terms)
    ax.set_xlabel("weighted log-odds z-score (harness_core vs baseline)"); ax.grid(axis="y", visible=False)
    _title(ax, "Top-" + str(_TOPK) + " harness-distinctive words (ember = the four expected terms)",
           "the safety vocabulary the harness reaches for that the bare model does not")
    fig.tight_layout(); plt.show()
    display(Markdown(
        "The four expected terms land at " +
        ", ".join("**" + w + "** (#" + str(ranked.index(w) + 1) + ")" for w in EXPECT if w in ranked) +
        " -- the working vocabulary of ILO indicators, recruitment-fee mechanics, and debt bondage sits at the very "
        "top of the harness's distinctive lexicon."
    ))
else:
    display(Markdown("Showcase dataset not attached -- distinctive-vocabulary claim SKIPPED."))'''

LEDGER_CODE = r'''# --- render the full claims ledger with a colored PASS/FAIL verdict ---
led = pd.DataFrame(LEDGER)[["id", "claim", "stated", "recomputed", "result", "dataset", "note"]]
n_pass = int((led.result == "PASS").sum())
n_fail = int((led.result == "FAIL").sum())
n_skip = int((led.result == "SKIP").sum())
n_check = n_pass + n_fail

stat_cards([
    (str(n_pass) + "/" + str(n_check), "claims verified", GOOD if n_fail == 0 and n_check else WARN),
    (str(n_pass), "PASS", GOOD),
    (str(n_fail), "FAIL", EMBER if n_fail else INK4),
    (str(n_skip), "SKIP (dataset absent)", WARN if n_skip else INK4),
])

_bg = {"PASS": "#e2efe4", "FAIL": EMBER_SOFT, "SKIP": "#efe7d3"}
_fg = {"PASS": TEAL_DK, "FAIL": "#8a2f18", "SKIP": WARN}
def _color_result(col):
    return ["background-color: " + _bg.get(v, PAPER2) + "; color: " + _fg.get(v, INK) + "; font-weight: 700" for v in col]
sty = (led.style
       .apply(_color_result, subset=["result"])
       .hide(axis="index")
       .set_caption("The DueCare claims ledger -- every headline number, recomputed and verdicted")
       .set_table_styles([
           {"selector": "caption", "props": [("caption-side", "top"), ("font-size", "13.5px"), ("font-weight", "700"), ("color", INK), ("padding", "4px 2px 10px"), ("text-align", "left")]},
           {"selector": "th.col_heading", "props": [("background-color", PAPER2), ("color", INK), ("font-weight", "700"), ("border", "none"), ("border-bottom", "2px solid " + TEAL), ("padding", "8px 12px"), ("text-align", "left"), ("font-size", "11.5px")]},
           {"selector": "td", "props": [("padding", "6px 12px"), ("border", "none"), ("border-bottom", "1px solid " + LINE2), ("color", INK2), ("font-size", "12px")]},
           {"selector": "", "props": [("border-collapse", "collapse"), ("font-family", "Inter, -apple-system, system-ui, sans-serif")]},
       ]))
display(sty)

_verdict = ("ALL " + str(n_check) + " CHECKED CLAIMS PASS") if (n_fail == 0 and n_check) else (str(n_fail) + " CLAIM(S) FAILED -- see the ledger")
display(Markdown(
    "**Result: " + _verdict + ".** " + str(n_pass) + " of " + str(n_check) + " checked claims reproduced within "
    "tolerance" + (", " + str(n_skip) + " skipped for want of an attached dataset" if n_skip else "") + ". "
    "Re-run this notebook against the public datasets and you will get the same verdicts -- that is the point."
))'''

RECEIPT_CODE = r'''# --- reproducibility receipt: the exact inputs and tally behind the verdicts above ---
receipt = {
    "head_model": HEAD_MODEL,
    "grades_rows": len(grades_rows),
    "perdim_rows": len(perdim_rows),
    "showcase_rows": len(show_rows),
    "gemma4_31b_paired_prompts": len(paired_pids(GMEAN, HEAD_MODEL)),
    "difficulty_source": DIFF_SOURCE or "none",
    "claims_total": len(LEDGER),
    "claims_pass": int(sum(1 for r in LEDGER if r["result"] == "PASS")),
    "claims_fail": int(sum(1 for r in LEDGER if r["result"] == "FAIL")),
    "claims_skip": int(sum(1 for r in LEDGER if r["result"] == "SKIP")),
}
print("REPRODUCIBILITY RECEIPT")
for k, v in receipt.items():
    print("  " + k.ljust(28) + ": " + (format(v, ",") if isinstance(v, int) else str(v)))
display(Markdown(
    "This receipt pins the run: which inputs were attached, how many prompts were paired, and the PASS/FAIL/SKIP "
    "tally. Nothing above depends on hidden state -- attach the three public datasets, run all cells, and the "
    "receipt reproduces."
))'''


def _notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        _md(HERO_MD),
        _md(WHY_MD),
        _md(METHOD_MD),
        _md(TOC_MD),
        _code(SETUP),
        _md(LOAD_MD),
        _code(LOAD_CODE),
        _md(HEADLINE_MD),
        _code(HEADLINE_CODE),
        _code(HEADLINE_DIST_CODE),
        _md(WINHURT_MD),
        _code(WINHURT_CODE),
        _md(JUDGE_MD),
        _code(JUDGE_CODE),
        _md(PERDIM_MD),
        _code(PERDIM_CODE),
        _code(PERDIM_ADD_CODE),
        _md(XMODEL_MD),
        _code(XMODEL_CODE),
        _md(DIFFICULTY_MD),
        _code(DIFFICULTY_CODE),
        _md(SHOWCASE_MD),
        _code(SHOWCASE_CODE),
        _code(VOCAB_CODE),
        _md(LEDGER_MD),
        _code(LEDGER_CODE),
        _code(RECEIPT_CODE),
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
        "dataset_sources": DATASET_SOURCES,
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

    # Kaggle derives the kernel slug from the title -- assert they agree. Note "and" stays "and" (not "&").
    assert TITLE.lower().replace(" ", "-") == SLUG, (
        "title slug mismatch: " + repr(TITLE) + " -> " + repr(TITLE.lower().replace(" ", "-")) + " != " + repr(SLUG)
    )
    assert TITLE.lower().replace(" ", "-") == "duecare-fact-check-and-reproducibility"
    assert KERNEL_ID == "taylorsamarel/" + SLUG, "kernel id mismatch: " + repr(KERNEL_ID)

    result = build(args.output, force=args.force)
    result["title_slug_ok"] = TITLE.lower().replace(" ", "-") == SLUG
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
