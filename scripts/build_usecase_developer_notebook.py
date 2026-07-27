#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Developer Integration use-case Kaggle notebook.

An applied, easy-to-use notebook for a developer or integration partner who wants to add DueCare's
forced-labour safety analysis to their product. It shows the EASY unified interface -- a single
`analyze(text) -> dict` call that returns indicators + risk + a reasoned chain + ILO citations +
referral resources -- and then the three deployment modes built on that one call: an enterprise
moderation waterfall, an on-device worker app (LiteRT / Gemma 4 framing), and an NGO batch
dashboard. It also shows the request/response contract, a pip-install / repo-source snippet, and how
to swap the embedded deterministic engine for the full Gemma-4-backed harness without changing any
call sites.

The notebook is FULLY SELF-CONTAINED on Kaggle: no dataset, no model, no internet. The first code
cell embeds two builder-time toolkits -- the shared DueCare notebook visualization helpers
(scripts/_notebook_viz.py) AND the grounded DueCare indicator engine (scripts/_usecase_engine.py:
scan / risk_level / generate_chain plus the ILO knowledge maps). It is a REPRESENTATIVE,
deterministic subset of the real 451-rule GREP layer + ILO knowledge packs; production uses the full
harness with retrieval and Gemma 4 reasoning.

    python scripts/build_usecase_developer_notebook.py

ASCII-only (no Kaggle mojibake). No [:N] truncation of any displayed input or result.
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "usecase_developer"
KERNEL_ID = "taylorsamarel/duecare-developer-integration"
TITLE = "DueCare Developer Integration"
DATASET_GRADES = "taylorsamarel/duecare-harness-benchmark-grades"
DATASET_PERDIM = "taylorsamarel/duecare-harness-perdim-grades"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"

# ---------------------------------------------------------------------------
# Cell 4: analyze() -- the one unified call -- plus a compact renderer. Offline.
# Runs in the same namespace as the embedded PALETTE/HELPERS/ENGINE cell.
# ---------------------------------------------------------------------------
ANALYZE_DEFS = '''try:                                 # IPython on Kaggle; a headless fallback so the notebook always runs
    from IPython.display import display, HTML, Markdown
except Exception:
    def display(*a, **k):
        for x in a: print(getattr(x, "data", x))
    def HTML(s): return s
    def Markdown(s): return s

RISK_COLOR = {"HIGH": EMBER, "ELEVATED": WARN, "WATCH": TEAL, "LOW": GOOD}

def analyze(text):
    """The one unified DueCare call. Give it text, get one JSON-serializable dict back:

      risk         : {level, reason}                       -- HIGH / ELEVATED / WATCH / LOW + rationale
      n_indicators : int                                   -- how many forced-labour indicators fired
      indicators   : [{indicator, label, snippet, ilo_ref}]-- each hit + the cue + the ILO instrument
      citations    : [str]                                 -- sorted unique controlling ILO instruments
      reasoning    : [{step, text}]                        -- the structured audit trail (generate_chain)
      resources    : {...}                                 -- referral hotlines / pathways (verify before use)
      meta         : {engine, n_rules_demo, n_rules_production}

    Deterministic, offline, CPU-only -- a representative subset of the DueCare harness. In production
    the SAME dict shape is returned by the full Gemma-4-backed harness (see the swap section).
    """
    hits = scan(text)
    level, why = risk_level(hits)
    chain = generate_chain(text)
    return {
        "risk": {"level": level, "reason": why},
        "n_indicators": len(hits),
        "indicators": hits,
        "citations": sorted({h["ilo_ref"] for h in hits}),
        "reasoning": [{"step": n, "text": t} for n, t in chain],
        "resources": HOTLINES,
        "meta": {"engine": "duecare-usecase-engine (representative subset)",
                 "n_rules_demo": len(PATTERNS), "n_rules_production": 451},
    }

def show_analysis(text, res=None):
    """Pretty-print an analyze() result: a risk card + the indicator/citation table."""
    res = res or analyze(text)
    print("INPUT:"); print(text); print()
    stat_cards([(res["risk"]["level"], "risk level", RISK_COLOR.get(res["risk"]["level"], INK2)),
                (res["n_indicators"], "indicators", TEAL),
                (len(res["citations"]), "ILO citations", INK2)])
    if res["indicators"]:
        det = pd.DataFrame([{"ILO indicator": h["label"], "matched cue": h["snippet"], "instrument": h["ilo_ref"]}
                            for h in res["indicators"]])
        display(pretty_table(det, caption="indicators + citations from analyze()"))
    else:
        print("No indicators detected (LOW). Absence of indicators is not evidence of safety.")
    return res

print("analyze() ready ->", len(ILO_INDICATORS), "ILO indicators,", len(PATTERNS), "demo rules.")
_smoke = analyze("they took my passport and I have not been paid for two months")
print("smoke -> risk:", _smoke["risk"]["level"], "| indicators:", _smoke["n_indicators"],
      "| citations:", len(_smoke["citations"]), "| reasoning steps:", len(_smoke["reasoning"]))'''

