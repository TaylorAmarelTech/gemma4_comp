#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare chain-of-thought *analysis* notebook: how the SAME situation is reasoned differently across perspectives, and the shared reasoning-axis structure.

This is the ANALYSIS angle (distinct from the separate "CoT Reasoning Explorer" overview
notebook). It reads the published `duecare-cot-reasoning` dataset (`cot_train.jsonl`) and
renders real matplotlib charts + Markdown, all from the data: the WHO x WHAT reasoning space
(category x situation heatmap), a "one situation, many minds" side-by-side of how different
perspectives reach different grounded safe actions on the *same* case, the reach x direction
reasoning axes, per-category perspective coverage, and the shared ~102-step reasoning skeleton
(every chain screens all 11 ILO indicators, maps the actors, walks the migration lifecycle).
CPU only, no model, no internet: it runs to completion on Kaggle and is verifiable.

    python scripts/build_cot_analysis_notebook.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _notebook_viz import HELPERS, PALETTE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "cot_analysis"
KERNEL_ID = "taylorsamarel/duecare-cot-reasoning-analysis"
TITLE = "DueCare CoT Reasoning Analysis"
DATASET_ID = "taylorsamarel/duecare-cot-reasoning"
DS = f"https://www.kaggle.com/datasets/{DATASET_ID}"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"
BENCH_DS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades"

DATALOAD = '''import glob, os, json, re
from IPython.display import Markdown, display

pd.set_option("display.max_colwidth", None)

# --- Load the chain-of-thought corpus by RECURSIVE glob (never hardcode the mount path) ---
print("mounted under /kaggle/input:", os.listdir("/kaggle/input") if os.path.exists("/kaggle/input") else "none")
fs = glob.glob("/kaggle/input/**/cot_train.jsonl", recursive=True)
if not fs:
    raise SystemExit("attach the dataset taylorsamarel/duecare-cot-reasoning (cot_train.jsonl not found)")
ROWS = [json.loads(l) for l in open(sorted(fs)[0], encoding="utf-8")]

FIELDS = ["perspective", "perspective_label", "category", "situation", "ilo_indicator",
          "reach", "direction", "step_count", "lineage_id", "lineage_family_id", "split"]
df = pd.DataFrame([{k: r.get(k) for k in FIELDS} for r in ROWS])

def assistant_text(row):
    """Return the assistant chain-of-thought text of a row."""
    return next((m["content"] for m in row["messages"] if m["role"] == "assistant"), "")

def user_text(row):
    """Return the user prompt text of a row."""
    return next((m["content"] for m in row["messages"] if m["role"] == "user"), "")

def parse_steps(text):
    """Parse a chain into {step_number: step_text}. Robust to punctuation / em-dashes."""
    out = {}
    for ln in text.split("\\n"):
        m = re.match(r"^\\s*(\\d+)\\.\\s+(.*)$", ln)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out

def phase_blocks(st):
    """Partition a parsed chain into its shared, ordered reasoning phases (anchored on step text)."""
    def first(pred, default):
        for i in sorted(st):
            if pred(st[i].lower()):
                return i
        return default
    n = max(st) if st else 0
    bounds = [
        ("1 - Fix the perspective (WHO reasons)", 1),
        ("2 - Set the reasoning axes (reach + direction)", 3),
        ("3 - Restate the situation + ILO hypothesis", 5),
        ("4 - Weigh every evidence state", first(lambda s: "evidence state" in s, 7)),
        ("5 - Map the actors and their leverage", first(lambda s: "actor map" in s, 15)),
        ("6 - Screen all 11 ILO indicators", first(lambda s: s.startswith("screen ilo indicator"), 31)),
        ("7 - Place across the migration lifecycle", first(lambda s: "place the situation against" in s, 64)),
        ("8 - Check the governing legal framework", first(lambda s: "which framework and effective date" in s, 78)),
        ("9 - Stress-test with counterfactuals", first(lambda s: s.startswith("counterfactual"), 87)),
        ("10 - Choose the safe, reversible action", first(lambda s: "options open to" in s, 92)),
        ("11 - Verify sources, log provenance, close", first(lambda s: "verified against a primary source" in s, 97)),
    ]
    out = []
    for k, (name, start) in enumerate(bounds):
        end = bounds[k + 1][1] - 1 if k + 1 < len(bounds) else n
        out.append((name, int(start), int(end), int(end - start + 1)))
    return out

print(f"loaded {len(df):,} chains | {df.perspective.nunique()} perspectives | "
      f"{df.category.nunique()} role categories | {df.situation.nunique()} situations | "
      f"reach {sorted(df.reach.unique())} | direction {sorted(df.direction.unique())}")'''

