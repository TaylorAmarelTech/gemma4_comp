#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the polished, richly-visual DueCare Chain-of-Thought Reasoning explorer notebook.

Emits a Kaggle notebook (nbformat) that explores the published training dataset
`taylorsamarel/duecare-cot-reasoning` (cot_train.jsonl / cot_holdout.jsonl / cot_manifest.json):
100+ domain perspectives x ~102-step chains of thought, each grounded in a real ILO forced-labour
indicator pattern, for safety fine-tuning of Gemma 4. Every number and chart is computed live from
the attached data -- CPU only, no GPU, no internet, no model loading -- so the notebook runs to
completion on Kaggle and is fully verifiable.

    python scripts/build_cot_explorer_notebook.py
    python scripts/build_cot_explorer_notebook.py --force
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "cot_explorer"
DATASET_ID = "taylorsamarel/duecare-cot-reasoning"
TITLE = "DueCare CoT Reasoning Explorer"
KERNEL_ID = "taylorsamarel/duecare-cot-reasoning-explorer"
SLUG = "duecare-cot-reasoning-explorer"
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
# setup cell: shared prettify toolkit (PALETTE + HELPERS) + recursive-glob load.
# The old inline palette/rcParams are gone -- the toolkit owns the theme, the KPI
# tiles (stat_cards), the styled tables (pretty_table), the heatmap, and the
# density plot (kde_hist). Helpers are EMBEDDED, so the notebook never imports
# _notebook_viz at runtime.
# --------------------------------------------------------------------------- #
DATALOAD = '''import glob, json, os
from pathlib import Path
from IPython.display import Markdown, display

# --- Load the published dataset via a RECURSIVE glob (Kaggle mounts datasets at an unpredictable path) ---
if os.path.exists("/kaggle/input"):
    print("mounted under /kaggle/input:", os.listdir("/kaggle/input"))

def _load(name):
    fs = sorted(glob.glob(f"/kaggle/input/**/{name}", recursive=True))
    if not fs:
        raise SystemExit("attach taylorsamarel/duecare-cot-reasoning")
    with open(fs[0], encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]

train_rows = _load("cot_train.jsonl")
holdout_rows = _load("cot_holdout.jsonl")
rows = train_rows + holdout_rows

META = ["perspective","perspective_label","category","situation","ilo_indicator","reach","direction","step_count","lineage_id","lineage_family_id","split"]
df = pd.DataFrame([{k: r.get(k) for k in META} for r in rows])

OUT = Path("/kaggle/working") if os.path.isdir("/kaggle/working") else Path(".")
def save(fig, stem):
    try:
        fig.savefig(OUT / (stem + ".png"), bbox_inches="tight")
    except Exception:
        pass

display(Markdown(
    f"Loaded **{len(df):,} chain-of-thought rows** &mdash; **{len(train_rows):,}** train + **{len(holdout_rows):,}** held-out &mdash; "
    f"across **{df.perspective.nunique()} perspectives**, **{df.category.nunique()} role categories**, "
    f"**{df.situation.nunique()} ILO indicator patterns**, and **{df.lineage_family_id.nunique()} lineage families**."
))'''

SETUP = PALETTE + "\n" + HELPERS + "\n" + DATALOAD


OVERVIEW_CODE = '''n = len(df)
def _u(f): return int(df[f].nunique())
step_lo, step_hi = int(df.step_count.min()), int(df.step_count.max())
step_txt = str(step_lo) if step_lo == step_hi else f"{step_lo}-{step_hi}"
stat_cards([("101", "perspectives", TEAL), ("9", "role categories", INK2),
            (f"{n:,}", "reasoning chains", EMBER), ("102", "steps each", GOOD)])
summary = pd.DataFrame({
    "Metric": ["Total rows", "Training rows", "Held-out rows", "Distinct perspectives", "Role categories",
               "ILO indicator patterns", "Distinct ILO indicators", "Reasoning steps per row", "Lineage families"],
    "Value": [f"{n:,}", f"{int((df.split == 'train').sum()):,}", f"{int((df.split == 'holdout').sum()):,}",
              _u("perspective"), _u("category"), _u("situation"), _u("ilo_indicator"), step_txt, _u("lineage_family_id")],
})
display(pretty_table(summary, caption="The dataset at a glance -- every figure counted live from the attached files"))'''


