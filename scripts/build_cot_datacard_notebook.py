#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare chain-of-thought DATA CARD notebook.

This is a data card / format walkthrough for the public `duecare-cot-reasoning`
dataset -- NOT an analysis or explorer notebook. The whole point is the SCHEMA
and the RAW ROWS: it documents every field, then shows the actual rows verbatim
(one complete row, the full user prompt, and the entire ~102-step assistant
chain with nothing truncated), a row-by-row scalar sample, how to load a row as
an SFT example, and the provenance / safety boundary. CPU only, no model, no
internet: it runs to completion on Kaggle with the dataset attached and is
verifiable.

    python scripts/build_cot_datacard_notebook.py

Then it validates itself against the local copy at reports/training/cot.jsonl
(regenerate with `python scripts/build_advanced_reasoning_materials.py`).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "cot_datacard"
LOCAL_DATA = ROOT / "reports" / "training" / "cot.jsonl"
KERNEL_ID = "taylorsamarel/duecare-cot-reasoning-data-card"
TITLE = "DueCare CoT Reasoning Data Card"
DATASET_ID = "taylorsamarel/duecare-cot-reasoning"
DS = "https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"


# --------------------------------------------------------------------------- #
# Notebook code cells (plain strings -- braces are literal, executed on Kaggle)
# --------------------------------------------------------------------------- #

SETUP = '''import glob, json, os
from collections import Counter

import pandas as pd
import matplotlib as mpl, matplotlib.pyplot as plt

# DueCare palette (warm paper / dark ink / civic teal; ember reserved for the safety boundary).
PAPER, INK, TEAL, EMBER, LINE = "#F7F6F1", "#14181B", "#2f7d8c", "#c15b2e", "#DDD8C9"
mpl.rcParams.update({
    "figure.facecolor": PAPER, "axes.facecolor": PAPER, "savefig.facecolor": PAPER,
    "axes.edgecolor": LINE, "axes.linewidth": 1.0, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "font.size": 11, "axes.titlesize": 13,
    "axes.titleweight": "bold", "axes.grid": True, "grid.color": LINE, "grid.alpha": 0.5,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 120,
})

# Recursive glob load -- never hardcode the Kaggle mount path.
print("mounted under /kaggle/input:", os.listdir("/kaggle/input") if os.path.exists("/kaggle/input") else "none")
fs = glob.glob("/kaggle/input/**/cot_train.jsonl", recursive=True) or glob.glob("/kaggle/input/**/cot.jsonl", recursive=True)
if not fs:
    raise SystemExit("attach the dataset taylorsamarel/duecare-cot-reasoning (cot_train.jsonl not found under /kaggle/input)")
PATH = sorted(fs)[0]
rows = [json.loads(line) for line in open(PATH, encoding="utf-8") if line.strip()]
if not rows:
    raise SystemExit(f"no rows parsed from {PATH}")
print(f"loaded {len(rows):,} rows from {PATH}")
print("fields per row:", list(rows[0].keys()))'''


ROW_FULL = '''row = rows[0]
# Show every metadata field in full; elide only the long assistant chain here (it is
# printed verbatim in the next section) so the metadata stays readable.
meta_view = dict(row)
meta_view["messages"] = [
    {
        "role": m["role"],
        "content": m["content"] if m["role"] != "assistant"
        else f"<{len(m['content']):,}-char {row.get('step_count', '?')}-step chain -- printed in full below>",
    }
    for m in row["messages"]
]
print(json.dumps(meta_view, indent=2, ensure_ascii=False))'''


ROW_MESSAGES = '''row = rows[0]
user = next(m["content"] for m in row["messages"] if m["role"] == "user")
assistant = next(m["content"] for m in row["messages"] if m["role"] == "assistant")
rule = "=" * 80

print(rule)
print("USER MESSAGE  --  the request the model is trained to answer")
print(rule)
print(user)
print()
print(rule)
print(f"ASSISTANT MESSAGE  --  the full {row.get('step_count', '?')}-step reasoning chain, verbatim (nothing truncated)")
print(rule)
print(assistant)'''