# The notebook's first code cell embeds the shared toolkit (theme + KPI tiles +
# styled tables + heatmap + density plots) ahead of the data load and helpers.
SETUP = PALETTE + "\n" + HELPERS + "\n" + DATALOAD

GLANCE = '''# An honest, compact summary of what the file actually contains.
stat_cards([(str(df.perspective.nunique()), "perspectives (WHO)", TEAL),
            (str(df.category.nunique()), "role categories", INK2),
            (str(df.situation.nunique()), "ILO situations (WHAT)", GOOD),
            (f"{len(df):,}", "reasoning chains", EMBER)])
census = pd.DataFrame({
    "Property": ["chains (rows)", "distinct perspectives (WHO)", "role categories", "situations (ILO patterns)",
                 "reach x direction axes", "steps per chain", "license"],
    "Value": [f"{len(df):,}", str(df.perspective.nunique()), str(df.category.nunique()), str(df.situation.nunique()),
              str(df.reach.nunique() * df.direction.nunique()),
              f"{df.step_count.min()}-{df.step_count.max()} (constant)", "MIT (synthetic / propose-only)"],
})
display(pretty_table(census, caption="What is in the file -- counted live from the attached rows"))
print("Every chain is one CELL of a grid:  WHO (perspective)  x  WHAT (ILO situation)  x  reach  x  direction.")'''

SPACE = '''# The reasoning space: role category (WHO, rows) x situation (WHAT, cols). Each cell is a count of chains.
ct = pd.crosstab(df.category, df.situation)
ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index]      # busiest roles on top
heatmap(ct.values, [r.replace("_", " ") for r in ct.index], [c.replace("_", "\\n") for c in ct.columns],
        title="The corpus crosses WHO x WHAT -- every role category reasons about every ILO situation",
        subtitle="rows = role category (who reasons); cols = situation (ILO indicator pattern); cell = chains",
        fmt=".0f", cmap="YlGnBu", cbar_label="chains")
print(f"crosstab shape: {ct.shape[0]} categories x {ct.shape[1]} situations - "
      f"every cell is populated: {int((ct.values > 0).all())==1}")'''

MINDS = '''# THE CENTERPIECE: one situation, reasoned by different minds. Hold the situation AND the
# reasoning axes fixed, and vary ONLY the perspective - so the difference is purely about WHO reasons.
SIT, REACH, DIR = "debt_bondage", "small_jump", "inward"
pool = [r for r in ROWS if r["situation"] == SIT and r["reach"] == REACH and r["direction"] == DIR]

picks, seen_cat, seen_p = [], set(), set()
for r in sorted(pool, key=lambda r: (r["category"], r["perspective"])):
    if r["category"] in seen_cat or r["perspective"] in seen_p:
        continue
    picks.append(r); seen_cat.add(r["category"]); seen_p.add(r["perspective"])
    if len(picks) == 4:
        break

shared_frame = parse_steps(assistant_text(picks[0])).get(5, "")   # step 5 is the neutral situation restatement (identical across minds)
md = [f"### One case, {len(picks)} minds\\n",
      f"**Situation** `{SIT}` &nbsp;|&nbsp; **reach** `{REACH}` &nbsp;|&nbsp; **direction** `{DIR}` "
      f"&nbsp;-&nbsp; *held constant, so only the perspective changes.*\\n",
      f"> **The shared case (same for every mind):** {shared_frame}\\n",
      "Each perspective runs the *same* 102-step skeleton but lands on a **different, role-appropriate safe action** and a **different boundary** - it never steps outside what that role can actually do:\\n"]
for r in picks:
    st = parse_steps(assistant_text(r))
    md.append(
        f"\\n#### {r['perspective_label']}  &nbsp;<span style='color:{INK3}'>({r['category']})</span>\\n"
        f"- **Frames it as (step 1):** {st.get(1, '')}\\n"
        f"- **Its safe action (step 95):** {st.get(95, '')}\\n"
        f"- **What it will _not_ do (step 96):** {st.get(96, '')}\\n")
display(Markdown("\\n".join(md)))'''

