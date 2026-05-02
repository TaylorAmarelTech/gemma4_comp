#!/usr/bin/env python3
"""Validate, stat, and split the Duecare prompt corpus.

Usage:
    python scripts/prompt_corpus.py validate
    python scripts/prompt_corpus.py stats              # writes docs/corpus_stats.md
    python scripts/prompt_corpus.py export-by-category # writes _examples/by_category/*.json
    python scripts/prompt_corpus.py all                # all three
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_DIR = (REPO_ROOT / "packages" / "duecare-llm-chat" / "src"
               / "duecare" / "chat" / "harness")
EXAMPLES_PATH = HARNESS_DIR / "_examples.json"
RUBRICS_5TIER_PATH = HARNESS_DIR / "_rubrics_5tier.json"
RUBRICS_REQUIRED_PATH = HARNESS_DIR / "_rubrics_required.json"
BY_CATEGORY_DIR = HARNESS_DIR / "_examples" / "by_category"
STATS_PATH = REPO_ROOT / "docs" / "corpus_stats.md"

CANONICAL_CATEGORIES = {
    "amplification_known_attacks", "jurisdictional_hierarchy",
    "victim_revictimization", "financial_crime_blindness",
    "social_media_recruitment", "business_framed_exploitation",
    "private_message_grooming", "group_chat_pattern", "fake_document",
    "receipt_evidence", "regulatory_evasion", "coercion_manipulation",
    "knowledge_check", "financial_obfuscation", "compound_textbook",
    "moral_religious_framing", "mega_variations",
    "prompt_injection_amplification",
}

CANONICAL_DIFFICULTY = {"easy", "medium", "hard"}

CANONICAL_ILO = {
    "debt_bondage", "deception", "withholding_documents",
    "wage_withholding", "freedom_of_movement", "excessive_overtime",
    "intimidation_threats", "abuse_of_vulnerability",
    "physical_sexual_violence", "isolation",
    "abusive_working_living_conditions",
    "child_labour_indicators", "discrimination_pregnancy",
    "id_theft_risk", "advance_fee_fraud",
    # Less-used but allowed
    "withholding_food", "withholding_of_documents", "withholding_of_wages",
    "restriction_of_movement",
}

CORRIDOR_RX = re.compile(r"^[A-Za-z]{2,6}-[A-Za-z]{2,6}$")


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------
def cmd_validate() -> int:
    """Check every prompt has required fields + valid vocabulary."""
    examples = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    print(f"Validating {len(examples)} prompts in {EXAMPLES_PATH.name}...")
    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    for i, p in enumerate(examples):
        prefix = f"  [{i}] id={p.get('id', '<missing>')}"
        if "id" not in p or not p["id"]:
            errors.append(f"{prefix}: missing id")
            continue
        if p["id"] in seen_ids:
            errors.append(f"{prefix}: duplicate id")
        seen_ids.add(p["id"])
        if "text" not in p or not p["text"]:
            errors.append(f"{prefix}: missing text")
        elif len(p["text"]) < 30:
            warnings.append(f"{prefix}: text < 30 chars ({len(p['text'])})")
        if "category" not in p:
            errors.append(f"{prefix}: missing category")
        elif p["category"] not in CANONICAL_CATEGORIES:
            warnings.append(f"{prefix}: non-canonical category "
                            f"{p['category']!r}")
        if "difficulty" in p and p["difficulty"] not in CANONICAL_DIFFICULTY:
            warnings.append(f"{prefix}: non-canonical difficulty "
                            f"{p['difficulty']!r}")
        if "corridor" in p and p["corridor"] and \
                not CORRIDOR_RX.match(p["corridor"]):
            warnings.append(f"{prefix}: corridor {p['corridor']!r} doesn't "
                            f"match XX-XX shape")
        for ind in (p.get("ilo_indicators") or []):
            if ind not in CANONICAL_ILO:
                warnings.append(f"{prefix}: non-canonical ILO indicator "
                                f"{ind!r}")
    print(f"  {len(errors)} errors, {len(warnings)} warnings")
    for e in errors:
        print(f"  ERROR: {e}")
    for w in warnings[:30]:
        print(f"  WARN:  {w}")
    if len(warnings) > 30:
        print(f"  ... + {len(warnings) - 30} more warnings")
    return 0 if not errors else 1


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
def _bar(n: int, max_n: int, width: int = 30) -> str:
    if max_n <= 0:
        return ""
    filled = int((n / max_n) * width)
    return "█" * filled + "░" * (width - filled)


def cmd_stats() -> int:
    examples = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    rubrics_5tier = (json.loads(RUBRICS_5TIER_PATH.read_text(encoding="utf-8"))
                     if RUBRICS_5TIER_PATH.exists() else {})
    rubrics_req = (json.loads(RUBRICS_REQUIRED_PATH.read_text(encoding="utf-8"))
                   if RUBRICS_REQUIRED_PATH.exists() else {})

    by_cat = Counter(p.get("category", "_unknown") for p in examples)
    by_sub = Counter(p.get("subcategory", "_unknown") for p in examples)
    by_corridor = Counter(p.get("corridor", "_unknown") for p in examples
                          if p.get("corridor"))
    by_difficulty = Counter(p.get("difficulty", "_unknown") for p in examples)
    by_sector = Counter(p.get("sector", "_unknown") for p in examples)
    by_ilo: Counter = Counter()
    for p in examples:
        for ind in (p.get("ilo_indicators") or []):
            by_ilo[ind] += 1

    by_id_prefix: Counter = Counter()
    for p in examples:
        pid = p.get("id", "")
        prefix = pid.split("_", 1)[0] if "_" in pid else pid
        by_id_prefix[prefix] += 1

    # Coverage matrix: category × corridor
    matrix: dict = defaultdict(Counter)
    for p in examples:
        cat = p.get("category", "_unknown")
        cor = p.get("corridor", "_unknown")
        if cor != "_unknown":
            matrix[cat][cor] += 1

    # Build the markdown
    md_lines = [
        "# Duecare Prompt Corpus — Statistics",
        "",
        f"> Auto-generated by `scripts/prompt_corpus.py stats` on every release.",
        f"> Re-run after adding new prompts. **Do not hand-edit.**",
        "",
        "## Headline numbers",
        "",
        f"- **Total prompts:** {len(examples)}",
        f"- **Categories represented:** {len(by_cat)}",
        f"- **Subcategories:** {len(by_sub)}",
        f"- **Corridors:** {len(by_corridor)}",
        f"- **ILO indicators tagged:** {len(by_ilo)}",
        f"- **5-tier rubrics:** {len(rubrics_5tier)} (per-prompt graded examples)",
        f"- **Required-element rubrics:** {len(rubrics_req)} (per-category)",
        "",
        "## By category",
        "",
        "| Category | Count | Distribution |",
        "|---|---:|---|",
    ]
    max_cat = max(by_cat.values()) if by_cat else 1
    for cat, n in by_cat.most_common():
        md_lines.append(f"| `{cat}` | {n} | `{_bar(n, max_cat)}` |")
    md_lines.append("")

    md_lines += ["## By difficulty", "",
                 "| Difficulty | Count |", "|---|---:|"]
    for diff in ["easy", "medium", "hard", "_unknown"]:
        n = by_difficulty.get(diff, 0)
        if n:
            md_lines.append(f"| `{diff}` | {n} |")
    md_lines.append("")

    md_lines += ["## By corridor", "",
                 "| Corridor | Count |", "|---|---:|"]
    for cor, n in by_corridor.most_common():
        md_lines.append(f"| `{cor}` | {n} |")
    md_lines.append("")

    md_lines += ["## By sector", "",
                 "| Sector | Count |", "|---|---:|"]
    for sec, n in by_sector.most_common():
        md_lines.append(f"| `{sec}` | {n} |")
    md_lines.append("")

    md_lines += ["## By ILO indicator", "",
                 "| Indicator | Count |", "|---|---:|"]
    for ind, n in by_ilo.most_common():
        md_lines.append(f"| `{ind}` | {n} |")
    md_lines.append("")

    md_lines += ["## By id prefix (provenance)", "",
                 "Tells you which corpus batch each prompt came from.",
                 "",
                 "| Prefix | Count | Provenance |", "|---|---:|---|"]
    PROVENANCE = {
        "traf":         "original hand-curated set",
        "amplification": "original (renumbered)",
        "jurisdictional": "original (renumbered)",
        "victim":       "original (renumbered)",
        "financial":    "original (renumbered)",
        "textbook":     "compound textbook scenarios",
        "multiparty":   "multi-party + governed-by additions (2026-04-29)",
        "social":       "social media post additions (2026-04-30)",
        "dm":           "private DM additions (2026-04-30)",
        "group":        "group chat additions (2026-04-30)",
        "doc":          "fake document additions (2026-04-30)",
        "receipt":      "receipt/financial evidence additions (2026-04-30)",
        "writeup":      "writeup canonical (gpt-oss-20b actionable tests)",
        "esoteric":     "esoteric / archaic legal language (2026-04-30)",
    }
    for prefix, n in by_id_prefix.most_common():
        prov = PROVENANCE.get(prefix, "")
        if "_nb_" in prefix:
            prov = "extracted from published Kaggle notebooks"
        md_lines.append(f"| `{prefix}_*` | {n} | {prov} |")
    md_lines.append("")

    # Coverage matrix
    md_lines += ["## Coverage matrix: category × corridor", "",
                 "How many prompts of each category exist for each corridor.",
                 "Empty cells reveal gaps in coverage.",
                 ""]
    cats_sorted = sorted(matrix.keys(), key=lambda c: -sum(matrix[c].values()))[:10]
    cors_sorted = sorted({c for cat_cors in matrix.values()
                          for c in cat_cors.keys()})
    md_lines.append("| Category | " + " | ".join(cors_sorted) + " | TOTAL |")
    md_lines.append("|" + "---|" * (len(cors_sorted) + 2))
    for cat in cats_sorted:
        row = [f"`{cat}`"] + \
              [str(matrix[cat].get(c, "")) for c in cors_sorted] + \
              [str(sum(matrix[cat].values()))]
        md_lines.append("| " + " | ".join(row) + " |")
    md_lines.append("")

    # Rubric coverage
    md_lines += ["## Rubric coverage", "",
                 f"Of {len(examples)} prompts, "
                 f"**{sum(1 for p in examples if any(p.get('id') in k for k in rubrics_5tier))}**"
                 f" have an explicit 5-tier rubric in `_rubrics_5tier.json`.",
                 "",
                 "Categories with required-element rubrics in `_rubrics_required.json`:",
                 ""]
    for cat, rub in rubrics_req.items():
        n_crit = len(rub.get("criteria", []))
        md_lines.append(f"- `{cat}` ({n_crit} criteria, "
                        f"name: \"{rub.get('name', cat)}\")")
    md_lines.append("")

    md_lines += ["---", "",
                 "Run `python scripts/prompt_corpus.py stats` to refresh."]

    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"Wrote {STATS_PATH}  ({STATS_PATH.stat().st_size:,} bytes)")
    print(f"  {len(examples)} prompts across {len(by_cat)} categories, "
          f"{len(by_corridor)} corridors")
    return 0


# ---------------------------------------------------------------------------
# Export by category
# ---------------------------------------------------------------------------
def cmd_export_by_category() -> int:
    examples = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    BY_CATEGORY_DIR.mkdir(parents=True, exist_ok=True)
    by_cat: dict = defaultdict(list)
    for p in examples:
        by_cat[p.get("category", "_unknown")].append(p)
    print(f"Writing {len(by_cat)} per-category JSON files to "
          f"{BY_CATEGORY_DIR.relative_to(REPO_ROOT)}/...")
    for cat, items in sorted(by_cat.items()):
        fp = BY_CATEGORY_DIR / f"{cat}.json"
        fp.write_text(
            json.dumps(items, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"  {cat}.json: {len(items)} prompts ({fp.stat().st_size:,} bytes)")
    # Index file
    idx = {
        "total":      len(examples),
        "categories": {cat: len(items) for cat, items in sorted(by_cat.items())},
        "generated_at": "auto",
    }
    (BY_CATEGORY_DIR / "_index.json").write_text(
        json.dumps(idx, indent=2) + "\n", encoding="utf-8")
    print(f"  _index.json: written")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=("validate", "stats",
                                     "export-by-category", "all"))
    args = ap.parse_args()
    rc = 0
    if args.cmd in ("validate", "all"):
        rc |= cmd_validate()
    if args.cmd in ("stats", "all"):
        rc |= cmd_stats()
    if args.cmd in ("export-by-category", "all"):
        rc |= cmd_export_by_category()
    return rc


if __name__ == "__main__":
    sys.exit(main())