SAMPLE_TABLE = '''cols = ["perspective", "perspective_label", "category", "situation", "reach", "direction", "step_count", "split"]
sample = pd.DataFrame([{c: r.get(c) for c in cols} for r in rows[:10]])
pd.set_option("display.max_colwidth", None)
pd.set_option("display.width", 200)
display(sample.head(10))'''


CHART_CAT = '''counts = Counter(r["category"] for r in rows)
items = sorted(counts.items(), key=lambda kv: kv[1])
labels = [k.replace("_", " ") for k, _ in items]
values = [v for _, v in items]

fig, ax = plt.subplots(figsize=(9.2, 0.5 * len(items) + 1.4))
ax.barh(range(len(items)), values, color=TEAL, edgecolor=PAPER)
ax.set_yticks(range(len(items)))
ax.set_yticklabels(labels)
for i, v in enumerate(values):
    ax.text(v, i, f" {v:,}", va="center", color=INK, fontsize=9)
ax.set_xlabel("rows")
ax.grid(axis="y", alpha=0)
ax.set_title("Rows per perspective category")
fig.tight_layout(); plt.show()

steps = Counter(r["step_count"] for r in rows)
print("step_count distribution:", dict(steps))
if len(steps) == 1:
    only = next(iter(steps))
    print(f"Every row is a {only}-step chain -- the chain length is fixed by construction.")
else:
    print(f"step_count ranges {min(steps)}-{max(steps)}; the chains are ~102 steps.")'''


USAGE = '''# 1) Read the JSONL -- one JSON object per line.
train = [json.loads(line) for line in open(PATH, encoding="utf-8") if line.strip()]

# 2) Each row is ALREADY chat-format, so an SFT example is a thin projection:
def to_sft_example(row):
    # row["messages"] == [{"role": "user", "content": ...}, {"role": "assistant", "content": <~102-step chain>}]
    return {"messages": row["messages"]}

example = to_sft_example(train[0])
print("SFT example keys:", list(example.keys()))
print("roles in order:", [m["role"] for m in example["messages"]])
print("assistant chars:", len(example["messages"][-1]["content"]))

# 3) For leakage-free evaluation, load the held-out split (cot_holdout.jsonl) the same way.
#    It shares the schema but no lineage_family_id with the train split.
holdout_fs = glob.glob("/kaggle/input/**/cot_holdout.jsonl", recursive=True)
print("held-out eval file attached:", bool(holdout_fs))
if holdout_fs:
    holdout = [json.loads(line) for line in open(sorted(holdout_fs)[0], encoding="utf-8") if line.strip()]
    train_families = {r["lineage_family_id"] for r in train}
    overlap = sum(1 for r in holdout if r["lineage_family_id"] in train_families)
    print(f"held-out rows: {len(holdout):,} | lineage-family overlap with train: {overlap}")'''


# --------------------------------------------------------------------------- #
# Notebook markdown cells
# --------------------------------------------------------------------------- #

TOC = (
    "0. [Files in the dataset](#files)\n"
    "1. [Load the data](#load)\n"
    "2. [Schema / data dictionary](#schema)\n"
    "3. [A row, in full](#row)\n"
    "4. [The user prompt and the full reasoning chain](#messages)\n"
    "5. [Row-by-row sample](#sample)\n"
    "6. [Category coverage](#coverage)\n"
    "7. [How to load and use](#usage)\n"
    "8. [Provenance and safety boundary](#boundary)"
)