MINDS_TABLE = '''# One perspective per ROLE CATEGORY: each role reaches a different, role-appropriate safe action
# on the SAME situation + axes. (The framing in step 1 is set per perspective; the safe action in
# step 95 is set per role - so the nine categories give nine distinct safe actions on one case.)
bycat = {}
for r in pool:
    bycat.setdefault(r["category"], []).append(r)
rows_tbl = []
for cat in sorted(bycat):
    r = sorted(bycat[cat], key=lambda x: x["perspective_label"])[0]
    st = parse_steps(assistant_text(r))
    rows_tbl.append({"role category": cat, "example perspective (WHO)": r["perspective_label"],
                     "its role-appropriate safe action (step 95)": st.get(95, "")})
tbl = pd.DataFrame(rows_tbl)
SA_COL = "its role-appropriate safe action (step 95)"
n_distinct = tbl[SA_COL].nunique()
print(f"{len(pool)} perspectives across {len(bycat)} role categories reason about {SIT} at ({REACH}, {DIR}); "
      f"the {len(bycat)} categories reach {n_distinct} distinct safe actions - the action is tailored to the role.")
display(pretty_table(tbl, caption=f"One case ({SIT}, {REACH}, {DIR}) -- {len(bycat)} roles, {n_distinct} role-appropriate safe actions"))'''

AXES = '''# The two reasoning axes every chain carries, beyond WHO and WHAT.
rd = pd.crosstab(df.reach, df.direction).reindex(index=["small_jump", "large_jump"], columns=["inward", "outward"])
heatmap(rd.values, ["small_jump", "large_jump"], ["inward", "outward"],
        title="Reasoning axes are fully crossed -- every (reach x direction) quadrant is balanced",
        subtitle="rows = reach; cols = direction; cell = chains",
        fmt=".0f", cmap="BuGn", cbar_label="chains")
print("balanced 2x2:\\n" + rd.to_string())'''

COVERAGE = '''# Per-category coverage: how many DISTINCT perspectives and how many chains each role category carries.
cov = (df.groupby("category")
         .agg(perspectives=("perspective", "nunique"), chains=("perspective", "size"))
         .sort_values("chains"))
fig, axes = plt.subplots(1, 2, figsize=(13.2, 4.8), sharey=True)
y = np.arange(len(cov))
axes[0].barh(y, cov.chains.values, color=TEAL, edgecolor=PAPER)
for i, v in enumerate(cov.chains.values):
    axes[0].text(v, i, f" {v}", va="center", fontsize=9, color=INK3)
axes[0].set_yticks(y); axes[0].set_yticklabels(cov.index, fontsize=9.5)
axes[0].set_title("chains per role category"); axes[0].set_xlabel("chains"); axes[0].grid(axis="y", alpha=0)
axes[1].barh(y, cov.perspectives.values, color=GOOD, edgecolor=PAPER)
for i, v in enumerate(cov.perspectives.values):
    axes[1].text(v, i, f" {v}", va="center", fontsize=9, color=INK3)
axes[1].set_title("distinct perspectives per category"); axes[1].set_xlabel("distinct perspectives"); axes[1].grid(axis="y", alpha=0)
fig.suptitle("Coverage across the 9 role categories - many minds per role", fontsize=13, fontweight="bold", y=1.02)
fig.tight_layout(); plt.show()
cov_tbl = (cov.reset_index().rename(columns={"category": "role category"})[["role category", "perspectives", "chains"]]
             .sort_values("chains", ascending=False).reset_index(drop=True))
display(pretty_table(cov_tbl, caption="Coverage per role category -- distinct minds and chains per role",
                     bars=["chains"], gradient=["perspectives"], cmap="BuGn"))'''

STRUCTURE = '''# The shared skeleton. First, confirm the constant scaffold holds across ALL chains, not just one.
def _count(st, pred):
    return sum(pred(s.lower()) for s in st.values())
recs = []
for r in ROWS:
    st = parse_steps(assistant_text(r))
    recs.append((len(st),
                 _count(st, lambda s: s.startswith("screen ilo indicator")),
                 _count(st, lambda s: "evidence state" in s),
                 _count(st, lambda s: "place the situation against" in s),
                 _count(st, lambda s: s.startswith("counterfactual"))))
sk = pd.DataFrame(recs, columns=["steps", "ilo_screens", "evidence_states", "lifecycle_stages", "counterfactuals"])
uniq = {c: sorted(sk[c].unique()) for c in sk.columns}
print("Across all", f"{len(sk):,}", "chains, each of these is CONSTANT (one shared reasoning contract):")
for c in sk.columns:
    vals = uniq[c]
    print(f"  - {c:<18}: {vals[0] if len(vals)==1 else vals}")

# The anatomy of one 102-step chain: how the steps split across the ordered phases.
blocks = phase_blocks(parse_steps(assistant_text(ROWS[0])))
names = [b[0] for b in blocks][::-1]; sizes = [b[3] for b in blocks][::-1]; spans = [f"{b[1]}-{b[2]}" for b in blocks][::-1]
cmap = plt.get_cmap("YlGnBu"); colors = [cmap(v) for v in np.linspace(0.30, 0.90, len(names))]
fig, ax = plt.subplots(figsize=(10.2, 5.6))
bars = ax.barh(range(len(names)), sizes, color=colors, edgecolor=PAPER)
for i, (v, sp) in enumerate(zip(sizes, spans)):
    ax.text(v + 0.3, i, f" {v} steps  (#{sp})", va="center", fontsize=9, color=INK3)
ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=9.5)
ax.set_xlim(0, max(sizes) * 1.35); ax.set_xlabel("steps in phase")
ax.set_title(f"Anatomy of every {int(df.step_count.iloc[0])}-step chain - one shared reasoning skeleton"); ax.grid(axis="y", alpha=0)
fig.tight_layout(); plt.show()'''

