"""llama.cpp adapter via llama-cpp-python.

Loads a GGUF file and runs inference on CPU or GPU. Primary runtime for
the fine-tuned Duecare model in the live demo.
"""

from __future__ import annotations

from pathlib import Path

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


@model_registry.register("llama_cpp")
class LlamaCppModel(ModelAdapterBase):
    """GGUF backend via llama-cpp-python. Lazy-imports the library."""

    provider = "llama_cpp"

    def __init__(
        self,
        model_path: Path | str,
        display_name: str | None = None,
        n_ctx: int = 4096,
        n_gpu_layers: int = 0,
        capabilities: set[Capability] | None = None,
    ) -> None:
        super().__init__()
        self.model_path = Path(model_path)
        self.id = f"llama_cpp:{self.model_path.stem}"
        self.display_name = display_name or self.model_path.stem
        self.context_length = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self.capabilities = capabilities or {Capability.TEXT, Capability.EMBEDDINGS}
        self._llm = None

    def _load(self) -> None:
        if self._llm is not None:
            return
        try:
            from llama_cpp import Llama  # type: ignore
        except ImportError as e:
            raise ImportError(
                "duecare-llm-models[llama-cpp] is required for LlamaCppModel. "
                "Install with: pip install 'duecare-llm-models[llama-cpp]'"
            ) from e

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"GGUF model file not found: {self.model_path}"
            )

        self._llm = Llama(
            model_path=str(self.model_path),
            n_ctx=self.context_length,
            n_gpu_layers=self.n_gpu_layers,
            verbose=False,
        )

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
        assert self._llm is not None

        chat = [{"role": m.role, "content": m.content} for m in messages]
        response = self._llm.create_chat_completion(
            messages=chat,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = response["choices"][0]
        usage = response.get("usage", {})

        return GenerationResult(
            text=choice["message"]["content"],
            finish_reason=choice.get("finish_reason", "stop"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            tokens_used=usage.get("total_tokens", 0),
            model_id=self.id,
            raw=response,
        )

    def embed(self, texts: list[str]) -> list[Embedding]:
        self._load()
        assert self._llm is not None
        results: list[Embedding] = []
        for text in texts:
            emb_data = self._llm.create_embedding(text)["data"][0]["embedding"]
            results.append(
                Embedding(
                    text=text,
                    vector=list(emb_data),
                    dimension=len(emb_data),
                    model_id=self.id,
                )
            )
        return results

    def healthcheck(self) -> ModelHealth:
        return ModelHealth(
            model_id=self.id,
            healthy=self.model_path.exists(),
            details={"path": str(self.model_path), "loaded": self._llm is not None},
        )
