"""Offline tests for the fail-closed shared provider budget ledger."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from scripts import provider_budget as pb


def _ledger(
    tmp_path: Path,
    *,
    run_id: str = "test-run",
    policy: pb.BudgetPolicy | None = None,
    pricing_path: Path | None = None,
) -> pb.ProviderBudgetLedger:
    return pb.ProviderBudgetLedger(
        tmp_path / "ledger.sqlite3",
        run_id=run_id,
        policy=policy
        or pb.BudgetPolicy(
            max_attempts=10,
            max_input_tokens=10_000,
            max_output_tokens=10_000,
            max_cost_microusd=1_000_000,
            allow_unknown_cost=True,
        ),
        pricing_path=pricing_path,
        receipt_path=tmp_path / "receipt.json",
    )


def _pricing_file(tmp_path: Path) -> Path:
    path = tmp_path / "pricing.json"
    path.write_text(
        json.dumps(
            {
                "schema": "duecare.provider-pricing.v1",
                "as_of": "2026-07-27",
                "prices": [
                    {
                        "provider": "example",
                        "model": "*",
                        "input_usd_per_million_tokens": "1.0",
                        "output_usd_per_million_tokens": "2.0",
                    },
                    {
                        "provider": "example",
                        "model": "exact-model",
                        "input_usd_per_million_tokens": "3.0",
                        "output_usd_per_million_tokens": "4.0",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_environment_is_disabled_without_budget_settings(tmp_path: Path) -> None:
    ledger = pb.ProviderBudgetLedger.from_environment(root=tmp_path, source={})
    assert isinstance(ledger, pb.DisabledProviderBudget)
    assert ledger.receipt()["enabled"] is False


def test_zero_call_budget_denies_before_reservation(tmp_path: Path) -> None:
    ledger = pb.ProviderBudgetLedger.from_environment(
        root=tmp_path,
        source={
            "DUECARE_MAX_PLANNED_MODEL_CALLS": "0",
            "DUECARE_PROVIDER_BUDGET_FILE": "budget.sqlite3",
            "DUECARE_PROVIDER_BUDGET_RECEIPT": "receipt.json",
        },
    )
    with pytest.raises(pb.BudgetExceededError, match="attempts"):
        ledger.attempt(
            provider="example",
            model="model",
            prompt="prompt",
            system=None,
            max_output_tokens=8,
        )
    totals = ledger.receipt()["totals"]
    assert totals["reserved_attempts"] == 0
    assert totals["denied_attempts"] == 1


def test_positive_call_budget_requires_explicit_finite_caps(tmp_path: Path) -> None:
    with pytest.raises(pb.BudgetConfigurationError, match="explicit finite"):
        pb.ProviderBudgetLedger.from_environment(
            root=tmp_path,
            source={
                "DUECARE_MAX_PLANNED_MODEL_CALLS": "1",
                "DUECARE_PROVIDER_RUN_ID": "incomplete-run",
            },
        )


def test_non_finite_cash_budget_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(pb.BudgetConfigurationError, match="must be finite"):
        pb.ProviderBudgetLedger.from_environment(
            root=tmp_path,
            source={
                "DUECARE_MAX_PLANNED_MODEL_CALLS": "1",
                "DUECARE_MAX_INPUT_TOKENS": "10",
                "DUECARE_MAX_OUTPUT_TOKENS": "10",
                "DUECARE_MAX_PROVIDER_COST_USD": "NaN",
                "DUECARE_PROVIDER_RUN_ID": "non-finite-run",
            },
        )


def test_atomic_attempt_reservations_hold_under_threads(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path,
        policy=pb.BudgetPolicy(5, 10_000, 10_000, 1_000_000, True),
    )

    def reserve(index: int) -> str:
        try:
            with ledger.attempt(
                provider="example",
                model="model",
                prompt=f"prompt-{index}",
                system=None,
                max_output_tokens=10,
            ) as attempt:
                attempt.settle(
                    response={"usage": {"prompt_tokens": 2, "completion_tokens": 3}},
                    output_text="ok",
                )
            return "reserved"
        except pb.BudgetExceededError:
            return "denied"

    with ThreadPoolExecutor(max_workers=12) as executor:
        outcomes = list(executor.map(reserve, range(20)))

    assert outcomes.count("reserved") == 5
    assert outcomes.count("denied") == 15
    totals = ledger.receipt()["totals"]
    assert totals["reserved_attempts"] == 5
    assert totals["succeeded_attempts"] == 5
    assert totals["denied_attempts"] == 15


def test_exact_usage_cost_and_sanitized_receipt(tmp_path: Path) -> None:
    pricing = _pricing_file(tmp_path)
    ledger = _ledger(tmp_path, pricing_path=pricing)
    prompt = "private worker narrative must not enter receipt"
    model = "exact-model"
    with ledger.attempt(
        provider="example",
        model=model,
        prompt=prompt,
        system="private system text",
        max_output_tokens=20,
    ) as attempt:
        attempt.settle(
            response={"usage": {"input_tokens": 5, "output_tokens": 7}},
            output_text="private response text",
        )

    receipt = ledger.receipt()
    totals = receipt["totals"]
    assert totals["actual_input_tokens"] == 5
    assert totals["actual_output_tokens"] == 7
    assert totals["actual_cost_microusd"] == 43
    serialized = json.dumps(receipt)
    assert prompt not in serialized
    assert model not in serialized
    assert "private system text" not in serialized
    assert "private response text" not in serialized
    assert receipt["privacy"]["model_ids_are_hashed"] is True


def test_failed_attempt_keeps_its_reservation(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    with (
        pytest.raises(TimeoutError),
        ledger.attempt(
            provider="example",
            model="model",
            prompt="prompt",
            system=None,
            max_output_tokens=50,
        ),
    ):
        raise TimeoutError("raw error text is never stored")
    receipt = ledger.receipt()
    assert receipt["totals"]["reserved_attempts"] == 1
    assert receipt["totals"]["reserved_output_tokens"] == 50
    assert receipt["totals"]["failed_attempts"] == 1
    assert receipt["recent_attempts"][0]["outcome_class"] == "transport"
    assert "raw error text" not in json.dumps(receipt)


def test_unknown_pricing_blocks_without_recorded_override(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path,
        policy=pb.BudgetPolicy(1, 100, 100, 100, False),
    )
    with pytest.raises(pb.BudgetConfigurationError, match="pricing is unknown"):
        ledger.attempt(
            provider="example",
            model="model",
            prompt="prompt",
            system=None,
            max_output_tokens=10,
        )
    assert ledger.receipt()["totals"]["reserved_attempts"] == 0


def test_explicit_zero_input_estimate_is_rejected(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path)
    with pytest.raises(pb.BudgetConfigurationError, match="estimated input tokens"):
        ledger.attempt(
            provider="example",
            model="model",
            prompt="prompt",
            system=None,
            max_output_tokens=10,
            estimated_input_tokens=0,
        )


def test_cash_cap_is_checked_against_conservative_reservation(tmp_path: Path) -> None:
    ledger = _ledger(
        tmp_path,
        pricing_path=_pricing_file(tmp_path),
        policy=pb.BudgetPolicy(1, 100, 100, 1, False),
    )
    with pytest.raises(pb.BudgetExceededError, match="cost"):
        ledger.attempt(
            provider="example",
            model="exact-model",
            prompt="prompt",
            system=None,
            max_output_tokens=10,
            estimated_input_tokens=5,
        )
    assert ledger.receipt()["totals"]["last_denial_category"] == "cost"


def test_run_policy_is_frozen_by_run_id(tmp_path: Path) -> None:
    _ledger(tmp_path, policy=pb.BudgetPolicy(1, 100, 100, 100, True))
    with pytest.raises(pb.BudgetConfigurationError, match="different frozen policy"):
        _ledger(tmp_path, policy=pb.BudgetPolicy(2, 100, 100, 100, True))


def test_exact_pricing_wins_over_provider_wildcard(tmp_path: Path) -> None:
    path = _pricing_file(tmp_path)
    exact = pb.load_pricing(path, "example", "exact-model")
    wildcard = pb.load_pricing(path, "example", "other-model")
    assert exact is not None and str(exact.input_usd_per_million) == "3.0"
    assert wildcard is not None and str(wildcard.input_usd_per_million) == "1.0"


def test_ollama_native_usage_shape_is_normalized() -> None:
    assert pb.usage_from_response(
        {"prompt_eval_count": 11, "eval_count": 13},
        reserved_input_tokens=99,
        output_text="ignored",
    ) == (11, 13, "provider")
