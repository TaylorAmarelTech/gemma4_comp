"""Bring all 13 Kaggle kernels up to a consistent UX bar.

For each kernel:

1. Insert a top-of-file comment-block intro in each script kernel so a
    judge sees a clear "what this is, what to look
   for, demo path" before the first code line.
2. Standardise the README h1 to ``DueCare - <title> (#01 core | #A1 appendix)``.
3. Insert a visible "Serves lanes" line under the h1 using the public
    website's five-lane taxonomy.
4. Append a shared cross-kernel nav footer to every README so the 13
   feel like a series, with prev / next / index links.

Idempotent: each transform looks for its own marker and skips if it
already ran.
"""

from __future__ import annotations

import re
from pathlib import Path

KAGGLE_ROOT = Path(__file__).resolve().parent.parent / "kaggle"

INTRO_MARKER = "<!-- duecare:kernel-intro -->"
LANE_MARKER = "<!-- duecare:lane-label -->"
FOOTER_MARKER = "<!-- duecare:kernel-footer -->"


# (folder, kind, title, lede, look_for, demo_path)
# kind: "core-NN" or "appendix-NN"
KERNELS: list[dict[str, object]] = [
    {
        "folder": "01-duecare-exploration-workbench",
        "kind": "core",
        "n": 1,
        "title": "Migrant-worker safety playground",
        "lanes": ["02 NGO & regulator", "04 Researcher", "05 Developer / integration partner"],
        "lede": "All 6 safety layers, all 4 grading modes, all 9 Gemma 4 variants. One configurable URL.",
        "look_for": [
            "Pick a Gemma 4 variant in the picker overlay (start with E2B for speed).",
            "Flip layer toggles below the input to see what each adds.",
            "Click Compare to run the same prompt with two harness configs side-by-side.",
        ],
        "demo_path": "Run All -> cloudflared URL prints -> pick a model -> click any of the example prompt buttons.",
    },
    {
        "folder": "02-live-demo",
        "kind": "core",
        "n": 2,
        "title": "Live demo (focused walkthrough)",
        "lanes": [
            "01 Platform safety",
            "02 NGO & regulator",
            "03 Individual worker / mobile",
            "04 Researcher",
            "05 Developer / integration partner",
        ],
        "lede": "The polished demo URL judges land on. Same harness, scripted demo path, +56pp lift baked in.",
        "look_for": [
            "The opening shows stock Gemma vs the harnessed answer, side by side.",
            "The retrieval-path trace card explains why the cited source was used.",
            "The grading panel shows the rubric breakdown for the visible answer.",
        ],
        "demo_path": "Run All -> open the live URL -> watch the scripted prompt sequence walk through the 6-layer story.",
    },
    {
        "folder": "A-01-chat-playground",
        "kind": "appendix",
        "n": 1,
        "title": "Stock Gemma 4 chat baseline",
        "lanes": ["04 Researcher"],
        "lede": "The before-the-harness baseline. No GREP, no RAG, no tools, no online. Pure stock Gemma 4.",
        "look_for": [
            "Stock Gemma's answer to a recruitment-fee question shows zero ILO citations.",
            "No corridor-specific guidance; no NGO contact suggestions.",
            "Use this as the contrast for the harnessed kernels.",
        ],
        "demo_path": "Run All -> open URL -> ask a corridor-specific safety question -> compare with kernel 01.",
    },
    {
        "folder": "A-02-chat-playground-with-grep-rag-tools",
        "kind": "appendix",
        "n": 2,
        "title": "Harness ablation runner",
        "lanes": ["04 Researcher"],
        "lede": "Compact ablation companion: GREP + RAG + Tools + Imports as toggleable layers while the model and prompt stay constant.",
        "look_for": [
            "Same chat surface as the stock baseline, now with four harness toggles.",
            "Layer-by-layer response changes as GREP, RAG, Tools, and Imports are enabled.",
            "Pipeline evidence shows which rules, documents, and lookups shaped the response.",
        ],
        "demo_path": "Run All -> open URL -> toggle layers one at a time on the same prompt to isolate contributions.",
    },
    {
        "folder": "A-03-content-classification-playground",
        "kind": "appendix",
        "n": 3,
        "title": "Hands-on classification sandbox",
        "lanes": ["01 Platform safety", "02 NGO & regulator"],
        "lede": "Paste content, pick a classification schema (4 shipped), see the structured risk envelope Gemma 4 returns.",
        "look_for": [
            "The schema picker selects which fields the model populates.",
            "JSON output is validated against the schema before display.",
            "Failure modes (under-classified, over-classified) are explained inline.",
        ],
        "demo_path": "Run All -> open URL -> paste a job-board post -> pick a schema -> read the classification.",
    },
    {
        "folder": "A-04-content-knowledge-builder-playground",
        "kind": "appendix",
        "n": 4,
        "title": "Knowledge-builder sandbox + JSON export",
        "lanes": ["02 NGO & regulator", "05 Developer / integration partner"],
        "lede": "Build a structured knowledge object from free-text input. Exports JSON ready for the hub's pack format.",
        "look_for": [
            "The form mirrors the schema.org-style pack envelope.",
            "Export downloads a candidate ContextPack that a curator can vet.",
            "The PII gate runs before any export.",
        ],
        "demo_path": "Run All -> open URL -> paste a public-source advisory -> review the extracted JSON -> export.",
    },
    {
        "folder": "A-05-gemma-content-classification-evaluation",
        "kind": "appendix",
        "n": 5,
        "title": "NGO classifier evaluation dashboard",
        "lanes": ["02 NGO & regulator"],
        "lede": "Risk-vector scorecard + intake queue view. The NGO-side moderation surface.",
        "look_for": [
            "The dashboard groups flagged content by corridor + risk vector.",
            "Each row shows the GREP rule(s) that fired and the rubric score.",
            "Click any row to drill into the full classification trace.",
        ],
        "demo_path": "Run All -> open URL -> browse the synthetic queue -> drill into one flagged item.",
    },
    {
        "folder": "A-06-prompt-generation",
        "kind": "appendix",
        "n": 6,
        "title": "Two-track synthetic data generator",
        "lanes": ["04 Researcher"],
        "lede": "Generates synthetic SafetyJudge training/evaluation prompts and PrivacyRedactor composite anonymization cases in separate tracks.",
        "look_for": [
            "Safety rows include graded response anchors for calibration.",
            "Privacy rows include composite intake notes and gold redaction plans.",
            "Outputs land in JSONL plus the A-07 handoff bundle.",
        ],
        "demo_path": "Run All -> watch the JSONLs fill -> open samples to see SafetyJudge anchors and PrivacyRedactor gold rows.",
    },
    {
        "folder": "A-07-bench-and-tune",
        "kind": "appendix",
        "n": 7,
        "title": "Adapter training + new-model benchmark",
        "lanes": ["04 Researcher", "05 Developer / integration partner"],
        "lede": "SafetyJudge adapter pipeline: load A-06 bundles, benchmark stock Gemma 4, train SFT/DPO adapters, re-benchmark, and export GGUF/HF Hub artifacts.",
        "look_for": [
            "A-06 handoff bundles are loaded from attached Kaggle datasets, not live notebook links.",
            "SFT/DPO train a SafetyJudge adapter; PrivacyRedactor data remains a separate adapter/eval track.",
            "eval_results.json is the stock-vs-fine-tuned benchmark artifact.",
        ],
        "demo_path": "Run All on a T4 -> watch stock benchmark -> train adapter -> re-benchmark -> see eval_results.json and GGUF artifact.",
    },
    {
        "folder": "A-08-research-graphs",
        "kind": "appendix",
        "n": 8,
        "title": "Research graphs (CPU-only)",
        "lanes": ["04 Researcher"],
        "lede": "Six interactive Plotly charts: corridor coverage, GREP-rule density, RAG-corpus map, rubric-dim drift, etc.",
        "look_for": [
            "Hover any chart to see the underlying counts + corridor breakdown.",
            "Each chart is reproducible from the data directory; no Gemma calls.",
            "Useful for the hackathon writeup as evidence figures.",
        ],
        "demo_path": "Run All -> scroll through the 6 charts -> hover any cell to read the data.",
    },
    {
        "folder": "A-09-chat-playground-with-agentic-research",
        "kind": "appendix",
        "n": 9,
        "title": "Agentic-research chat (BYOK + Playwright)",
        "lanes": ["04 Researcher", "05 Developer / integration partner"],
        "lede": "The deeper Online layer. Real-browser agentic search via Playwright + BYO API key for live web grounding.",
        "look_for": [
            "Watch the agent open multiple pages in headless Playwright.",
            "Citations are pulled from the rendered DOM, not just the URL.",
            "The grading panel shows whether the cited URL actually supports the claim.",
        ],
        "demo_path": "Run All -> add your API key -> ask a corridor question that needs fresh data -> watch the agent work.",
    },
    {
        "folder": "A-10-chat-playground-jailbroken-models",
        "kind": "appendix",
        "n": 10,
        "title": "Jailbroken-Gemma comparison",
        "lanes": ["04 Researcher"],
        "lede": "Loads abliterated / cracked Gemma 4 variants. Proves the harness still works when the model's refusals are gone.",
        "look_for": [
            "The same harness runs on a refusal-ablated Gemma 4 31B variant.",
            "GREP + RAG + tool-call grounding compensate for the missing safety tuning.",
            "The grading panel shows the lift on adversarial prompts even against a jailbroken model.",
        ],
        "demo_path": "Run All -> pick a jailbroken variant in the picker -> ask the same adversarial prompts as kernel 01.",
    },
    {
        "folder": "A-11-grading-evaluation",
        "kind": "appendix",
        "n": 11,
        "title": "Runtime harness-lift regenerator",
        "lanes": ["04 Researcher"],
        "lede": "Recomputes the harness OFF vs ON lift with the same Gemma 4 weights, then emits provenance-pinned JSON, Markdown, and CSV artifacts.",
        "look_for": [
            "The output is a provenance-pinned report you can cite in the writeup.",
            "Run N from 10 (smoke) up to 207 (full reference set).",
            "Harness OFF vs ON is recomputed live; this is not the fine-tuned-model benchmark.",
        ],
        "demo_path": "Run All -> wait for the report -> see the headline lift number with the git SHA pinned.",
    },
]


