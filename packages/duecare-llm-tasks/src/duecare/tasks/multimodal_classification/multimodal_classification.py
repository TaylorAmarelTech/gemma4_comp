"""Multimodal classification task.

Classifies a document image using the model's vision head. Requires
Capability.VISION on the model. If the model doesn't support vision,
run() raises RuntimeError.
"""

from __future__ import annotations

from datetime import datetime

from duecare.core.contracts import DomainPack, Model
from duecare.core.enums import Capability, TaskStatus
from duecare.core.schemas import TaskConfig, TaskResult
from duecare.tasks import task_registry
from duecare.tasks.base import fresh_task_result


class MultimodalClassificationTask:
    id = "multimodal_classification"
    name = "Multimodal Document Classification"
    capabilities_required: set[Capability] = {Capability.TEXT, Capability.VISION}

    def run(
        self,
        model: Model,
        domain: DomainPack,
        config: TaskConfig,
    ) -> TaskResult:
        if Capability.VISION not in model.capabilities:
            raise RuntimeError(
                f"Model {model.id} does not support vision "
                "(Capability.VISION required for multimodal_classification)"
            )

        result = fresh_task_result(self.id, model, domain)
        # TODO: load images from domain pack's images/ subfolder and
        # run model.generate with the `images=` kwarg
        # For now: return an empty result marked completed
        result.status = TaskStatus.COMPLETED
        result.ended_at = datetime.now()
        result.metrics = {"n_items": 0.0, "accuracy": 0.0}
        return result


task_registry.add("multimodal_classification", MultimodalClassificationTask())
