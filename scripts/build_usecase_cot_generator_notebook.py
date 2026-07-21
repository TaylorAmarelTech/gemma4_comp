#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Chain-of-Thought Generator use-case notebook.

An easy-to-use, self-contained Kaggle notebook (nbformat) that *generates a chain of thought by asking
numerous structured questions*. Given a worker's account, it asks the ILO forced-labour indicator
questions, the migration lifecycle-stage questions, and the counterfactual challenge questions -- one
at a time -- and assembles the answers into a numbered, reasoned chain that ends in a grounded
conclusion. This is reasoning *by asking many questions*, the opposite of matching a single keyword,
and it is a live, tiny version of how the published `taylorsamarel/duecare-cot-reasoning` training
dataset (101 perspectives x reach x direction, ~102-step chains) is built.

Everything runs on the shared, grounded DueCare indicator engine (`_usecase_engine.ENGINE`) --
deterministic, CPU-only, offline. No dataset is attached, no GPU, no internet, no model download.
Every optional dependency in the shared viz toolkit degrades to an offline-safe fallback, so the
notebook always runs to completion. ASCII-only source -> no Kaggle mojibake.

    python scripts/build_usecase_cot_generator_notebook.py
    python scripts/build_usecase_cot_generator_notebook.py --force
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
from _usecase_engine import ENGINE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "usecase_cot_generator"
TITLE = "DueCare Chain Of Thought Generator"
SLUG = "duecare-chain-of-thought-generator"
KERNEL_ID = "taylorsamarel/" + SLUG
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
# SETUP -- the first CODE cell: the shared prettify toolkit (PALETTE + HELPERS)
# and the grounded indicator ENGINE, embedded so the notebook is fully
# self-contained on Kaggle (nothing imported at runtime, no dataset attached).
# --------------------------------------------------------------------------- #
SETUP = PALETTE + "\n" + HELPERS + "\n" + ENGINE


# --------------------------------------------------------------------------- #
# The generator -- built directly on the engine's generate_chain() + the three
# question banks (INDICATOR_QUESTIONS / LIFECYCLE / COUNTERFACTUALS).
# --------------------------------------------------------------------------- #
FUNC_CODE = r'''from IPython.display import Markdown, display
NL = chr(10)

# Block sizes come straight from the engine's question banks -- never hard-coded.
N_IND = len(INDICATOR_QUESTIONS)
N_LIFE = len(LIFECYCLE)
N_CF = len(COUNTERFACTUALS)
N_STEPS = 1 + N_IND + N_LIFE + N_CF + 1   # restate + indicators + lifecycle + counterfactuals + conclusion

LIGHT = {"HIGH": EMBER, "ELEVATED": EMBER, "WATCH": WARN, "LOW": GOOD}

def present_indicators(scenario):
    """The set of ILO indicators whose questions answer PRESENT for this scenario."""
    return {h["indicator"] for h in scan(scenario)}

def _stage_of(i):
    """Classify a 1-based step number into its reasoning stage using the engine's block sizes."""
    if i == 1:
        return "Frame"
    if i <= 1 + N_IND:
        return "ILO indicator question"
    if i <= 1 + N_IND + N_LIFE:
        return "Lifecycle-stage question"
    if i <= 1 + N_IND + N_LIFE + N_CF:
        return "Counterfactual question"
    return "Conclusion"

def _answer_of(text):
    if "PRESENT" in text:
        return "PRESENT"
    if "not evident" in text:
        return "absent"
    return ""

def ask_and_reason(scenario, render=True, title=None):
    """Ask the structured ILO questions of `scenario` and build the reasoned chain.

    Uses the engine's generate_chain(). Returns the list of (step_number, text) steps;
    when render=True it also draws the summary card, the present-indicator radar, and the step table."""
    steps = generate_chain(scenario)
    if render:
        present = present_indicators(scenario)
        level, why = risk_level(scan(scenario))
        stat_cards([(str(len(steps)), "questions / steps", TEAL),
                    (str(len(present)) + " / " + str(N_IND), "indicators PRESENT", EMBER),
                    (level, "risk conclusion", LIGHT[level])])
        head = "**Scenario: " + title + "**" if title else "**Scenario checked:**"
        display(Markdown(head + NL + NL + "> " + str(scenario).strip().replace(NL, NL + "> ")))
        # radar: which ILO indicator questions came back PRESENT
        labels = [ind.replace("_", " ") for ind, _ in INDICATOR_QUESTIONS]
        vals = [1 if ind in present else 0 for ind, _ in INDICATOR_QUESTIONS]
        radar(labels, [("this scenario", vals, EMBER)],
              title="Which ILO indicator questions answered PRESENT",
              subtitle="1 = the question found evidence in the account, 0 = not evident", rmax=1)
        # the full reasoned chain as a readable step table
        tbl = pd.DataFrame([{"#": n, "Stage": _stage_of(n), "Question asked / reasoning step": t, "Answer": _answer_of(t)}
                            for n, t in steps])
        display(pretty_table(tbl, caption="The reasoned chain - " + str(len(steps)) + " structured questions, asked and answered in order"))
    return steps

def chain_text(steps):
    """Join the (n, text) steps into one verbatim, numbered block - nothing truncated."""
    return NL.join(str(n) + ". " + t for n, t in steps)

display(Markdown("Generator ready. `ask_and_reason(scenario)` asks the **" + str(N_STEPS) +
                 "** structured questions (" + str(N_IND) + " ILO indicator + " + str(N_LIFE) +
                 " lifecycle + " + str(N_CF) + " counterfactual, plus frame and conclusion) and returns the "
                 "reasoned chain. Everything runs locally - nothing is sent anywhere."))'''


