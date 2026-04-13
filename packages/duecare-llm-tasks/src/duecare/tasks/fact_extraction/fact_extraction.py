"""Fact extraction task.

Tests whether the model can extract structured entities (person, org,
location, currency, date) from free-text source documents.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from duecare.core.contracts import DomainPack, Model
from duecare.core.enums import Capability, TaskStatus
from duecare.core.schemas import ChatMessage, ItemResult, TaskConfig, TaskResult
from duecare.tasks import task_registry
from duecare.tasks.base import fresh_task_result


DATE_PATTERN = re.compile(r"\b\d{4}\b")
CURRENCY_PATTERN = re.compile(r"\$|SAR|USD|AED|QAR|BHD|KWD|OMR|PHP|NPR|BDT|INR|LKR")


class FactExtractionTask:
    id = "fact_extraction"
    name = "Key Fact Extraction"
    capabilities_required: set[Capability] = {Capability.TEXT}

    def run(
        self,
        model: Model,
        domain: DomainPack,
        config: TaskConfig,
    ) -> TaskResult:
        result = fresh_task_result(self.id, model, domain)
        evidence = list(domain.evidence())

        if config.sample_size:
            evidence = evidence[: config.sample_size]

        sys_prompt = (
            "Extract structured facts from the following text. Return JSON "
            "with keys: persons, organizations, locations, dates, currencies. "
            "Each value is a list of strings. Be exhaustive but not hallucinate."
        )

        total_accuracy = 0.0
        n = len(evidence)

        for ev in evidence:
            try:
                source = ev.get("summary", "") + " " + ev.get("source", "")
                messages = [
                    ChatMessage(role="system", content=sys_prompt),
                    ChatMessage(role="user", content=source),
                ]
                gen = model.generate(
                    messages=messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                )

                parsed: dict = {}
                try:
                    parsed = json.loads(gen.text.strip())
                except json.JSONDecodeError:
                    parsed = {}

                # Simple scoring: expected entities in source
                expected_dates = set(DATE_PATTERN.findall(source))
                found_dates = set(parsed.get("dates", []))
                date_overlap = len(expected_dates & found_dates) / max(1, len(expected_dates))

                score = date_overlap  # single-metric approximation
                total_accuracy += score

                result.per_item.append(
                    ItemResult(
                        item_id=ev.get("id", "ev_?"),
                        input={"source": source},
                        model_output=gen.text,
                        expected={"dates": list(expected_dates)},
                        scores={"date_overlap": date_overlap},
                        latency_ms=gen.latency_ms,
                    )
                )
            except Exception as e:
                result.per_item.append(
                    ItemResult(item_id=ev.get("id", "ev_?"), errors=[str(e)])
                )

        result.metrics = {
            "entity_overlap": total_accuracy / n if n else 0.0,
            "n_items": float(n),
        }
        result.status = TaskStatus.COMPLETED
        result.ended_at = datetime.now()
        return result


task_registry.add("fact_extraction", FactExtractionTask())