# ---------------------------------------------------------------------------
# Cell 6: TRY YOUR OWN -- call analyze() on your text, near the top.
# ---------------------------------------------------------------------------
TRY = '''# ============================================================================
#  TRY YOUR OWN -- paste text between the triple quotes and run. One call.
#  (Composite or test data please: no real PII in a shared notebook.)
# ============================================================================
text = """We can offer you overseas factory work starting now. There is a processing fee of 1,800 that we
deduct from your salary each month, and we keep your passport for safekeeping. You cannot leave the site
without permission."""

result = analyze(text)
show_analysis(text, result)
print()
print("The returned object is a plain dict -- keys:", list(result.keys()))'''

# ---------------------------------------------------------------------------
# Cell 8-9: the unified interface + a one-call/three-deployments diagram.
# ---------------------------------------------------------------------------
INTERFACE = '''import json
res = analyze("They took my passport on arrival and I have not been paid for two months.")
print("analyze() returns ONE JSON-serializable dict. Top-level keys:")
print("   " + ", ".join(res.keys()))
print()
# A compact projection for a quick look (the FULL dict is returned intact; nothing is dropped).
compact = {"risk": res["risk"], "n_indicators": res["n_indicators"],
           "indicators": [h["label"] for h in res["indicators"]],
           "citations": res["citations"], "reasoning_steps": len(res["reasoning"])}
print(json.dumps(compact, indent=2))

# The full structured reasoning is part of the same object -- shown here in full (nothing truncated).
rdf = pd.DataFrame(res["reasoning"])
display(pretty_table(rdf, caption="analyze()['reasoning'] -- the full structured audit trail returned with every call"))

stat_cards([("1", "function to call", TEAL),
            (len(ILO_INDICATORS), "ILO indicators", INK2),
            ("dict", "JSON-serializable out", GOOD),
            ("offline", "no GPU / net / model", EMBER)])'''

DIAGRAM = '''fig, ax = plt.subplots(figsize=(10.6, 2.3)); ax.axis("off"); ax.set_xlim(0, 10.4); ax.set_ylim(0, 2)
stages = [("text in", "a post, message, or filing", INK3),
          ("analyze()", "the one unified call", TEAL),
          ("dict out", "risk + indicators + citations\\n+ reasoning + resources", GOOD)]
xs = [0.5, 4.0, 7.5]; w = 2.4
for (t, s, col), x in zip(stages, xs):
    ax.add_patch(FancyBboxPatch((x, 0.5), w, 1.0, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=PAPER2, edgecolor=col, linewidth=2.4))
    ax.text(x + w / 2, 1.15, t, ha="center", va="center", fontsize=11.5, fontweight="bold", color=INK)
    ax.text(x + w / 2, 0.78, s, ha="center", va="center", fontsize=8.2, color=INK3)
for i in range(len(xs) - 1):
    ax.annotate("", xy=(xs[i + 1] - 0.04, 1.0), xytext=(xs[i] + w + 0.04, 1.0),
                arrowprops=dict(arrowstyle="-|>", color=INK3, lw=1.9))
plt.tight_layout(); plt.show()

# The same one call powers all three deployment patterns below.
stat_cards([("Enterprise", "waterfall: filter -> analyze()", GOOD),
            ("On-device", "same analyze(), on the phone", EMBER),
            ("NGO", "batch analyze() dashboard", TEAL)])'''