TRYOWN_CODE = r'''# ================== TRY YOUR OWN =====================================
# Describe a worker's situation in your own words between the triple quotes,
# then run this cell to generate its full chain of reasoning by asking questions.
my_scenario = """
A woman took a domestic job in another country. On arrival the agency kept her
passport, told her the contract had changed to a lower salary, and said she must
work to repay her recruitment fee before she can leave.
"""

steps = ask_and_reason(my_scenario, title="your scenario")'''


FRAMEWORK_STATS_CODE = r'''stat_cards([(str(N_IND), "ILO indicator questions", TEAL),
            (str(N_LIFE), "lifecycle-stage questions", EMBER),
            (str(N_CF), "counterfactual questions", GOOD),
            (str(N_STEPS), "questions per scenario", INK2)])
display(Markdown(
    "Every scenario is put through the **same** structured interview: restate it neutrally, then ask **" +
    str(N_IND) + "** ILO forced-labour indicator questions (the 11 ILO 2012 indicators plus a recruitment-fee "
    "screen), **" + str(N_LIFE) + "** lifecycle-stage questions, and **" + str(N_CF) + "** counterfactual "
    "challenges, and finish with a conclusion. That is **reasoning by asking many questions** - the opposite "
    "of matching a single keyword."
))'''


FRAMEWORK_TABLE_CODE = r'''rows = []
for ind, q in INDICATOR_QUESTIONS:
    rows.append({"Type": "ILO indicator", "The question asked": q,
                 "Reference": ILO_REFS.get(ind, "ILO Indicators of Forced Labour (2012)")})
for stage in LIFECYCLE:
    rows.append({"Type": "Lifecycle stage",
                 "The question asked": "Stage '" + stage + "': what to verify here, and what the worker or caseworker should do next.",
                 "Reference": "ILO migration lifecycle"})
for cf in COUNTERFACTUALS:
    rows.append({"Type": "Counterfactual", "The question asked": cf, "Reference": "structured skepticism"})
display(pretty_table(pd.DataFrame(rows),
                     caption="The full question bank - " + str(len(rows)) + " questions asked of every scenario (before the frame and the conclusion)"))'''


CHAIN_CODE = r'''scenario = ("A recruiter offered a factory job abroad with a high salary. The worker paid a "
            "2,000 dollar placement fee up front. On arrival the employer took his passport, "
            "housed eight men in one crowded room, and said his salary would be withheld for the "
            "first six months as 'savings'. He works twelve hours a day with no day off and cannot "
            "leave the compound without permission.")
steps = ask_and_reason(scenario, title="factory job abroad")'''


