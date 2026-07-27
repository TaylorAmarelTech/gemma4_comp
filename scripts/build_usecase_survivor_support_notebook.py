#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Survivor Support Responder use-case Kaggle notebook.

An applied, trauma-informed notebook for a hotline responder or survivor-support caseworker helping a
worker in distress. `respond(message, country)` gives a plain, validating, non-blaming reading of the
message, the red flags in plain words, IMMEDIATE safety steps, the person's rights in simple terms,
and a local referral pathway. The language is deliberately NON-alarmist and agency-preserving: a calm
risk stat card, a plain red-flag table, and a resources callout, with emergency services put first
when there is acute danger.

The notebook is FULLY SELF-CONTAINED on Kaggle: no dataset, no model, no internet. The first code
cell embeds two builder-time toolkits -- the shared DueCare notebook visualization helpers
(scripts/_notebook_viz.py) AND the grounded DueCare indicator engine (scripts/_usecase_engine.py:
scan / risk_level plus the ILO knowledge maps). It is a REPRESENTATIVE, deterministic subset of the
real 451-rule GREP layer + ILO knowledge packs; production runs the same logic on-device via Gemma 4
(LiteRT / llama.cpp) so a worker's chats, IDs, and documents never leave their phone.

    python scripts/build_usecase_survivor_support_notebook.py

ASCII-only (no Kaggle mojibake). No [:N] truncation of any displayed message or result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nbformat as nbf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _notebook_viz import HELPERS, PALETTE  # noqa: E402
from _usecase_engine import ENGINE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "usecase_survivor_support"
KERNEL_ID = "taylorsamarel/duecare-survivor-support-responder"
TITLE = "DueCare Survivor Support Responder"
DATASET_ID = "taylorsamarel/duecare-harness-benchmark-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

