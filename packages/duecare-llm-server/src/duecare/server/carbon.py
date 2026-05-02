"""Carbon-cost estimator for inference calls.

Estimates ``kg CO2eq`` per inference using:

  - **Energy per token** (Wh) — depends on model size + hardware
  - **Region grid intensity** (g CO2eq / kWh) — published by
    [Electricity Maps](https://app.electricitymaps.com/zone/) and
    archived in [`CARBON_INTENSITY_BY_REGION`].

This is an **estimate**, not a billing-grade carbon meter. It's
useful for:

- Per-tenant sustainability dashboards (Prometheus counter
  `duecare_inference_co2_kg_total{tenant, model, region}`)
- ESG reporting (annualized kg CO2eq per workforce)
- Model-selection guidance (the dashboard shows that switching
  E4B → E2B halves energy at minor quality cost)

For billing-grade accuracy, use the cloud provider's own carbon API
(GCP Carbon Footprint, AWS Customer Carbon Footprint, Azure
Sustainability Calculator).

Usage:

    from duecare.server import carbon, metering

    response = model.generate(...)
    cost_usd = metering.record(...)              # token + cost meter
    co2_kg = carbon.record(
        tenant=tenant_id,
        model=model_name,
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        region=os.environ.get("DUECARE_REGION", "us-east1"),
    )
"""
from __future__ import annotations

import os
from typing import Any

try:
    from prometheus_client import Counter
    from duecare.server.observability import _REGISTRY, _PROM_AVAILABLE
    if _PROM_AVAILABLE:
        _co2_counter: Any = Counter(
            "duecare_inference_co2_kg_total",
            "Estimated kg CO2eq per inference, by tenant + model + region.",
            ["tenant", "model", "region"],
            registry=_REGISTRY,
        )
    else:
        _co2_counter = None
except Exception:                                # pragma: no cover
    _co2_counter = None


# Energy per 1k tokens, in Wh (watt-hours). Derived from public
# benchmarks for inference power draw at typical batch sizes; treat
# as ±50% accurate. Sources: HuggingFace optimum + Stanford HAI 2024
# AI Index estimates.
ENERGY_WH_PER_1K_TOKENS: dict[str, float] = {
    # Local / Ollama (CPU + iGPU + small NPU)
    "gemma3:1b":           0.05,
    "gemma4:e2b":          0.10,
    "gemma4:e4b":          0.20,
    "gemma2:2b":           0.10,
    "gemma2:9b":           0.40,
    # Hosted endpoints — published energy-per-token estimates
    "gemini-2.5-flash":    0.08,
    "gemini-2.5-pro":      0.30,
    "claude-sonnet-4":     0.40,
    "claude-opus-4":       1.20,
    "gpt-4o":              0.40,
    "gpt-4o-mini":         0.10,
    "_default":            0.20,
}


# Average grid carbon intensity, g CO2eq / kWh. Source:
# Electricity Maps daily averages for 2024-2025. Update annually.
CARBON_INTENSITY_BY_REGION: dict[str, float] = {
    # Cloud regions — GCP / AWS / Azure region codes
    "us-east1":             390.0,    # GCP / AWS Virginia
    "us-east-1":            390.0,
    "us-west-2":            155.0,    # AWS Oregon — heavy hydro
    "us-central1":          410.0,    # GCP Iowa
    "europe-west1":         165.0,    # GCP Belgium
    "europe-west2":         210.0,    # GCP London
    "europe-west3":         330.0,    # GCP Frankfurt
    "europe-west4":         320.0,    # GCP Netherlands
    "asia-southeast1":      450.0,    # GCP Singapore
    "asia-east1":           650.0,    # GCP Taiwan
    "asia-northeast1":      490.0,    # GCP Tokyo
    "ap-south-1":           700.0,    # AWS Mumbai
    "asia-south1":          700.0,    # GCP Mumbai
    # Common ISO country codes (Electricity Maps zone)
    "US":                   390.0,
    "DE":                   330.0,
    "FR":                    65.0,    # nuclear-heavy
    "NO":                    25.0,    # hydro-heavy
    "SE":                    30.0,
    "GB":                   210.0,
    "IN":                   700.0,
    "CN":                   650.0,
    "JP":                   490.0,
    "BR":                   100.0,
    "AU":                   500.0,
    "ZA":                   850.0,
    "_default":             450.0,    # global average
}


def estimate_co2_kg(
    model: str,
    tokens_in: int,
    tokens_out: int,
    region: str = "_default",
) -> float:
    """Estimate kg CO2eq for one inference call. Returns 0.0 for
    unknown models when no _default is set."""
    energy_per_1k = (
        ENERGY_WH_PER_1K_TOKENS.get(model)
        or ENERGY_WH_PER_1K_TOKENS.get("_default")
        or 0.0
    )
    intensity_g_per_kwh = (
        CARBON_INTENSITY_BY_REGION.get(region)
        or CARBON_INTENSITY_BY_REGION.get("_default")
        or 0.0
    )
    total_tokens_k = (tokens_in + tokens_out) / 1000.0
    energy_wh = total_tokens_k * energy_per_1k
    energy_kwh = energy_wh / 1000.0
    co2_g = energy_kwh * intensity_g_per_kwh
    return round(co2_g / 1000.0, 9)               # convert g → kg


def record(
    *,
    tenant: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    region: str | None = None,
) -> float:
    """Estimate + record kg CO2eq for one inference call. Returns
    the estimate (also exposed as the
    ``duecare_inference_co2_kg_total`` Prometheus counter)."""
    region = region or os.environ.get("DUECARE_REGION", "_default")
    kg = estimate_co2_kg(model, tokens_in, tokens_out, region)
    if _co2_counter is not None and kg > 0.0:
        _co2_counter.labels(
            tenant=tenant, model=model, region=region,
        ).inc(kg)
    return kg


def reference_table() -> dict[str, Any]:
    """Return the lookup tables for /admin or display. Useful for
    populating a Sustainability page in a dashboard."""
    return {
        "energy_wh_per_1k_tokens": dict(ENERGY_WH_PER_1K_TOKENS),
        "carbon_intensity_g_per_kwh_by_region": dict(CARBON_INTENSITY_BY_REGION),
    }