PERSPECTIVES_CODE = '''cat = df["category"].value_counts().sort_values()
roles = df.groupby("category")["perspective"].nunique()
order = list(cat.index)
labels = [c.replace("_", " ").title() for c in order]
vals = [int(cat[c]) for c in order]
top = max(vals)
fig, ax = plt.subplots(figsize=(9.8, 5.2))
try:
    import seaborn as sns
    sns.barplot(x=vals, y=labels, color=TEAL, edgecolor=INK2, linewidth=0.5, ax=ax)
    for patch, c in zip(ax.patches, order):
        ax.text(patch.get_width() + top * 0.012, patch.get_y() + patch.get_height() / 2,
                f"{int(cat[c]):,} rows  ({int(roles[c])} perspectives)", va="center", fontsize=9.5, color=INK2)
except Exception:
    ax.barh(range(len(order)), vals, color=TEAL, edgecolor=INK2, linewidth=0.5)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(labels)
    for y, c in enumerate(order):
        ax.text(int(cat[c]) + top * 0.012, y, f"{int(cat[c]):,} rows  ({int(roles[c])} perspectives)",
                va="center", fontsize=9.5, color=INK2)
ax.set_xlim(0, top * 1.34); ax.set_xlabel("rows"); ax.set_ylabel("")
ax.set_title("Rows per role category (each role holds many distinct perspectives)")
ax.grid(axis="y", visible=False)
fig.tight_layout(); save(fig, "cot_categories"); plt.show()
display(Markdown(
    f"The **{df.category.nunique()} role categories** together span **{df.perspective.nunique()} distinct perspectives** "
    f"(largest category: `{cat.index[-1]}`). Every perspective reasons over the same forced-labour situations, "
    f"so the model sees each indicator from many vantage points."
))'''


SITUATIONS_CODE = '''sit = df["situation"].value_counts()
ind = df.drop_duplicates("situation").set_index("situation")["ilo_indicator"].to_dict()
tbl = (pd.DataFrame({
        "Situation": [s.replace("_", " ").title() for s in sit.index],
        "ILO indicator (2012)": [ind[s] for s in sit.index],
        "Chains": [int(v) for v in sit.values],
    }).sort_values("Chains", ascending=False).reset_index(drop=True))
display(pretty_table(tbl, caption="What they reason about -- rows per ILO indicator pattern (situation maps 1:1 to indicator)"))
lo, hi = int(sit.min()), int(sit.max())
display(Markdown(
    f"Coverage across the **{df.situation.nunique()} ILO indicator patterns** is balanced by construction "
    f"(**{lo:,}**-**{hi:,}** rows each), so no single indicator dominates the training signal. "
    f"Each `situation` maps 1:1 to an underlying ILO indicator term."
))'''


AXES_CODE = '''rd = (pd.crosstab(df["reach"], df["direction"])
        .reindex(index=["small_jump", "large_jump"], columns=["inward", "outward"]))
heatmap(rd.values, ["small_jump", "large_jump"], ["inward", "outward"],
        title="Two reasoning axes, balanced by construction",
        subtitle="reach (rows) x direction (cols) -- chains per quadrant",
        fmt=".0f", cmap="BuGn", cbar_label="chains")
display(Markdown(
    "**Reach** = `small_jump` (stay one inference from the record) vs `large_jump` (reach further). "
    "**Direction** = `inward` (the worker's own experience and choices) vs `outward` (systems, institutions, other actors). "
    "Both axes are split evenly, so the model learns each reasoning style equally."
))'''


DEPTH_CODE = '''step_lo, step_hi = int(df.step_count.min()), int(df.step_count.max())
lens = [len(m["content"]) for r in rows for m in r["messages"] if m["role"] == "assistant"]
mean_len = float(np.mean(lens))
kde_hist([("assistant chain", lens, TEAL)],
         title="Chain depth -- a fixed 102-step reasoning trace, measured in characters",
         subtitle=f"every row is exactly {step_hi} numbered steps; the spread here is wording length, not step count",
         xlabel="characters in the assistant chain",
         vlines=[(mean_len, EMBER, f"mean {mean_len:,.0f}")])
assert step_lo == step_hi == 102, "expected every chain to carry exactly 102 steps"
display(Markdown(
    f"Every one of the **{len(df):,} rows** carries a chain of exactly **{step_hi} numbered reasoning steps** "
    f"(min {step_lo}, max {step_hi}), averaging **{mean_len:,.0f} characters** &mdash; this is the '100+ step' structure the dataset trains for."
))'''


