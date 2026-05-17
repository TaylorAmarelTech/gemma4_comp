from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from duecare.chat.app import create_app
from duecare.chat.harnesses import all_harnesses
from duecare.chat.harnesses.base import MODEL_CAPABILITIES, MODEL_TRANSPORTS
from duecare.chat.harnesses.model_interface import (
    UniversalModelResponse,
    call_model_backend,
    normalize_model_messages,
)


def test_every_registered_harness_declares_model_targets():
    valid_transports = set(MODEL_TRANSPORTS)
    valid_capabilities = set(MODEL_CAPABILITIES)

    for module in all_harnesses():
        spec = module.spec
        assert spec.model_targets, module.name
        assert any(target.default for target in spec.model_targets), module.name
        for target in spec.model_targets:
            assert target.transport in valid_transports, (module.name, target.transport)
            assert set(target.capabilities).issubset(valid_capabilities), (
                module.name,
                target.id,
                target.capabilities,
            )
            assert target.trust_boundary in {"local", "external", "configurable"}, (
                module.name,
                target.id,
                target.trust_boundary,
            )


def test_chat_harness_can_target_local_adapter_and_frontier_models():
    by_name = {module.name: module.spec for module in all_harnesses()}
    chat_targets = {target.id: target for target in by_name["chat"].model_targets}
    assert chat_targets["local_gemma4_runtime"].transport == "gemma4_runtime"
    assert chat_targets["local_gemma4_runtime"].required is True
    assert chat_targets["duecare_model_adapter"].transport == "duecare_model_adapter"
    assert chat_targets["frontier_chat_or_judge"].transport == "frontier_api"
    assert chat_targets["frontier_chat_or_judge"].trust_boundary == "external"


def test_deterministic_safety_and_utility_harnesses_keep_no_model_defaults():
    by_name = {module.name: module.spec for module in all_harnesses()}
    for name in ("anonymization", "search_safety", "search", "import_corpus"):
        defaults = [target for target in by_name[name].model_targets if target.default]
        assert defaults, name
        assert defaults[0].transport == "none", name


def test_harness_endpoint_serializes_model_targets():
    client = TestClient(create_app())
    data = client.get("/api/harnesses").json()
    assert "model_targets" in data["contract_fields"]
    by_name = {item["name"]: item for item in data["harnesses"]}
    assert by_name["chat"]["model_targets"][0]["transport"] == "gemma4_runtime"
    assert by_name["search"]["model_targets"][0]["transport"] == "none"


def test_normalize_model_messages_accepts_prompt_dict_and_list():
    assert normalize_model_messages("hello") == ({"role": "user", "content": "hello"},)
    assert normalize_model_messages({"role": "system", "content": "policy"}) == (
        {"role": "system", "content": "policy"},
    )
    assert normalize_model_messages([
        {"role": "user", "content": "question"},
        {"role": "assistant", "content": "answer"},
    ])[1]["role"] == "assistant"


def test_call_model_backend_supports_direct_callable():
    calls = []

    def backend(payload, **kwargs):
        calls.append((payload, kwargs))
        return "callable response"

    response = call_model_backend(
        backend,
        "prompt",
        max_new_tokens=33,
        temperature=0.7,
        top_p=0.95,
        top_k=64,
    )
    assert isinstance(response, UniversalModelResponse)
    assert response.text == "callable response"
    assert calls[0][0] == "prompt"
    assert calls[0][1]["max_new_tokens"] == 33
    assert calls[0][1]["top_p"] == 0.95
    assert calls[0][1]["top_k"] == 64


def test_call_model_backend_supports_duecare_generate_adapter_shape():
    class FakeAdapter:
        provider = "fake_provider"

        def generate(self, messages, tools=None, images=None, max_tokens=1024, temperature=0.0, **kwargs):
            assert messages[0].role == "user"
            assert max_tokens == 17
            assert temperature == 0.2
            return SimpleNamespace(
                text="generated response",
                model_id="fake-model",
                finish_reason="stop",
                latency_ms=12,
                prompt_tokens=3,
                completion_tokens=4,
                tokens_used=7,
                tool_calls=[],
            )

    response = call_model_backend(FakeAdapter(), "hello", max_tokens=17, temperature=0.2)
    assert response.text == "generated response"
    assert response.model_id == "fake-model"
    assert response.provider == "fake_provider"
    assert response.usage["tokens_used"] == 7
    assert response.latency_ms == 12


def test_call_model_backend_supports_chat_and_complete_shapes():
    class FakeChat:
        provider = "chat_provider"

        def chat(self, messages, **kwargs):
            assert messages[0]["role"] == "user"
            return {"choices": [{"message": {"content": "chat response"}}], "model": "chat-model"}

    class FakeComplete:
        provider = "complete_provider"

        def complete(self, prompt, **kwargs):
            assert "user: hello" in prompt
            return {"text": "complete response", "model": "complete-model"}

    chat_response = call_model_backend(FakeChat(), "hello")
    complete_response = call_model_backend(FakeComplete(), "hello")
    assert chat_response.text == "chat response"
    assert chat_response.model_id == "chat-model"
    assert complete_response.text == "complete response"
    assert complete_response.model_id == "complete-model"
