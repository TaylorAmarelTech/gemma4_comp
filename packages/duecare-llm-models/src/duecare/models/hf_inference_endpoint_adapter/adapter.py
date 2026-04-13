"""HuggingFace Inference Endpoints adapter.

Calls any HF-hosted endpoint via stdlib urllib. Useful for arbitrary
community models without local download.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from duecare.core.enums import Capability
from duecare.core.schemas import (
    ChatMessage,
    GenerationResult,
    ModelHealth,
    ToolSpec,
)
from duecare.models import model_registry
from duecare.models.base import ModelAdapterBase


@model_registry.register("hf_inference_endpoint")
class HFInferenceEndpointModel(ModelAdapterBase):
    """HuggingFace Inference Endpoint adapter."""

    provider = "hf_inference_endpoint"

    def __init__(
        self,
        endpoint_url: str,
        model_id: str,
        api_key_env: str = "HUGGINGFACE_TOKEN",
        display_name: str | None = None,
        capabilities: set[Capability] | None = None,
        timeout: float = 120.0,
    ) -> None:
        super().__init__()
        self.model_id = model_id
        self.id = f"hf_endpoint:{model_id}"
        self.display_name = display_name or model_id
        self.endpoint_url = endpoint_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.context_length = 8192
        self.capabilities = capabilities or {Capability.TEXT}

    def _api_key(self) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(
                f"Environment variable {self.api_key_env!r} is not set."
            )
        return key

    def _generate_impl(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None,
        images: list[bytes] | None,
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> GenerationResult:
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        body = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature if temperature > 0 else 0.01,
                "return_full_text": False,
            },
        }
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key()}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                response = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_text = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"HTTP {e.code} from {self.endpoint_url}: {body_text[:500]}"
            ) from e

        # HF inference API returns a list of {"generated_text": "..."}
        if isinstance(response, list) and response:
            text = response[0].get("generated_text", "")
        else:
            text = response.get("generated_text", "") if isinstance(response, dict) else ""

        return GenerationResult(
            text=text,
            finish_reason="stop",
            model_id=self.id,
            raw={"response": response} if not isinstance(response, dict) else response,
        )

    def healthcheck(self) -> ModelHealth:
        try:
            _ = self._api_key()
            return ModelHealth(
                model_id=self.id, healthy=True,
                details={"endpoint_url": self.endpoint_url},
            )
        except RuntimeError as e:
            return ModelHealth(
                model_id=self.id, healthy=False, details={"error": str(e)}
            )
