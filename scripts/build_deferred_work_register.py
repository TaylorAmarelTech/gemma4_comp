#!/usr/bin/env python3
"""Render the public deferred-work register from its canonical JSON source.

The generated document is intentionally detailed: every unfinished item has a
real owner role, reason, prerequisites, ordered actions, acceptance gates, and
evidence paths. Rendering is deterministic and never calls a model or network.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "configs" / "duecare" / "deferred_work.json"
DOCUMENT_PATH = ROOT / "docs" / "DEFERRED_WORK.md"

STATUS_LABELS = {
    "blocked_private_access": "Blocked: private access",
    "blocked_human_review": "Blocked: human review",
    "deferred_owner_decision": "Deferred: owner decision",
    "deferred_budget": "Deferred: budget or quota",
    "ready_local": "Ready: local and model-free",
    "recurring_maintenance": "Recurring maintenance",
}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    """Load the canonical registry as a JSON object."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("deferred-work registry root must be an object")
    return data


def _evidence_link(path: str) -> str:
    target = path.removeprefix("docs/") if path.startswith("docs/") else f"../{path}"
    return f"[`{path}`]({target})"


def _bullet_list(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values]


def _numbered_list(values: list[str]) -> list[str]:
    return [f"{index}. {value}" for index, value in enumerate(values, 1)]


def render_registry(data: dict[str, Any]) -> str:
    """Return the deterministic Markdown representation of *data*."""
    items = data.get("items") or []
    lines = [
        "# Deferred Work Register",
        "",
        "This document is generated from",
        "[`configs/duecare/deferred_work.json`](../configs/duecare/deferred_work.json).",
        "It is the canonical boundary between work that can be completed in a",
        "model-free repository change and work that requires private access, human",
        "review, owner authorization, provider spend, or Kaggle quota.",
        "",
        f"**Current as of:** {data.get('as_of', '')}",
        "",
        f"**Maintenance posture:** {data.get('maintenance_posture', '')}",
        "",
        "## Completion Policy",
        "",
        data["policy"]["completion_rule"],
        "",
        data["policy"]["claim_rule"],
        "",
        data["policy"]["cost_rule"],
        "",
        data["policy"]["privacy_rule"],
        "",
        "A status records why work is not complete; it is not permission to bypass",
        "the listed boundary. Empty fields, fabricated approvals, guessed versions,",
        "and undated completion claims are rejected by",
        "`python scripts/validate_deferred_work.py`.",
        "",
        "## Summary",
        "",
        "| Priority | Work item | Status | Owner role | Model-credit policy |",
        "|---|---|---|---|---|",
    ]
    for item in items:
        lines.append(
            "| "
            f"{item['priority']} | "
            f"[{item['title']}](#{item['id']}) | "
            f"{STATUS_LABELS.get(item['status'], item['status'])} | "
            f"{item['owner_role']} | "
            f"{item['model_credit_policy']} |"
        )

    ready = [item for item in items if item["status"] == "ready_local"]
    recurring = [item for item in items if item["status"] == "recurring_maintenance"]
    gated = [item for item in items if item not in ready and item not in recurring]
    lines.extend(
        [
            "",
            "## Pickup Order",
            "",
            "The safe sequence is:",
            "",
            "1. Preserve the whole-stack cost stop and establish live Git, process,",
            "   scheduler, provider, and publication truth.",
            "2. Complete local model-free items in small reviewable changes.",
            "3. Continue recurring source-freshness work without silently replacing",
            "   older evidence.",
            "4. Start a gated item only when its owner, prerequisites, and authorization",
            "   are present; then retain every acceptance artifact.",
            "",
            "**Ready for model-free repository work:** "
            + ", ".join(f"`{item['id']}`" for item in ready)
            + ".",
            "",
            "**Recurring maintenance:** "
            + ", ".join(f"`{item['id']}`" for item in recurring)
            + ".",
            "",
            "**Externally or human gated:** "
            + ", ".join(f"`{item['id']}`" for item in gated)
            + ".",
        ]
    )

    for item in items:
        dependencies = item["depends_on"]
        lines.extend(
            [
                "",
                f"## {item['title']}",
                f"<a id=\"{item['id']}\"></a>",
                "",
                f"- **ID:** `{item['id']}`",
                f"- **Priority:** {item['priority']}",
                f"- **Status:** {STATUS_LABELS.get(item['status'], item['status'])}",
                f"- **Owner role:** {item['owner_role']}",
                f"- **Target:** {item['target']}",
                f"- **Model-credit policy:** `{item['model_credit_policy']}`",
                f"- **Network/write policy:** `{item['network_policy']}`",
                "- **Depends on:** "
                + (
                    ", ".join(f"`{dependency}`" for dependency in dependencies)
                    if dependencies
                    else "No other register item"
                ),
                "",
                f"**Why it remains open:** {item['reason']}",
                "",
                "### Prerequisites",
                "",
                *_bullet_list(item["prerequisites"]),
                "",
                "### Ordered next actions",
                "",
                *_numbered_list(item["next_actions"]),
                "",
                "### Done only when",
                "",
                *_bullet_list(item["acceptance_gates"]),
                "",
                "### Evidence and controls",
                "",
                *[f"- {_evidence_link(path)}" for path in item["evidence"]],
            ]
        )

    lines.extend(
        [
            "",
            "## Updating This Register",
            "",
            "1. Edit `configs/duecare/deferred_work.json`.",
            "2. Run `python scripts/build_deferred_work_register.py`.",
            "3. Run `python scripts/validate_deferred_work.py`.",
            "4. Run `python scripts/validate_publication_readiness.py --scope core`",
            "   and the smallest tests for any affected surface.",
            "5. Change an item to a completed historical receipt only in a separate",
            "   dated document after every acceptance gate has evidence; remove it from",
            "   this outstanding-work registry in the same reviewed change.",
            "",
        ]
    )
    return "\n".join(lines)


def write_atomic(path: Path, content: str) -> None:
    """Write *content* atomically using UTF-8 and LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when docs/DEFERRED_WORK.md differs from the canonical rendering",
    )
    args = parser.parse_args(argv)

    rendered = render_registry(load_registry())
    if args.check:
        current = DOCUMENT_PATH.read_text(encoding="utf-8") if DOCUMENT_PATH.exists() else ""
        if current == rendered:
            print("Deferred-work document: current")
            return 0
        print("Deferred-work document: stale; run python scripts/build_deferred_work_register.py")
        return 1

    write_atomic(DOCUMENT_PATH, rendered)
    print(f"Wrote {DOCUMENT_PATH.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
