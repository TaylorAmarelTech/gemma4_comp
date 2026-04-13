"""Document classification task.

Tests whether the model can multi-label classify a document against the
domain pack's taxonomy.
"""

from __future__ import annotations

import json
from datetime import datetime

from duecare.core.contracts import DomainPack, Model
from duecare.core.enums import Capability, TaskStatus
from duecare.core.schemas import ChatMessage, ItemResult, TaskConfig, TaskResult
from duecare.tasks import task_registry
from duecare.tasks.base import fresh_task_result


class ClassificationTask:
    id = "classification"
    name = "Document Classification"
    capabilities_required: set[Capability] = {Capability.TEXT}

    def run(
        self,
        model: Model,
        domain: DomainPack,
        config: TaskConfig,
    ) -> TaskResult:
        result = fresh_task_result(self.id, model, domain)
        taxonomy = domain.taxonomy()
        prompts = list(domain.seed_prompts())

        if config.sample_size:
            prompts = prompts[: config.sample_size]

        category_names = [c.get("id", c.get("name", "")) for c in taxonomy.get("categories", [])]

        sys_prompt = (
            f"Classify the following prompt into one of these categories: "
            f"{', '.join(category_names)}. "
            f"Respond with JSON: {{\"category\": \"<id>\"}}"
        )

        correct = 0
        n = len(prompts)

        for prompt in prompts:
            try:
                messages = [
                    ChatMessage(role="system", content=sys_prompt),
                    ChatMessage(role="user", content=prompt["text"]),
                ]
                gen = model.generate(
                    messages=messages,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature,
                )

                predicted = None
                try:
                    data = json.loads(gen.text.strip())
                    predicted = data.get("category")
                except json.JSONDecodeError:
                    # Fallback: look for category id in the free text
                    for cat in category_names:
                        if cat in gen.text:
                            predicted = cat
                            break

                expected = prompt.get("category")
                match = predicted == expected

                if match:
                    correct += 1

                result.per_item.append(
                    ItemResult(
                        item_id=prompt["id"],
                        input={"text": prompt["text"]},
                        model_output=gen.text,
                        expected={"category": expected},
                        scores={"predicted": predicted, "match": 1.0 if match else 0.0},
                        latency_ms=gen.latency_ms,
                    )
                )
            except Exception as e:
                result.per_item.append(
                    ItemResult(item_id=prompt["id"], errors=[str(e)])
                )

        result.metrics = {
            "category_accuracy": correct / n if n else 0.0,
            "n_prompts": float(n),
        }
        result.status = TaskStatus.COMPLETED
        result.ended_at = datetime.now()
        return result


task_registry.add("classification", ClassificationTask())
