"""Generate the human-readable DueCare notebook guide.

The authoritative kernel inventory lives in ``kaggle/kernels/*`` metadata and
``scripts/kaggle_live_slug_map.json``. This script keeps
``docs/notebook_guide.md`` from drifting away from those sources while
preserving manually curated purpose text when it already exists.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from kaggle_notebook_utils import REPO_ROOT, KaggleNotebook, discover_kernel_notebooks


OUTPUT_PATH = REPO_ROOT / "docs" / "notebook_guide.md"
LIVE_MAP_PATH = REPO_ROOT / "scripts" / "kaggle_live_slug_map.json"


REVIEW_PRIORITY_ROWS = [
    (
        "P0",
        "000 / 005 / 010 / 600 / 610",
        "Judge path: index, glossary, quickstart, proof dashboard, and capstone walkthrough.",
    ),
    (
        "P0",
        "520 / 525 / 527 / 530 / 540",
        "Fine-tuning proof: curriculum, graded data, rubrics, Unsloth training, and delta visualization.",
    ),
    (
        "P1",
        "150 / 152 / 155 / 160 / 180 / 190",
        "Visible Gemma 4 features: chat, tool calling, multimodal document analysis, and retrieval inspection.",
    ),
    (
        "P1",
        "200-270 / 300-460 / 500-550",
        "Technical depth: cross-domain proof, model comparisons, adversarial testing, judge grading, and agent swarm.",
    ),
    (
        "P1",
        "620 / 650 / 660 / 670 / 680 / 690 / 695",
        "Implementation surfaces: API tour, custom-domain adoption, and deployment-application narratives.",
    ),
    (
        "P2",
        "Tracked drafts and skunkworks",
        "Keep structurally valid and documented; publish only if they strengthen the video story.",
    ),
]


def _load_live_map() -> dict[str, str | None]:
    if not LIVE_MAP_PATH.exists():
        return {}
    return json.loads(LIVE_MAP_PATH.read_text(encoding="utf-8"))


def _extract_existing_purposes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    purposes: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) < 5:
            continue
        notebook_id = parts[0].strip("`")
        purpose = parts[-1]
        if purpose and purpose != "Purpose":
            purposes[notebook_id] = purpose
    return purposes


def _extract_header_description(entry: KaggleNotebook) -> str | None:
    if entry.mirror_path is None or not entry.mirror_path.exists():
        return None
    try:
        notebook = json.loads(entry.mirror_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    joined = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook.get("cells", [])[:3]
    )
    match = re.search(r"font-size:13px;[^>]*>([^<]+)</div>", joined)
    if not match:
        return None
    text = html.unescape(match.group(1)).replace("\\'", "'").strip()
    return re.sub(r"\s+", " ", text)


def _fallback_purpose(entry: KaggleNotebook) -> str:
    clean_title = entry.title.replace("DueCare", "DueCare").strip()
    return f"Tracked DueCare notebook for {clean_title}; review builder, setup, outputs, and publication status before relying on it in the demo."


def _purpose_for(entry: KaggleNotebook, existing_purposes: dict[str, str]) -> str:
    return (
        existing_purposes.get(entry.notebook_number)
        or _extract_header_description(entry)
        or _fallback_purpose(entry)
    )


def _status_and_url(entry: KaggleNotebook, live_map: dict[str, str | None]) -> tuple[str, str]:
    live_id = live_map.get(entry.dir_name)
    if live_id:
        url = f"https://www.kaggle.com/code/{live_id}"
        return "Live", f"[{url}]({url})"
    return "Tracked draft", "Pending publication"


def render_notebook_guide(*, existing_path: Path = OUTPUT_PATH) -> str:
    """Render the notebook guide from metadata plus preserved purpose text."""
    entries = discover_kernel_notebooks()
    live_map = _load_live_map()
    existing_purposes = _extract_existing_purposes(existing_path)
    live_count = sum(1 for entry in entries if live_map.get(entry.dir_name))
    draft_count = len(entries) - live_count

    lines: list[str] = []
    lines.append("# DueCare Notebook Guide")
    lines.append("")
    lines.append(
        "`docs/current_kaggle_notebook_state.md` is the authoritative tracked-kernel inventory. "
        "This guide is the human-readable purpose map and review queue generated from the same metadata plus `scripts/kaggle_live_slug_map.json` for public live status."
    )
    lines.append("")
    lines.append("## Review order")
    lines.append("")
    lines.append(f"- Tracked kernels: **{len(entries)}**")
    lines.append(f"- Public-live notebooks in `kaggle_live_slug_map.json`: **{live_count}**")
    lines.append(f"- Tracked drafts / pending-publication notebooks: **{draft_count}**")
    lines.append("")
    lines.append("| Priority | Notebooks / modules | Why review in depth |")
    lines.append("|---|---|---|")
    for priority, notebooks, why in REVIEW_PRIORITY_ROWS:
        lines.append(f"| {priority} | {notebooks} | {why} |")
    lines.append("")
    lines.append("## Notebook purpose map")
    lines.append("")
    lines.append("| ID | Title | Status | Kaggle URL | Purpose |")
    lines.append("|---|---|---|---|---|")
    for entry in entries:
        status, url = _status_and_url(entry, live_map)
        purpose = _purpose_for(entry, existing_purposes)
        lines.append(
            f"| `{entry.notebook_number}` | {entry.title} | {status} | {url} | {purpose} |"
        )
    lines.append("")
    lines.append("## Module deep-review queue")
    lines.append("")
    lines.append("1. **Public hub IA and forms** — `apps/duecare-ai.com/app/main.py`, templates, pack filters, contribute flow, admin logs, and Render notes.")
    lines.append("2. **Wheel chat/runtime** — `packages/duecare-llm-chat/src/duecare/chat/app.py`, static viewers, classifier, harness data, and Cloudflare notebook launchers.")
    lines.append("3. **Fine-tuning data spine** — notebooks 520/525/527/530/540, `data/training*`, Unsloth settings, SFT/DPO wording, and artifact provenance.")
    lines.append("4. **Notebook builders and presentation gates** — `scripts/build_notebook_*.py`, `scripts/_notebook_display.py`, no lossy previews, Kaggle-safe HTML, and generated metadata.")
    lines.append("5. **Publishing and package split** — `packages/duecare-llm-*`, wheel metadata, Kaggle wheel datasets, README/package version consistency.")
    lines.append("6. **Demo surfaces** — `src/demo`, Cloudflare A-series kernels, deployment notebooks 660-695, cached demo examples, and no-wait recording flow.")
    lines.append("7. **Safety/privacy gates** — PII detectors, local-KB storage, anonymization previews, admin redaction, and public copy claims.")
    lines.append("")
    lines.append("Generated by `python scripts/generate_notebook_guide.py`.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUTPUT_PATH.write_text(render_notebook_guide(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