STRUCTURE_TABLE = '''# The skeleton as a table: what each phase does, and how many steps it spends.
skel = pd.DataFrame([(b[0], f"{b[1]}-{b[2]}", b[3]) for b in blocks],
                    columns=["phase", "steps", "# steps"])
display(pretty_table(skel, caption="The shared reasoning skeleton -- ordered phases every chain walks",
                     bars=["# steps"]))
print("Phases 6 (11 ILO indicators) and 7 (7 lifecycle stages) are the same screen every time - "
      "the model learns to always test the full indicator set and place the case in the migration lifecycle, "
      "then adapt only the safe action to WHO is reasoning.")'''


def _toc() -> str:
    items = [
        ("0", "What is in the dataset", "glance"),
        ("1", "The reasoning space (WHO x WHAT)", "space"),
        ("2", "One situation, many minds", "minds"),
        ("3", "The reasoning axes (reach x direction)", "axes"),
        ("4", "Perspective coverage", "coverage"),
        ("5", "The shared 102-step skeleton", "structure"),
        ("6", "What this proves - and does not", "boundary"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c: list = []

    c.append(md(
        "# One case, many minds: how DueCare teaches a model to *situate* its reasoning\n\n"
        "A trafficking indicator does not mean the same thing to a construction worker, an immigration "
        "officer, an NGO caseworker, and a worker's spouse back home. This dataset teaches a model to "
        "reason about the **same situation from over 100 different perspectives** - crossing **who** is "
        "reasoning (perspective) x **what** ILO pattern is in play (situation) x **how far** the inference "
        "reaches (reach) x **which way** it moves (direction). Every chain runs the *same* ~102-step "
        "reasoning skeleton, but lands on a **different, role-appropriate safe action**.\n\n"
        "This notebook is the **analysis** angle: not a tour of one sample, but *how the reasoning differs "
        "across minds* and *what structure is shared*. Everything below is computed **live** from the public "
        f"[`{DATASET_ID.split('/')[1]}`]({DS}) dataset - CPU only, no model, no internet - so every figure is verifiable.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** These are **illustrative** reasoning chains, grounded in real "
        "ILO forced-labour indicator patterns but built from **synthetic / composite** situations - *silver* "
        "labels, **propose-only**, **not** field detection and **not** advice about any real person or case. "
        "No real name, number, address, or case appears anywhere. License: MIT."))
    c.append(md(
        "### The grid, in one paragraph\n"
        "Each row is one **cell of a grid**. `perspective` / `perspective_label` is **who** reasons "
        "(e.g. *construction worker*, *immigration officer*, *NGO caseworker*), bucketed into 9 `category` "
        "roles. `situation` / `ilo_indicator` is **what** pattern is present (debt bondage, contract "
        "substitution, passport retention, wage withholding, movement control). `reach` "
        "(*small_jump* / *large_jump*) and `direction` (*inward* / *outward*) are two **reasoning axes**. "
        "`step_count` is the length of the chain (a constant ~102). The whole point of the corpus is to "
        "cross these so a model learns to *adapt its reasoning to who is asking and what is in front of them*."))

    c.append(md('<a id="glance"></a>\n## 0 - What is in the dataset'))
    c.append(code(SETUP))
    c.append(code(GLANCE))

    c.append(md('<a id="space"></a>\n## 1 - The reasoning space (WHO x WHAT)\n'
                "The corpus is a grid. This heatmap counts chains for every **role category** (who) against "
                "every **situation** (what) - the point is that the corpus *crosses* them, so no role is "
                "trained on only one kind of case and no case is seen from only one kind of mind."))
    c.append(code(SPACE))

    c.append(md('<a id="minds"></a>\n## 2 - One situation, many minds  *(the centerpiece)*\n'
                "Here is the core idea made concrete. We hold the **situation** fixed (`debt_bondage`) *and* "
                "both reasoning axes fixed (`small_jump`, `inward`), then pull four rows from four different "
                "role categories. The only thing that changes is **who is reasoning** - and each mind runs "
                "the same skeleton to a **different, grounded safe action** and a **different boundary**."))
    c.append(code(MINDS))
    c.append(md("The four above are just a slice, and they hint at a two-level structure: the **framing** "
                "(step 1) is worded per **perspective** - each of the dozens of minds phrases it its own way - "
                "while the **safe action** (step 95) is set per **role category**, because what you can safely "
                "*do* depends on your role. So the same case yields one distinct, role-appropriate safe action "
                "per category. All nine roles at a glance:"))
    c.append(code(MINDS_TABLE))

    c.append(md('<a id="axes"></a>\n## 3 - The reasoning axes (reach x direction)\n'
                "Beyond who and what, every chain declares **how** it reasons on two axes, and the corpus is "
                "balanced across all four quadrants:\n\n"
                "| axis | value | meaning |\n|---|---|---|\n"
                "| **reach** | `small_jump` | stay one inference from the record; prefer the conservative reading, name what more is needed |\n"
                "| **reach** | `large_jump` | reach further across the corridor pattern, while flagging the added assumptions |\n"
                "| **direction** | `inward` | start from the corridor-level pattern and narrow to this specific worker |\n"
                "| **direction** | `outward` | start from the specific record and widen to the systemic pattern |\n\n"
                "Crossing reach x direction gives four reasoning stances on the same facts - a model trained on "
                "all four learns to say *how sure* it is and *which way* it is generalizing."))
    c.append(code(AXES))

    c.append(md('<a id="coverage"></a>\n## 4 - Perspective coverage\n'
                "How many distinct minds and how many chains each of the 9 role categories carries. The "
                "*affected worker*, *supply chain*, and *frontline support* roles are the deepest, but every "
                "category carries many distinct perspectives - the corpus is broad, not a handful of voices repeated."))
    c.append(code(COVERAGE))

    c.append(md('<a id="structure"></a>\n## 5 - The shared 102-step skeleton\n'
                "If every mind reasons differently, what makes it *one* dataset? A shared **reasoning "
                "contract**. First we confirm the scaffold is constant across all chains; then we show the "
                "anatomy of a single chain - the ordered phases every perspective walks before it acts."))
    c.append(code(STRUCTURE))
    c.append(code(STRUCTURE_TABLE))

    c.append(md(
        '<a id="boundary"></a>\n## 6 - What this proves - and what it does not\n\n'
        "**What it shows.** A model fine-tuned on this corpus is taught to *situate* its reasoning: to fix "
        "**who** it is speaking as, hold a **role boundary**, test the full **11-indicator** ILO set and the "
        "**migration lifecycle** as hypotheses rather than conclusions, weigh what the record does and does "
        "not establish, and end on the **smallest reversible safe action** for that specific role - naming "
        "explicitly what it will *not* do and to whom that part is referred.\n\n"
        "**What it does not show.** These are **synthetic / composite** situations with **silver** labels - "
        "illustrative reasoning grounded in real ILO indicator patterns, **not** real-world detection, **not** "
        "legal advice, and **not** a claim about any real person or case. The chains are **propose-only** "
        "material for teaching reasoning structure; volatile facts (hotlines, fee caps, current statutes) "
        "belong in tools and retrieval, never memorized.\n\n"
        "### Use the data\n"
        f"- **Fine-tune for situated reasoning:** each row is a ready SFT example (user prompt -> ~102-step chain) tagged with perspective, situation, reach, and direction.\n"
        f"- **Measure the payoff:** the separate [`duecare-harness-benchmark-grades`]({BENCH_DS}) dataset scores whether this kind of grounding actually lifts a model's answers.\n"
        f"- **Read the harness:** the [source repository]({REPO}) has the perspective taxonomy, the ILO indicator rules, and the generator that produced these chains.\n\n"
        "License: MIT. Illustrative synthetic reasoning only - no PII, no real cases."))

    nb = nbf.v4.new_notebook()
    nb["cells"] = c
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                      "language_info": {"name": "python"}}
    nbf.write(nb, str(nb_dir / "notebook.ipynb"))

    meta = {"id": KERNEL_ID, "title": TITLE, "code_file": "notebook.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": False, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": [DATASET_ID], "competition_sources": [], "kernel_sources": []}
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"kernel_id": KERNEL_ID, "cells": len(c), "notebook_dir": str(nb_dir)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    summary = build(args.output, force=args.force)
    slug = summary["kernel_id"].split("/", 1)[1]
    assert "DueCare CoT Reasoning Analysis".lower().replace(" ", "-") == "duecare-cot-reasoning-analysis"
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
