"""Bring all 13 Kaggle kernels up to a consistent UX bar.

For each kernel:

1. Insert a top-of-file markdown intro (notebook) or comment-block
   intro (script) so a judge sees a clear "what this is, what to look
   for, demo path" before the first code line.
2. Standardise the README h1 to ``Duecare - <title> (#01 core | #A1 appendix)``.
3. Append a shared cross-kernel nav footer to every README so the 13
   feel like a series, with prev / next / index links.

Idempotent: each transform looks for its own marker and skips if it
already ran.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

KAGGLE_ROOT = Path(__file__).resolve().parent.parent / "kaggle"

INTRO_MARKER = "<!-- duecare:kernel-intro -->"
FOOTER_MARKER = "<!-- duecare:kernel-footer -->"


# (folder, kind, title, lede, look_for, demo_path)
# kind: "core-NN" or "appendix-NN"
KERNELS: list[dict[str, object]] = [
    {
        "folder": "01-duecare-harness-chat",
        "kind": "core",
        "n": 1,
        "title": "Migrant-worker safety playground",
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
        "title": "Original 4-toggle subset playground",
        "lede": "The pre-omni subset: GREP + RAG + Tools + Imports as toggleable layers (no Persona, no Online).",
        "look_for": [
            "Same chat surface as kernel 01 with 4 toggles instead of 6.",
            "Useful for showing how each layer contributes incrementally.",
            "The compare view shows GREP-only vs GREP+RAG side-by-side.",
        ],
        "demo_path": "Run All -> open URL -> toggle layers one at a time on the same prompt to isolate contributions.",
    },
    {
        "folder": "A-03-content-classification-playground",
        "kind": "appendix",
        "n": 3,
        "title": "Hands-on classification sandbox",
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
        "title": "Gemma generates evaluation prompts",
        "lede": "Gemma 4 self-generates new evaluation prompts plus 5 graded responses each (worst -> best).",
        "look_for": [
            "Each generated prompt comes with 5 anchor responses for grading calibration.",
            "Topics are seeded by corridor + sector; outputs land in JSONL.",
            "The grading rubric used here is the same shipped in citation-rubric@3.0.0.",
        ],
        "demo_path": "Run All -> watch the JSONL file fill -> open a sample prompt + 5 responses to see the grading anchors.",
    },
    {
        "folder": "A-07-bench-and-tune",
        "kind": "appendix",
        "n": 7,
        "title": "Unsloth fine-tune + GGUF export pipeline",
        "lede": "End-to-end SFT + DPO + GGUF Q8_0 + HF Hub push. The training pipeline behind the harness.",
        "look_for": [
            "SFT runs on the curated training set with the same anonymizer gate.",
            "DPO uses the 5-grade prompt set from kernel A-06 as preference pairs.",
            "GGUF export is the same path used for the LiteRT mobile build.",
        ],
        "demo_path": "Run All on a T4 -> watch the SFT curve -> see the GGUF artifact -> push to HF Hub (BYO token).",
    },
    {
        "folder": "A-08-research-graphs",
        "kind": "appendix",
        "n": 8,
        "title": "Research graphs (CPU-only)",
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
        "title": "Grading-lift regenerator",
        "lede": "Runs N prompts x 2 conditions, grades both, emits MD + JSON with provenance tuple (model, git_sha, dataset_version). The +56pp number, regenerated live.",
        "look_for": [
            "The output is a provenance-pinned report you can cite in the writeup.",
            "Run N from 10 (smoke) up to 207 (full reference set).",
            "Both the rule-based and LLM-based scores are recomputed live.",
        ],
        "demo_path": "Run All -> wait for the report -> see the headline lift number with the git_sha pinned.",
    },
]


def kernel_label(entry: dict[str, object]) -> str:
    if entry["kind"] == "core":
        return f"Core notebook #{entry['n']:02d}"
    return f"Appendix notebook #A{int(entry['n']):02d}"


def kernel_short_id(entry: dict[str, object]) -> str:
    if entry["kind"] == "core":
        return f"#{int(entry['n']):02d} core"
    return f"#A{int(entry['n']):02d} appendix"


def render_intro_markdown(entry: dict[str, object]) -> str:
    look_for = "\n".join(f"- {bullet}" for bullet in entry["look_for"])
    return (
        f"{INTRO_MARKER}\n\n"
        f"## DueCare — {entry['title']}\n\n"
        f"_{kernel_label(entry)} of 13 in the DueCare submission._\n\n"
        f"> {entry['lede']}\n\n"
        f"**What to look for after Run All:**\n\n{look_for}\n\n"
        f"**Demo path:** {entry['demo_path']}\n\n"
        f"Full README + cross-kernel index: see the README in this folder.\n"
    )


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


def insert_notebook_intro(notebook_path: Path, intro_md: str) -> bool:
    """Insert a markdown cell at the top of the notebook if not already present."""
    try:
        data = json.loads(notebook_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    cells = data.get("cells", [])
    for cell in cells:
        if cell.get("cell_type") == "markdown" and INTRO_MARKER in "".join(cell.get("source", [])):
            return False  # already present
    new_cell = {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in intro_md.splitlines()],
    }
    # Drop trailing newline on the last source line so the cell renders cleanly.
    if new_cell["source"]:
        new_cell["source"][-1] = new_cell["source"][-1].rstrip("\n")
    cells.insert(0, new_cell)
    data["cells"] = cells
    notebook_path.write_text(
        json.dumps(data, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


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
        f"### All DueCare notebooks\n\n"
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
    edited = {"intros": 0, "h1s": 0, "footers": 0}
    for entry in KERNELS:
        folder = KAGGLE_ROOT / str(entry["folder"])
        if not folder.is_dir():
            print(f"SKIP {entry['folder']}: folder not found")
            continue

        notebook = folder / "notebook.ipynb"
        script = folder / "kernel.py"
        readme = folder / "README.md"

        # Add intro to whichever surface(s) exist. Some kernels ship both
        # a kernel.py (what Kaggle executes) and a notebook.ipynb (what
        # judges open in their browser); both should carry the same intro.
        if notebook.is_file():
            if insert_notebook_intro(notebook, render_intro_markdown(entry)):
                edited["intros"] += 1
                print(f"INTRO {entry['folder']} (notebook)")
        if script.is_file():
            if insert_script_intro(script, render_intro_python_comment(entry)):
                edited["intros"] += 1
                print(f"INTRO {entry['folder']} (script)")

        if readme.is_file():
            if standardize_readme_h1(readme, entry):
                edited["h1s"] += 1
                print(f"H1    {entry['folder']}")
            if append_or_replace_footer(readme, render_footer(entry)):
                edited["footers"] += 1
                print(f"FOOT  {entry['folder']}")

    print(
        "\nDone. "
        f"Inserted {edited['intros']} kernel intros, "
        f"standardized {edited['h1s']} README h1s, "
        f"refreshed {edited['footers']} footers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
