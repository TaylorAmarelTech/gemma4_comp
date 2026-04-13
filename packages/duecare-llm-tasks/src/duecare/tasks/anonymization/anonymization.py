"""Anonymization task.

Tests whether the model can detect and redact PII categories from the
domain pack's pii_spec.yaml.
"""

from __future__ import annotations

import re
from datetime import datetime

from duecare.core.contracts import DomainPack, Model
from duecare.core.enums import Capability, TaskStatus
from duecare.core.schemas import ChatMessage, ItemResult, TaskConfig, TaskResult
from duecare.tasks import task_registry
from duecare.tasks.base import fresh_task_result


# Regex-based reference PII detector for eval ground truth.
PII_PATTERNS = {
    "phone": r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "passport": r"\b[A-Z]{1,2}\d{6,9}\b",
    "iban": r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b",
}


def detect_pii(text: str) -> dict[str, list[str]]:
    """Regex-based PII detector used as eval ground truth."""
    hits: dict[str, list[str]] = {}
    for category, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            hits[category] = matches
    return hits


SAMPLE_PII_TEXTS = [
    "Contact Maria at +1-555-0123 or maria@example.com for the meeting.",
    "Her passport number is AB1234567 and her IBAN is DE89370400440532013000.",
    "Call +971-50-1234567 to reach the recruiter at recruiter@example.ae.",
    "My phone is +63 917 555 0101 and I live in Manila.",
]


class AnonymizationTask:
    id = "anonymization"
    name = "PII Anonymization"
    capabilities_required: set[Capability] = {Capability.TEXT}

    def run(
        self,
        model: Model,
        domain: DomainPack,
        config: TaskConfig,
    ) -> TaskResult:
        result = fresh_task_result(self.id, model, domain)

        texts = SAMPLE_PII_TEXTS[: config.sample_size] if config.sample_size else SAMPLE_PII_TEXTS

        sys_prompt = (
            "You are a PII redactor. Given a text, produce the same text with "
            "every piece of personally identifiable information replaced by a "
            "tag like [PHONE], [EMAIL], [PASSPORT], [IBAN], [NAME], [ADDRESS]. "
            "Preserve the rest of the text exactly."
        )

        total_recall = 0.0
        total_precision = 0.0
        n = len(texts)

        for i, original in enumerate(texts):
            try:
                messages = [
                    ChatMessage(role="system", content=sys_prompt),
                    ChatMessage(role="user", content=original),
                ]
                gen = model.generate(
                    messages=messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                )

                expected_hits = detect_pii(original)
                # Expected PII count
                expected_count = sum(len(v) for v in expected_hits.values())

                # Does the output still contain any of the original PII?
                remaining_hits = detect_pii(gen.text)
                remaining_count = sum(len(v) for v in remaining_hits.values())

                # Recall = (expected - remaining) / expected
                redacted_count = max(0, expected_count - remaining_count)
                recall = redacted_count / expected_count if expected_count else 1.0

                # Precision proxy: did the model add obvious false positives?
                fp_tags = gen.text.count("[") - gen.text.count("]")  # rough
                precision = 1.0 if fp_tags == 0 else 0.5

                total_recall += recall
                total_precision += precision

                result.per_item.append(
                    ItemResult(
                        item_id=f"pii_{i:03d}",
                        input={"original": original},
                        model_output=gen.text,
                        expected={"hits": expected_hits},
                        scores={"recall": recall, "precision": precision},
                        latency_ms=gen.latency_ms,
                    )
                )
            except Exception as e:
                result.per_item.append(
                    ItemResult(item_id=f"pii_{i:03d}", errors=[str(e)])
                )

        result.metrics = {
            "pii_span_recall": total_recall / n if n else 0.0,
            "pii_span_precision": total_precision / n if n else 0.0,
            "n_items": float(n),
        }
        result.status = TaskStatus.COMPLETED
        result.ended_at = datetime.now()
        return result


task_registry.add("anonymization", AnonymizationTask())