# ---------------------------------------------------------------------------
# Cell 4: respond() + the plain-language / rights maps + renderers. Pure, offline.
# Runs in the same namespace as the embedded PALETTE/HELPERS/ENGINE cell.
# ---------------------------------------------------------------------------
RESPOND_DEFS = '''try:                    # IPython on Kaggle; a headless fallback so the notebook always runs
    from IPython.display import display, HTML, Markdown
except Exception:
    def display(*a, **k):
        for x in a: print(getattr(x, "data", x))
    def HTML(s): return s
    def Markdown(s): return s
NL = chr(10)

# The engine's four risk levels, mapped to a CALM, non-alarmist band a responder can hold steady.
# (band label, one-line tone note, colour). The colour stays muted -- this is support, not an alarm.
CALM = {
    "LOW":      ("Steady",                 "No clear warning signs today", GOOD),
    "WATCH":    ("Worth a gentle question", "One thing worth asking about", TEAL),
    "ELEVATED": ("Let us make a plan",      "Several concerns -- go at their pace", WARN),
    "HIGH":     ("Let us focus on safety",  "Serious concerns -- safety first", EMBER),
}

# Plain, non-clinical "what this may mean" for every ILO forced-labour indicator the engine detects.
PLAIN = {
    "document_retention": "Having your passport or ID taken can leave you feeling trapped. Your documents belong to you.",
    "debt_bondage": "Being told to work off a debt before you can leave is a way some employers keep control. A debt does not make you anyone's property.",
    "recruitment_fee": "You should not have to pay to get a job. If you were charged, that was not your fault.",
    "wage_withholding": "Wages that are held back or kept for you are a way to stop you leaving. You have a right to be paid.",
    "restriction_of_movement": "Not being free to come and go is frightening. You have a right to move freely.",
    "intimidation": "Threats -- deportation, police, blacklisting -- are used to keep people silent. Asking for help is your right.",
    "deception": "If the real job or pay is different from what you were promised, being misled is not your fault.",
    "excessive_overtime": "No days off and extreme hours are not a normal job. You have a right to rest.",
    "isolation": "Being cut off -- phone taken, no way to reach family -- is a way to control people. You deserve to stay connected.",
    "abuse_of_vulnerability": "Being new, far from home, or in debt does not make any of this your fault.",
    "violence": "No one is allowed to hurt you. Violence is a crime, and your safety comes first.",
    "abusive_conditions": "Unsafe housing, no food or water, being treated as disposable -- these are warning signs, and you deserve dignity.",
}

# The person's rights in simple terms, grounded in the ILO instrument the indicator engages.
RIGHTS = {
    "document_retention": "Your passport and ID belong to you. No employer has the right to keep them (ILO C029; ICRMW Art.21).",
    "debt_bondage": "No debt makes you anyone's property, and a debt cannot force you to keep working (ILO C029; 1956 Slavery Convention).",
    "recruitment_fee": "You should not have to pay to get a job. Honest recruiters do not charge workers (ILO C181 Art.7).",
    "wage_withholding": "You have a right to be paid, in full and on time, for the work you have already done (ILO C095).",
    "restriction_of_movement": "You have the right to leave and to move freely. No one may lock you in (ILO C029).",
    "intimidation": "Asking for help is your right; threats made to keep you silent are not lawful (ILO C029).",
    "deception": "You were entitled to honest information about the job. Being misled was not your fault (ILO C181).",
    "excessive_overtime": "You have a right to rest and to reasonable working hours (ILO C001 / C030).",
    "isolation": "You have a right to contact your family and to reach the outside world (ILO 2012 indicators).",
    "abuse_of_vulnerability": "Being far from home or in debt does not take away any of your rights (ICRMW Art.21).",
    "violence": "No one is allowed to hurt you. Violence against you is a crime (ILO C029; C190).",
    "abusive_conditions": "You have a right to safe housing, to food and water, and to be treated with dignity (ILO C155).",
}

def _reading(inds, acute):
    """A short, validating, non-blaming reflection of what the person may be experiencing."""
    parts = ["Thank you for trusting someone with this. What you are describing is not your fault, and you are not in trouble for reaching out."]
    if acute:
        parts.append("Right now, the most important thing is your safety.")
    if "document_retention" in inds:
        parts.append("Having your passport or papers held can feel like being trapped -- that feeling makes sense, and it is not a reflection on you.")
    if ("wage_withholding" in inds) or ("debt_bondage" in inds) or ("recruitment_fee" in inds):
        parts.append("Being told you owe money, or not being paid, is a way some employers try to keep control. It does not make what is happening your fault.")
    if ("restriction_of_movement" in inds) or ("isolation" in inds):
        parts.append("Being cut off or unable to come and go is frightening. You deserve to feel safe and connected.")
    if not inds:
        parts.append("Nothing here jumped out as a clear warning sign, which is good to hear -- and you can reach out any time something feels wrong.")
    parts.append("We can go at your pace. You decide what happens next.")
    return " ".join(parts)

def _safety_steps(inds, acute):
    """IMMEDIATE, agency-preserving safety steps -- what the person can do now, in their control."""
    steps = []
    if acute:
        steps.append("If you are in immediate danger, contact local emergency services now -- your safety comes first.")
    steps.append("You have not done anything wrong, and you are allowed to ask for help.")
    if "document_retention" in inds:
        steps.append("If it is safe to do so, keep a photo or copy of your passport and papers somewhere private -- your documents belong to you.")
    if ("intimidation" in inds) or ("violence" in inds):
        steps.append("Try to keep any threatening messages, and note the dates and what was said, somewhere safe.")
    steps.append("Write down names, dates, and places when you can, and keep them somewhere only you can reach.")
    steps.append("Reach out to one person or service you trust -- a hotline, a caseworker, or your embassy labour attache. It is free and confidential.")
    out = []
    for s in steps:
        if s not in out:
            out.append(s)
    return out

def respond(message, country="global"):
    """A trauma-informed reading of a worker-in-distress message for a hotline responder / caseworker.

    Returns a dict with: band (a CALM, non-alarmist label) + band_note + level (the engine level),
    a validating, non-blaming reading, red_flags (each: sign / plain / words / ilo_ref), immediate
    safety_steps, rights (in simple terms, grounded in the ILO instruments), help (a local referral
    pathway), country, and acute (True when emergency services should be surfaced first). Deterministic,
    offline, CPU-only -- a representative subset of the DueCare harness, tuned for calm support.
    """
    hits = scan(message)
    level, why = risk_level(hits)
    band, band_note, band_color = CALM[level]
    inds = [h["indicator"] for h in hits]
    acute = ("violence" in inds) or (level == "HIGH")
    red_flags = [{"sign": h["label"], "plain": PLAIN.get(h["indicator"], "This is a recognised warning sign worth talking through."),
                  "words": h["snippet"], "ilo_ref": h["ilo_ref"]} for h in hits]
    rights = [RIGHTS[k] for k in dict.fromkeys(inds) if k in RIGHTS]
    rights.append("You have the right to ask for help, and asking for help is not a betrayal of anyone.")
    return {
        "band": band, "band_note": band_note, "level": level, "why": why,
        "reading": _reading(inds, acute), "red_flags": red_flags,
        "safety_steps": _safety_steps(inds, acute), "rights": rights,
        "help": HOTLINES.get(country, HOTLINES["global"]), "country": country, "acute": acute,
    }

# ---- rendering: a calm risk stat card + a plain red-flag table + a resources callout ----
def _resources_callout(res):
    tone = CALM[res["level"]][2]
    lead = "If you are in immediate danger, please contact local emergency services first. " if res["acute"] else ""
    return ('<div style="padding:16px 20px;border-radius:12px;border-left:6px solid ' + tone +
            ';background:' + PAPER2 + ';color:' + INK + '">'
            '<b>You are not alone -- here is where to get help</b><br>' + lead + str(res["help"]) +
            '<br><span style="color:' + INK3 + ';font-size:12px">' + HOTLINES["note"] + '</span></div>')

def show_response(message, country="global"):
    """Run respond() and render it: the calm stat card, the message, a trauma-informed reading, the
    plain red-flag table, immediate safety steps, rights in simple terms, and where to get help."""
    res = respond(message, country)
    color = CALM[res["level"]][2]
    stat_cards([(res["band"], res["band_note"], color),
                (len(res["red_flags"]), "things to talk through", INK2),
                (res["country"], "help location", TEAL)])
    display(Markdown("**The message:**" + NL + NL + "> " + str(message).strip().replace(NL, NL + "> ")))
    display(Markdown("**A trauma-informed reading:**" + NL + NL + res["reading"]))
    if res["red_flags"]:
        tbl = pd.DataFrame([{"What was noticed": f["sign"], "In plain words": f["plain"],
                             "What triggered it": f["words"], "Their right (ILO basis)": f["ilo_ref"]} for f in res["red_flags"]])
        display(pretty_table(tbl, caption="What the message may be pointing to -- in plain, non-clinical words"))
    else:
        display(Markdown("_No specific warning signs matched -- that is good to hear. Keep listening; the absence of a "
                         "flag is not a verdict either way._"))
    display(Markdown("**Immediate safety steps:**" + NL + NL + NL.join("- " + s for s in res["safety_steps"])))
    display(Markdown("**Their rights, in simple terms:**" + NL + NL + NL.join("- " + r for r in res["rights"])))
    display(Markdown(_resources_callout(res)))
    return res

print("respond() ready. Tracking", len(ILO_INDICATORS), "ILO indicators;", len(PATTERNS), "demo indicator rules;",
      len([k for k in HOTLINES if k != "note"]), "referral locations.")
_smoke = respond("they took my passport and I have not been paid, and I am scared to leave")
print("smoke -> band:", _smoke["band"], "| level:", _smoke["level"], "| acute:", _smoke["acute"],
      "| flags:", [f["sign"] for f in _smoke["red_flags"]])'''