CHAIN_VERBATIM_CODE = r'''display(Markdown("**The full chain, verbatim - every question asked and answered, nothing truncated:**"))
display(Markdown("```text" + NL + chain_text(steps) + NL + "```"))'''


CLOSEUP_CODE = r'''# Close-up: how ONE indicator question gets answered - the engine keeps the exact cue.
demo = "The sponsor is holding my passport and I have not been paid for two months."
hits = scan(demo)
display(Markdown("Account: _'" + demo + "'_"))
display(pretty_table(pd.DataFrame([{
    "Indicator question": "Is there evidence of " + h["label"].lower() + "?",
    "Answer": "PRESENT",
    "Cue kept from the account": h["snippet"],
    "ILO basis": h["ilo_ref"],
} for h in hits]), caption="Each PRESENT answer keeps the exact words that triggered it - grounded, auditable reasoning"))'''


CONTRAST_CODE = r'''benign = ("A worker was offered a warehouse job. The salary matches the written contract. The "
          "employer sends the contract in her own language to sign before travel. Her passport stays "
          "with her, she pays no fee, and she can come and go freely.")
steps_b = ask_and_reason(benign, title="an ordinary, clean offer")'''


SENSITIVITY_CODE = r'''variants = {
    "Base account": "A worker was told her pay would be different from the signed contract.",
    "+ passport kept": ("A worker was told her pay would be different from the signed contract. "
                        "On arrival the employer also took her passport."),
    "+ fee to repay": ("A worker was told her pay would be different from the signed contract. "
                       "On arrival the employer also took her passport. She is told she must repay a "
                       "placement fee through salary deductions before she can leave."),
}
keys = [ind for ind, _ in INDICATOR_QUESTIONS]
mat = [[1 if ind in present_indicators(v) else 0 for v in variants.values()] for ind in keys]
show = [i for i, row in enumerate(mat) if any(row)]   # only indicators that fire in >=1 variant
heatmap([mat[i] for i in show], [keys[i].replace("_", " ") for i in show], list(variants.keys()),
        title="Add one detail at a time - watch the questions flip to PRESENT",
        subtitle="1 = that ILO indicator question answers PRESENT for the variant",
        fmt=".0f", cmap="BuGn", cbar_label="PRESENT")'''


SENSITIVITY_TABLE_CODE = r'''rows = []
for name, v in variants.items():
    p = present_indicators(v)
    level, why = risk_level(scan(v))
    rows.append({"Variant": name, "Indicators PRESENT": len(p), "Risk conclusion": level, "Why": why})
display(pretty_table(pd.DataFrame(rows), caption="One detail at a time changes the conclusion", bars=["Indicators PRESENT"]))
display(Markdown(
    "Adding a single concrete detail flips new questions to **PRESENT** and moves the conclusion. The "
    "reasoning is **compositional**: each fact is weighed by its own question, so the chain shows exactly "
    "*why* the risk rose, not just *that* it rose. That auditability is the whole point of reasoning by "
    "asking questions."
))'''


SCALE_CODE = r'''stat_cards([("1", "scenario in this demo", TEAL),
            (str(N_STEPS), "questions asked here", EMBER),
            ("100+", "perspectives in the dataset", INK2),
            ("~102", "steps per published chain", GOOD)])
display(Markdown(
    "This notebook builds the chain for **one** scenario at a time. The published **DueCare CoT Reasoning** "
    "dataset scales the exact same idea: the same structured questions are asked from **101 perspectives** "
    "(the affected worker outward to family, frontline support, the origin and destination states, the "
    "justice system, the supply chain, and outside observers), crossed with two reasoning axes - **reach** "
    "(small vs large jump) and **direction** (inward vs outward) - to produce **~102-step** chains of thought "
    "for fine-tuning Gemma 4. What you generated live above is a small, transparent version of how each of "
    "those training chains is built."
))'''


