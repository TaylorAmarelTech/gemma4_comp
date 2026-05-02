"""UnslothDatasetBuilder: takes labeled_examples + reviewed items and
produces a chat-format JSONL ready for unslothai/unsloth.
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional


# Each target_kind has its own prompt template that becomes the user
# turn in the Gemma 4 chat dataset. The label becomes the assistant
# turn. This mirrors the prompts the production harness uses, so the
# fine-tuned model's distribution matches the inference distribution.
_USER_PROMPT_TEMPLATES = {
    "document_category": (
        "Classify this document. Available categories: "
        "recruitment_contract, employment_contract, complaint_letter, "
        "passport_scan, remittance_slip, hotline_poster, chat_log, "
        "id_card, employer_letter, bank_statement, other.\n\n"
        "DOCUMENT TEXT:\n{input_text}\n\n"
        "Respond with the single category name only."
    ),
    "entity_type": (
        "Identify the entity type for the value in this snippet. "
        "Available types: person_or_org, organization, "
        "recruitment_agency, employer, phone, email, "
        "financial_account, address, passport_number, id_number, "
        "money, location, date.\n\n"
        "SNIPPET:\n{input_text}\n\n"
        "Respond with the single type name only."
    ),
    "fee_legitimacy": (
        "Assess whether the fee in this scenario is illegal under "
        "migrant-worker recruitment law.\n\n"
        "SCENARIO:\n{input_text}\n\n"
        "Respond with one of: illegal, legitimate, unknown."
    ),
    "finding_severity": (
        "Rate the severity of this trafficking-safety finding on a "
        "0-10 scale.\n\n"
        "FINDING:\n{input_text}\n\n"
        "Respond with the integer only."
    ),
}


class UnslothDatasetBuilder:
    """Read labeled_examples, write a chat-format JSONL Unsloth
    consumes (matches the format used by the existing NB 530)."""

    def __init__(self, store, system_prompt: Optional[str] = None) -> None:
        self.store = store
        self.system_prompt = system_prompt or (
            "You are Duecare, a privacy-preserving migrant-worker "
            "trafficking-safety assistant. Be terse, factual, and "
            "cite ILO / national statutes by code when relevant.")

    def build(self,
                output_path: str,
                min_confidence: float = 0.7,
                only_human_reviewed: bool = False,
                train_frac: float = 0.85,
                val_frac: float = 0.10,
                seed: int = 17) -> dict:
        """Write JSONL splits and return the manifest dict.

        Output structure:
          <output_path>             -- the train split (default)
          <output_path>.val.jsonl   -- val split
          <output_path>.test.jsonl  -- test split
          <output_path>.manifest.json -- counts + class distribution
        """
        rows = self.store.fetchall(
            "SELECT example_id, target_kind, target_id, input_text, "
            "label, confidence, source_strategy, review_status "
            "FROM labeled_examples "
            "WHERE confidence >= ? "
            "AND review_status IN "
            f"({'(\"human_approved\")' if only_human_reviewed else '(\"auto\", \"human_approved\")'})",
            (min_confidence,))
        if not rows:
            raise RuntimeError(
                "no labeled examples meet the criteria. Lower "
                "min_confidence or run `duecare train labels` first.")

        # Stratified split per (target_kind, label).
        rng = random.Random(seed)
        by_class: dict = defaultdict(list)
        for r in rows:
            key = (r["target_kind"], r["label"])
            by_class[key].append(r)
        train, val, test = [], [], []
        for key, items in by_class.items():
            rng.shuffle(items)
            n = len(items)
            n_train = max(1, int(n * train_frac))
            n_val = max(0, int(n * val_frac))
            train.extend(items[:n_train])
            val.extend(items[n_train:n_train + n_val])
            test.extend(items[n_train + n_val:])

        # Write splits
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        train_path = out_path
        val_path = out_path.with_suffix(out_path.suffix + ".val.jsonl")
        test_path = out_path.with_suffix(out_path.suffix + ".test.jsonl")
        manifest_path = out_path.with_suffix(
            out_path.suffix + ".manifest.json")

        for split_path, split_rows in (
                (train_path, train), (val_path, val), (test_path, test)):
            with split_path.open("w", encoding="utf-8") as f:
                for r in split_rows:
                    f.write(json.dumps(self._row_to_chat(r),
                                          ensure_ascii=False) + "\n")

        manifest = {
            "n_total": len(rows),
            "n_train": len(train),
            "n_val": len(val),
            "n_test": len(test),
            "min_confidence": min_confidence,
            "only_human_reviewed": only_human_reviewed,
            "class_distribution": dict(
                Counter(f"{r['target_kind']}::{r['label']}" for r in rows)),
            "train_path": str(train_path),
            "val_path": str(val_path),
            "test_path": str(test_path),
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, default=str), encoding="utf-8")
        return manifest

    def _row_to_chat(self, r: dict) -> dict:
        kind = r["target_kind"]
        tmpl = _USER_PROMPT_TEMPLATES.get(
            kind, "{input_text}\n\nLabel:")
        user = tmpl.format(input_text=r["input_text"])
        return {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user},
                {"role": "assistant", "content": str(r["label"])},
            ],
            "metadata": {
                "example_id": r["example_id"],
                "target_kind": kind,
                "target_id": r["target_id"],
                "confidence": r["confidence"],
                "source_strategy": r["source_strategy"],
                "review_status": r["review_status"],
            },
        }
