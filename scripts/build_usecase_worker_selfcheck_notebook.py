#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Worker Self-Check use-case notebook.

An easy-to-use, self-contained Kaggle notebook (nbformat) for a migrant worker -- or a friend
helping one -- who wants to know: *is this job offer safe?* Paste a suspicious offer or message and
get a plain-language traffic-light safety check (GREEN / AMBER / RED), the specific forced-labour
red flags it found (each explained in simple words), a short list of concrete things you can do, and
where to get real help.

The whole check runs on the shared, grounded DueCare indicator engine (`_usecase_engine.ENGINE`) --
deterministic, CPU-only, offline. It is a representative subset of the real DueCare GREP layer
(451 rules across 11 languages) plus the ILO forced-labour indicator knowledge; the real product
runs the same logic on-device via Gemma 4 (LiteRT / llama.cpp) so a worker's chats, IDs, and
documents never leave their phone. No dataset is attached, no GPU, no internet, no model download.
Every optional dependency in the shared viz toolkit degrades to an offline-safe fallback, so the
notebook always runs to completion. ASCII-only source -> no Kaggle mojibake.

    python scripts/build_usecase_worker_selfcheck_notebook.py
    python scripts/build_usecase_worker_selfcheck_notebook.py --force
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "usecase_worker_selfcheck"
TITLE = "DueCare Worker Self Check"
SLUG = "duecare-worker-self-check"
KERNEL_ID = "taylorsamarel/" + SLUG
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
# The safety check -- built directly on the engine's scan() + risk_level().
# --------------------------------------------------------------------------- #
FUNC_CODE = r'''from IPython.display import Markdown, display
NL = chr(10)

# Map the engine's four risk levels onto a plain traffic light a worker reads at a glance.
TRAFFIC = {
    "LOW":      ("GREEN", "No clear warning signs"),
    "WATCH":    ("AMBER", "One warning sign - ask questions"),
    "ELEVATED": ("RED",   "Several warning signs"),
    "HIGH":     ("RED",   "Multiple serious warning signs"),
}
LIGHT_COLOR = {"GREEN": GOOD, "AMBER": WARN, "RED": EMBER}

# Plain-language "why it matters" for every ILO forced-labour indicator the engine can detect.
PLAIN = {
    "document_retention": "A real employer never needs to keep your passport or ID. Whoever holds your papers can stop you leaving.",
    "debt_bondage": "Being told to 'work off' a debt or fee before you can leave is a classic trap. Your freedom should never depend on a debt.",
    "recruitment_fee": "You should not have to pay to get a job. Honest recruiters do not charge workers placement or processing fees.",
    "wage_withholding": "Wages that are held back, delayed, or 'kept safe' for you are a way to stop you leaving.",
    "restriction_of_movement": "You have the right to come and go. Being locked in, or needing permission to leave, is a serious red flag.",
    "intimidation": "Threats - deportation, police, blacklisting - are used to keep workers silent. A real employer does not threaten you.",
    "deception": "If the real job, pay, or conditions differ from what you were promised, the offer may be bait to get you there.",
    "excessive_overtime": "No days off and extreme hours are signs of forced labour, not a normal job.",
    "isolation": "Being cut off - phone taken, no way to reach family - is a way to control workers.",
    "abuse_of_vulnerability": "Traffickers target people far from home, in debt, or unsure of the language. Extra caution helps.",
    "violence": "Any violence or force is a crime. Get to safety and seek help right away.",
    "abusive_conditions": "Unsafe housing, no food or water, and being treated as disposable are warning signs of exploitation.",
}

def _actions(hits, risk):
    """Turn the detected indicators into 3-4 concrete things the worker can do."""
    inds = {h["indicator"] for h in hits}
    acts = []
    if risk == "RED":
        acts.append("Slow down. Do not pay, sign, or travel yet - these are serious warning signs.")
    if "recruitment_fee" in inds or "debt_bondage" in inds:
        acts.append("Do not pay any fee to get a job. Ask, in writing, what every charge is for - honest jobs do not charge workers.")
    if "document_retention" in inds:
        acts.append("Never hand over your only passport or ID. Keep your own copies, and leave a spare with someone you trust.")
    if "deception" in inds:
        acts.append("Get the real contract in a language you read and compare it, line by line, to what you were promised.")
    # general safety advice that applies to any offer
    if "document_retention" not in inds:
        acts.append("Never give anyone your only passport or ID - always keep your own copies.")
    acts.append("Get the full offer and contract in writing, in a language you read, before you pay or travel.")
    acts.append("Tell someone you trust the employer's name and exactly where you are going.")
    if risk in ("AMBER", "RED"):
        acts.append("Contact a hotline or your country's embassy labour attache before you commit - it is free and confidential.")
    out = []
    for a in acts:
        if a not in out:
            out.append(a)
    return out[:4]

def check(message, country="global"):
    """Plain-language safety check for a job offer or message.

    Returns a dict with: risk (GREEN/AMBER/RED), level (engine level), headline, why,
    red_flags (each: what / why_it_matters / words / ilo_ref), actions, and help."""
    hits = scan(message)
    level, why = risk_level(hits)
    risk, headline = TRAFFIC[level]
    red_flags = [{
        "what": h["label"],
        "why_it_matters": PLAIN.get(h["indicator"], "This is a recognised forced-labour warning sign."),
        "words": h["snippet"],
        "ilo_ref": h["ilo_ref"],
    } for h in hits]
    return {
        "risk": risk, "level": level, "headline": headline, "why": why,
        "red_flags": red_flags, "actions": _actions(hits, risk),
        "help": HOTLINES.get(country, HOTLINES["global"]), "country": country,
    }

def _callout(help_text, risk):
    tone = LIGHT_COLOR[risk]
    return ('<div style="padding:16px 20px;border-radius:12px;border-left:6px solid ' + tone +
            ';background:' + PAPER2 + ';color:' + INK + '">'
            '<b>Where to get help</b><br>' + help_text +
            '<br><span style="color:' + INK3 + ';font-size:12px">' + HOTLINES["note"] + '</span></div>')

def show_check(message, country="global"):
    """Run check() and render it: a big traffic-light card, the red-flag table, actions, and where to get help."""
    res = check(message, country)
    color = LIGHT_COLOR[res["risk"]]
    stat_cards([(res["risk"], res["headline"], color),
                (str(len(res["red_flags"])), "warning signs found", INK2),
                (res["country"], "help location", TEAL)])
    display(Markdown("**The message checked:**" + NL + NL + "> " + str(message).strip().replace(NL, NL + "> ")))
    if res["red_flags"]:
        tbl = pd.DataFrame([{
            "Warning sign": f["what"],
            "Why it matters (plain words)": f["why_it_matters"],
            "What triggered it": f["words"],
            "Basis (ILO)": f["ilo_ref"],
        } for f in res["red_flags"]])
        display(pretty_table(tbl, caption="What the check noticed - and why each one matters"))
    else:
        display(Markdown("_No specific warning signs matched the message. That is reassuring - but it is not a "
                         "guarantee. Trust your instincts and still verify the offer._"))
    display(Markdown("**What you can do:**" + NL + NL + NL.join("- " + a for a in res["actions"])))
    display(Markdown(_callout(res["help"], res["risk"])))
    return res

# collected as the four worked examples run, for the recap at the end
EXAMPLES = []

display(Markdown("Safety check ready. `check(message, country)` returns the result; "
                 "`show_check(message, country)` runs it and draws the traffic light, the red-flag table, "
                 "the actions, and where to get help. Everything runs locally - nothing is sent anywhere."))'''