HERO = (
    "# DueCare Chain-of-Thought Reasoning -- Data Card\n\n"
    "**What this is.** [`duecare-cot-reasoning`](" + DS + ") is a synthetic, MIT-licensed "
    "**chain-of-thought** dataset for migrant-worker anti-trafficking reasoning. Each row is one "
    "**chat-format** training example: a short user request, then an assistant reply that is an explicit "
    "**~102-step reasoning chain** grounded in a real ILO forced-labour indicator pattern -- with no real "
    "people, cases, or contacts.\n\n"
    "**One-line summary.** ~1,740 training rows + ~280 held-out rows; 101 perspectives x 5 ILO-indicator "
    "situations x {small / large reach} x {inward / outward direction}; every row a 102-step chain; "
    "`synthetic`, `pii_checked`, and `propose_only` all true; silver (not gold) labels.\n\n"
    "This notebook is a **data card / format walkthrough**. It documents the exact schema and then shows the "
    "actual rows -- one complete row, the full user prompt, and the entire reasoning chain, nothing truncated. "
    "It is **CPU only, no model, no internet**, so every number and row is verifiable.\n\n"
    "### Contents\n" + TOC
)

FILES_MD = (
    '<a id="files"></a>\n'
    "## 0 - Files in the dataset\n\n"
    "The dataset ships three files. This notebook loads `cot_train.jsonl`; the counts below are as published "
    "and are re-verified live in the next section.\n\n"
    "| File | Rows | What it holds |\n"
    "|---|---|---|\n"
    "| `cot_train.jsonl` | ~1,740 | Training split. One JSON object per line, `split=\"train\"`. The file this notebook loads. |\n"
    "| `cot_holdout.jsonl` | ~280 | Held-out split for evaluation, `split=\"holdout\"`. Same schema, but **no** `lineage_family_id` overlaps the train split -- leakage-free eval. |\n"
    "| `cot_manifest.json` | -- | Dataset-level manifest: row counts, coverage (perspectives / situations / reach / direction), the quality gates that passed, and the frozen held-out lineage ids. |"
)

LOAD_MD = (
    '<a id="load"></a>\n'
    "## 1 - Load the data\n\n"
    "A recursive glob finds `cot_train.jsonl` wherever Kaggle mounts the attached dataset (the mount path is "
    "never hardcoded), parses the JSONL, and prints the row count and the field list of the first row. This is "
    "the only setup cell; every later cell reuses `rows` and `PATH`."
)