def kernel_label(entry: dict[str, object]) -> str:
    if entry["kind"] == "core":
        return f"Core kernel #{entry['n']:02d}"
    return f"Appendix kernel #A{int(entry['n']):02d}"


def kernel_short_id(entry: dict[str, object]) -> str:
    if entry["kind"] == "core":
        return f"#{int(entry['n']):02d} core"
    return f"#A{int(entry['n']):02d} appendix"


def render_intro_python_comment(entry: dict[str, object]) -> str:
    look_for = "\n".join(f"#   - {bullet}" for bullet in entry["look_for"])
    return (
        f"# {INTRO_MARKER}\n"
        f"# DueCare — {entry['title']}\n"
        f"# {kernel_label(entry)} of 13 in the DueCare submission.\n"
        f"#\n"
        f"# {entry['lede']}\n"
        f"#\n"
        f"# What to look for after Run All:\n"
        f"{look_for}\n"
        f"#\n"
        f"# Demo path: {entry['demo_path']}\n"
        f"#\n"
        f"# Full README + cross-kernel index: see the README in this folder.\n"
        f"\n"
    )


def insert_script_intro(script_path: Path, intro_comment: str) -> bool:
    """Prepend a comment-block intro to the kernel script if not already present."""
    text = script_path.read_text(encoding="utf-8")
    if INTRO_MARKER in text:
        return False
    script_path.write_text(intro_comment + text, encoding="utf-8")
    return True


