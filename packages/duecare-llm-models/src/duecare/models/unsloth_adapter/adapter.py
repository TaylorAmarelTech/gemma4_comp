"""Unsloth adapter - fast local inference + fine-tune.

Wraps Unsloth's FastLanguageModel. Used by the Trainer agent for Gemma 4
LoRA fine-tunes.
"""

from __future__ import annotations

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("unsloth")
class UnslothModel(ModelAdapterBase):
    """Unsloth FastLanguageModel wrapper. Lazy-imports unsloth + torch."""

    provider = "unsloth"

    def __init__(
        self,
        model_id: str,
        display_name: str | None = None,
        max_seq_length: int = 4096,
        load_in_4bit: bool = True,
    ) -> None:
        super().__init__()
        self.id = f"unsloth:{model_id}"
        self.display_name = display_name or model_id
        self.model_id = model_id
        self.max_seq_length = max_seq_length
        self.load_in_4bit = load_in_4bit
        self.context_length = max_seq_length
        self.capabilities = {Capability.TEXT, Capability.FINE_TUNABLE}
        self._model = None
        self._tokenizer = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from unsloth import FastLanguageModel  # type: ignore
        except ImportError as e:
            raise ImportError(
                "duecare-llm-models[unsloth] is required for UnslothModel. "
                "Install with: pip install 'duecare-llm-models[unsloth]'"
            ) from e

        self._model, self._tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.model_id,
            max_seq_length=self.max_seq_length,
            load_in_4bit=self.load_in_4bit,
        )
        FastLanguageModel.for_inference(self._model)

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        self._load()
        assert self._tokenizer is not None and self._model is not None

        chat = [{"role": m.role, "content": m.content} for m in messages]
        prompt = self._tokenizer.apply_chat_template(
            chat, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        out = self._model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            pad_token_id=self._tokenizer.eos_token_id,
        )
        completion_ids = out[0][inputs["input_ids"].shape[1] :]
        text = self._tokenizer.decode(completion_ids, skip_special_tokens=True)

        return GenerationResult(
            text=text,
            finish_reason="stop",
            prompt_tokens=int(inputs["input_ids"].shape[1]),
            completion_tokens=int(completion_ids.shape[0]),
            tokens_used=int(inputs["input_ids"].shape[1] + completion_ids.shape[0]),
            model_id=self.id,
        )

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(
            model_id=self.id, healthy=self._model is not None
        )
