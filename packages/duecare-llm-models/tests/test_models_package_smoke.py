"""Package-level tests for duecare-llm-models. Verifies all 8 adapters register,
the base helper works, and the OpenAI-compatible adapter handles errors
cleanly without network calls."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from duecare.core import Capability, Model
from duecare.models import model_registry, ModelAdapterBase


class TestAdapterRegistration:
    def test_all_8_adapters_register(self):
        expected = {
            "transformers",
            "llama_cpp",
            "unsloth",
            "ollama",
            "openai_compatible",
            "anthropic",
            "google_gemini",
            "hf_inference_endpoint",
        }
        assert set(model_registry.all_ids()) == expected
        assert len(model_registry) == 8

    def test_registry_kind(self):
        assert model_registry.kind == "model"


class TestTransformersAdapter:
    def test_constructs_without_loading(self):
        from duecare.models.transformers_adapter import TransformersModel
        m = TransformersModel("google/gemma-4-e4b-it")
        assert m.id == "transformers:google/gemma-4-e4b-it"
        assert m.provider == "transformers"
        assert Capability.TEXT in m.capabilities
        assert Capability.FINE_TUNABLE in m.capabilities

    def test_satisfies_model_protocol(self):
        from duecare.models.transformers_adapter import TransformersModel
        m = TransformersModel("google/gemma-4-e4b-it")
        assert isinstance(m, Model)

    def test_load_raises_without_transformers(self):
        from duecare.models.transformers_adapter import TransformersModel
        m = TransformersModel("google/gemma-4-e4b-it")
        # transformers isn't installed in the test env; should raise ImportError
        with pytest.raises(ImportError, match=r"duecare-llm-models\[transformers\]"):
            m._load()


class TestLlamaCppAdapter:
    def test_constructs_with_path(self):
        from duecare.models.llama_cpp_adapter import LlamaCppModel
        m = LlamaCppModel("/tmp/fake_model.gguf")
        assert "fake_model" in m.id
        assert m.provider == "llama_cpp"

    def test_satisfies_model_protocol(self):
        from duecare.models.llama_cpp_adapter import LlamaCppModel
        m = LlamaCppModel("/tmp/fake.gguf")
        assert isinstance(m, Model)

    def test_healthcheck_reports_missing_file(self, tmp_path):
        from duecare.models.llama_cpp_adapter import LlamaCppModel
        m = LlamaCppModel(tmp_path / "does_not_exist.gguf")
        health = m.healthcheck()
        assert not health.healthy


class TestOllamaAdapter:
    def test_constructs(self):
        from duecare.models.ollama_adapter import OllamaModel
        m = OllamaModel("llama3.1:8b")
        assert m.id == "ollama:llama3.1:8b"
        assert m.provider == "ollama"
        assert m.host == "http://localhost:11434"

    def test_satisfies_model_protocol(self):
        from duecare.models.ollama_adapter import OllamaModel
        assert isinstance(OllamaModel("x"), Model)

    def test_healthcheck_handles_no_server(self):
        from duecare.models.ollama_adapter import OllamaModel
        m = OllamaModel("x", host="http://localhost:11434")
        # No ollama server running in test env
        health = m.healthcheck()
        # Will be False since there's no server, but should not raise
        assert isinstance(health.healthy, bool)


class TestOpenAICompatibleAdapter:
    def test_constructs(self):
        from duecare.models.openai_compatible_adapter import OpenAICompatibleModel
        m = OpenAICompatibleModel(
            model_id="gpt-4o-mini",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
        )
        assert "gpt-4o-mini" in m.id
        assert m.provider == "openai_compatible"
        assert Capability.FUNCTION_CALLING in m.capabilities

    def test_satisfies_model_protocol(self):
        from duecare.models.openai_compatible_adapter import OpenAICompatibleModel
        m = OpenAICompatibleModel("gpt-4o-mini")
        assert isinstance(m, Model)

    def test_healthcheck_requires_api_key(self, monkeypatch):
        from duecare.models.openai_compatible_adapter import OpenAICompatibleModel
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        m = OpenAICompatibleModel("gpt-4o-mini")
        health = m.healthcheck()
        assert not health.healthy
        assert "error" in health.details

    def test_healthcheck_with_api_key(self, monkeypatch):
        from duecare.models.openai_compatible_adapter import OpenAICompatibleModel
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        m = OpenAICompatibleModel("gpt-4o-mini")
        health = m.healthcheck()
        assert health.healthy
        assert health.details["api_key_set"] is True

    def test_generate_mocked(self, monkeypatch):
        """Mock urllib to verify the adapter builds the right request body
        and parses responses correctly."""
        from duecare.core.schemas import ChatMessage, ToolSpec
        from duecare.models.openai_compatible_adapter import OpenAICompatibleModel
        import duecare.models.openai_compatible_adapter.adapter as adapter_mod

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        mock_response = {
            "choices": [{
                "message": {
                    "content": "Hello from mock",
                    "tool_calls": [{
                        "id": "call_1",
                        "function": {"name": "anonymize", "arguments": '{"text": "hi"}'},
                    }],
                },
                "finish_reason": "tool_calls",
            }],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            "model": "gpt-4o-mini-2024",
        }

        class FakeResp:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass
            def read(self):
                import json
                return json.dumps(mock_response).encode("utf-8")

        def fake_urlopen(req, timeout=None):
            return FakeResp()

        monkeypatch.setattr(adapter_mod.urllib.request, "urlopen", fake_urlopen)

        m = OpenAICompatibleModel("gpt-4o-mini")
        result = m.generate(
            [ChatMessage(role="user", content="hi")],
            tools=[ToolSpec(name="anonymize", description="Redact PII", parameters={})],
        )
        assert result.text == "Hello from mock"
        assert result.finish_reason == "tool_calls"
        assert result.prompt_tokens == 5
        assert result.completion_tokens == 3
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "anonymize"
        assert result.tool_calls[0].arguments == {"text": "hi"}


class TestAnthropicAdapter:
    def test_constructs(self):
        from duecare.models.anthropic_adapter import AnthropicModel
        m = AnthropicModel("claude-haiku-4-5-20251001")
        assert "anthropic" in m.id
        assert m.provider == "anthropic"
        assert Capability.VISION in m.capabilities
        assert Capability.LONG_CONTEXT in m.capabilities

    def test_satisfies_model_protocol(self):
        from duecare.models.anthropic_adapter import AnthropicModel
        assert isinstance(AnthropicModel("claude-haiku-4-5"), Model)


class TestGoogleGeminiAdapter:
    def test_constructs(self):
        from duecare.models.google_gemini_adapter import GoogleGeminiModel
        m = GoogleGeminiModel("gemini-2.0-flash")
        assert "gemini" in m.id
        assert m.provider == "google_gemini"
        assert Capability.AUDIO in m.capabilities


class TestHFInferenceEndpointAdapter:
    def test_constructs(self):
        from duecare.models.hf_inference_endpoint_adapter import HFInferenceEndpointModel
        m = HFInferenceEndpointModel(
            endpoint_url="https://example.hf.space",
            model_id="my-model",
        )
        assert m.endpoint_url == "https://example.hf.space"


class TestBase:
    def test_unsupported_raises_clean_error(self):
        from duecare.models.base import unsupported
        with pytest.raises(NotImplementedError, match="does not support 'embed'"):
            unsupported("embed", "openai_compatible")

    def test_base_tracks_latency_via_generate_wrapper(self, monkeypatch):
        from duecare.core.schemas import ChatMessage, GenerationResult
        from duecare.models.base import ModelAdapterBase

        class FakeAdapter(ModelAdapterBase):
            id = "fake"
            display_name = "Fake"
            provider = "fake"
            capabilities = {Capability.TEXT}
            context_length = 4096

            def _generate_impl(self, **kwargs):
                return GenerationResult(text="ok", model_id=self.id)

        a = FakeAdapter()
        result = a.generate([ChatMessage(role="user", content="hi")])
        assert result.text == "ok"
        assert result.latency_ms >= 0
        assert a._healthy is True