def standardize_readme_h1(readme_path: Path, entry: dict[str, object]) -> bool:
    """Replace whatever the README's first h1 is with the canonical form."""
    text = readme_path.read_text(encoding="utf-8")
    canonical_h1 = f"# DueCare — {entry['title']} ({kernel_short_id(entry)})\n"
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("# "):
            if line == canonical_h1:
                return False
            lines[index] = canonical_h1
            readme_path.write_text("".join(lines), encoding="utf-8")
            return True
    # No h1 yet; prepend one.
    readme_path.write_text(canonical_h1 + "\n" + text, encoding="utf-8")
    return True


def render_lane_label(entry: dict[str, object]) -> str:
    """Return the canonical visible lane label for one kernel README."""
    lanes = " · ".join(str(lane) for lane in entry.get("lanes", []))
    return f"{LANE_MARKER}\n> **Serves lanes:** {lanes}\n"


def insert_or_replace_lane_label(readme_path: Path, entry: dict[str, object]) -> bool:
    """Place the lane label immediately below the README h1."""
    text = readme_path.read_text(encoding="utf-8")
    lane_label = render_lane_label(entry)
    if LANE_MARKER in text:
        pattern = re.compile(
            rf"{re.escape(LANE_MARKER)}\n> \*\*Serves lanes:\*\* [^\n]*(?:\n|$)"
        )
        new_text = pattern.sub(lane_label, text, count=1)
        if new_text == text:
            return False
        readme_path.write_text(new_text, encoding="utf-8")
        return True

    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("# "):
            tail = lines[index + 1:]
            if tail and not tail[0].strip():
                tail = tail[1:]
            new_lines = lines[:index + 1] + [lane_label, "\n"] + tail
            readme_path.write_text("".join(new_lines), encoding="utf-8")
            return True

    readme_path.write_text(lane_label + "\n" + text, encoding="utf-8")
    return True