# ---------------------------------------------------------------------------
# Cell 11: the request/response contract (a pretty_table of the fields).
# ---------------------------------------------------------------------------
CONTRACT = '''contract = pd.DataFrame([
    {"field": "risk.level",   "type": "str",        "description": "HIGH / ELEVATED / WATCH / LOW"},
    {"field": "risk.reason",  "type": "str",        "description": "one-line rationale for the band"},
    {"field": "n_indicators", "type": "int",        "description": "number of forced-labour indicators detected"},
    {"field": "indicators[]", "type": "list[dict]", "description": "each: indicator, label, matched snippet, ilo_ref"},
    {"field": "citations[]",  "type": "list[str]",  "description": "sorted unique controlling ILO instruments"},
    {"field": "reasoning[]",  "type": "list[dict]", "description": "structured audit trail: step number + text"},
    {"field": "resources",    "type": "dict",       "description": "referral hotlines / pathways (verify before use)"},
    {"field": "meta",         "type": "dict",       "description": "engine name + demo / production rule counts"},
])
display(pretty_table(contract, caption="analyze() response contract -- the stable dict shape your product integrates against"))
print("Request : analyze(text: str)")
print("Response: the dict above -- JSON-serializable, so you can return it straight from an HTTP handler:")
print()
print("    @app.post('/analyze')")
print("    def handler(body):")
print("        return analyze(body['text'])        # -> the contract above, as JSON")'''

# ---------------------------------------------------------------------------
# Cell 12: prove the contract is JSON-safe end to end (serialize -> parse back).
# ---------------------------------------------------------------------------
JSON_ROUNDTRIP = '''import json
# The contract is JSON-safe end to end: dump a full analyze() result and read it straight back.
payload = analyze("They keep my passport and I have not been paid; I cannot leave until I work off the fee.")
wire = json.dumps(payload)                          # serialize -- exactly what an HTTP handler returns
restored = json.loads(wire)                         # a client parses it back
assert restored["risk"]["level"] == payload["risk"]["level"], "risk survives the round-trip"
assert restored["citations"] == payload["citations"], "citations survive the round-trip"
print("round-trip OK -- %d bytes on the wire, %d top-level keys, risk=%s, citations=%d"
      % (len(wire), len(restored), restored["risk"]["level"], len(restored["citations"])))
print("first reasoning step over the wire:", restored["reasoning"][0]["text"])'''

