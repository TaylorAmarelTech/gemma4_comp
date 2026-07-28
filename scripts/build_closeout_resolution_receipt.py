#!/usr/bin/env python3
"""Render the dated DueCare closeout receipt from its canonical JSON source."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = ROOT / "configs" / "duecare" / "closeout_resolutions.json"
DOCUMENT_PATH = ROOT / "docs" / "CLOSEOUT_RESOLUTIONS_2026_07_28.md"

OUTCOME_LABELS = {
    "retained_risk": "Closed with retained risk",
    "owner_retained": "Closed; current owner retained",
    "decided": "Decision completed",
    "declined": "Explicitly declined",
    "excluded": "Excluded from claims",
    "completed_current_cycle": "Current cycle completed",
}


def load_receipt(path: Path = RECEIPT_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("closeout receipt root must be an object")
    return data


def _evidence_link(path: str) -> str:
    target = path.removeprefix("docs/") if path.startswith("docs/") else f"../{path}"
    return f"[`{path}`]({target})"


def render_receipt(data: dict[str, Any]) -> str:
    items = data["items"]
    posture = data["maintenance_mode"]
    counts = Counter(item["outcome"] for item in items)
    lines = [
        "# Closeout Resolution Receipt - 2026-07-28",
        "",
        "This dated receipt is generated from",
        "[`configs/duecare/closeout_resolutions.json`](../configs/duecare/closeout_resolutions.json).",
        "It records the final disposition of the inherited closeout queue without",
        "inventing private account evidence, human review, source rights, billing",
        "records, model runs, notebook runs, or publication events.",
        "",
        f"**Closed on:** {data['closed_on']}",
        "",
        f"**Scope:** {data['scope']}",
        "",
        f"**Decision authority:** {data['authority']}",
        "",
        "## Result",
        "",
        f"All **{len(items)} inherited items have a dated disposition**. The canonical",
        "[deferred-work register](DEFERRED_WORK.md) therefore contains zero current",
        "items. Zero outstanding items does not mean every proposed activity was",
        "performed; the table distinguishes completed decisions and maintenance from",
        "declined work, exclusions, current-owner retention, and retained risk.",
        "",
        "| Outcome | Count |",
        "|---|---:|",
    ]
    for outcome, label in OUTCOME_LABELS.items():
        lines.append(f"| {label} | {counts.get(outcome, 0)} |")
    lines.extend(
        [
            "",
            "## Enacted Maintenance Mode",
            "",
            f"- **Effective:** {posture['effective_on']}",
            f"- **Public surfaces:** {posture['public_surfaces']}",
            f"- **Models:** {posture['model_posture']}",
            f"- **Publication:** {posture['publication_posture']}",
            f"- **Claims:** {posture['claim_posture']}",
            f"- **Next scheduled freshness review:** {posture['next_freshness_review']}",
            "",
            "## Item-by-item Disposition",
            "",
            "| Item | Outcome | Reversible |",
            "|---|---|---|",
        ]
    )
    for item in items:
        lines.append(
            f"| [{item['title']}](#{item['id']}) | "
            f"{OUTCOME_LABELS[item['outcome']]} | "
            f"{'Yes' if item['reversible'] else 'No'} |"
        )
    for item in items:
        lines.extend(
            [
                "",
                f"### {item['title']}",
                f'<a id="{item["id"]}"></a>',
                "",
                f"- **Register ID:** `{item['id']}`",
                f"- **Outcome:** {OUTCOME_LABELS[item['outcome']]}",
                f"- **Decision:** {item['decision']}",
                f"- **Rationale:** {item['rationale']}",
                f"- **Verification:** {item['verification']}",
                f"- **Claim boundary:** {item['claim_boundary']}",
                f"- **Reversible:** {'Yes' if item['reversible'] else 'No'}",
                "",
                "**Reopen only when:**",
                "",
                *[f"- {condition}" for condition in item["reopen_conditions"]],
                "",
                "**Evidence and controls:**",
                "",
                *[f"- {_evidence_link(path)}" for path in item["evidence"]],
            ]
        )
    lines.extend(
        [
            "",
            "## How To Reopen Work Safely",
            "",
            "A future maintainer should add a new outstanding item to",
            "`configs/duecare/deferred_work.json` only when a stated reopen condition",
            "is actually met. Preserve this receipt unchanged as the 2026-07-28",
            "decision record, give the new work a dated target and acceptance evidence,",
            "and rerun both closeout and deferred-work validators.",
            "",
        ]
    )
    return "\n".join(lines)


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent,
        prefix=f".{path.name}.", delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    rendered = render_receipt(load_receipt())
    if args.check:
        current = DOCUMENT_PATH.read_text(encoding="utf-8") if DOCUMENT_PATH.exists() else ""
        if current == rendered:
            print("Closeout resolution receipt: current")
            return 0
        print("Closeout resolution receipt: stale; run the receipt builder")
        return 1
    write_atomic(DOCUMENT_PATH, rendered)
    print(f"Wrote {DOCUMENT_PATH.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