TRYOWN_CODE = r'''# ================== TRY YOUR OWN =====================================
# Paste a suspicious job offer or message between the triple quotes, set your
# country (global, US, Philippines, Nepal, or "Gulf / GCC"), and run this cell.
my_message = """
We can get you a hotel job in the Gulf with a great salary. There is a
placement fee of 1,800 dollars, but you can pay it back from your wages.
The agency will keep your passport safe for you once you arrive.
"""
my_country = "Gulf / GCC"

_ = show_check(my_message, my_country)'''


EX1_CODE = r'''# Example 1 - a "too good to be true" Gulf offer with fees (expected: RED)
msg = ("Great news - you are selected for a cleaning job in the Gulf. 12-hour shifts, "
       "no day off for the first three months, and the salary is higher than any local job. "
       "There is a placement fee of 2,500 dollars; you can pay it back through monthly salary "
       "deductions once you start. The agency will hold your passport for safekeeping when you arrive.")
EXAMPLES.append(("Too-good Gulf offer with fees", msg, "Gulf / GCC"))
_ = show_check(msg, "Gulf / GCC")'''


EX2_CODE = r'''# Example 2 - a message from an employer holding documents and freedom (expected: RED)
msg = ("Your employer will keep your passport and residence permit in the office safe. "
       "You are not allowed to leave the accommodation without the manager's permission. "
       "If you complain, they said they will report you to the police and cancel your visa.")
EXAMPLES.append(("Employer holding passport and freedom", msg, "global"))
_ = show_check(msg, "global")'''