# ---------------------------------------------------------------------------
# Cell 13: Pattern 1 -- enterprise moderation waterfall.
# ---------------------------------------------------------------------------
PATTERN_ENTERPRISE = '''# Pattern 1 -- ENTERPRISE WATERFALL (job board / social platform).
# A cheap keyword filter runs on EVERY item; the expensive analyze() runs only on the suspicious few.
_KW = ["passport", "visa", "iqama", "fee", "deposit", "bond", "debt", "loan", "advance", "recruit",
       "placement", "agency", "broker", "salary", "wage", "withheld", "overtime", "no day off",
       "document", "permit", "cannot leave", "not allowed", "no phone", "sleep on the floor"]
def cheap_prefilter(text):
    """Stage 1 (near-free): True if any recruitment-risk keyword is present."""
    t = (text or "").lower()
    return any(k in t for k in _KW)

DECISION = {"LOW": "WATCH", "WATCH": "WARN", "ELEVATED": "QUEUE", "HIGH": "QUEUE"}
def moderate_post(text):
    """Enterprise integration: cheap filter -> analyze() -> routing decision.
    Returns {decision, risk, indicators, citations}. CLEAR posts never reach analyze()."""
    if not cheap_prefilter(text):
        return {"decision": "CLEAR", "risk": "LOW", "indicators": 0, "citations": []}
    res = analyze(text)
    return {"decision": DECISION[res["risk"]["level"]], "risk": res["risk"]["level"],
            "indicators": res["n_indicators"], "citations": res["citations"]}

demo_posts = [
    "Now hiring baristas downtown, flexible shifts, training provided.",
    "Nursing role, visa sponsorship available, the agency never charges candidates a fee.",
    "Warehouse packers wanted, one-time placement fee of 500 to reserve your slot.",
    "Overseas placement: processing fee applies, salary deducted monthly, and we keep your passport.",
]
rows = [dict(post=p, **moderate_post(p)) for p in demo_posts]
mdf = pd.DataFrame(rows)
mdf["citations"] = mdf["citations"].apply(lambda cs: "; ".join(cs))
display(pretty_table(mdf, caption="Pattern 1: enterprise waterfall -- CLEAR (publish) / WATCH (log) / WARN (user popup) / QUEUE (human)"))
print("CLEAR posts skip analyze() entirely -- the expensive call runs only on the flagged few.")'''

# ---------------------------------------------------------------------------
# Cell 15: Pattern 2 -- on-device worker app.
# ---------------------------------------------------------------------------
PATTERN_ONDEVICE = '''# Pattern 2 -- ON-DEVICE (worker app). The SAME analyze() call. In production the model backend is
# Gemma 4 running locally via LiteRT / llama.cpp, so the worker's text never leaves the phone.
def worker_check(offer):
    """On-device integration: identical analyze() call; render a worker-friendly traffic-light summary."""
    res = analyze(offer)
    light = {"HIGH": "RED", "ELEVATED": "RED", "WATCH": "AMBER", "LOW": "GREEN"}[res["risk"]["level"]]
    lines = ["**Safety check: " + light + "**  (risk band: " + res["risk"]["level"] + ")", ""]
    if res["indicators"]:
        lines.append("Red flags found in this offer:")
        for h in res["indicators"]:
            lines.append("- " + h["label"] + "  (" + h["ilo_ref"] + ")")
    else:
        lines.append("No clear red flags -- but stay careful; this is not a guarantee.")
    lines += ["", "Where to get free, confidential help: " + res["resources"]["global"]]
    display(Markdown("\\n".join(lines)))
    return res

offer = """They said it would be office work, but actually it is fishing at sea for months. They keep your
passport, and you owe a recruitment fee you must work off before you can leave."""
_ = worker_check(offer)
print()
print("The analyze() call is byte-for-byte identical to the server integration -- only the model backend")
print("differs (Gemma 4 on-device via LiteRT / llama.cpp). Same contract, same code, private by construction.")'''

# ---------------------------------------------------------------------------
# Cell 17: Pattern 3 -- NGO batch dashboard.
# ---------------------------------------------------------------------------
PATTERN_DASHBOARD = '''# Pattern 3 -- NGO DASHBOARD (batch). Call analyze() over a list; build a review table, riskiest first.
def batch_dashboard(items):
    """NGO integration: batch analyze() -> one row per item for a review dashboard (full text kept)."""
    rows = []
    for it in items:
        res = analyze(it["text"])
        rows.append({"id": it["id"], "risk": res["risk"]["level"], "indicators": res["n_indicators"],
                     "top citation": (res["citations"][0] if res["citations"] else ""),
                     "text": it["text"]})
    return pd.DataFrame(rows)

caseload = [
    {"id": "C-1", "text": "Stable factory job, salary on time, one rest day a week, free to come and go."},
    {"id": "C-2", "text": "The agency charged a placement fee I am still repaying and I cannot leave until it is paid off."},
    {"id": "C-3", "text": "They took my passport, I sleep on the floor in a crowded room, and there is no day off."},
]
board = batch_dashboard(caseload)
RANK = {"HIGH": 3, "ELEVATED": 2, "WATCH": 1, "LOW": 0}
board = (board.assign(_r=board.risk.map(RANK)).sort_values("_r", ascending=False)
              .drop(columns="_r").reset_index(drop=True))
display(pretty_table(board, caption="Pattern 3: NGO dashboard -- batch analyze(), riskiest first (full text shown, nothing truncated)"))'''