# ---------------------------------------------------------------------------
# Cell 6: TRY YOUR OWN -- the paste cell, placed early so it is obvious.
# ---------------------------------------------------------------------------
TRY = '''# ============================================================================
#  TRY YOUR OWN -- paste a worker's message (composite / test data only, no real
#  PII) between the triple quotes, set the country (global, US, Philippines,
#  Nepal, "Gulf / GCC", ...), and run. respond() gives a calm, trauma-informed
#  reading, the concerns in plain words, immediate safety steps, rights in simple
#  terms, and where to get help. Nothing you type leaves this notebook.
# ============================================================================
my_message = """I came here to work in a house. They took my passport when I arrived and I have not been paid for
two months. I am not allowed to go out alone and I am starting to feel frightened. I do not know what to do."""
my_country = "Gulf / GCC"

_ = show_response(my_message, my_country)'''

# ---------------------------------------------------------------------------
# Cell 8: how it helps -- listen -> name it plainly -> safety -> rights -> refer.
# ---------------------------------------------------------------------------
HOWITWORKS = '''# respond() is five gentle steps: listen, name it plainly, immediate safety, rights, refer.
stat_cards([(len(ILO_INDICATORS), "warning signs it knows", TEAL),
            (len([k for k in HOTLINES if k != "note"]), "referral locations", INK2),
            ("on-device", "where it runs", GOOD)])

steps = pd.DataFrame({
    "step": ["1. Listen", "2. Name it plainly", "3. Immediate safety", "4. Rights", "5. Refer"],
    "what respond() does": [
        "read the person's own words -- nothing is sent anywhere",
        "recognise the ILO forced-labour warning signs and say what they are in plain, non-clinical words",
        "offer agency-preserving safety steps, and put emergency services first when there is acute danger",
        "explain the person's rights in simple terms, grounded in the ILO instruments the signs engage",
        "point to a real, local referral pathway -- the person decides whether to use it"],
    "engine call": ["scan(text)", "PLAIN / ILO_INDICATORS", "safety_steps()", "RIGHTS / ILO_REFS", "HOTLINES"]})
display(pretty_table(steps, caption="How respond() helps -- listen, name it plainly, safety, rights, refer"))

band = pd.DataFrame({
    "warning signs": ["4 or more", "2 - 3", "1", "0"],
    "calm band": ["Let us focus on safety", "Let us make a plan", "Worth a gentle question", "Steady"],
    "the tone it sets": ["safety first, without alarm", "steady, plan together, at their pace",
                         "gentle, curious, one question", "reassuring, door left open"]})
display(pretty_table(band, caption="Calm banding -- the same risk_level() count, mapped to a non-alarmist tone"))
print("The band never shouts. A calm, agency-preserving tone keeps trust; the person decides what happens next.")'''