EX3_CODE = r'''# Example 3 - an ordinary, real job offer that should come back clean (expected: GREEN)
msg = ("Thank you for the interview last week. We would like to offer you the warehouse "
       "assistant role. The salary is 1,400 US dollars per month, paid on the 1st of each month. "
       "The company covers your flight and your first week of housing. Your contract will be sent "
       "in English and Tagalog to read and sign before you travel. Your passport and documents "
       "stay with you at all times. Please take your time to decide.")
EXAMPLES.append(("Ordinary, clean offer", msg, "Philippines"))
_ = show_check(msg, "Philippines")'''


EX4_CODE = r'''# Example 4 - an ambiguous offer with one small red flag (expected: AMBER)
msg = ("The job looks real and the pay matches what we discussed. The only thing I am unsure "
       "about is a one-time 50 dollar processing fee they asked for to cover paperwork. "
       "Everything else seems fine. Should I go ahead?")
EXAMPLES.append(("Ambiguous - one small red flag", msg, "global"))
_ = show_check(msg, "global")'''


RECAP_CODE = r'''rows = []
for label, m, c in EXAMPLES:
    r = check(m, c)
    rows.append({"Example": label, "Colour": r["risk"], "Warning signs": len(r["red_flags"]), "What it means": r["headline"]})
recap = pd.DataFrame(rows)
display(pretty_table(recap, caption="The four examples at a glance - every colour decided live by the engine", bars=["Warning signs"]))
vc = recap["Colour"].value_counts()
stat_cards([(str(int(vc.get("GREEN", 0))), "GREEN results", GOOD),
            (str(int(vc.get("AMBER", 0))), "AMBER results", WARN),
            (str(int(vc.get("RED", 0))), "RED results", EMBER)])'''


COLORS_CODE = r'''# The traffic light comes straight from how many forced-labour indicators appear.
rows = []
for n in [0, 1, 2, 4]:
    fake_hits = [{"indicator": "x"}] * n            # only the COUNT matters to risk_level()
    level, why = risk_level(fake_hits)
    risk, headline = TRAFFIC[level]
    rows.append({"Warning signs found": n, "Colour": risk, "What it means": headline, "Engine level": level, "Why": why})
legend = pd.DataFrame(rows)
display(pretty_table(legend, caption="What the colours mean - decided live by risk_level() from the number of indicators"))
stat_cards([("GREEN", "0 signs - looks OK, stay alert", GOOD),
            ("AMBER", "1 sign - ask questions", WARN),
            ("RED", "2+ signs - treat as serious", EMBER)])
display(Markdown(
    "The colour is not a verdict about a person - it is a prompt to **slow down and ask the right questions**. "
    "GREEN means nothing matched, not that the offer is guaranteed safe. AMBER means one warning sign worth a "
    "question. RED means two or more recognised forced-labour indicators appear together - the point to stop and "
    "get help before you pay, sign, or travel."
))'''


