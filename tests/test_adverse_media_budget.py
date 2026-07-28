"""Offline budget-boundary tests for the optional adverse-media model caller."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import adverse_media as am
from scripts import provider_budget as pb


def test_adverse_media_uses_canonical_provider_budget_module() -> None:
    assert am.provider_budget is pb


@pytest.fixture(autouse=True)
def _reset_environment_ledger() -> None:
    pb.reset_environment_ledger_for_tests()
    yield
    pb.reset_environment_ledger_for_tests()


def _configure_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    attempts: int,
    allow_unknown_cost: bool,
) -> None:
    values = {
        "DUECARE_MODEL_BASE_URL": "https://private-model.example/v1",
        "DUECARE_MODEL_API_KEY": "private-test-key",
        "DUECARE_MODEL_NAME": "private-test-model",
        "DUECARE_ADVERSE_MEDIA_MAX_OUTPUT_TOKENS": "32",
        "DUECARE_PROVIDER_RUN_ID": f"adverse-test-{attempts}",
        "DUECARE_MAX_PLANNED_MODEL_CALLS": str(attempts),
        "DUECARE_MAX_INPUT_TOKENS": "10000",
        "DUECARE_MAX_OUTPUT_TOKENS": "10000",
        "DUECARE_MAX_PROVIDER_COST_USD": "0",
        "DUECARE_PROVIDER_BUDGET_FILE": str(tmp_path / "budget.sqlite3"),
        "DUECARE_PROVIDER_BUDGET_RECEIPT": str(tmp_path / "receipt.json"),
        "DUECARE_ALLOW_UNKNOWN_PROVIDER_COST": "1" if allow_unknown_cost else "0",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_zero_call_budget_denies_before_direct_transport(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_budget(monkeypatch, tmp_path, attempts=0, allow_unknown_cost=False)
    transport_calls = 0

    def forbidden_transport(*_args: object, **_kwargs: object) -> None:
        nonlocal transport_calls
        transport_calls += 1
        raise AssertionError("transport must not be reached")

    monkeypatch.setattr(am.urllib.request, "urlopen", forbidden_transport)
    model_fn = am._model_fn_from_env()
    assert model_fn is not None
    prompt = "private worker narrative"
    with pytest.raises(pb.BudgetExceededError, match="attempts"):
        model_fn(prompt)

    assert transport_calls == 0
    receipt = pb.environment_ledger().receipt()
    serialized = json.dumps(receipt)
    for private_value in (
        prompt,
        "private-test-key",
        "private-model.example",
        "private-test-model",
    ):
        assert private_value not in serialized
    assert receipt["totals"]["denied_attempts"] == 1


def test_unknown_pricing_blocks_direct_transport(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_budget(monkeypatch, tmp_path, attempts=1, allow_unknown_cost=False)
    monkeypatch.setattr(
        am.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("transport must not be reached"),
    )
    model_fn = am._model_fn_from_env()
    assert model_fn is not None
    with pytest.raises(pb.BudgetConfigurationError, match="pricing is unknown"):
        model_fn("bounded prompt")
    assert pb.environment_ledger().receipt()["totals"]["reserved_attempts"] == 0


def test_failed_attempt_keeps_reservation_and_retry_is_denied(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_budget(monkeypatch, tmp_path, attempts=1, allow_unknown_cost=True)
    transport_calls = 0

    def failed_transport(*_args: object, **_kwargs: object) -> None:
        nonlocal transport_calls
        transport_calls += 1
        raise TimeoutError("private raw transport detail")

    monkeypatch.setattr(am.urllib.request, "urlopen", failed_transport)
    model_fn = am._model_fn_from_env()
    assert model_fn is not None
    with pytest.raises(TimeoutError):
        model_fn("first prompt")
    with pytest.raises(pb.BudgetExceededError, match="attempts"):
        model_fn("retry prompt")

    assert transport_calls == 1
    receipt = pb.environment_ledger().receipt()
    assert receipt["totals"]["reserved_attempts"] == 1
    assert receipt["totals"]["failed_attempts"] == 1
    assert receipt["totals"]["denied_attempts"] == 1
    assert "private raw transport detail" not in json.dumps(receipt)


def test_successful_direct_call_is_capped_settled_and_sanitized(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_budget(monkeypatch, tmp_path, attempts=1, allow_unknown_cost=True)
    observed_body: dict[str, object] = {}

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            payload = {
                "choices": [{"message": {"content": "private response"}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            }
            return json.dumps(payload).encode("utf-8")

    def fake_transport(request: object, *, timeout: int) -> FakeResponse:
        assert timeout == 90
        observed_body.update(json.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(am.urllib.request, "urlopen", fake_transport)
    model_fn = am._model_fn_from_env()
    assert model_fn is not None
    assert model_fn("private success prompt") == "private response"
    assert observed_body["max_tokens"] == 32

    receipt = pb.environment_ledger().receipt()
    assert receipt["totals"]["succeeded_attempts"] == 1
    assert receipt["totals"]["actual_input_tokens"] == 7
    assert receipt["totals"]["actual_output_tokens"] == 3
    serialized = json.dumps(receipt)
    assert "private success prompt" not in serialized
    assert "private response" not in serialized
