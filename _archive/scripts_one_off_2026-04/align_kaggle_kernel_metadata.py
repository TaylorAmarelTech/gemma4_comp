"""Align Kaggle kernel metadata with the current publish plan.

This script is the local preparation step before any publish run. It
does not talk to Kaggle. Instead, it normalizes every
`kernel-metadata.json` so the next authenticated push uses the correct
kernel id, visibility, competition tag, and keywords.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from kaggle_notebook_utils import discover_kernel_notebooks, slugify_title


REPO_ROOT = Path(__file__).resolve().parents[1]
SLUG_MAP_PATH = REPO_ROOT / "scripts" / "kaggle_live_slug_map.json"
COMPETITION_SOURCE = ["gemma-4-good-hackathon"]
WHEELS_DATASET = "taylorsamarel/duecare-llm-wheels"

KEYWORDS_BY_SECTION = {
    "orientation": ["gemma", "safety", "llm", "trafficking", "tutorial"],
    "exploration": ["gemma", "safety", "llm", "trafficking", "baseline"],
    "comparison": ["gemma", "llm-comparison", "safety", "evaluation"],
    "adversarial": ["adversarial", "red-team", "jailbreak", "safety"],
    "tools": ["function-calling", "tool-use", "multimodal", "gemma"],
    "evaluation": ["llm-judge", "rubric", "grading", "safety"],
    "pipeline": ["agent", "fine-tuning", "unsloth", "lora"],
    "results": ["evaluation"],
    "deployment": ["deployment", "gemma", "safety", "evaluation"],
    "conclusion": ["gemma", "safety", "evaluation", "summary"],
}

CONCLUSION_IDS = {99, 199, 299, 399, 499, 599, 699, 799, 899}
JAILBREAK_IDS = set(range(181, 190))
DEPLOYMENT_IDS = {620, 650, 660, 670, 680, 690, 695}
PIPELINE_IDS = {500, 510, 520, 525, 527, 530, 540, 550}


def _load_slug_map() -> dict[str, str | None]:
    return json.loads(SLUG_MAP_PATH.read_text(encoding="utf-8"))


def _section_for(notebook_number: str) -> str:
    numeric_id = int(notebook_number)
    if numeric_id in CONCLUSION_IDS:
        return "conclusion"
    if numeric_id <= 99:
        return "orientation"
    if numeric_id in JAILBREAK_IDS:
        return "adversarial"
    if 100 <= numeric_id <= 199:
        return "exploration"
    if 200 <= numeric_id <= 270:
        return "comparison"
    if 300 <= numeric_id <= 399:
        return "adversarial"
    if numeric_id == 400:
        return "tools"
    if 401 <= numeric_id <= 499:
        return "evaluation"
    if numeric_id in PIPELINE_IDS or 500 <= numeric_id <= 599:
        return "pipeline"
    if 600 <= numeric_id <= 610:
        return "results"
    if numeric_id in DEPLOYMENT_IDS or 620 <= numeric_id <= 695:
        return "deployment"
    if 696 <= numeric_id <= 899:
        return "results"
    raise ValueError(f"Unsupported notebook id: {notebook_number}")


def _normalized_title(existing_title: str, notebook_number: str) -> str:
    if "duecare" in existing_title.lower():
        return existing_title
    return f"DueCare {notebook_number} {existing_title}".strip()


def _desired_kernel_id(*, current_id: str | None, title: str, slug_override: str | None) -> str:
    if slug_override:
        return slug_override
    if current_id:
        return current_id
    return f"taylorsamarel/{slugify_title(title)}"


def _align_metadata(meta: dict[str, Any], *, notebook_number: str, slug_override: str | None) -> dict[str, Any]:
    aligned = dict(meta)
    aligned_title = _normalized_title(str(meta["title"]), notebook_number)
    aligned["title"] = aligned_title
    aligned["id"] = _desired_kernel_id(
        current_id=str(meta.get("id", "")).strip() or None,
        title=aligned_title,
        slug_override=slug_override,
    )
    aligned["keywords"] = KEYWORDS_BY_SECTION[_section_for(notebook_number)]
    aligned["is_private"] = False
    aligned["competition_sources"] = COMPETITION_SOURCE
    aligned.setdefault("enable_tpu", False)
    dataset_sources = list(aligned.get("dataset_sources", []))
    if WHEELS_DATASET not in dataset_sources:
        dataset_sources.insert(0, WHEELS_DATASET)
    aligned["dataset_sources"] = dataset_sources
    aligned.setdefault("kernel_sources", [])
    return aligned


def main() -> int:
    parser = argparse.ArgumentParser(description="Align Kaggle kernel metadata before publishing.")
    parser.add_argument("--check", action="store_true", help="Report drift without writing files.")
    args = parser.parse_args()

    slug_map = _load_slug_map()
    changed = 0

    for entry in discover_kernel_notebooks():
        meta_path = entry.dir_path / "kernel-metadata.json"
        current = json.loads(meta_path.read_text(encoding="utf-8"))
        slug_override = slug_map.get(entry.dir_name)
        aligned = _align_metadata(
            current,
            notebook_number=entry.notebook_number,
            slug_override=slug_override,
        )

        if aligned == current:
            print(f"ok    {entry.dir_name} -> {aligned['id']}")
            continue

        changed += 1
        print(f"fix   {entry.dir_name} -> {aligned['id']}")
        if not args.check:
            meta_path.write_text(json.dumps(aligned, indent=2) + "\n", encoding="utf-8")

    if args.check and changed:
        print(f"\n{changed} metadata files need alignment.")
        return 1

    print(f"\nAlignment complete. Changed: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())