CATALOG_CODE = r'''# Everything the check can currently recognise - a representative slice of the DueCare
# GREP layer (production has 451 rules across 11 languages).
cat = pd.DataFrame([{
    "Warning sign": ILO_INDICATORS[k],
    "Why it matters (plain words)": PLAIN.get(k, ""),
    "Basis (ILO)": ILO_REFS.get(k, "ILO Indicators of Forced Labour (2012)"),
} for k in ILO_INDICATORS])
display(pretty_table(cat, caption=str(len(ILO_INDICATORS)) + " forced-labour warning signs the check looks for (ILO Indicators of Forced Labour, 2012, plus a recruitment-fee screen)"))

# A live look under the hood: scan() returns structured hits, not just a colour.
demo = ("The recruiter kept my passport and said I must repay the agency fee "
        "through salary deductions before I can leave.")
hits = scan(demo)
display(Markdown("**Under the hood** - `scan()` on one message returns each matched indicator with the exact words that triggered it:"))
display(pretty_table(pd.DataFrame([{
    "Indicator": h["label"], "Triggered by these words": h["snippet"], "ILO basis": h["ilo_ref"],
} for h in hits]), caption="scan() output for the demo message - " + str(len(hits)) + " indicators, each grounded in an ILO reference"))'''


HELP_CODE = r'''# The check points to real referral pathways. These are examples - in the live product the
# current numbers come from a versioned knowledge pack / tool call, never from memory.
help_rows = [{"Location": k, "Where to get help": v} for k, v in HOTLINES.items() if k != "note"]
display(pretty_table(pd.DataFrame(help_rows), caption="Referral pathways by location (pass the location name to check(message, country=...))"))
display(Markdown("> " + HOTLINES["note"]))'''


PRIVACY_CODE = r'''stat_cards([("0", "messages sent anywhere", GOOD),
            ("100%", "runs on your device", TEAL),
            ("offline", "no internet needed", INK2)])
display(Markdown(
    "This check ran **entirely on this machine**. Nothing you typed left the notebook - there is no server, "
    "no upload, and no internet call in the safety check. In the real DueCare product the same logic runs "
    "**on-device** through a small Gemma 4 model (via LiteRT / llama.cpp), so a worker can check a suspicious "
    "message on their own phone and **keep their chats, IDs, and documents private**. Only if the worker "
    "chooses to ask for help does a sanitised, PII-free summary ever leave the device."
))'''


# --------------------------------------------------------------------------- #
# markdown cells (URLs literal; HTML entities keep the source ASCII)
# --------------------------------------------------------------------------- #
HERO_MD = '''<div style="padding:26px 32px;border-radius:16px;background:linear-gradient(120deg,#14181B 0%,#2A2D34 42%,#2f7d8c 118%);color:#F7F6F1">
<div style="font-size:12px;letter-spacing:.16em;text-transform:uppercase;opacity:.82">DueCare &middot; Gemma 4 safety &middot; for workers</div>
<h1 style="margin:.28em 0 .2em;font-size:30px;color:#ffffff;font-weight:800">Is this job offer safe? A plain-language self-check</h1>
<p style="font-size:15px;line-height:1.6;margin:0;max-width:940px">You have a job offer, or a message from a recruiter, and something feels off. This notebook is for <b>a migrant worker &mdash; or a friend helping one</b>. Paste the message and get a simple <b>traffic-light safety check</b>: <b style="color:#8fd19e">GREEN</b> (looks OK, stay alert), <b style="color:#f0c674">AMBER</b> (one warning sign, ask questions), or <b style="color:#f0a582">RED</b> (serious warning signs &mdash; stop and get help). For every red flag it explains, <b>in simple words</b>, what it is and why it matters, gives you a few <b>concrete things you can do</b>, and points to <b>real help</b>. It recognises the well-known <b>ILO forced-labour warning signs</b> of recruitment fraud &mdash; fees to get a job, held passports, wages kept back, threats. It runs entirely <b>on this device</b>: nothing you type is sent anywhere.</p>
</div>'''

TOC_MD = '''## What is in this notebook

Everything here runs **locally, offline, on CPU** &mdash; no model download, no internet, nothing uploaded. Paste your own message in the first cell, or read the worked examples.

- [Try your own &mdash; paste a message and check it](#tryown)
- [Four worked examples &mdash; from a scam to a real offer](#examples)
- [What the colours mean](#colours)
- [The warning signs it looks for](#catalog)
- [Where to get help](#help)
- [Runs on your device &mdash; your privacy](#privacy)
- [Honest boundary](#boundary)

**This is not legal advice, and not a verdict about any person.** It is a friendly early-warning check built on a representative subset of the DueCare safety harness. **Source repo:** [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''

FUNC_MD = '''## The safety check, in one function