# ---------------------------------------------------------------------------
# Cell 19: swap the engine for the full Gemma-4 harness (same call sites).
# ---------------------------------------------------------------------------
SWAP = '''# Swap the deterministic engine for the full Gemma-4 harness WITHOUT touching your call sites:
# analyze(text) -> dict IS the interface. A factory returns the offline analyzer by default; in
# production it returns a Gemma-4-backed analyzer with the SAME dict shape.
def make_analyzer(backend="offline"):
    """Return an analyzer callable honoring the analyze(text) -> dict contract."""
    if backend == "offline":
        return analyze                       # this notebook: deterministic, CPU, offline
    raise NotImplementedError(
        "In production return a Gemma-4-backed analyzer with the SAME dict shape, e.g.:\\n"
        "    from duecare.chat.harnesses import default_harness\\n"
        "    harness = default_harness()      # Persona + GREP(451) + RAG + tools\\n"
        "    return lambda text: harness.analyze(text)")

analyzer = make_analyzer("offline")
print("resolved analyzer backend: offline (deterministic representative subset)")
print("sample ->", analyzer("they took my passport and withheld my wages")["risk"]["level"])
print()

PROD_SNIPPET = """# Development / CI / air-gapped: the embedded deterministic engine (this notebook).
analyzer = make_analyzer("offline")

# Production: the full harness -- same analyze(text) -> dict contract, Gemma 4 does the reasoning.
# pip install duecare-llm-core duecare-llm-chat
from duecare.chat.harnesses import default_harness
harness = default_harness()               # Persona + GREP (451 rules, 11 languages) + RAG + tools
def analyze(text):
    return harness.analyze(text)          # identical dict shape; model-backed, retrieval-grounded"""
print(PROD_SNIPPET)'''

# ---------------------------------------------------------------------------
# Cell 21: install + a CI-style self-test against the contract.
# ---------------------------------------------------------------------------
SELFTEST = '''# Install (shown for reference -- THIS notebook needs no install; it is self-contained):
INSTALL = """pip install duecare-llm-core duecare-llm-chat        # or the full duecare-llm-* family
# ...or straight from source:
pip install "git+https://github.com/TaylorAmarelTech/gemma4_comp" """
print(INSTALL); print()

# A CI-style self-test: the SHAPE of a test you would run against the published DueCare benchmark.
# It asserts the contract holds and that the risk ordering is monotone on three labeled probes.
def _risk_rank(text): return {"LOW": 0, "WATCH": 1, "ELEVATED": 2, "HIGH": 3}[analyze(text)["risk"]["level"]]
benign = "Stable job, salary paid on time, free to come and go, one rest day a week."
one    = "There is a one-time placement fee to reserve the slot."
many   = "They took my passport, withheld my wages, and I cannot leave until I work off the debt; no day off."

res = analyze(many)
assert set(res.keys()) >= {"risk", "indicators", "citations", "reasoning", "resources", "meta"}, "contract keys present"
assert isinstance(res["citations"], list) and all(isinstance(c, str) for c in res["citations"]), "citations well-typed"
assert _risk_rank(benign) < _risk_rank(one) < _risk_rank(many), "risk ordering is monotone"
print("self-test PASSED: contract keys present, citations well-typed, risk ordering monotone.")
print("   benign  ->", analyze(benign)["risk"]["level"])
print("   one-flag->", analyze(one)["risk"]["level"])
print("   many    ->", analyze(many)["risk"]["level"])'''

