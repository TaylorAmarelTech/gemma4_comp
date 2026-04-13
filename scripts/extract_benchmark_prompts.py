#!/usr/bin/env python3
"""Extract prompts from the trafficking LLM benchmark into DueCare format.

Reads from ALL sources in the original benchmark codebase and produces:
  1. configs/duecare/domains/trafficking/seed_prompts.jsonl  (full corpus)
  2. configs/duecare/domains/trafficking/rubric.yaml          (ported 5 rubrics)
  3. A summary report of what was extracted

Sources (in priority order):
  - manual_tests/taylor_amarel_tests.json          (graded, highest quality)
  - manual_tests/taylor_amarel_extended.json        (graded, highest quality)
  - legacy_kaggle_tests/*.json                      (graded, with responses)
  - all_conversations.json                          (graded, with responses)
  - untested_prompts_final.json                     (prompts only, 42K)
  - untested_prompts_500k.json                      (prompts only, 28K)
  - untested_prompts_massive.json                   (prompts only, 2.4K)
  - untested_prompts.json                           (prompts only, 1K)
  - generated_tests/*.json                          (prompts with metadata)
  - advanced_test_variations.json                   (prompts with attack metadata)
  - data/test_catalog.db                            (SQLite)
  - trafficking_tests.db                            (SQLite)

Output format (JSONL, one per line):
{
  "id": "...",
  "text": "the actual prompt text",
  "category": "business_framed_exploitation|victim_revictimization|...",
  "difficulty": "basic|medium|hard",
  "expected_grade": "best",
  "source": "taylor_amarel_tests|untested_prompts_final|...",
  "graded_responses": {"worst": "...", "best": "..."} | null,
  "metadata": {...}
}
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

BENCHMARK_ROOT = Path(
    r"C:\Users\amare\OneDrive\Documents\Migrant_Worker_LLM_Test_Benchmark_Trafficking_Bondage_Etc\trafficking_llm_benchmark"
)
DUECARE_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = DUECARE_ROOT / "configs" / "duecare" / "domains" / "trafficking"

# DueCare grade mapping: benchmark uses 1-5, DueCare uses worst/bad/neutral/good/best
GRADE_MAP = {"1": "worst", "2": "bad", "3": "neutral", "4": "good", "5": "best"}

# Category normalization
CATEGORY_ALIASES = {
    "business_framed_exploitation": "business_framed_exploitation",
    "bfe": "business_framed_exploitation",
    "jurisdictional_hierarchy": "jurisdictional_hierarchy_exploitation",
    "jurisdictional_hierarchy_exploitation": "jurisdictional_hierarchy_exploitation",
    "jhe": "jurisdictional_hierarchy_exploitation",
    "financial_crime_blindness": "financial_crime_blindness",
    "fcb": "financial_crime_blindness",
    "prompt_injection_amplification": "prompt_injection_amplification",
    "pia": "prompt_injection_amplification",
    "victim_revictimization": "victim_revictimization",
    "victim_support": "victim_revictimization",
    "vrv": "victim_revictimization",
    "persona_attack": "prompt_injection_amplification",
    "regulatory_evasion": "jurisdictional_hierarchy_exploitation",
    "recruitment_fees": "business_framed_exploitation",
    "debt_bondage": "business_framed_exploitation",
    "document_fraud": "jurisdictional_hierarchy_exploitation",
    "wage_theft": "financial_crime_blindness",
    "coercion": "victim_revictimization",
}


def normalize_category(raw: str) -> str:
    lower = raw.lower().strip()
    return CATEGORY_ALIASES.get(lower, lower)


def extract_graded_responses(responses: dict) -> dict | None:
    """Convert benchmark's {1: [...], 2: [...], ...} to DueCare format."""
    if not responses:
        return None
    result = {}
    for grade_num, texts in responses.items():
        grade_name = GRADE_MAP.get(str(grade_num))
        if grade_name and texts:
            # Take the first (best) example for each grade
            result[grade_name] = texts[0] if isinstance(texts, list) else texts
    return result if result else None