# --------------------------------------------------------------------------- #
# markdown cells (URLs literal; HTML entities keep the source ASCII)
# --------------------------------------------------------------------------- #
HERO_MD = '''<div style="padding:26px 32px;border-radius:16px;background:linear-gradient(120deg,#14181B 0%,#2A2D34 40%,#c15b2e 118%);color:#F7F6F1">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.82">DueCare &middot; Gemma 4 safety &middot; chain-of-thought</div>
<h1 style="margin:.28em 0 .2em;font-size:30px;color:#ffffff;font-weight:800">Reasoning by asking many questions, not pattern-matching</h1>
<p style="font-size:15px;line-height:1.6;margin:0;max-width:940px">A safety judge should not fire on a single scary keyword. It should <b>reason</b> &mdash; ask the account a long series of structured questions and weigh each answer. This notebook <b>generates a chain of thought</b> for any worker's situation by asking the <b>ILO forced-labour indicator questions</b> (present or absent?), the <b>migration lifecycle-stage questions</b>, and the <b>counterfactual challenges</b>, one at a time, and assembling them into a numbered, reasoned chain that ends in a grounded conclusion. Paste your own scenario, watch the questions get asked and answered, and see how changing a single detail flips which questions come back <b>PRESENT</b>. It is a live, tiny version of how the published <b>DueCare CoT Reasoning</b> dataset (101 perspectives &times; reach &times; direction, ~102-step chains) is built to fine-tune Gemma 4. Entirely on CPU, no model, no internet.</p>
</div>'''

TOC_MD = '''## What is in this notebook

Every chain below is generated **live, offline, on CPU** &mdash; no model download, no internet, no dataset attached. Paste your own scenario in the first cell, or read along.

- [Try your own &mdash; write a scenario, generate its chain](#tryown)
- [The question framework &mdash; every question we ask](#framework)
- [Generate a full chain for one scenario](#chain)
- [A clean scenario, for contrast](#contrast)
- [Scenario sensitivity &mdash; change one detail, watch the questions flip](#sensitivity)
- [How this scales to the CoT dataset](#scale)
- [Honest boundary](#boundary)

**Dataset:** [`taylorsamarel/duecare-cot-reasoning`](https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning) &middot; **Source repo:** [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''

FUNC_MD = '''## The generator, in one function

The whole thing is one function, `ask_and_reason(scenario)`, built directly on the DueCare engine. It calls `generate_chain()`, which asks the account each of the structured questions in the engine's three question banks &mdash; the ILO indicator questions, the lifecycle-stage questions, and the counterfactual questions &mdash; and returns a numbered list of `(step, text)` reasoning steps. Run the cell below once to load it, then use it anywhere.'''

TRYOWN_MD = '''<a id="tryown"></a>
## Try your own &mdash; write a scenario, generate its chain

Describe a worker's situation in your own words between the triple quotes below and run the cell. You will get a summary card, a radar of which ILO indicator questions came back **PRESENT**, and the full numbered chain of every question asked and answered. **Nothing you type leaves this notebook.**'''

FRAMEWORK_MD = '''<a id="framework"></a>
## The question framework &mdash; every question we ask

Reasoning here means asking the **same structured battery of questions of every account**, not spotting one word. There are three banks: the **ILO forced-labour indicator** questions (the 11 ILO 2012 indicators plus a recruitment-fee screen), the **migration lifecycle-stage** questions, and the **counterfactual** challenges that stress-test the reading. The tiles count them live; the table lists every single one with its reference.'''

CHAIN_MD = '''<a id="chain"></a>
## Generate a full chain for one scenario

One worked scenario, put through the whole interview. Watch it: the summary card, the radar of which indicator questions answered PRESENT, the full step table (frame, then every indicator question, then the lifecycle questions, then the counterfactuals, then the conclusion), and finally the entire chain verbatim &mdash; nothing truncated. This is exactly the shape the CoT dataset teaches Gemma 4 to produce.'''

CLOSEUP_MD = '''### Close-up: how one question gets answered

Each PRESENT answer is not a black box &mdash; the engine keeps the **exact words** from the account that triggered it, plus the controlling ILO reference. That is what makes the chain auditable: you can always see *why* a question was answered PRESENT.'''

CONTRAST_MD = '''<a id="contrast"></a>
## A clean scenario, for contrast

The same interview run on an ordinary, honest offer. Almost every question should come back *not evident*, the radar should be nearly empty, and the conclusion should be low risk. A good reasoner is just as clear about what is **absent** as about what is present &mdash; it does not invent alarm.'''