SCHEMA_MD = (
    '<a id="schema"></a>\n'
    "## 2 - Schema / data dictionary\n\n"
    "Every row is a flat JSON object with the 24 fields below. `messages` is the only nested training payload "
    "-- **chat format**: a `user` prompt followed by an `assistant` turn that is the full ~102-step chain. The "
    "remaining fields are scalars or small metadata objects used for filtering, splitting, provenance, and the "
    "quality gate.\n\n"
    "| Field | Type | Example | Meaning |\n"
    "|---|---|---|---|\n"
    "| `id` | string | `advcot:debt_bondage:worker_construction:small_jump:inward` | Stable unique row id. Encodes situation - perspective - reach - direction. |\n"
    "| `schema` | string | `advanced_reasoning_v1` | Row schema / contract version. |\n"
    "| `messages` | list of `{role, content}` | `[{\"role\":\"user\",...}, {\"role\":\"assistant\",...}]` | **Chat format.** The user turn is the request; the assistant turn is the full ~102-step reasoning chain. Directly usable as an SFT example. |\n"
    "| `perspective` | string | `worker_construction` | Machine key for the reasoning voice / role (101 available). |\n"
    "| `perspective_label` | string | `construction worker` | Human-readable label for `perspective`. |\n"
    "| `category` | string | `affected_worker` | Nine-way grouping of the perspective (e.g. affected_worker, frontline_support, justice_system, private_supply_chain, recruitment_chain). |\n"
    "| `situation` | string | `debt_bondage` | Scenario pattern; one of five ILO-indicator situations. |\n"
    "| `ilo_indicator` | string | `debt_bondage` | ILO forced-labour indicator the scenario is grounded in (mirrors `situation`). |\n"
    "| `reach` | string | `small_jump` | Reasoning reach: `small_jump` (stay one inference from the record) or `large_jump` (broader inference). |\n"
    "| `direction` | string | `inward` | Reasoning direction: `inward` (toward the worker's own experience) or `outward` (toward systems and other actors). |\n"
    "| `step_count` | integer | `102` | Number of enumerated steps in the assistant chain (102 across the dataset). |\n"
    "| `lineage_id` | string | `advcot:debt_bondage:worker_construction:small_jump:inward` | Provenance id for this exact row (equals `id`). |\n"
    "| `lineage_family_id` | string | `advcot:debt_bondage:worker_construction` | Groups the reach / direction variants of one situation+perspective. Held-out families never appear in train (leakage control). |\n"
    "| `split` | string | `train` | `train` in `cot_train.jsonl`; `holdout` in `cot_holdout.jsonl`. |\n"
    "| `source_profile` | object | `{\"kind\":\"deterministic_reasoning_scaffold\",\"generator\":\"build_advanced_reasoning_materials\",\"schema\":\"advanced_reasoning_v1\"}` | How the row was produced. |\n"
    "| `source_refs` | list of string | `[\"ILO, Indicators of Forced Labour (2012)\", \"ILO Forced Labour Convention, 1930 (No. 29)\"]` | Reference sources grounding the legal / indicator content. |\n"
    "| `rubric_targets` | list of string | `[\"A_indicator_reasoning\",\"B_legal_grounding\",\"C_role_boundary\",\"D_safe_action\",\"E_privacy_provenance\"]` | The five rubric dimensions the chain is written to satisfy. |\n"
    "| `synthetic` | boolean | `true` | Row is synthetic / illustrative, not a real case. |\n"
    "| `pii_checked` | boolean | `true` | Passed the PII detector; no real personal data. |\n"
    "| `license` | string | `MIT` | Row license. |\n"
    "| `quality_gate` | object | `{\"accepted\":true,\"unsafe_advice_filtered\":true,\"checks\":{\"contract\":\"advanced_reasoning_v1\"}}` | Per-row quality-gate result. |\n"
    "| `provenance` | string | `illustrative reasoning grounded in a real ILO indicator pattern; no real individual, case, or contact` | One-line provenance / safety statement. |\n"
    "| `propose_only` | boolean | `true` | Advisory / propose-only; contains no operational uplift. |\n"
    "| `sha256` | string | `6ba0aee7...` (64 hex) | SHA-256 integrity hash of the canonical row content. |\n\n"
    "That is every field in a row. The next three sections show a real row against this dictionary."
)

ROW_MD = (
    '<a id="row"></a>\n'
    "## 3 - A row, in full\n\n"
    "One complete row, pretty-printed. Every metadata field is shown verbatim; only the long assistant chain "
    "is elided here (it is printed in full in the next section) so the metadata stays readable. Compare each "
    "key against the data dictionary above."
)

MESSAGES_MD = (
    '<a id="messages"></a>\n'
    "## 4 - The user prompt and the full reasoning chain\n\n"
    "`messages` is standard chat format. The **user** turn is the request; the **assistant** turn is the full "
    "~102-step chain. **Nothing below is truncated** -- you can read every step, exactly as a model would be "
    "trained on it."
)

SAMPLE_MD = (
    '<a id="sample"></a>\n'
    "## 5 - Row-by-row sample\n\n"
    "The scalar (non-text) columns for the first ten rows -- the fields you would filter, group, or stratify on. "
    "The two chat turns live in `messages` (shown above) and are omitted here."
)

COVERAGE_MD = (
    '<a id="coverage"></a>\n'
    "## 6 - Category coverage\n\n"
    "The 101 perspectives roll up into nine categories, and the chain length is fixed by construction. Both are "
    "computed live from the loaded rows."
)

