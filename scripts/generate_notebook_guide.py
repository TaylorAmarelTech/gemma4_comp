"""Generate the human-readable DueCare active-kernel guide.

The active judge-facing Kaggle path lives in the root ``kaggle/*``
script-kernel folders with ``kernel-metadata.json``. This script keeps
``docs/notebook_guide.md`` aligned with that active inventory while
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
        "01-duecare-exploration-workbench",
        "Broad reviewer workbench: chat, harness comparison, search, knowledge extraction, bulk review, and trace inspection.",
    ),
    (
        "P0",
        "02-live-demo",
        "Focused live demo and video path for the current judging story.",
    ),
    (
        "P1",
        "A-00-omni-experiment-workbench",
        "Quantitative proof path: baseline, harnessed, synthetic-data, fine-tuning, judging, and report artifacts.",
    ),
    (
        "P1",
        "kaggle/kernels/* generated mirrors",
        "Reference-only generated mirror material. Do not treat it as the active submission path.",
    ),
]

ACTIVE_KERNEL_PURPOSES = {
    "01-duecare-exploration-workbench": (
        "Broad reviewer workbench for chat, harness comparison, bulk review, "
        "knowledge extraction, search, sharing, traces, and activity logs."
    ),
    "02-live-demo": (
        "Focused live demo path for judges and video capture, using the shared "
        "Gemma 4 runtime and live-demo surface."
    ),
    "A-00-omni-experiment-workbench": (
        "Quantitative control plane for baseline, harnessed, synthetic-data, "
        "fine-tuning, judging, checkpointing, and report evidence bundles."
    ),
}


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
        ACTIVE_KERNEL_PURPOSES.get(entry.dir_name)
        or existing_purposes.get(entry.notebook_number)
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
    lines.append("# DueCare Kaggle Kernel Guide")
    lines.append("")
    lines.append(
        "`kaggle/_INDEX.md` and `docs/current_kaggle_notebook_state.md` are the authoritative active-kernel inventory. "
        "This guide is the human-readable purpose map generated from the same root `kaggle/*/kernel-metadata.json` script-kernel folders, "
        "plus `scripts/kaggle_live_slug_map.json` for public live status."
    )
    lines.append("")
    lines.append("## Notebook artifact policy")
    lines.append("")
    lines.append(
        "Do not create `.ipynb` notebooks for the judge-facing submission by default. "
        "Treat `kernel.py` plus the folder README as the source of truth. "
        "Historical notebook wrappers live under `_archive/kaggle-notebook-previews-2026-05-11/`; "
        "do not recreate them in active `kaggle/*/` folders unless Taylor explicitly asks."
    )
    lines.append("")
    lines.append(
        "Every judge-facing Kaggle bundle must make its own bootstrap path explicit: "
        "print required Kaggle settings, fail fast on missing GPU/secrets/datasets/model "
        "sources, install DueCare from attached Kaggle wheels first, then pinned PyPI, "
        "then immutable GitHub release assets or commit-pinned archives only as a fallback, "
        "and print the resolved DueCare version before loading Gemma 4. Never rely on "
        "`_reference/`, local `.venv`, root-level legacy mirrors, untracked files, or "
        "a moving GitHub branch such as `main`."
    )
    lines.append("")
    lines.append("## Review order")
    lines.append("")
    lines.append(f"- Active script kernels: **{len(entries)}**")
    lines.append(f"- Public-live active kernels in `kaggle_live_slug_map.json`: **{live_count}**")
    lines.append(f"- Active kernels without a live slug: **{draft_count}**")
    lines.append("")
    lines.append("| Priority | Notebooks / modules | Why review in depth |")
    lines.append("|---|---|---|")
    for priority, notebooks, why in REVIEW_PRIORITY_ROWS:
        lines.append(f"| {priority} | {notebooks} | {why} |")
    lines.append("")
    lines.append("## Active kernel purpose map")
    lines.append("")
    lines.append("| ID | Title | Status | Kaggle URL | Purpose |")
    lines.append("|---|---|---|---|---|")
    for entry in entries:
        status, url = _status_and_url(entry, live_map)
        purpose = _purpose_for(entry, existing_purposes)
        display_id = entry.notebook_number if entry.notebook_number != "kernel" else entry.dir_name
        lines.append(
            f"| `{display_id}` | {entry.title} | {status} | {url} | {purpose} |"
        )
    lines.append("")
    lines.append("## Active module deep-review queue")
    lines.append("")
    lines.append("1. **Exploration workbench** - `kaggle/01-duecare-exploration-workbench/kernel.py`, `packages/duecare-llm-chat/src/duecare/chat/app.py`, and the registered harness pages.")
    lines.append("2. **Live demo** - `kaggle/02-live-demo/kernel.py`, `packages/duecare-llm-server/src/duecare/server`, and the Cloudflare launch path.")
    lines.append("3. **A-00 experiment pipeline** - `kaggle/A-00-omni-experiment-workbench/kernel.py`, checkpointing, activity artifacts, reports, and judge options.")
    lines.append("4. **Shared runtime and harnesses** - `gemma4_runtime.py`, `harness/__init__.py`, `harnesses/base.py`, and `harnesses/model_interface.py`.")
    lines.append("5. **Docs and contract tests** - harness trinity docs, model-loading trace, A-00 parity tests, workbench UI tests, and active Kaggle state docs.")
    lines.append("")
    lines.append("Generated by `python scripts/generate_notebook_guide.py`.")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUTPUT_PATH.write_text(render_notebook_guide(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
