#!/usr/bin/env python3
# ruff: noqa: E501
"""Build the DueCare Platform Moderation At Scale use-case Kaggle notebook.

An applied, easy-to-use notebook for a job-board / social-platform **trust and safety**
team. It shows a two-stage moderation **waterfall** that catches trafficking-style
recruitment fraud at scale: a cheap keyword pre-filter runs on *every* post, and the
expensive indicator analysis runs only on the suspicious few. Each post is routed to
one of four decisions -- CLEAR / WATCH / WARN / QUEUE -- and WARN posts get a
Facebook-safety-prompt-style resource popup shown to the user.

The notebook is **fully self-contained**: both shared DueCare toolkits are embedded in
the first code cell -- the prettify toolkit (scripts/_notebook_viz.py: PALETTE + HELPERS)
and the grounded indicator engine (scripts/_usecase_engine.py: ENGINE, a representative
subset of the 451-rule GREP layer + the 12 ILO 2012 forced-labour indicators). CPU only,
no GPU, no internet, no model, no attached dataset: it runs to completion on Kaggle and
every number is reproducible.

    python scripts/build_usecase_platform_moderation_notebook.py

The moderation logic is deterministic: keyword pre-filter -> ILO indicator scan ->
decision from the indicator count. In production the expensive stage is the full DueCare
harness + Gemma 4; here it is the offline indicator engine so the whole pipeline is
verifiable without a GPU.
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
DEFAULT_OUT = ROOT / "reports" / "kaggle_publish" / "usecase_platform_moderation"
KERNEL_ID = "taylorsamarel/duecare-platform-moderation-at-scale"
TITLE = "DueCare Platform Moderation At Scale"
REPO = "https://github.com/TaylorAmarelTech/gemma4_comp"
BENCH = "https://www.kaggle.com/code/taylorsamarel/duecare-harness-lift-benchmark-start-here"

# ---------------------------------------------------------------------------
# Cell 2 (TOOLKIT): the moderation waterfall itself -- moderate() + warning_popup().
# Runs in the same namespace as the embedded PALETTE/HELPERS/ENGINE cell, so it can
# use scan / risk_level / ILO_INDICATORS / HOTLINES and the palette colors directly.
# ---------------------------------------------------------------------------
TOOLKIT = '''try:
    from IPython.display import display, HTML, Markdown
except Exception:                       # plain-python fallback so the notebook still runs headless
    def display(*a, **k):
        for x in a: print(getattr(x, "data", x))
    def HTML(s): return s
    def Markdown(s): return s

# --- Stage 1: the cheap keyword pre-filter -----------------------------------------------
# Broad, tuned for RECALL. In production this is a compiled keyword/regex gate (or a tiny
# classifier) that runs on EVERY post for near-zero cost. A post with no keyword is CLEAR
# and never reaches the expensive analysis.
KEYWORDS = ["passport", "visa", "iqama", "recruit", "placement", "agency", "broker", "sponsor",
            "fee", "deposit", "bond", "debt", "loan", "advance", "salary", "wage", "overtime",
            "no day off", "document", "papers", "permit", "withheld", "confiscat", "deploy",
            "not allowed", "cannot leave", "no phone", "sleep on the floor"]

def prefilter(text):
    """Stage 1 (cheap): return the keyword triggers found in `text` (empty list = pass = CLEAR)."""
    t = (text or "").lower()
    return [k for k in KEYWORDS if k in t]

# --- Stage 3: map the risk level to a moderation decision --------------------------------
# risk_level(hits) -> LOW / WATCH / ELEVATED / HIGH (0 / 1 / 2-3 / 4+ indicators).
# A LOW result means the cheap keyword tripped but the ILO scan found NO indicator, so the
# decision is WATCH, not WARN -- the harness refuses to warn a user on a bare keyword.
DECISION_BY_LEVEL = {"LOW": "WATCH", "WATCH": "WARN", "ELEVATED": "QUEUE", "HIGH": "QUEUE"}
DECISION_NOTE = {
    "CLEAR": "no recruitment-risk keyword -- publish, no analysis needed",
    "WATCH": "keyword present but no forced-labour indicator -- log only, no user warning",
    "WARN":  "one indicator -- show the user a warning + resources before they proceed",
    "QUEUE": "multiple indicators -- route to a human trust-and-safety reviewer",
}
DECISION_COLOR = {"CLEAR": GOOD, "WATCH": TEAL, "WARN": WARN, "QUEUE": EMBER}

def moderate(posts):
    """The two-stage moderation WATERFALL, the one function a T&S team calls.

      Stage 1 (cheap):     keyword pre-filter on EVERY post; no keyword -> CLEAR (scan skipped).
      Stage 2 (expensive): the ILO forced-labour indicator scan, ONLY on posts that tripped stage 1.
      Stage 3 (decision):  CLEAR / WATCH / WARN / QUEUE from the indicator count (risk_level).

    Returns a pandas DataFrame with one row per post:
      post_id, snippet, n_indicators, indicators, decision, top_ilo_ref
    """
    rows = []
    for i, post in enumerate(posts, 1):
        pid = "P%02d" % i
        kw = prefilter(post)
        if not kw:                                  # stage 1 pass -> cheap CLEAR, scan never runs
            rows.append(dict(post_id=pid, snippet=post, n_indicators=0, indicators="",
                             decision="CLEAR", top_ilo_ref=""))
            continue
        hits = scan(post)                           # stage 2 -- the expensive analysis
        level = risk_level(hits)[0]
        rows.append(dict(post_id=pid, snippet=post, n_indicators=len(hits),
                         indicators=", ".join(h["label"] for h in hits),
                         decision=DECISION_BY_LEVEL[level],
                         top_ilo_ref=(hits[0]["ilo_ref"] if hits else "")))
    return pd.DataFrame(rows, columns=["post_id", "snippet", "n_indicators", "indicators", "decision", "top_ilo_ref"])

def color_decisions(sty):
    """Tint the `decision` cells of a Styler by their decision color."""
    def _c(v): return "color:%s;font-weight:700" % DECISION_COLOR.get(v, INK2)
    try:
        return sty.map(_c, subset=["decision"])
    except Exception:
        return sty.applymap(_c, subset=["decision"])

def warning_popup(post):
    """Render the user-facing, Facebook-safety-prompt-style resource card a platform would show
    in-app on a WARN post. Kaggle-safe inline-styled HTML only (no flex / script / max-height)."""
    hits = scan(post)
    items = "".join("<li style='margin:3px 0'>" + h["label"]
                    + " <span style='color:#5B5F68'>(" + h["ilo_ref"] + ")</span></li>" for h in hits)
    if not items:
        items = "<li style='margin:3px 0'>a recruitment-risk keyword</li>"
    res = "".join("<tr><td style='padding:3px 12px 3px 0;color:#14181B;font-weight:600;vertical-align:top'>" + k
                  + "</td><td style='padding:3px 0;color:#2A2D34'>" + v + "</td></tr>"
                  for k, v in HOTLINES.items() if k != "note")
    html = (
        "<div style='background:#F7F6F1;border:1px solid #DDD8C9;border-left:6px solid #b8873a;"
        "border-radius:10px;padding:16px 18px;font-family:Inter,-apple-system,system-ui,sans-serif;"
        "color:#14181B;max-width:660px'>"
        "<div style='font-size:15px;font-weight:700'>Before you continue &mdash; this job offer has warning signs</div>"
        "<div style='font-size:12.5px;color:#5B5F68;margin:5px 0 11px'>Recruitment-fraud and forced-labour schemes "
        "often look like ordinary job ads. You are not in any trouble. Here is what we noticed, and where to get "
        "free, confidential help.</div>"
        "<div style='font-size:12.5px'><b>What we noticed in this post</b>"
        "<ul style='margin:6px 0 11px 20px;padding:0'>" + items + "</ul></div>"
        "<div style='font-size:12.5px'><b>Free, confidential help</b> "
        "<span style='color:#5B5F68'>(always verify the current in-country number)</span>"
        "<table style='border-collapse:collapse;margin-top:6px;font-size:12px'>" + res + "</table></div>"
        "<div style='font-size:11px;color:#8A8E97;margin-top:11px'>You control your data. Nothing in this post is "
        "reported anywhere unless you choose to report it.</div></div>")
    display(HTML(html))
    return html

print("moderation waterfall ready:", len(KEYWORDS), "keywords (stage 1),",
      len(ILO_INDICATORS), "ILO indicators (stage 2), decisions CLEAR/WATCH/WARN/QUEUE")'''

# ---------------------------------------------------------------------------
# Cell 3 (TRY YOUR OWN): the paste-your-own entry point, kept near the top.
# ---------------------------------------------------------------------------
TRY = '''# ============================================================================
# TRY YOUR OWN -- paste your own posts / messages below, one string per line,
# then run this cell. Everything is local, deterministic, and offline.
# ============================================================================
posts = [
    "Now hiring baristas for our downtown cafe, flexible shifts and training provided.",
    "Nursing role in the NHS, visa sponsorship available, agency never charges candidates a fee.",
    "Overseas hotel jobs. Pay a processing fee and we keep your passport until the contract ends.",
    "Warehouse packers wanted, one-time placement fee of 500 to reserve your slot.",
]
display(color_decisions(pretty_table(moderate(posts),
        caption="Your posts, moderated by the DueCare two-stage waterfall")))
print("Edit the list above and re-run. CLEAR = publish, WATCH = log only, WARN = show a warning, QUEUE = human review.")'''

# ---------------------------------------------------------------------------
# Cell 6: the grounding tables -- the 12 ILO indicators and the stage-1 keyword list.
# ---------------------------------------------------------------------------
GROUND = '''ind_tbl = pd.DataFrame({"ILO forced-labour indicator": list(ILO_INDICATORS.values()),
                        "controlling instrument": [ILO_REFS[k] for k in ILO_INDICATORS]})
display(pretty_table(ind_tbl, caption="Stage 2 looks for these 12 ILO (2012) forced-labour indicators -- a representative subset of the 451-rule DueCare GREP layer"))
print("Stage 1 cheap keyword pre-filter (%d terms):" % len(KEYWORDS))
print("   " + ", ".join(KEYWORDS))
print("Stage 1 is deliberately broad (high recall, low precision); stage 2 is where precision comes from.")
print()
print("Stage 2 also catches %d camouflaged worker-paid fee labels (a recruitment fee wearing a friendlier name):" % len(FEE_CAMOUFLAGE))
print("   " + ", ".join(FEE_CAMOUFLAGE))'''

# ---------------------------------------------------------------------------
# Cell 7: the pipeline diagram (flow boxes) + a 3-stage stat_cards row.
# ---------------------------------------------------------------------------
DIAGRAM = '''fig, ax = plt.subplots(figsize=(10.6, 2.5)); ax.axis("off"); ax.set_xlim(0, 10.4); ax.set_ylim(0, 2)
stages = [("EVERY post", "the full firehose", INK3),
          ("Stage 1: keyword\\npre-filter (cheap)", "runs on 100% of posts", TEAL),
          ("Stage 2: ILO\\nindicator scan", "only the flagged few", EMBER),
          ("Decision", "CLEAR / WATCH / WARN / QUEUE", GOOD)]
xs = [0.15, 2.75, 5.45, 8.15]; w = 2.1
for (title, sub, col), x in zip(stages, xs):
    ax.add_patch(FancyBboxPatch((x, 0.5), w, 1.0, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=PAPER2, edgecolor=col, linewidth=2.4))
    ax.text(x + w / 2, 1.14, title, ha="center", va="center", fontsize=10.5, fontweight="bold", color=INK)
    ax.text(x + w / 2, 0.74, sub, ha="center", va="center", fontsize=8.3, color=INK3)
for i in range(len(xs) - 1):
    ax.annotate("", xy=(xs[i + 1] - 0.04, 1.0), xytext=(xs[i] + w + 0.04, 1.0),
                arrowprops=dict(arrowstyle="-|>", color=INK3, lw=1.9))
plt.tight_layout(); plt.show()

stat_cards([("100%", "posts hit the cheap filter", TEAL),
            ("few %", "reach the expensive scan", EMBER),
            ("humans", "review only the QUEUE", GOOD)])'''

# ---------------------------------------------------------------------------
# Cell 8: one post per outcome, walked through the two-stage waterfall.
# ---------------------------------------------------------------------------
TRACE = '''trace_posts = [
    "Now hiring baristas for our downtown cafe, training provided.",                  # no keyword -> CLEAR
    "Software role, visa sponsorship available for the right candidate.",             # keyword, clean -> WATCH
    "Warehouse jobs, one-time placement fee of 500 to secure your slot.",             # one indicator -> WARN
    "Processing fee applies, your salary is deducted, and we keep your passport.",     # several -> QUEUE
]
rows = []
for p in trace_posts:
    kw = prefilter(p)
    hits = scan(p) if kw else []
    level = risk_level(hits)[0] if kw else "LOW"
    decision = "CLEAR" if not kw else DECISION_BY_LEVEL[level]
    rows.append({"post": p,
                 "stage 1 keyword hits": ", ".join(kw) if kw else "(none -> CLEAR, scan skipped)",
                 "stage 2 indicators": len(hits),
                 "risk": level,
                 "decision": decision})
display(color_decisions(pretty_table(pd.DataFrame(rows),
        caption="One post per outcome, walked through the two-stage waterfall")))'''

# ---------------------------------------------------------------------------
# Cell 10: the synthetic batch + the moderation queue table (sorted by risk).
# ---------------------------------------------------------------------------
SYNTH = '''# ~16 SYNTHETIC posts: legitimate job ads mixed with trafficking-style recruitment
# (fee camouflage, passport retention, debt bondage). All composite -- no real names, no PII.
SYNTH_POSTS = [
    "Now hiring baristas for our downtown cafe. Flexible shifts, training provided, competitive hourly pay.",
    "Seeking software engineers. Remote-friendly, full benefits, visa sponsorship available for the right candidate.",
    "Weekend farmhands needed for the apple harvest. Transport from town provided, meals included, paid weekly.",
    "Part-time dog walkers wanted. Set your own hours, get paid per walk, must love animals.",
    "Busy restaurant seeking dishwashers and line cooks. Overtime is available and paid at time-and-a-half per state law.",
    "Licensed nursing recruitment agency. We never charge candidates a fee; all costs are employer-paid and audited.",
    "Retail associate for our flagship store. Friendly team, staff discount, paid training on the floor.",
    "Warehouse packers wanted now. One-time placement fee of 500 to reserve your slot, refundable after six months.",
    "Live-in housekeeper wanted. Salary is withheld for the first three months as a guarantee, then paid in full.",
    "Cross-border delivery driver role. We hold your travel permit, and you are not allowed to leave the depot during your shift rotation.",
    "Overseas factory placement, start now. Processing fee of 1800 dollars. Your salary is deducted each month to cover it. Your passport is kept by the agency for safekeeping. You cannot leave the site without permission.",
    "Hiring cleaners in the Gulf. There is a training bond to pay back. Long hours, and no day off.",
    "Come work in the city. We paid for your travel, so you owe us and must work it off. We keep your passport here. If you complain we report you to immigration.",
    "Live-in domestic worker needed. We keep your passport for safety. No phone is allowed during work hours. You will sleep on the floor in a crowded room.",
    "Fishing crew wanted. The recruiter said the job was office work; actually it is dangerous fishing at sea. You cannot contact your family for months.",
    "Freelance graphic designer needed for a logo project. Fixed budget, remote, portfolio required.",
]
MQ = moderate(SYNTH_POSTS)
RANK = {"QUEUE": 0, "WARN": 1, "WATCH": 2, "CLEAR": 3}
MQ_sorted = (MQ.assign(_r=MQ.decision.map(RANK))
               .sort_values(["_r", "n_indicators"], ascending=[True, False])
               .drop(columns="_r").reset_index(drop=True))
display(color_decisions(pretty_table(MQ_sorted, bars=["n_indicators"],
        caption="The moderation queue -- %d synthetic posts, riskiest first (full post text, nothing truncated)" % len(MQ))))'''

# ---------------------------------------------------------------------------
# Cell 11: batch stat_cards summary.
# ---------------------------------------------------------------------------
BATCH_STATS = '''n = len(MQ)
to_scan = int((MQ.decision != "CLEAR").sum())
n_warn = int((MQ.decision == "WARN").sum())
n_queue = int((MQ.decision == "QUEUE").sum())
stat_cards([("%d" % n, "posts moderated", INK2),
            ("%d%%" % round(100 * to_scan / n), "reached the stage-2 scan", TEAL),
            ("%d" % n_warn, "user warnings (WARN)", WARN),
            ("%d" % n_queue, "queued for humans (QUEUE)", EMBER)])
print("Only %d of %d posts (%d%%) needed the expensive analysis; the other %d cleared on the cheap filter alone."
      % (to_scan, n, round(100 * to_scan / n), n - to_scan))'''

# ---------------------------------------------------------------------------
# Cell 12: decision-distribution bar.
# ---------------------------------------------------------------------------
DIST = '''order = ["CLEAR", "WATCH", "WARN", "QUEUE"]
counts = [int((MQ.decision == d).sum()) for d in order]
fig, ax = plt.subplots(figsize=(8.4, 4.3))
bars = ax.bar(order, counts, color=[DECISION_COLOR[d] for d in order], edgecolor=PAPER, linewidth=1.3, width=0.62)
for b, cnt in zip(bars, counts):
    ax.text(b.get_x() + b.get_width() / 2, cnt + 0.06, str(cnt), ha="center", va="bottom",
            fontsize=13, fontweight="bold", color=INK2)
ax.set_ylabel("posts"); ax.set_ylim(0, max(counts) + 1); ax.grid(axis="x", alpha=0)
_title(ax, "Moderation queue: decision distribution",
       "%d synthetic posts -- most clear cheaply, only the risky few reach a human reviewer" % len(MQ))
plt.tight_layout(); plt.show()
print("decision distribution:", {d: c for d, c in zip(order, counts)})'''

# ---------------------------------------------------------------------------
# Cell 13: indicator-frequency bar.
# ---------------------------------------------------------------------------
FREQ = '''from collections import Counter
freq = Counter()
for post in SYNTH_POSTS:
    if prefilter(post):
        for h in scan(post):
            freq[h["label"]] += 1
if freq:
    pairs = sorted(freq.items(), key=lambda kv: kv[1])
    labs = [p[0] for p in pairs]; vals = [p[1] for p in pairs]
    fig, ax = plt.subplots(figsize=(9.8, 0.5 * len(labs) + 1.7))
    ax.barh(range(len(labs)), vals, color=TEAL, edgecolor=PAPER, linewidth=0.9)
    for i, v in enumerate(vals):
        ax.text(v + 0.05, i, str(v), va="center", fontsize=10, color=INK3)
    ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs)
    ax.set_xlabel("times detected across the batch"); ax.set_xlim(0, max(vals) + 1); ax.grid(axis="y", alpha=0)
    _title(ax, "Which forced-labour indicators showed up",
           "ILO 2012 indicators the stage-2 scan flagged across the synthetic batch")
    plt.tight_layout(); plt.show()
else:
    print("no indicators detected in the batch")'''

# ---------------------------------------------------------------------------
# Cell 14: the two most-severe queued posts, in full (no truncation).
# ---------------------------------------------------------------------------
WORKED = '''q = MQ_sorted[MQ_sorted.decision == "QUEUE"].head(2)
lines = ["### Two queued posts, in full", ""]
for _, r in q.iterrows():
    hits = scan(r.snippet)
    lines.append("**%s -- %s** (%d indicators)  \\n" % (r.post_id, r.decision, r.n_indicators))
    lines.append("> " + r.snippet + "\\n")
    for h in hits:
        lines.append("- **%s** -- %s  \\n  matched cue: `%s`" % (h["label"], h["ilo_ref"], h["snippet"]))
    lines.append("")
display(Markdown("\\n".join(lines)))'''

# ---------------------------------------------------------------------------
# Cell 16: the warning popup for a WARN post.
# ---------------------------------------------------------------------------
POPUP = '''warn_row = MQ[MQ.decision == "WARN"].iloc[0]
print("A WARN post -- one indicator, so the platform shows the user this in-app popup:")
print()
print("  " + warn_row.snippet)
print()
warning_popup(warn_row.snippet)'''

# ---------------------------------------------------------------------------
# Cell 18 + 19: throughput framing (illustrative cost stat_cards + bar).
# ---------------------------------------------------------------------------
THROUGH_STATS = '''DAILY = 1_000_000                       # illustrative daily post volume for a mid-size platform
REALISTIC_STAGE2 = 0.04                 # illustrative: on a real feed the vast majority of posts are benign
scanned = int(DAILY * REALISTIC_STAGE2)
# ILLUSTRATIVE unit costs (placeholders, NOT a benchmark): a keyword pass is ~free; a full
# model analysis costs real compute. The point is the SHAPE of the saving, not the dollars.
C_CHEAP, C_SCAN = 0.000001, 0.002
cost_waterfall = DAILY * C_CHEAP + scanned * C_SCAN
cost_scan_all = DAILY * C_SCAN
stat_cards([("{:,}".format(DAILY), "posts / day (illustrative)", INK2),
            ("%d%%" % round(100 * REALISTIC_STAGE2), "reach the expensive scan", TEAL),
            ("%.0fx" % (cost_scan_all / max(cost_waterfall, 1e-9)), "cheaper than scan-all", GOOD),
            ("${:,.0f}".format(cost_scan_all - cost_waterfall), "saved / day (illustrative)", EMBER)])
print("ILLUSTRATIVE ONLY -- unit costs are placeholders to show the shape of the saving, not a measured benchmark.")
print("Measured on THIS batch, %d%% of posts reached stage 2, but the batch is deliberately risk-dense;"
      % round(100 * (MQ.decision != "CLEAR").mean()))
print("a real feed is mostly benign, so the true stage-2 rate is a few percent.")'''

THROUGH_BAR = '''labels = ["scan every post\\n(no waterfall)", "waterfall\\n(cheap filter first)"]
vals = [cost_scan_all, cost_waterfall]
fig, ax = plt.subplots(figsize=(7.6, 4.3))
bars = ax.bar(labels, vals, color=[INK3, TEAL], edgecolor=PAPER, linewidth=1.3, width=0.55)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v, "${:,.0f}".format(v), ha="center", va="bottom",
            fontsize=12, fontweight="bold", color=INK2)
ax.set_ylabel("illustrative cost / day ($)"); ax.set_ylim(0, cost_scan_all * 1.18); ax.grid(axis="x", alpha=0)
_title(ax, "Why a waterfall: run the expensive model only on the suspicious few",
       "illustrative unit costs -- the shape of the saving, not a benchmark")
plt.tight_layout(); plt.show()'''

# ---------------------------------------------------------------------------
# Cell 21: false-positive care + keyword-only vs waterfall comparison.
# ---------------------------------------------------------------------------
FPCARE = '''# A benign ad that trips a keyword but scans clean -> WATCH, not WARN.
fp = [p for p in SYNTH_POSTS if "time-and-a-half" in p][0]
print("Benign post (a legitimate overtime offer):")
print("  " + fp)
print()
print("stage 1 keyword hits :", prefilter(fp))
print("stage 2 ILO indicators:", [h["label"] for h in scan(fp)])
print("decision             :", MQ[MQ.snippet == fp].iloc[0].decision)
print()
print("The word 'overtime' trips the cheap filter, but the scan finds NO forced-labour indicator")
print("(paid at time-and-a-half, no excessive-hours pattern), so it is logged as WATCH and NO user")
print("warning fires. Keyword matching alone would over-warn; the stage-2 scan is what adds precision.")

# Keyword-only flagging vs the full waterfall, on the same batch.
kw_flagged = sum(1 for p in SYNTH_POSTS if prefilter(p))
warn_or_queue = int(MQ.decision.isin(["WARN", "QUEUE"]).sum())
watch_only = int((MQ.decision == "WATCH").sum())
comp = pd.DataFrame({
    "approach": ["keyword-only (stage 1 alone)", "full waterfall (stage 1 + ILO scan)"],
    "posts escalated to a user or human": [kw_flagged, warn_or_queue],
    "keyword-tripping posts spared a false alarm": [0, watch_only]})
display(pretty_table(comp,
        caption="The scan cuts over-flagging: keyword-only would alarm on %d posts; the waterfall escalates %d and lets %d keyword-tripping-but-clean posts through as WATCH"
                % (kw_flagged, warn_or_queue, watch_only)))'''

# ---------------------------------------------------------------------------
# Cell 23: trust-boundary card + go-to-production stat_cards.
# ---------------------------------------------------------------------------
BOUNDARY = '''tb = ("<div style='background:#f0d8c8;border:1px solid #c15b2e;border-left:6px solid #c15b2e;"
      "border-radius:10px;padding:15px 18px;font-family:Inter,-apple-system,system-ui,sans-serif;"
      "color:#14181B;max-width:680px'>"
      "<div style='font-size:14px;font-weight:700'>Trust boundary</div>"
      "<div style='font-size:12.5px;color:#2A2D34;margin-top:6px'>Posts are analyzed <b>inside the platform's own "
      "environment</b>. No raw user text leaves: the DueCare harness runs on-prem or on-device (Gemma 4 via "
      "llama.cpp or LiteRT). Only <b>aggregate signals</b> -- indicator counts and decision tallies -- are ever "
      "shared for oversight. Neither the keyword filter nor the scan transmits the post.</div></div>")
display(HTML(tb))
stat_cards([("2-stage", "cheap filter -> Gemma 4 scan", TEAL),
            ("human", "in the loop on every QUEUE", EMBER),
            ("on-prem", "no raw user data leaves", GOOD),
            ("MIT", "open source", INK2)])'''


def _toc() -> str:
    items = [
        ("1", "Try it yourself", "try"),
        ("2", "The waterfall, explained", "waterfall"),
        ("3", "A worked batch: the moderation queue", "batch"),
        ("4", "The user-facing warning popup", "popup"),
        ("5", "Throughput: why two stages", "throughput"),
        ("6", "False-positive care", "fpcare"),
        ("7", "Trust boundary and going to production", "boundary"),
    ]
    return "\n".join(f"{n}. [{t}](#{a})" for n, t, a in items)


def build(output_dir: Path, *, force: bool = False) -> dict:
    nb_dir = output_dir / "notebooks" / KERNEL_ID.split("/", 1)[1]
    nb_dir.mkdir(parents=True, exist_ok=True)
    md = nbf.v4.new_markdown_cell
    code = nbf.v4.new_code_cell
    c: list = []

    # ---- Section 0: hero ----
    c.append(md(
        "# DueCare Platform Moderation At Scale\n\n"
        "**For a job-board or social-platform trust-and-safety team.** Recruitment fraud and "
        "trafficking-style job offers arrive at feed scale -- millions of posts a day -- and the "
        "dangerous ones look almost exactly like legitimate ads. You cannot run a heavy model on "
        "every post, and you cannot afford to miss the ones that matter.\n\n"
        "The answer is a **waterfall**: a cheap keyword pre-filter runs on *every* post, and the "
        "expensive indicator analysis runs *only* on the suspicious few. Each post is routed to one "
        "of four decisions -- **CLEAR** (publish), **WATCH** (log only), **WARN** (show the user a "
        "safety popup with resources), or **QUEUE** (send to a human reviewer). It is the same idea "
        "as a platform's suicide-prevention prompt, aimed at labor trafficking.\n\n"
        "This notebook is **self-contained and easy to use**: paste your own posts into the first "
        "TRY YOUR OWN cell and run. The whole pipeline is deterministic, CPU-only, offline, and needs "
        "no GPU, no model, and no attached data -- so every number here is reproducible.\n\n"
        "### Contents\n" + _toc() + "\n\n"
        "> **Honest boundary (please read).** The stage-2 analysis here is a grounded, deterministic "
        "**representative subset** of the DueCare harness (12 ILO 2012 indicators; the production GREP "
        "layer has 451 rules) -- it stands in for the full harness + Gemma 4 so the notebook runs "
        "anywhere. It flags *indicators*, not a legal finding, and it is **decision support for human "
        "reviewers**, not an automated takedown system. All posts below are composite / synthetic: no "
        "real names, no real people, no PII."))

    # ---- Section 1: TRY YOUR OWN (+ setup) ----
    c.append(md(
        '<a id="try"></a>\n## 1 - Try it yourself\n'
        "The first code cell embeds both shared DueCare toolkits so the notebook is self-contained: "
        "the **prettify toolkit** (palette, tables, KPI tiles) and the grounded **indicator engine** "
        "(`scan`, `risk_level`, the 12 ILO indicators, the fee-camouflage list, hotline pathways). The "
        "second cell defines the one function you call -- `moderate(posts)` -- plus `warning_popup(post)`. "
        "Then paste your own posts and run."))
    c.append(code(PALETTE + "\n" + HELPERS + "\n" + ENGINE))
    c.append(code(TOOLKIT))
    c.append(code(TRY))

    # ---- Section 2: the waterfall explained ----
    c.append(md(
        '<a id="waterfall"></a>\n## 2 - The waterfall, explained\n'
        "A waterfall spends compute where it matters. **Stage 1** is a cheap keyword pre-filter tuned for "
        "recall -- it runs on 100% of posts and lets the obviously-benign ones through as CLEAR without any "
        "further work. **Stage 2** is the expensive ILO forced-labour indicator scan (the full harness + "
        "Gemma 4 in production) and runs *only* on the posts stage 1 flagged. **Stage 3** turns the indicator "
        "count into a decision. Below: the indicators stage 2 looks for, the flow, and one post per outcome "
        "traced end to end."))
    c.append(code(GROUND))
    c.append(code(DIAGRAM))
    c.append(code(TRACE))

    # ---- Section 3: worked batch ----
    c.append(md(
        '<a id="batch"></a>\n## 3 - A worked batch: the moderation queue\n'
        "Now a realistic mixed batch of ~16 synthetic posts -- ordinary job ads alongside trafficking-style "
        "recruitment with fee camouflage, passport retention, and debt bondage. `moderate()` produces the "
        "**moderation queue**: one row per post, riskiest first, with the detected indicators and the "
        "controlling ILO reference. Full post text is shown -- nothing is truncated. Then the decision "
        "distribution and which indicators drove the flags."))
    c.append(code(SYNTH))
    c.append(code(BATCH_STATS))
    c.append(code(DIST))
    c.append(code(FREQ))
    c.append(code(WORKED))

    # ---- Section 4: warning popup ----
    c.append(md(
        '<a id="popup"></a>\n## 4 - The user-facing warning popup\n'
        "A WARN post is not taken down -- the user sees a gentle, supportive popup (the same pattern as a "
        "platform's suicide-prevention prompt) that names what was noticed, cites the relevant ILO instrument, "
        "and points to free confidential help. It is rendered as Kaggle-safe inline-styled HTML."))
    c.append(code(POPUP))

    # ---- Section 5: throughput ----
    c.append(md(
        '<a id="throughput"></a>\n## 5 - Throughput: why two stages\n'
        "The whole point of the waterfall is cost. The cheap filter runs on everything for near-zero cost; the "
        "expensive model runs on the small suspicious fraction. The tiles and bar below make the saving visible. "
        "**These unit costs are illustrative placeholders**, not a benchmark -- they show the *shape* of the "
        "saving, and the notebook says so out loud."))
    c.append(code(THROUGH_STATS))
    c.append(code(THROUGH_BAR))

    # ---- Section 6: false-positive care ----
    c.append(md(
        '<a id="fpcare"></a>\n## 6 - False-positive care\n'
        "Over-flagging erodes trust and buries reviewers. A legitimate ad that says 'overtime ... paid at "
        "time-and-a-half' trips the cheap keyword filter, but the stage-2 scan finds no forced-labour indicator, "
        "so it is logged as **WATCH** and no user warning fires. Keyword matching alone would over-warn; the "
        "scan is what adds precision. The comparison below quantifies it on this batch."))
    c.append(code(FPCARE))

    # ---- Section 7: trust boundary + production ----
    c.append(md(
        '<a id="boundary"></a>\n## 7 - Trust boundary and going to production\n\n'
        "**Where the data lives.** Posts are analyzed inside the platform's own environment. No raw user text "
        "leaves it -- the DueCare harness runs on-prem or on-device (Gemma 4 via llama.cpp or LiteRT). Only "
        "aggregate signals (indicator counts, decision tallies) are shared for oversight.\n\n"
        "**Going to production.** Swap the offline indicator engine for the full DueCare harness + Gemma 4: the "
        "same waterfall, but stage 2 becomes the fine-tuned model with the full 451-rule GREP layer, retrieval "
        "over the ILO / statute corpus, and the reasoned five-dimension rubric. The "
        f"[harness-lift benchmark]({BENCH}) shows the measured improvement the harness adds over a bare model.\n\n"
        "**Honest boundary.** This is a **representative deterministic subset**, not the production model; it flags "
        "indicators, not legal findings; and a **human stays in the loop** on every QUEUE. It is a scale filter that "
        "routes attention -- not an automated takedown system.\n\n"
        f"- **Source and harness:** the [repository]({REPO}).\n"
        f"- **Measured lift:** the [harness-lift benchmark]({BENCH}).\n\n"
        "License: MIT. All posts here are composite / synthetic -- no real names, no PII."))
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
    return {"kernel_id": KERNEL_ID, "title": TITLE, "cells": len(c), "notebook_dir": str(nb_dir)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    summary = build(args.output, force=args.force)
    slug = summary["kernel_id"].split("/", 1)[1]
    assert TITLE.lower().replace(" ", "-") == slug, f"title must slugify to id: {TITLE!r} vs {slug!r}"
    assert TITLE.lower().replace(" ", "-") == "duecare-platform-moderation-at-scale"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
