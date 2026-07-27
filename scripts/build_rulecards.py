#!/usr/bin/env python3
"""Compile DueCare's real GREP indicator rules into an auditable RuleCard deck.

Reads the live ``GREP_RULES`` data plus the ``CATEGORY X: ...`` section headers
in ``_grep_rules.py`` (so every card knows its category), compiles each rule into
a typed ``RuleCard``, and writes:

- ``rulecard-deck.json``        -- the full typed deck
- ``rulecard-summary.json``     -- aggregate roll-up
- ``rulecard-independence.json``-- correlated-witness families + concentration
- ``rulecard_independence.md``  -- a human-readable independence report

Everything is derived deterministically from the real rules; no model is called
and nothing is invented. This turns the hard-coded harness into a governed
supervision fabric per the 2026-07 finetuning blueprint.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GREP_RULES_PATH = (
    ROOT
    / "packages"
    / "duecare-llm-chat"
    / "src"
    / "duecare"
    / "chat"
    / "harness"
    / "_grep_rules.py"
)
DEFAULT_OUTPUT = ROOT / "reports" / "rulecards"

_RULECARDS_SPEC = importlib.util.spec_from_file_location(
    "duecare_rulecards",
    ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "rulecards.py",
)
assert _RULECARDS_SPEC and _RULECARDS_SPEC.loader
rulecards = importlib.util.module_from_spec(_RULECARDS_SPEC)
# Register before exec so the frozen dataclass can resolve its own annotations.
sys.modules["duecare_rulecards"] = rulecards
_RULECARDS_SPEC.loader.exec_module(rulecards)


def load_grep_rules(path: Path) -> list[dict[str, Any]]:
    spec = importlib.util.spec_from_file_location("_grep_rules_data", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load GREP rules from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rules = list(module.GREP_RULES)
    if not rules:
        raise RuntimeError("GREP_RULES is empty")
    return rules


def categories_by_rule_order(path: Path) -> list[str]:
    """Map each rule (in file order) to the nearest preceding CATEGORY comment.

    The rules file marks sections with ``# CATEGORY A: DEBT BONDAGE ...``
    comments. We parse the AST to find each rule dict in order and the source
    text to find which category comment most recently preceded it.
    """
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    category_at_line: list[tuple[int, str]] = []
    header = re.compile(r"#\s*CATEGORY\s+([A-Z0-9]+)\s*:\s*(.+?)\s*$")
    for index, line in enumerate(lines):
        match = header.search(line)
        if match:
            label = f"{match.group(1)}: {match.group(2).strip()}"
            category_at_line.append((index, label))

    def category_for_line(lineno: int) -> str:
        current = "uncategorized"
        for at_line, label in category_at_line:
            if at_line < lineno:
                current = label
            else:
                break
        return current

    tree = ast.parse(source, filename=str(path))
    categories: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "GREP_RULES" for t in node.targets
        ):
            if not isinstance(node.value, ast.List):
                continue
            for element in node.value.elts:
                if isinstance(element, ast.Dict):
                    categories.append(category_for_line(element.lineno))
    return categories


def build(output_dir: Path, *, grep_path: Path = GREP_RULES_PATH) -> dict[str, Any]:
    rules = load_grep_rules(grep_path)
    categories = categories_by_rule_order(grep_path)
    if len(categories) != len(rules):
        # Fall back to uncategorized rather than mis-align; the AST walk and the
        # runtime list can only diverge if the file structure changed.
        categories = ["uncategorized"] * len(rules)
    cards = rulecards.compile_deck(rules, categories)
    deck = [card.to_dict() for card in cards]
    summary = rulecards.deck_summary(cards)
    independence = rulecards.independence_report(cards)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "rulecard-deck.json", {
        "schema_version": rulecards.SCHEMA_VERSION,
        "source": str(grep_path.relative_to(ROOT)).replace("\\", "/"),
        "cards": deck,
    })
    _write_json(output_dir / "rulecard-summary.json", summary)
    _write_json(output_dir / "rulecard-independence.json", independence)
    (output_dir / "rulecard_independence.md").write_text(
        render_independence_markdown(summary, independence), encoding="utf-8", newline="\n"
    )
    return {
        "output_dir": str(output_dir),
        "cards": len(deck),
        "families": independence["effective_independent_families"],
        "largest_family": independence["largest_family_rule_count"],
        "summary": summary,
    }


def render_independence_markdown(
    summary: dict[str, Any], independence: dict[str, Any]
) -> str:
    lines = [
        "# RuleCard independence report",
        "",
        "> Generated by `scripts/build_rulecards.py` from the real GREP rule deck. "
        "Deterministic; no model call.",
        "",
        independence["interpretation"],
        "",
        "## Deck at a glance",
        "",
        f"- **{summary['total_cards']:,} RuleCards** compiled from the live harness rules.",
        "- Severity: " + ", ".join(
            f"{sev} {n}" for sev, n in summary["severity_counts"].items()
        ) + ".",
        f"- {summary['cards_with_authoritative_source']:,} cite a recognized authoritative "
        f"instrument; {summary['cards_missing_source']:,} do not.",
        f"- {summary['candidate_invariant_review_count']:,} critical-severity cards are "
        "flagged for human hard-invariant review (never auto-promoted).",
        "",
        "## Correlated-witness families",
        "",
        f"The {independence['total_rules']:,} rules resolve to "
        f"**{independence['effective_independent_families']:,} witness families** "
        f"(reduction ratio {independence['reduction_ratio']}). The top five families "
        f"hold {int(independence['top5_family_concentration'] * 100)}% of the deck.",
        "",
        "| Authoritative source | Rules anchored on it |",
        "|---|---:|",
    ]
    for source, count in list(independence["rules_per_authoritative_source"].items())[:15]:
        lines.append(f"| `{source}` | {count:,} |")
    lines += [
        "",
        "**Why this matters:** a family of rules that all cite the same instrument "
        "are correlated votes, not independent confirmations. Weak-supervision "
        "label models must down-weight within-family agreement so a single legal "
        "principle expressed as many patterns cannot masquerade as many independent "
        "witnesses.",
        "",
        "## Universal calibration gaps",
        "",
        "Every card inherits these gaps from its raw GREP source; closing them is "
        "the RuleCard roadmap:",
        "",
    ]
    for gap in summary["universal_calibration_gaps"]:
        lines.append(f"- `{gap}`")
    lines.append("")
    return "\n".join(lines)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    value.add_argument("--grep-rules", type=Path, default=GREP_RULES_PATH)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    result = build(args.output, grep_path=args.grep_rules)
    printable = {k: v for k, v in result.items() if k != "summary"}
    printable["severity_counts"] = result["summary"]["severity_counts"]
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