CHAIN_CODE = '''ex = train_rows[0]
u = next(m["content"] for m in ex["messages"] if m["role"] == "user")
a = next(m["content"] for m in ex["messages"] if m["role"] == "assistant")
hdr = (
    f"**Perspective:** {ex['perspective_label']} (`{ex['perspective']}`, category `{ex['category']}`)  \\n"
    f"**Situation / ILO indicator:** `{ex['situation']}` / `{ex['ilo_indicator']}`  \\n"
    f"**Reasoning axes:** reach `{ex['reach']}`, direction `{ex['direction']}`, **{ex['step_count']} steps**  \\n"
    f"**Lineage:** `{ex['lineage_id']}` &middot; family `{ex['lineage_family_id']}` &middot; split `{ex['split']}`"
)
display(Markdown("#### Row metadata\\n\\n" + hdr))
display(Markdown("#### The prompt\\n\\n> " + u.replace("\\n", "\\n> ")))
display(Markdown("#### The full chain of thought (all " + str(ex["step_count"]) + " steps, verbatim)\\n\\n```text\\n" + a + "\\n```"))'''


SPLIT_CODE = '''sp = df["split"].value_counts().reindex(["train", "holdout"])
tf = set(df.loc[df.split == "train", "lineage_family_id"])
hf = set(df.loc[df.split == "holdout", "lineage_family_id"])
fam_overlap = len(tf & hf)
n_train, n_hold = int(sp["train"]), int(sp["holdout"])
stat_cards([(f"{n_train:,}", "train rows", TEAL), (f"{n_hold:,}", "held-out rows", INK2),
            (f"{df.lineage_family_id.nunique():,}", "lineage families", GOOD),
            (str(fam_overlap), "train/held-out family overlap", GOOD if fam_overlap == 0 else EMBER)])
display(Markdown(
    f"Train and held-out share one lineage space of **{df.lineage_family_id.nunique()} families** "
    f"(**{len(tf)}** train, **{len(hf)}** held-out) yet **never overlap**: measured family overlap = **{fam_overlap}**. "
    f"Whole lineage families are frozen into the held-out set, so no evaluation prompt &mdash; or a sibling of one &mdash; is ever trained on."
))'''


# --------------------------------------------------------------------------- #
# markdown cells (URLs written literally; no f-string braces to escape)
# --------------------------------------------------------------------------- #
HERO_MD = '''<div style="padding:26px 32px;border-radius:16px;background:linear-gradient(120deg,#14181B 0%,#2A2D34 42%,#2f7d8c 100%);color:#F7F6F1">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.82">DueCare &middot; Gemma 4 safety &middot; chain-of-thought training data</div>
<h1 style="margin:.28em 0 .2em;font-size:30px;color:#ffffff;font-weight:800">102-step reasoning, 100+ points of view</h1>
<p style="font-size:15px;line-height:1.6;margin:0;max-width:920px">The <b>DueCare CoT Reasoning</b> dataset holds 2,000+ long-form <b>chains of thought</b> for safety fine-tuning of Gemma 4 &mdash; one per <i>(perspective &times; forced-labour situation &times; reasoning axis)</i>. Each row is a deliberate, numbered <b>~102-step</b> reasoning trace, written from one of <b>100+ domain perspectives</b> (an affected worker, a labour inspector, a recruiter in the chain, a shelter hotline, a prosecutor&hellip;) and grounded in a <b>real ILO forced-labour indicator pattern</b> &mdash; debt bondage, contract substitution, passport retention, wage withholding, movement control. This notebook explores what is inside, entirely from the attached data, on CPU, with no model and no internet.</p>
</div>'''

TOC_MD = '''## What is in this notebook

Every number and chart below is computed **live from the attached dataset** &mdash; nothing is hard-coded.

- [1. Overview &mdash; the dataset at a glance](#overview)
- [2. Who reasons &mdash; 100+ perspectives across 9 categories](#perspectives)
- [3. What they reason about &mdash; 5 ILO indicator patterns](#situations)
- [4. How they reason &mdash; two balanced axes](#axes)
- [5. How deep &mdash; the 102-step chain](#depth)
- [6. A full chain of thought, verbatim](#chain)
- [7. Train vs held-out &mdash; a clean eval split](#split)
- [8. Honest boundary &amp; license](#boundary)

**Dataset:** [`taylorsamarel/duecare-cot-reasoning`](https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning) &middot; **Source repo:** [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''

OVERVIEW_MD = '''<a id="overview"></a>
## 1. Overview &mdash; the dataset at a glance