USAGE_MD = (
    '<a id="usage"></a>\n'
    "## 7 - How to load and use\n\n"
    "Because `messages` is already SFT-ready chat format, turning the dataset into training data is a thin "
    "projection -- no reformatting. Pair the training split with the held-out split for leakage-free evaluation."
)

BOUNDARY_MD = (
    '<a id="boundary"></a>\n'
    "## 8 - Provenance and safety boundary\n\n"
    "Every row carries `synthetic=true`, `pii_checked=true`, and `propose_only=true`, plus a one-line "
    "`provenance` string. **What that means:**\n\n"
    "- **Illustrative, not real.** The reasoning is grounded in real ILO forced-labour *indicator patterns* "
    "(debt bondage, passport retention, wage withholding, movement control, contract substitution), but no real "
    "individual, case, phone number, address, or contact appears anywhere.\n"
    "- **Silver labels.** The chains are deterministically authored reasoning scaffolds, not human-verified "
    "gold, and not a claim of real-world detection.\n"
    "- **Propose-only.** Rows describe how to *reason* about protecting a worker; they carry no operational "
    "uplift and passed an unsafe-advice filter.\n"
    "- **Licensed + traceable.** MIT license; each row carries `lineage_id`, `lineage_family_id`, and a "
    "`sha256` content hash, so any row can be traced and integrity-checked.\n\n"
    "### Links\n"
    "- Dataset: " + DS + "\n"
    "- Source repository: " + REPO + "\n\n"
    "License: MIT. Synthetic reasoning only -- no response harvested from a real person, no PII."
)


def build(output_dir: Path, *, force: bool = False) -> dict:
    """Emit the data-card notebook and its Kaggle kernel metadata."""
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell

    cells = [
        md(HERO),
        md(FILES_MD),
        md(LOAD_MD),
        code(SETUP),
        md(SCHEMA_MD),
        md(ROW_MD),
        code(ROW_FULL),
        md(MESSAGES_MD),
        code(ROW_MESSAGES),
        md(SAMPLE_MD),
        code(SAMPLE_TABLE),
        md(COVERAGE_MD),
        code(CHART_CAT),
        md(USAGE_MD),
        code(USAGE),
        md(BOUNDARY_MD),
    ]

    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "language_info": {"name": "python"},
    }
    nbf.write(nb, str(nb_dir / "notebook.ipynb"))

    meta = {
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
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"kernel_id": KERNEL_ID, "cells": len(cells), "notebook_dir": str(nb_dir)}


def validate_local(data_path: Path) -> dict:
    """Validate the emitted schema story against the local dataset copy.

    Confirms the file loads, reports the field list of row 0, the step_count of a
    couple of rows, and that `messages` carries a user and an assistant entry.
    """
    if not data_path.is_file():
        return {
            "validated": False,
            "reason": f"local copy missing: {data_path} "
            "(regenerate with `python scripts/build_advanced_reasoning_materials.py`)",
        }
    rows = [json.loads(line) for line in data_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        return {"validated": False, "reason": f"no rows parsed from {data_path}"}
    row0 = rows[0]
    roles = [m.get("role") for m in row0.get("messages", [])]
    has_user = "user" in roles
    has_assistant = "assistant" in roles
    return {
        "validated": bool(rows) and has_user and has_assistant,
        "data_path": str(data_path),
        "row_count": len(rows),
        "row0_fields": list(row0.keys()),
        "step_counts_first_2": [r.get("step_count") for r in rows[:2]],
        "messages_roles_row0": roles,
        "messages_has_user_and_assistant": has_user and has_assistant,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--data", type=Path, default=LOCAL_DATA, help="local cot.jsonl for self-validation")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-validate", action="store_true", help="do not validate against the local copy")
    args = ap.parse_args(argv)

    summary = build(args.output, force=args.force)

    slug = summary["kernel_id"].split("/", 1)[1]
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    summary["title_slug_ok"] = True

    if not args.skip_validate:
        summary["local_validation"] = validate_local(args.data)

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