class Extractor:
    def __init__(self) -> None:
        self.prompts: list[dict] = []
        self.seen_ids: set[str] = set()
        self.seen_texts: set[str] = set()  # dedupe by first 200 chars
        self.source_counts: Counter = Counter()

    def add(self, item: dict, source: str) -> bool:
        """Add a prompt item. Returns True if added (not a duplicate)."""
        pid = item.get("id", "")
        text = item.get("text", "")
        if not text or len(text.strip()) < 10:
            return False

        text_key = text.strip()[:200].lower()
        if text_key in self.seen_texts:
            return False

        if pid and pid in self.seen_ids:
            return False

        self.seen_ids.add(pid)
        self.seen_texts.add(text_key)
        item["source"] = source
        self.prompts.append(item)
        self.source_counts[source] += 1
        return True

    def _load_json(self, path: Path) -> list | dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ! Failed to read {path.name}: {e}")
            return []

    # ── Graded tests (manual + legacy + conversations) ──

    def extract_graded_json(self, path: Path, source: str) -> int:
        """Extract from files with responses: {1: [...], 2: [...], ...}"""
        data = self._load_json(path)
        if isinstance(data, dict) and "variations" in data:
            data = data["variations"]
        if not isinstance(data, list):
            print(f"  ! {path.name}: expected list, got {type(data).__name__}")
            return 0
        count = 0
        for entry in data:
            text = entry.get("prompt", "")
            if not text:
                continue
            graded = extract_graded_responses(entry.get("responses", {}))
            item = {
                "id": entry.get("id", f"{source}_{count}"),
                "text": text,
                "category": normalize_category(entry.get("category", "unknown")),
                "difficulty": entry.get("difficulty", "medium"),
                "expected_grade": "best",
                "graded_responses": graded,
                "metadata": {
                    k: v
                    for k, v in entry.items()
                    if k not in ("id", "prompt", "category", "difficulty", "responses", "text")
                },
            }
            if self.add(item, source):
                count += 1
        return count

    # ── Untested prompts (no responses) ──

    def extract_untested_json(self, path: Path, source: str) -> int:
        data = self._load_json(path)
        if not isinstance(data, list):
            return 0
        count = 0
        for entry in data:
            text = entry.get("prompt", "")
            if not text:
                continue
            item = {
                "id": entry.get("id", f"{source}_{count}"),
                "text": text,
                "category": normalize_category(
                    entry.get("category", entry.get("subcategory", "unknown"))
                ),
                "difficulty": entry.get("difficulty", "medium"),
                "expected_grade": "best",
                "graded_responses": None,
                "metadata": {
                    "attack_strategy": entry.get("attack_strategy"),
                    "corridor": entry.get("corridor"),
                    "scheme": entry.get("scheme"),
                    "source_file": entry.get("source_file"),
                },
            }
            if self.add(item, source):
                count += 1
        return count

    # ── Generated tests (with variation metadata) ──

    def extract_generated_json(self, path: Path, source: str) -> int:
        data = self._load_json(path)
        if isinstance(data, dict) and "variations" in data:
            data = data["variations"]
        if not isinstance(data, list):
            return 0
        count = 0
        for entry in data:
            text = entry.get("prompt", "")
            if not text:
                continue
            item = {
                "id": entry.get("id", f"{source}_{count}"),
                "text": text,
                "category": normalize_category(
                    entry.get("suite", entry.get("category", "unknown"))
                ),
                "difficulty": entry.get("difficulty", "hard"),
                "expected_grade": "best",
                "graded_responses": extract_graded_responses(entry.get("responses", {})),
                "metadata": {
                    "variation_type": entry.get("variation_type"),
                    "base_test_id": entry.get("base_test_id"),
                    "amplifier": entry.get("amplifier"),
                    "corridor": entry.get("corridor"),
                },
            }
            if self.add(item, source):
                count += 1
        return count

    # ── SQLite databases ──

    def extract_sqlite(self, db_path: Path, source: str) -> int:
        if not db_path.exists():
            print(f"  ! {db_path.name}: not found")
            return 0
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tests LIMIT 100000")
            count = 0
            for row in cursor:
                row_dict = dict(row)
                text = row_dict.get("prompt", row_dict.get("test_prompt", ""))
                if not text or len(str(text).strip()) < 10:
                    continue
                item = {
                    "id": str(row_dict.get("id", f"{source}_{count}")),
                    "text": str(text),
                    "category": normalize_category(
                        str(row_dict.get("category", row_dict.get("vulnerability_category", "unknown")))
                    ),
                    "difficulty": str(row_dict.get("difficulty", "medium")),
                    "expected_grade": "best",
                    "graded_responses": None,
                    "metadata": {"db_source": source},
                }
                if self.add(item, source):
                    count += 1
            conn.close()
            return count
        except Exception as e:
            print(f"  ! {db_path.name}: {e}")
            return 0

    def run(self) -> None:
        print("# Extracting benchmark prompts into DueCare format")
        print(f"  Benchmark root: {BENCHMARK_ROOT}")
        print(f"  Output dir:     {OUTPUT_DIR}")
        print()

        # Phase 1: Highest quality — graded manual tests
        print("## Phase 1: Graded manual tests")
        for f in ["taylor_amarel_tests.json", "taylor_amarel_extended.json"]:
            p = BENCHMARK_ROOT / "data" / "manual_tests" / f
            if p.exists():
                n = self.extract_graded_json(p, f.replace(".json", ""))
                print(f"  {f}: {n} prompts")

        # Phase 2: Graded legacy Kaggle tests
        print("\n## Phase 2: Legacy Kaggle tests (graded)")
        legacy_dir = BENCHMARK_ROOT / "legacy_kaggle_tests"
        if legacy_dir.exists():
            for f in sorted(legacy_dir.glob("*.json")):
                n = self.extract_graded_json(f, f"legacy_{f.stem}")
                if n > 0:
                    print(f"  {f.name}: {n} prompts")

        # Phase 3: All conversations (graded)
        print("\n## Phase 3: All conversations (graded)")
        conv = BENCHMARK_ROOT / "all_conversations.json"
        if conv.exists():
            n = self.extract_graded_json(conv, "all_conversations")
            print(f"  all_conversations.json: {n} prompts")

        # Phase 4: Consolidated tests
        for f in sorted(BENCHMARK_ROOT.glob("all_tests_consolidated_*.json")):
            n = self.extract_graded_json(f, f"consolidated_{f.stem}")
            if n > 0:
                print(f"  {f.name}: {n} prompts")

        # Phase 5: Generated tests (with attack metadata)
        print("\n## Phase 4: Generated tests")
        gen_dir = BENCHMARK_ROOT / "generated_tests"
        if gen_dir.exists():
            for f in sorted(gen_dir.glob("*.json")):
                n = self.extract_generated_json(f, f"gen_{f.stem}")
                if n > 0:
                    print(f"  {f.name}: {n} prompts")

        # Phase 6: Advanced test variations
        adv = BENCHMARK_ROOT / "advanced_test_variations.json"
        if adv.exists():
            n = self.extract_generated_json(adv, "advanced_variations")
            print(f"  advanced_test_variations.json: {n} prompts")

        # Phase 7: Untested prompts (largest volume)
        print("\n## Phase 5: Untested prompts")
        for f in [
            "untested_prompts.json",
            "untested_prompts_massive.json",
            "untested_prompts_500k.json",
            "untested_prompts_final.json",
        ]:
            p = BENCHMARK_ROOT / "data" / f
            if p.exists():
                n = self.extract_untested_json(p, f.replace(".json", ""))
                print(f"  {f}: {n} prompts")

        # Phase 8: SQLite databases
        print("\n## Phase 6: SQLite databases")
        for db_name in ["test_catalog.db", "trafficking_tests.db", "test_results.db"]:
            candidates = [
                BENCHMARK_ROOT / db_name,
                BENCHMARK_ROOT / "data" / db_name,
            ]
            for db_path in candidates:
                if db_path.exists():
                    n = self.extract_sqlite(db_path, db_name.replace(".db", ""))
                    print(f"  {db_name}: {n} prompts")
                    break

        # Phase 9: CLI-generated tests
        print("\n## Phase 7: Other JSON sources")
        for f in [
            "claude_cli_generated_tests.json",
            "claude_cli_tests_expanded.json",
            "multi_turn_attacks.json",
            "dual_encoding_attacks.json",
        ]:
            p = BENCHMARK_ROOT / f
            if p.exists():
                n = self.extract_graded_json(p, f.replace(".json", ""))
                if n > 0:
                    print(f"  {f}: {n} prompts")

        # Summary
        print("\n" + "=" * 60)
        print(f"  TOTAL UNIQUE PROMPTS: {len(self.prompts)}")
        print("=" * 60)
        print("\n  By source:")
        for source, count in self.source_counts.most_common():
            print(f"    {source:<45} {count:>7}")

        print("\n  By category:")
        cat_counts = Counter(p["category"] for p in self.prompts)
        for cat, count in cat_counts.most_common():
            print(f"    {cat:<45} {count:>7}")

        graded = sum(1 for p in self.prompts if p.get("graded_responses"))
        print(f"\n  Graded (with reference responses): {graded}")
        print(f"  Ungraded (prompt only):            {len(self.prompts) - graded}")

        # Write output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / "seed_prompts.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for item in self.prompts:
                # Clean up None metadata values
                if item.get("metadata"):
                    item["metadata"] = {
                        k: v for k, v in item["metadata"].items() if v is not None
                    }
                f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")

        print(f"\n  Written to: {out_path}")
        print(f"  File size:  {out_path.stat().st_size / 1024 / 1024:.1f} MB")


def main() -> int:
    extractor = Extractor()
    extractor.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