The whole check is one small function, `check(message, country)`, built directly on the DueCare engine: `scan()` finds the ILO forced-labour indicators in the text, `risk_level()` turns the count into a level, and we map that to a plain **GREEN / AMBER / RED** light with a red-flag table, a few concrete actions, and a real referral pathway. Run the cell below once to load it, then use `show_check(...)` anywhere.'''

TRYOWN_MD = '''<a id="tryown"></a>
## Try your own &mdash; paste a message and check it

Put a real (or made-up) job offer or recruiter message between the triple quotes below, set your country, and run the cell. You will get the traffic light, the specific red flags with plain-language explanations, what you can do, and where to get help. **Nothing you type leaves this notebook.**'''

EXAMPLES_MD = '''<a id="examples"></a>
## Four worked examples &mdash; from a scam to a real offer

Four short, made-up messages, each run through the same `show_check(...)`. They are composite and synthetic &mdash; no real person, number, or address. Watch how the colour and the red flags change with the content: a fee-laden Gulf offer, a controlling employer message, an ordinary honest offer, and an ambiguous one with a single small flag.'''

COLORS_MD = '''<a id="colours"></a>
## What the colours mean

The traffic light is not magic and not a judgement about anyone &mdash; it comes straight from **how many forced-labour warning signs** appear in the message. The table and tiles below are generated live by the same `risk_level()` the check uses.'''

CATALOG_MD = '''<a id="catalog"></a>
## The warning signs it looks for

These are the **ILO Indicators of Forced Labour (2012)** the check recognises, each in plain words with its ILO basis, plus a live look at how `scan()` pulls the exact triggering words out of a message. This is a **representative subset** of the real DueCare detection layer (451 rules across 11 languages).'''

HELP_MD = '''<a id="help"></a>
## Where to get help

A safety check is only useful if it connects you to real people. The check returns a referral pathway for your location. These are **examples**; hotline numbers change, so in the real product the current number always comes from an up-to-date knowledge pack, never from a model's memory.'''

PRIVACY_MD = '''<a id="privacy"></a>
## Runs on your device &mdash; your privacy

The most sensitive thing a worker has is their own story. So this check is built to need **none of it to leave the device**.'''

BOUNDARY_MD = '''<a id="boundary"></a>
## Honest boundary

**What this is.** A friendly, plain-language safety check that recognises well-known **ILO forced-labour warning signs** in a job offer or message, explains them simply, and points to real help. It runs offline, on CPU, with no model download.

**What this is not.** It is **not legal advice**, and it is **not a verdict** about any person or employer. A GREEN result is not a guarantee the offer is safe; a RED result is a prompt to slow down and get help, not proof of a crime. The detector here is a **representative subset** of the DueCare GREP layer (production has 451 rules across 11 languages) plus the ILO knowledge packs &mdash; it will miss things and it can over-flag. Trust your instincts and talk to a real person you trust.

**Privacy.** Everything you type stays in this notebook. The real product runs the same check **on-device** via Gemma 4 (LiteRT / llama.cpp); raw messages, IDs, and documents never leave the worker's phone unless they choose to send a sanitised, PII-free summary.

**Links.** Source repository: [`TaylorAmarelTech/gemma4_comp`](https://github.com/TaylorAmarelTech/gemma4_comp)'''


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
        _md(EXAMPLES_MD),
        _code(EX1_CODE),
        _code(EX2_CODE),
        _code(EX3_CODE),
        _code(EX4_CODE),
        _code(RECAP_CODE),
        _md(COLORS_MD),
        _code(COLORS_CODE),
        _md(CATALOG_MD),
        _code(CATALOG_CODE),
        _md(HELP_MD),
        _code(HELP_CODE),
        _md(PRIVACY_MD),
        _code(PRIVACY_CODE),
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
