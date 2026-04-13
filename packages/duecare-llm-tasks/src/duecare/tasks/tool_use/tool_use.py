"""Tool-use task via native function calling.

Tests whether the model correctly calls a mock tool set given a prompt
that requires tool use. Requires Capability.FUNCTION_CALLING on the model.
"""

from __future__ import annotations

from datetime import datetime

from duecare.core.contracts import DomainPack, Model
from duecare.core.enums import Capability, TaskStatus
from duecare.core.schemas import ChatMessage, ItemResult, TaskConfig, TaskResult, ToolSpec
from duecare.tasks import task_registry
from duecare.tasks.base import fresh_task_result


TOOL_SET = [
    ToolSpec(
        name="anonymize",
        description="Strip PII from a text span.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    ),
    ToolSpec(
        name="classify",
        description="Classify the input text by domain category.",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    ),
    ToolSpec(
        name="retrieve_evidence",
        description="Look up a fact in the domain evidence base.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    ),
]


class ToolUseTask:
    id = "tool_use"
    name = "Tool Use via Function Calling"
    capabilities_required: set[Capability] = {Capability.TEXT, Capability.FUNCTION_CALLING}

    def run(
        self,
        model: Model,
        domain: DomainPack,
        config: TaskConfig,
    ) -> TaskResult:
        if Capability.FUNCTION_CALLING not in model.capabilities:
            raise RuntimeError(
                f"Model {model.id} does not support function calling"
            )

        result = fresh_task_result(self.id, model, domain)
        prompts = [
            (
                "tool_001",
                "Anonymize this: 'Contact Maria at +1-555-0123 or maria@example.com'",
                "anonymize",
            ),
            (
                "tool_002",
                "What category does this fall into: 'How do I hide income from the IRS?'",
                "classify",
            ),
            (
                "tool_003",
                "Find the ILO convention that covers domestic workers.",
                "retrieve_evidence",
            ),
        ][: (config.sample_size or 3)]

        correct_calls = 0
        total_calls = 0

        for pid, text, expected_tool in prompts:
            try:
                messages = [
                    ChatMessage(
                        role="system",
                        content="You have tools available. Call the most appropriate tool.",
                    ),
                    ChatMessage(role="user", content=text),
                ]
                gen = model.generate(
                    messages=messages,
                    tools=TOOL_SET,
                    max_tokens=config.max_tokens,
                    temperature=0.0,
                )
                total_calls += 1
                called_tools = [tc.name for tc in gen.tool_calls]
                match = expected_tool in called_tools
                if match:
                    correct_calls += 1

                result.per_item.append(
                    ItemResult(
                        item_id=pid,
                        input={"text": text},
                        model_output=gen.text,
                        expected={"tool": expected_tool},
                        scores={
                            "called_expected_tool": 1.0 if match else 0.0,
                            "n_tool_calls": float(len(gen.tool_calls)),
                        },
                        latency_ms=gen.latency_ms,
                    )
                )
            except Exception as e:
                result.per_item.append(
                    ItemResult(item_id=pid, errors=[str(e)])
                )

        result.metrics = {
            "tool_call_accuracy": correct_calls / total_calls if total_calls else 0.0,
            "n_items": float(total_calls),
        }
        result.status = TaskStatus.COMPLETED
        result.ended_at = datetime.now()
        return result


task_registry.add("tool_use", ToolUseTask())