# ---------------------------------------------------------------------------
# Cell 23: trust boundary + honest boundary card.
# ---------------------------------------------------------------------------
BOUNDARY = '''tb = ("<div style='background:#f0d8c8;border:1px solid #c15b2e;border-left:6px solid #c15b2e;"
      "border-radius:10px;padding:15px 18px;font-family:Inter,-apple-system,system-ui,sans-serif;"
      "color:#14181B;max-width:700px'>"
      "<div style='font-size:14px;font-weight:700'>Trust boundary</div>"
      "<div style='font-size:12.5px;color:#2A2D34;margin-top:6px'>analyze() runs wherever you deploy it -- "
      "your server, or on the worker's device via Gemma 4 (LiteRT / llama.cpp). No raw text has to leave that "
      "boundary: the same call works air-gapped. In the on-device pattern the worker's messages, IDs, and "
      "documents never leave the phone unless the worker explicitly shares a sanitized submission.</div></div>")
display(HTML(tb))
stat_cards([("1 call", "analyze(text) -> dict", TEAL),
            ("3", "deployment patterns", INK2),
            ("same", "dict shape everywhere", GOOD),
            ("MIT", "open source", EMBER)])'''


def _toc() -> str:
    items = [
        ("1", "Try it yourself: call analyze()", "try"),
        ("2", "The unified interface", "interface"),
        ("3", "The request/response contract", "contract"),
        ("4", "The three integration patterns", "patterns"),
        ("5", "Swap in the full Gemma 4 harness", "swap"),
        ("6", "Install + test against the benchmark", "test"),
        ("7", "Trust boundary + honest boundary", "boundary"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c: list = []

    # ---- Section 0: hero + who it is for + the problem + TOC + honest boundary ----
    c.append(md(
        "# DueCare Developer Integration\n\n"
        "**For the developer or integration partner.** You have a product -- a job board, a messaging app, a "
        "case-management dashboard -- and you want to add forced-labour and recruitment-fraud safety analysis "
        "without becoming an expert in ILO conventions or standing up a model yourself. This notebook shows the "
        "**easy path**: one function, `analyze(text)`, that returns everything you need as a plain dict -- the "
        "forced-labour indicators, the risk band, a reasoned chain, the ILO citations, and referral resources -- "
        "and then the **three deployment modes** built on that single call.\n\n"
        "**The problem it helps with.** Safety analysis is usually all-or-nothing: either you ship nothing, or you "
        "take on a whole ML stack. DueCare gives you one stable interface. The same `analyze()` call powers an "
        "enterprise moderation waterfall, an on-device worker app, and an NGO batch dashboard -- and you can start "
        "with the deterministic engine embedded here and swap in the full Gemma-4-backed harness later **without "
        "changing a single call site**.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** This notebook runs a **representative, deterministic subset** of the "
        "DueCare harness -- a compact indicator scanner plus the ILO knowledge map -- so it is fully reproducible "
        "offline. `analyze()` flags *indicators* and returns *decision support*; it is **not** a trafficking "
        "determination, **not** legal advice, and **not** an automated-takedown engine. Every input here is "
        "composite / synthetic (no real people, no real PII). Production DueCare uses the full 451-rule GREP layer, "
        "retrieval, and Gemma 4 reasoning behind the *same* dict contract (see the swap section)."))

    # ---- Setup ----
    c.append(md(
        "## Setup -- run these two cells once\n\n"
        "The first cell embeds the DueCare notebook visualization toolkit **and** the grounded indicator engine "
        "(the ILO indicators, the `scan()` / `risk_level()` / `generate_chain()` logic, and the knowledge maps). "
        "The second defines `analyze()` -- the one call you integrate against -- plus a small renderer. After both "
        "run, everything else is self-contained: **no dataset, no model, no internet.**"))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + ENGINE))
    c.append(code(ANALYZE_DEFS))

    # ---- Section 1: TRY YOUR OWN ----
    c.append(md(
        '<a id="try"></a>\n## 1 - Try it yourself: call analyze()\n\n'
        "**Edit the `text` string in the next cell** -- paste a job ad, a worker message, or a filing (composite or "
        "test data, please: no real PII in a shared notebook) -- and run it. `analyze()` returns the full dict and "
        "`show_analysis()` renders the risk card and the indicator/citation table. This is the entire integration "
        "surface: one call in, one dict out.\n\n"
        "*(Run the two setup cells above first -- they embed the visualization toolkit and the DueCare indicator "
        "engine so the notebook is completely self-contained.)*"))
    c.append(code(TRY))

    # ---- Section 2: the unified interface ----
    c.append(md(
        '<a id="interface"></a>\n## 2 - The unified interface\n\n'
        "`analyze(text)` returns one JSON-serializable dict with everything a product needs: the risk band and its "
        "reason, the detected indicators (each with its matched cue and controlling ILO instrument), the unique "
        "citations, the full structured reasoning chain, referral resources, and a small meta block. One shape, "
        "every surface. The cell below shows the keys, a compact projection, and the full reasoning chain returned "
        "with every call."))
    c.append(code(INTERFACE))
    c.append(code(DIAGRAM))

    # ---- Section 3: the contract ----
    c.append(md(
        '<a id="contract"></a>\n## 3 - The request/response contract\n\n'
        "The whole point of a unified interface is a **stable contract** you can code against. Request: "
        "`analyze(text: str)`. Response: the dict below -- JSON-serializable, so you can return it straight from an "
        "HTTP handler, store it, or hand it to a UI. The field table is the schema your product integrates against; "
        "it does not change when the model behind it changes. The second cell proves the contract survives a "
        "JSON round-trip -- serialize it, parse it back, and every field is intact."))
    c.append(code(CONTRACT))
    c.append(code(JSON_ROUNDTRIP))

    # ---- Section 4: the three integration patterns ----
    c.append(md(
        '<a id="patterns"></a>\n## 4 - The three integration patterns\n\n'
        "One call, three deployment modes. Each pattern below is real, runnable code -- copy it into your product "
        "and change the inputs. They differ only in *where* `analyze()` runs and *what* you do with the dict; the "
        "call itself is identical.\n\n"
        "### 4A - Enterprise waterfall (job board / social platform)\n"
        "Run a cheap keyword filter on **every** item and the expensive `analyze()` only on the suspicious few. "
        "Route each item to CLEAR (publish), WATCH (log), WARN (show the user a safety popup), or QUEUE (human "
        "review). This is the pattern a platform uses to catch recruitment fraud at feed scale."))
    c.append(code(PATTERN_ENTERPRISE))
    c.append(md(
        "### 4B - On-device worker app (LiteRT / Gemma 4)\n"
        "The **same** `analyze()` call, but running entirely on the worker's phone -- Gemma 4 via LiteRT or "
        "llama.cpp -- so their messages, IDs, and documents never leave the device. A worker pastes a suspicious "
        "offer and gets a plain-language GREEN / AMBER / RED check with the red flags named and a hotline. The "
        "integration code is byte-for-byte the same as the server; only the model backend differs."))
    c.append(code(PATTERN_ONDEVICE))
    c.append(md(
        "### 4C - NGO batch dashboard\n"
        "Call `analyze()` over a caseload and build a review table sorted riskiest-first. This is the pattern behind "
        "the caseworker and regulator surfaces -- the same one call, applied to a list instead of a single item, "
        "with the full text preserved for human review."))
    c.append(code(PATTERN_DASHBOARD))

    # ---- Section 5: swap in the full harness ----
    c.append(md(
        '<a id="swap"></a>\n## 5 - Swap in the full Gemma 4 harness (no call-site changes)\n\n'
        "`analyze(text) -> dict` **is** the interface, so the model behind it is a swappable detail. Start with the "
        "deterministic engine embedded here -- perfect for development, CI, and air-gapped environments -- and move "
        "to the full Gemma-4-backed harness (Persona + the 451-rule GREP layer + retrieval + tools) when you are "
        "ready. A tiny factory keeps every call site unchanged; the production analyzer returns the **same dict "
        "shape**, just model-backed and retrieval-grounded."))
    c.append(code(SWAP))

    # ---- Section 6: install + testing against the benchmark ----
    c.append(md(
        '<a id="test"></a>\n## 6 - Install + test against the published benchmark\n\n'
        "Installing the real thing is one line -- `pip install duecare-llm-core duecare-llm-chat` (the "
        "`duecare-llm-*` family) or straight from source. And because DueCare publishes its graded benchmark, you "
        "can regression-test your integration against real data:\n\n"
        f"- **Grades dataset:** [`{DATASET_GRADES}`](https://www.kaggle.com/datasets/{DATASET_GRADES})\n"
        f"- **Per-dimension grades:** [`{DATASET_PERDIM}`](https://www.kaggle.com/datasets/{DATASET_PERDIM})\n"
        f"- **Source + harness:** the [repository]({REPO})\n\n"
        "The cell below shows the *shape* of a CI test against that benchmark: assert the contract holds and that "
        "the risk ordering is monotone across labeled probes. Wire the same asserts to the published rows and they "
        "become a real regression gate."))
    c.append(code(SELFTEST))

    # ---- Section 7: trust boundary + honest boundary ----
    c.append(md(
        '<a id="boundary"></a>\n## 7 - Trust boundary + honest boundary\n\n'
        "**Where the data lives.** `analyze()` runs wherever you deploy it -- your server, or on the worker's device "
        "via Gemma 4 (LiteRT / llama.cpp). No raw text has to leave that boundary; the same call works air-gapped. "
        "In the on-device pattern the worker's messages, IDs, and documents never leave the phone unless the worker "
        "explicitly shares a sanitized submission. When you send text to an external frontier model instead, send "
        "only redacted, generalized, or policy-approved content.\n\n"
        "**Honest boundary.** What runs here is a **representative deterministic subset** for integration, not the "
        "production model. `analyze()` flags indicators and returns decision support -- it is **not** a trafficking "
        "determination, **not** legal advice, and **not** an automated-takedown engine. Keep a human in the loop on "
        "consequential decisions, and apply local law.\n\n"
        f"- **Source and harness:** the [repository]({REPO}).\n"
        f"- **Benchmark data:** [`{DATASET_GRADES}`](https://www.kaggle.com/datasets/{DATASET_GRADES}).\n\n"
        "License: MIT. All inputs here are composite / synthetic -- no real names, no real PII.\n\n"
        "[Back to contents](#try)"))
    c.append(code(BOUNDARY))

    nb = nbf.v4.new_notebook()
    nb["cells"] = c
    nb["metadata"] = {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                      "language_info": {"name": "python"}}
    nbf.write(nb, str(nb_dir / "notebook.ipynb"))

    meta = {"id": KERNEL_ID, "title": TITLE, "code_file": "notebook.ipynb", "language": "python",
            "kernel_type": "notebook", "is_private": False, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": [], "competition_sources": [], "kernel_sources": []}
    (nb_dir / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"kernel_id": KERNEL_ID, "title": TITLE, "cells": len(c),
            "code_cells": sum(1 for x in c if x.cell_type == "code"), "notebook_dir": str(nb_dir)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    summary = build(args.output, force=args.force)
    slug = summary["kernel_id"].split("/", 1)[1]
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    assert TITLE.lower().replace(" ", "-") == "duecare-developer-integration"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