SENSITIVITY_MD = '''<a id="sensitivity"></a>
## Scenario sensitivity &mdash; change one detail, watch the questions flip

The real payoff of reasoning-by-questions is that it is **compositional**. Start from a mild base account and add one concrete detail at a time; each new fact flips a different indicator question to PRESENT and moves the conclusion. The heatmap shows which questions light up as the account grows, and the table shows the conclusion climbing with the evidence.'''

SCALE_MD = '''<a id="scale"></a>
## How this scales to the CoT dataset

You just generated one chain, live. The published training dataset is the same idea at scale.'''

SCALE_LINKS_MD = '''The full training corpus and its explorers are public:

- **Dataset:** [`taylorsamarel/duecare-cot-reasoning`](https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning) &mdash; 100+ perspectives &times; reach &times; direction, ~102-step chains of thought, each grounded in an ILO forced-labour indicator pattern, for safety fine-tuning of Gemma 4.
- **CoT explorer notebooks:** the *Reasoning Explorer* (who / what / chain-depth / schema) and the *Direction &amp; Intent Explorer* (the reasoning axes and their tone) take those chains apart, chart by chart.
- **Source repository:** [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''

BOUNDARY_MD = '''<a id="boundary"></a>
## Honest boundary

**What this is.** A live, tiny demonstration of **reasoning by asking many structured questions**. Given an account, it asks the ILO forced-labour indicator questions, the lifecycle-stage questions, and the counterfactual questions, keeps the exact cue behind every PRESENT answer, and ends in a grounded conclusion. It runs offline, on CPU, with no model.

**What this is not.** The indicator detector is a **representative subset** of the DueCare GREP layer (production has 451 rules across 11 languages) plus the ILO knowledge packs &mdash; it is deterministic and illustrative, not a trained model and not a verdict about any person. A PRESENT answer is a **prompt to verify**, never proof. The chains are **silver** reasoning scaffolds &mdash; they teach a *structure and register*, not a lookup table of volatile facts, and they are not legal advice.

**Privacy.** Everything you type stays in this notebook. In the real product the same reasoning runs **on-device** via Gemma 4 (LiteRT / llama.cpp); raw accounts, IDs, and documents never leave the device unless the worker chooses to send a sanitised, PII-free summary.

**Links.** Dataset: [`taylorsamarel/duecare-cot-reasoning`](https://www.kaggle.com/datasets/taylorsamarel/duecare-cot-reasoning) &middot; Source repository: [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''


def _notebook() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        _md(HERO_MD),
        _md(TOC_MD),
        _code(SETUP),
        _md(FUNC_MD),
        _code(FUNC_CODE),
        _md(TRYOWN_MD),
        _code(TRYOWN_CODE),
        _md(FRAMEWORK_MD),
        _code(FRAMEWORK_STATS_CODE),
        _code(FRAMEWORK_TABLE_CODE),
        _md(CHAIN_MD),
        _code(CHAIN_CODE),
        _code(CHAIN_VERBATIM_CODE),
        _md(CLOSEUP_MD),
        _code(CLOSEUP_CODE),
        _md(CONTRAST_MD),
        _code(CONTRAST_CODE),
        _md(SENSITIVITY_MD),
        _code(SENSITIVITY_CODE),
        _code(SENSITIVITY_TABLE_CODE),
        _md(SCALE_MD),
        _code(SCALE_CODE),
        _md(SCALE_LINKS_MD),
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
        "dataset_sources": [],
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
    assert TITLE.lower().replace(" ", "-") == SLUG, (
        "title slug mismatch: " + repr(TITLE) + " -> " + repr(TITLE.lower().replace(" ", "-")) + " != " + repr(SLUG)
    )
    assert KERNEL_ID == "taylorsamarel/" + SLUG, "kernel id mismatch: " + repr(KERNEL_ID)

    result = build(args.output, force=args.force)
    result["title_slug_ok"] = TITLE.lower().replace(" ", "-") == SLUG
    assert not result["non_ascii_chars"], "non-ASCII characters leaked into the notebook: " + repr(result["non_ascii_chars"])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