# ---------------------------------------------------------------------------
# Cell 10: the four composite messages.
# ---------------------------------------------------------------------------
MESSAGES_DEF = '''# Four COMPOSITE / SYNTHETIC messages. No real people, no real PII. They show the range: a serious
# Gulf domestic-work case, an ambiguous fee question, a benign check-in, and an acute-danger message.
MESSAGES = {
"A -- passport taken, unpaid (Gulf domestic work)": ("""I came to work as a housemaid far from home. When I
arrived they took my passport and said they would keep it. I have not been paid for two months and I am told I
must first work off the fee I was charged. I cannot leave the house on my own and I am frightened.""", "Gulf / GCC"),
"B -- an ambiguous fee question": ("""A recruiter offered me a cleaning job and asked for a small processing fee
before I start. The pay sounds okay and everything else seems normal. I am just not sure if paying this fee is
usual. What do you think?""", "Philippines"),
"C -- a benign check-in": ("""I just wanted to check in and say things are going okay. I get paid on time, I have
one rest day a week, and I can come and go freely. Thank you for being there.""", "global"),
"D -- acute danger": ("""My employer hit me last night and locked me in the room. They took my phone and I
managed to send this quickly while they are out. I am scared and I do not know what to do.""", "global"),
}
print("defined", len(MESSAGES), "composite messages:")
for k in MESSAGES:
    print("   -", k)'''

EX_A = '''_ = show_response(*MESSAGES["A -- passport taken, unpaid (Gulf domestic work)"])'''
EX_B = '''_ = show_response(*MESSAGES["B -- an ambiguous fee question"])'''
EX_C = '''_ = show_response(*MESSAGES["C -- a benign check-in"])'''
EX_D = '''# Acute danger: respond() surfaces emergency services FIRST and keeps the tone steady, not alarmed.
_ = show_response(*MESSAGES["D -- acute danger"])'''

