"""Per-tenant token + cost meter.

Tracks total input / output tokens per (tenant, model) tuple in
Prometheus counters and emits an estimated USD cost using a static
``MODEL_COST_PER_1K_TOKENS`` lookup. The cost numbers are *estimates*
suitable for internal chargeback dashboards; for billing-grade
accuracy the operator should use the model provider's own usage API.

Wire the counters via [`record`][duecare.server.metering.record] from
inside route handlers after a model call returns:

    from duecare.server import metering
    usage = response.usage
    metering.record(
        tenant=request.state.tenant_id,
        model=cfg.model_name,
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
    )

The model-cost table is overridable by writing
``DUECARE_MODEL_COSTS_FILE=/path/to/costs.json`` — useful for keeping
chargeback rates in sync with a procurement contract without a
container rebuild.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from duecare.server import observability as obs


# Default cost-per-1k-tokens table (mid-2026 published rates, in USD).
# input + output costs together; for asymmetric pricing override via
# DUECARE_MODEL_COSTS_FILE. Override file shape: same dict shape as below.
DEFAULT_MODEL_COSTS_PER_1K: dict[str, dict[str, float]] = {
    # Local-Ollama Gemma 4 — operator hardware cost only; bill at
    # cost recovery rather than market rate
    "gemma4:e2b":          {"in": 0.0,    "out": 0.0},
    "gemma4:e4b":          {"in": 0.0,    "out": 0.0},
    "gemma3:1b":           {"in": 0.0,    "out": 0.0},
    "gemma2:2b":           {"in": 0.0,    "out": 0.0},
    # Hosted endpoints — published rates (USD per 1k tokens)
    "gemini-2.5-pro":      {"in": 0.00125, "out": 0.005},
    "gemini-2.5-flash":    {"in": 0.000075, "out": 0.0003},
    "claude-sonnet-4":     {"in": 0.003,  "out": 0.015},
    "claude-opus-4":       {"in": 0.015,  "out": 0.075},
    "gpt-4o":              {"in": 0.0025, "out": 0.01},
    "gpt-4o-mini":         {"in": 0.00015, "out": 0.0006},
    # Fallback for unknown models — per-1k input + output equal
    "_default":            {"in": 0.0005, "out": 0.0015},
}


def _load_costs() -> dict[str, dict[str, float]]:
    """Read the cost table from the env-var-pointed file if set,
    otherwise return the bundled defaults."""
    override = os.environ.get("DUECARE_MODEL_COSTS_FILE", "").strip()
    if not override:
        return DEFAULT_MODEL_COSTS_PER_1K
    try:
        text = Path(override).read_text(encoding="utf-8")
        loaded = json.loads(text)
        if isinstance(loaded, dict):
            # Merge with defaults so missing models still resolve
            merged = dict(DEFAULT_MODEL_COSTS_PER_1K)
            merged.update(loaded)
            return merged
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return DEFAULT_MODEL_COSTS_PER_1K


_COSTS: dict[str, dict[str, float]] = _load_costs()


def estimate_cost_usd(
    model: str,
    tokens_in: int,
    tokens_out: int,
) -> float:
    """Estimate USD cost of a single inference call. Returns 0.0
    for unrecognized models when no _default is set."""
    rates = _COSTS.get(model) or _COSTS.get("_default") or {"in": 0.0, "out": 0.0}
    cost_in = (tokens_in / 1000.0) * rates.get("in", 0.0)
    cost_out = (tokens_out / 1000.0) * rates.get("out", 0.0)
    return round(cost_in + cost_out, 6)


def record(
    *,
    tenant: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
) -> float:
    """Increment per-tenant counters and return the estimated USD cost.

    Safe to call with zero tokens (no-ops the counter, returns 0.0).
    """
    if tokens_in > 0:
        obs.model_tokens_in_total.labels(
            tenant=tenant, model=model,
        ).inc(tokens_in)
    if tokens_out > 0:
        obs.model_tokens_out_total.labels(
            tenant=tenant, model=model,
        ).inc(tokens_out)
    return estimate_cost_usd(model, tokens_in, tokens_out)


def set_tenant_budget(tenant: str, daily_token_budget: int) -> None:
    """Configure / update a tenant's daily output-token budget.

    The Prometheus alert `DuecareTokenBudgetExhausted` fires when
    `sum(increase(duecare_model_tokens_out_total[24h])) by (tenant)`
    exceeds 80% of the gauge value set here.

    Operators typically call this at server startup from a config
    file (`/etc/duecare/tenants.yaml`) or after a control-plane API
    call. The current package does not include the control plane.
    """
    obs.tenant_token_budget_daily.labels(tenant=tenant).set(daily_token_budget)