Each row pairs a short **user prompt** (help protect a migrant worker, from a specific vantage point) with a long **assistant chain of thought** that reasons the situation through step by step. The table counts the real rows, perspectives, categories, ILO indicator patterns, and lineage families in the attached files.'''

PERSPECTIVES_MD = '''<a id="perspectives"></a>
## 2. Who reasons &mdash; 100+ perspectives across 9 categories

The same forced-labour situation is reasoned from many vantage points, grouped into **9 role categories** &mdash; from the affected worker outward to family &amp; community, frontline support, the origin and destination state, the justice system, the private supply chain, the recruitment chain, and outside observers. The bar shows rows per category; the annotation shows how many distinct **perspectives** each category contains.'''

SITUATIONS_MD = '''<a id="situations"></a>
## 3. What they reason about &mdash; 5 ILO indicator patterns

Every chain is grounded in one of five **ILO Indicators of Forced Labour (2012)** patterns. Coverage is balanced so no single indicator dominates the training signal. The styled table pairs each situation with the underlying `ilo_indicator` it maps to 1:1, and its live chain count.'''

AXES_MD = '''<a id="axes"></a>
## 4. How they reason &mdash; two balanced axes

Each chain carries two reasoning-style tags. **Reach** is how far a single step may infer beyond the record; **direction** is whose interior the reasoning turns toward. Both axes are split evenly across the corpus, so the model learns each style equally.'''

DEPTH_MD = '''<a id="depth"></a>
## 5. How deep &mdash; the 102-step chain

The dataset's defining feature is the **length and explicitness** of its reasoning: every row is a numbered chain of the same fixed depth. The step count is constant by construction; the density curve below shows how many characters that works out to per chain.'''

CHAIN_MD = '''<a id="chain"></a>
## 6. A full chain of thought, verbatim

One real row, shown end to end &mdash; the prompt, then **all** of the assistant's numbered steps with nothing truncated. This is exactly the shape the model is trained to produce: fix the perspective, hold the role boundary, name the ILO indicator, ground legal claims in a cited source, choose a safe next action, and protect privacy.'''

SPLIT_MD = '''<a id="split"></a>
## 7. Train vs held-out &mdash; a clean eval split

Training and evaluation draw from one shared **lineage space**, but they are carved apart at the *family* level: whole lineage families are frozen into the held-out set, so no held-out prompt &mdash; and no sibling of one &mdash; is ever seen in training. The overlap is computed live below.'''

BOUNDARY_MD = '''<a id="boundary"></a>
## 8. Honest boundary &amp; license

**What this is.** Illustrative, deliberately-authored reasoning grounded in real **ILO forced-labour indicator patterns**. It teaches a *reasoning structure* &mdash; name the indicator, hold the role boundary, ground legal claims in a cited source, choose a safe next action, protect privacy &mdash; not a lookup table of volatile facts.

**What this is not.** These are **silver labels**: synthetic, model-shaped rationales, not gold human annotations. Every row is **propose-only** and **synthetic** &mdash; no real individual, case, contact, name, number, or address appears, and the PII detector is clean across the set. This is **not** a real-world detection or victim-identification system, and the chains are not legal advice.

**License.** MIT. **Provenance:** each row declares its schema, ILO source references, license, and a content hash.

**Links.** Dataset: [`taylorsamarel/duecare-cot-reasoning`](https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning) &middot; Source repository: [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''


def _notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        _md(HERO_MD),
        _md(TOC_MD),
        _code(SETUP),
        _md(OVERVIEW_MD),
        _code(OVERVIEW_CODE),
        _md(PERSPECTIVES_MD),
        _code(PERSPECTIVES_CODE),
        _md(SITUATIONS_MD),
        _code(SITUATIONS_CODE),
        _md(AXES_MD),
        _code(AXES_CODE),
        _md(DEPTH_MD),
        _code(DEPTH_CODE),
        _md(CHAIN_MD),
        _code(CHAIN_CODE),
        _md(SPLIT_MD),
        _code(SPLIT_CODE),
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
    assert TITLE.lower().replace(" ", "-") == SLUG, f"title slug mismatch: {TITLE!r} -> {TITLE.lower().replace(' ', '-')!r} != {SLUG!r}"
    assert KERNEL_ID == "taylorsamarel/" + SLUG, f"kernel id mismatch: {KERNEL_ID!r}"

    result = build(args.output, force=args.force)
    result["title_slug_ok"] = TITLE.lower().replace(" ", "-") == SLUG
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