# ---------------------------------------------------------------------------
# Cell 19: trauma-informed principles.
# ---------------------------------------------------------------------------
PRINCIPLES = '''# The principles this responder is built around -- and how each shows up in respond().
principles = pd.DataFrame({
    "principle": ["Safety first", "Trustworthiness", "Choice and control", "Do not blame",
                  "Plain language", "Confidentiality"],
    "how this tool honours it": [
        "when there is acute danger, emergency services come before anything else",
        "it says what it noticed and why, and never pretends to be a caseworker or the law",
        "it offers options, not orders -- the person decides what happens next",
        "every message reflects that the situation is not the person's fault",
        "it explains warning signs and rights in simple, non-clinical words",
        "nothing the person says leaves the device unless they choose to seek help"]})
display(pretty_table(principles, caption="Trauma-informed principles this responder is built around"))
stat_cards([("safety", "always comes first", EMBER),
            ("choice", "the person stays in control", TEAL),
            ("no blame", "it is never their fault", GOOD)])
print("A responder that alarms or blames loses trust. Calm, validating, agency-preserving language keeps the door open.")'''

# ---------------------------------------------------------------------------
# Cell 21: trust / privacy -- what stays on the device.
# ---------------------------------------------------------------------------
PRIVACY = '''# The data-flow boundary, made explicit. Nothing here calls out; respond() is pure local Python.
stat_cards([("0", "messages sent anywhere", GOOD),
            ("100%", "runs on the device", TEAL),
            ("offline", "no internet needed", INK2)])
flow = pd.DataFrame({
    "data": ["the worker's message (their own words)",
             "the trauma-informed reading and safety steps",
             "an anonymized, PII-free summary"],
    "where it lives": ["the responder's / worker's device only",
                       "the device only",
                       "shared only if the person chooses to seek help"],
    "leaves the device?": ["never", "never", "only after the person opts in"]})
display(pretty_table(flow, caption="Trust boundary -- the person's words stay on the device"))
print("In the real product the same reading runs on-device via Gemma 4 (LiteRT / llama.cpp), so a worker can use it")
print("on their own phone. Only if they choose to ask for help does a sanitised, PII-free summary ever leave.")'''


