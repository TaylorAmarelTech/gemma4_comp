"""HuggingFace Transformers adapter.

Loads any HF-hosted causal LM with optional 4-bit quantization via
bitsandbytes. Widest model coverage of any adapter.

The `transformers` / `torch` / `bitsandbytes` dependencies are imported
lazily so that `duecare-llm-models` can be installed without pulling in
the full ML stack. If you try to call `generate()` without the extras
installed, you get a clean ImportError with install instructions.
"""

from __future__ import annotations

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    Embedding,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("transformers")
class TransformersModel(ModelAdapterBase):
    """HuggingFace Transformers adapter. Lazy-imports torch + transformers."""

    provider = "transformers"

    def __init__(
        self,
        model_id: str,
        display_name: str | None = None,
        load_in_4bit: bool = True,
        device: str = "auto",
        capabilities: set[Capability] | None = None,
        context_length: int = 8192,
    ) -> None:
        super().__init__()
        self.model_id = model_id
        self.id = f"transformers:{model_id}"
        self.display_name = display_name or model_id
        self.load_in_4bit = load_in_4bit
        self.device = device
        self.capabilities = capabilities or {Capability.TEXT, Capability.FINE_TUNABLE}
        self.context_length = context_length
        self._model = None
        self._tokenizer = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch  # noqa: F401
            from transformers import (  # type: ignore
                AutoModelForCausalLM,
                AutoTokenizer,
            )
        except ImportError as e:
            raise ImportError(
                "duecare-llm-models[transformers] is required for TransformersModel. "
                "Install with: pip install 'duecare-llm-models[transformers]'"
            ) from e

        kwargs: dict = {"device_map": self.device}
        if self.load_in_4bit:
            try:
                from transformers import BitsAndBytesConfig  # type: ignore
                kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype="bfloat16",
                    bnb_4bit_quant_type="nf4",
                )
            except ImportError:
                # bitsandbytes not installed - fall back to fp16
                pass

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_id, **kwargs)

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

        # Build chat prompt via the tokenizer's chat template
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
            model_version="",
        )

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(
            model_id=self.id,
            healthy=self._model is not None,
            details={"loaded": self._model is not None},
        )