def render_footer(current: dict[str, object]) -> str:
    """Build the shared cross-kernel footer with prev/next/index nav."""
    rows: list[str] = []
    for entry in KERNELS:
        marker = "**" if entry["folder"] == current["folder"] else ""
        slug = entry["folder"]
        label = f"{kernel_short_id(entry)}: {entry['title']}"
        rows.append(f"- {marker}[{label}](../{slug}/README.md){marker}")
    body = "\n".join(rows)
    return (
        f"\n\n---\n\n{FOOTER_MARKER}\n\n"
        f"### All DueCare kernels\n\n"
        f"You are here: **{kernel_short_id(current)} — {current['title']}**.\n\n"
        f"{body}\n\n"
        f"Index page: [`kaggle/_INDEX.md`](../_INDEX.md).\n"
    )


def append_or_replace_footer(readme_path: Path, footer: str) -> bool:
    text = readme_path.read_text(encoding="utf-8")
    if FOOTER_MARKER in text:
        before, _, _ = text.partition(FOOTER_MARKER)
        # Drop the previous "---" separator we added so footer regenerates cleanly.
        before = re.sub(r"\n+---\n+$", "\n", before)
        new_text = before.rstrip() + footer
    else:
        new_text = text.rstrip() + footer
    if new_text == text:
        return False
    readme_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    edited = {"intros": 0, "h1s": 0, "lane_labels": 0, "footers": 0}
    for entry in KERNELS:
        folder = KAGGLE_ROOT / str(entry["folder"])
        if not folder.is_dir():
            print(f"SKIP {entry['folder']}: folder not found")
            continue

        script = folder / "kernel.py"
        readme = folder / "README.md"

        # Add intro to kernel.py only. The judge-facing submission is a
        # copy/paste script-kernel workflow; root notebook wrappers are
        # intentionally not tracked.
        if script.is_file():
            if insert_script_intro(script, render_intro_python_comment(entry)):
                edited["intros"] += 1
                print(f"INTRO {entry['folder']} (script)")

        if readme.is_file():
            if standardize_readme_h1(readme, entry):
                edited["h1s"] += 1
                print(f"H1    {entry['folder']}")
            if insert_or_replace_lane_label(readme, entry):
                edited["lane_labels"] += 1
                print(f"LANE  {entry['folder']}")
            if append_or_replace_footer(readme, render_footer(entry)):
                edited["footers"] += 1
                print(f"FOOT  {entry['folder']}")

    print(
        "\nDone. "
        f"Inserted {edited['intros']} kernel intros, "
        f"standardized {edited['h1s']} README h1s, "
        f"updated {edited['lane_labels']} lane labels, "
        f"refreshed {edited['footers']} footers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