def _toc() -> str:
    items = [
        ("1", "Try your own message", "try"),
        ("2", "How it helps: listen, name it plainly, safety, rights, refer", "how"),
        ("3", "Four worked examples", "examples"),
        ("4", "Trauma-informed principles", "principles"),
        ("5", "Runs on the device: privacy", "privacy"),
        ("6", "Honest boundary + go to production", "boundary"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c: list = []

    # ---- Section 0: hero + who it is for + the problem + emergency note + TOC + honest boundary ----
    c.append(md(
        "# DueCare Survivor Support Responder\n\n"
        "**For a hotline responder or a survivor-support caseworker.** A migrant worker reaches out, frightened and "
        "unsure, and the first minutes matter. This notebook turns one worker's message into a **calm, "
        "trauma-informed reading**: a plain, validating reflection of what they may be experiencing (you are not to "
        "blame), the warning signs in simple words, **immediate safety steps** they can take, their **rights in "
        "plain terms**, and a local referral pathway -- all **on your own device**, with no model, no internet, and "
        "nothing leaving the machine.\n\n"
        "> **If you or the person you are helping is in immediate danger, contact local emergency services first.** "
        "This notebook is a support aid, not an emergency service.\n\n"
        "**The problem it helps with.** In a first conversation it is hard to stay calm, name the risk accurately, "
        "and still keep the person in control of what happens next. `respond()` gives every message the same steady, "
        "non-alarmist reading -- it validates, it explains the warning signs and rights plainly, it puts safety "
        "first, and it always leaves the choice with the person.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** This notebook runs a **representative, deterministic subset** of the "
        "DueCare harness -- a compact indicator scanner plus the ILO knowledge map -- so it is fully reproducible "
        "offline. It is a support aid: **not** a substitute for a trained responder, a caseworker, or emergency "
        "services, and **not** legal advice or a verdict about any person. Every message here is composite / "
        "synthetic (no real people, no real PII). Production DueCare runs the same logic on-device via Gemma 4 "
        "(LiteRT / llama.cpp)."))

    # ---- Setup ----
    c.append(md(
        "## Setup -- run these two cells once\n\n"
        "The first cell embeds the DueCare notebook visualization toolkit **and** the grounded indicator engine "
        "(the ILO indicators, the `scan()` / `risk_level()` logic, and the knowledge maps). The second defines "
        "`respond()`, the plain-language and rights maps, and the renderers. After both run, everything else is "
        "self-contained: **no dataset, no model, no internet.**"))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + ENGINE))
    c.append(code(RESPOND_DEFS))

    # ---- Section 1: TRY YOUR OWN ----
    c.append(md(
        '<a id="try"></a>\n## 1 - Try your own message\n\n'
        "**Edit the `my_message` string in the next cell** -- paste a worker's message (composite or test data, "
        "please: no real PII in a shared notebook), set the country, and run it. `respond()` returns the structured "
        "result and `show_response()` draws the calm risk card, a trauma-informed reading, the red-flag table, "
        "immediate safety steps, the person's rights, and where to get help. Everything runs locally.\n\n"
        "*(Run the two setup cells above first -- they embed the visualization toolkit and the DueCare indicator "
        "engine so the notebook is completely self-contained.)*"))
    c.append(code(TRY))

    # ---- Section 2: how it helps ----
    c.append(md(
        '<a id="how"></a>\n## 2 - How it helps: listen, name it plainly, safety, rights, refer\n\n'
        "`respond()` is five gentle steps -- no black box, and never alarmist:\n\n"
        "```\n"
        "the worker's message (their own words, stay on the device)\n"
        "        |\n"
        "  [1] listen           read the message -- nothing is sent anywhere\n"
        "  [2] name it plainly  recognise the ILO forced-labour warning signs; say what they are in plain words\n"
        "  [3] immediate safety agency-preserving steps; emergency services first when there is acute danger\n"
        "  [4] rights           the person's rights in simple terms, grounded in the ILO instruments\n"
        "  [5] refer            a real, local referral pathway -- the person decides whether to use it\n"
        "        |\n"
        "  a calm, trauma-informed response (validating, in the person's control)\n"
        "```\n\n"
        "The next cell shows the coverage, the five-step map, and the **calm banding**: the same `risk_level()` "
        "count the other DueCare tools use, mapped to a steady, non-alarmist tone instead of an alarm."))
    c.append(code(HOWITWORKS))

    # ---- Section 3: four worked examples ----
    c.append(md(
        '<a id="examples"></a>\n## 3 - Four worked examples\n\n'
        "Four **composite / synthetic** messages, each run through the same `show_response()`. Watch how the tone "
        "and the guidance change with the content: a serious Gulf domestic-work case, an ambiguous fee question, a "
        "benign check-in that should stay **Steady**, and an acute-danger message where the response puts emergency "
        "services first. No message describes a real person, and full message text is preserved -- nothing is "
        "truncated."))
    c.append(code(MESSAGES_DEF))
    c.append(md(
        "### 3A - Passport taken, unpaid (Gulf domestic work)\n"
        "Several serious concerns together -- a held passport, unpaid wages, a fee to work off, and confinement. The "
        "reading validates the fear, names each concern plainly, and routes to help."))
    c.append(code(EX_A))
    c.append(md(
        "### 3B - An ambiguous fee question\n"
        "One small warning sign and an honest question. The tone stays gentle and curious -- a single question to "
        "ask, not an alarm."))
    c.append(code(EX_B))
    c.append(md(
        "### 3C - A benign check-in\n"
        "Paid on time, a rest day, free to come and go. A calm tool must be willing to say **Steady** -- a responder "
        "that cried wolf on every message would lose trust."))
    c.append(code(EX_C))
    c.append(md(
        "### 3D - Acute danger\n"
        "Violence and confinement. The response puts **local emergency services first**, keeps the tone steady "
        "rather than panicked, and still centres the person's own choices."))
    c.append(code(EX_D))

    # ---- Section 4: trauma-informed principles ----
    c.append(md(
        '<a id="principles"></a>\n## 4 - Trauma-informed principles\n\n'
        "The response is written around well-established trauma-informed principles: safety first, trustworthiness, "
        "choice and control, and a refusal to blame. A tool that alarms or judges loses the trust that makes help "
        "possible. The cell below lists the principles and how each one shows up in `respond()`."))
    c.append(code(PRINCIPLES))

    # ---- Section 5: privacy ----
    c.append(md(
        '<a id="privacy"></a>\n## 5 - Runs on the device: privacy\n\n'
        "The most sensitive thing a worker has is their own story. This responder is built so **none of it has to "
        "leave the device**:\n\n"
        "- **The worker's words stay local.** `respond()` is pure Python running in this notebook -- no request goes "
        "anywhere.\n"
        "- **Only an anonymized, PII-free summary can ever be shared**, and only if the person chooses to seek help. "
        "In production the DueCare anonymizer (a hard PII gate) redacts names, IDs, and phone numbers **before** "
        "anything is shareable.\n"
        "- **The person controls every step** -- what is written down, what is shared, and whether anything is "
        "shared at all.\n\n"
        "The cell below shows the data-flow boundary explicitly."))
    c.append(code(PRIVACY))

    # ---- Section 6: honest boundary + go to production ----
    c.append(md(
        '<a id="boundary"></a>\n## 6 - Honest boundary + go to production\n\n'
        "**What this is.** A calm, trauma-informed support aid that recognises well-known **ILO forced-labour "
        "warning signs** in a worker's message, reflects them back in plain words, offers immediate safety steps and "
        "rights, and points to real help. It runs offline, on CPU, with no model download.\n\n"
        "**What this is not.** It is **not a substitute for a trained responder, a caseworker, or emergency "
        "services**, and it is **not legal advice** or a verdict about any person. **If someone is in immediate "
        "danger, contact local emergency services.** A **Steady** result is not a guarantee of safety; a "
        "**safety-first** result is a prompt to help the person get support, not proof of a crime. The detector here "
        "is a **representative subset** of the DueCare GREP layer (production has 451 rules across 11 languages) plus "
        "the ILO knowledge packs -- it will miss things and it can over-flag.\n\n"
        "**Go to production.** The production system runs the full harness -- 451 GREP indicator rules across 11 "
        "languages, retrieval over an ILO / trafficking corpus, and **Gemma 4** doing the reasoning -- **on-device** "
        "via LiteRT / llama.cpp, so a worker can use it on their own phone and keep their chats, IDs, and documents "
        "private. Install the `duecare-llm-*` family (`pip install duecare-llm-core duecare-llm-chat`); the "
        f"published benchmark grades live on Kaggle (e.g. `{DATASET_ID}`), and the [repository]({REPO}) has the "
        "harness, the grader, and the fine-tuning path.\n\n"
        "License: MIT. Everything in this notebook is composite / synthetic -- no real people, no real PII.\n\n"
        "[Back to contents](#try)"))

    nb = nbf.v4.new_notebook()
    nb["cells"] = c
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                      "language_info": {"name": "python"}}
    nbf.validate(nb)
    nbf.write(nb, str(nb_dir / "notebook.ipynb"))

    meta = {"id": KERNEL_ID, "title": TITLE, "code_file": "notebook.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": False, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    raw = (nb_dir / "notebook.ipynb").read_text(encoding="utf-8")
    non_ascii = sorted({ch for ch in raw if ord(ch) > 127})
    return {"kernel_id": KERNEL_ID, "title": TITLE, "cells": len(c),
            "code_cells": sum(1 for x in c if x.cell_type == "code"), "notebook_dir": str(nb_dir),
            "non_ascii_chars": "".join(non_ascii)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    summary = build(args.output, force=args.force)
    slug = summary["kernel_id"].split("/", 1)[1]
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    assert TITLE.lower().replace(" ", "-") == "duecare-survivor-support-responder"
    assert not summary["non_ascii_chars"], f"non-ASCII leaked into the notebook: {summary['non_ascii_chars']!r}"
    summary["title_slug_ok"] = True
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
