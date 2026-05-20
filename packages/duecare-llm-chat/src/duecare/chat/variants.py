"""Gemma 4 variant registry.

Single source of truth for the model variants the kernel exposes via
the picker. Replaces four independently-maintained kernel-side dicts
(_VARIANT_HF_ID / _VARIANT_INFO / _VARIANT_FOOTPRINT_GB /
_UNSLOTH_ALIASES) that drifted out of sync whenever someone added a
new variant to one dict but forgot the others.

Each variant is a frozen ``VariantSpec``. The registry is immutable;
callers that need a UI-shaped dict (legacy ``_VARIANT_INFO`` shape)
call :func:`to_ui_map` which is recomputed from the registry.

Wiring:

    from duecare.chat.variants import (
        VARIANT_REGISTRY, VariantSpec, get_variant, list_variant_ids,
        is_cloud_variant, footprint_gb, hf_id, unsloth_alias,
        to_ui_map,
    )

The kernel imports these functions instead of carrying four parallel
dicts. The function names match the previous inline helpers so the
call sites change minimally.

Adding a new variant: append one ``VariantSpec`` to BUILTIN_VARIANTS
below. Every consumer (preflight, picker, purge, UI) picks it up
automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class VariantSpec:
    """One Gemma 4 variant the kernel knows how to load.

    All fields are required at construction so we cannot register a
    half-defined variant. Optional behaviour (unsloth alias for the
    fallback cache purge, cloud route credentials) is expressed as
    explicit fields with sentinel empty-string defaults.
    """

    id: str                  # stable picker key, e.g. "31b-it"
    display: str             # human label, e.g. "Gemma 4 31B-it"
    hf_id: str               # canonical HF repo or "" for cloud variants
    size_gb: float           # rough resident size for the picker UI
    fits: str                # "single T4" / "T4 ×2 (4-bit)" / "no GPU"
    category: str            # "on-device" / "cloud" / "jailbroken"
    load_eta: str            # picker hint, e.g. "~30-60 sec"
    disk_gb: float           # preflight disk-need estimate
    gpu_gb: float            # preflight GPU-need estimate
    unsloth_alias: str = ""  # fallback HF id used when google/* is gated

    @property
    def is_cloud(self) -> bool:
        return self.category == "cloud" or self.id.startswith("cloud-")

    def ui_dict(self) -> dict[str, Any]:
        """Legacy ``_VARIANT_INFO`` shape used by older UI code paths."""
        return {
            "display": self.display,
            "size_gb": self.size_gb,
            "fits": self.fits,
            "category": self.category,
            "load_eta": self.load_eta,
        }


# ---------------------------------------------------------------------------
# Built-in registry. The kernel may override the UI portion at runtime
# via :func:`duecare.chat.portability.model_variant_ui_map`; the
# footprint / disk / gpu / unsloth_alias fields here remain
# authoritative for preflight + purge.
#
# Disk + GPU numbers were lowered on 2026-05-19 to match the quantised
# shards Unsloth actually downloads on Kaggle, after the preflight gate
# was rejecting 31b-it on fresh sessions despite the 18 GB shard fitting.
# ---------------------------------------------------------------------------


BUILTIN_VARIANTS: tuple[VariantSpec, ...] = (
    VariantSpec(
        id="e2b-it",
        display="Gemma 4 E2B-it",
        hf_id="google/gemma-4-2b-it",
        size_gb=2.0,
        fits="single T4",
        category="on-device",
        load_eta="~20–30 sec",
        disk_gb=4.0,
        gpu_gb=3.0,
        unsloth_alias="unsloth/gemma-4-E2B-it",
    ),
    VariantSpec(
        id="e4b-it",
        display="Gemma 4 E4B-it",
        hf_id="google/gemma-4-4b-it",
        size_gb=4.0,
        fits="single T4",
        category="on-device",
        load_eta="~30–60 sec",
        disk_gb=8.0,
        gpu_gb=5.0,
        unsloth_alias="unsloth/gemma-4-E4B-it",
    ),
    VariantSpec(
        id="26b-a4b-it",
        display="Gemma 4 26B-A4B-it",
        hf_id="google/gemma-4-26b-a4b-it",
        size_gb=14.0,
        fits="T4 ×2 (4-bit)",
        category="on-device",
        load_eta="~6–15 min first run · ~3–5 min cached",
        disk_gb=16.0,
        gpu_gb=14.0,
        unsloth_alias="unsloth/gemma-4-26B-A4B-it",
    ),
    VariantSpec(
        id="31b-it",
        display="Gemma 4 31B-it",
        hf_id="google/gemma-4-31b-it",
        size_gb=18.0,
        fits="T4 ×2 (4-bit)",
        category="on-device",
        load_eta="~15–25 min first run (HF download) · ~5–8 min cached",
        disk_gb=18.0,
        gpu_gb=16.0,
        unsloth_alias="unsloth/gemma-4-31B-it",
    ),
    VariantSpec(
        id="jailbroken-31b",
        display="Gemma 4 31B (abliterated)",
        hf_id="dealignai/Gemma-4-31B-JANG_4M-CRACK",
        size_gb=18.0,
        fits="T4 ×2 (4-bit)",
        category="jailbroken",
        load_eta="~15–25 min first run · repo quirks possible",
        disk_gb=18.0,
        gpu_gb=16.0,
    ),
    VariantSpec(
        id="jailbroken-e4b",
        display="Gemma 4 E4B (abliterated)",
        hf_id="mlabonne/Gemma-4-E4B-it-abliterated",
        size_gb=4.0,
        fits="single T4",
        category="jailbroken",
        load_eta="~30–60 sec",
        disk_gb=8.0,
        gpu_gb=5.0,
    ),
    VariantSpec(
        id="cloud-gemini",
        display="Gemini API (cloud)",
        hf_id="",
        size_gb=0.0,
        fits="no GPU",
        category="cloud",
        load_eta="instant",
        disk_gb=0.0,
        gpu_gb=0.0,
    ),
    VariantSpec(
        id="cloud-openai",
        display="OpenAI-compat (cloud)",
        hf_id="",
        size_gb=0.0,
        fits="no GPU",
        category="cloud",
        load_eta="instant",
        disk_gb=0.0,
        gpu_gb=0.0,
    ),
    VariantSpec(
        id="cloud-ollama",
        display="Ollama (cloud/local)",
        hf_id="",
        size_gb=0.0,
        fits="no GPU",
        category="cloud",
        load_eta="instant",
        disk_gb=0.0,
        gpu_gb=0.0,
    ),
)


# Frozen dict-by-id for O(1) lookups. The tuple above is the source of
# truth for ORDER (picker presentation) and the dict is derived.
VARIANT_REGISTRY: dict[str, VariantSpec] = {v.id: v for v in BUILTIN_VARIANTS}


# ---------------------------------------------------------------------------
# Helpers used by the kernel script (and tests). These intentionally
# match the names of the inline helpers they replace so the call-site
# diff stays minimal.
# ---------------------------------------------------------------------------


def get_variant(variant_id: str) -> Optional[VariantSpec]:
    """Return the spec for a variant id, or None if unknown."""
    return VARIANT_REGISTRY.get(variant_id)


def list_variant_ids() -> list[str]:
    """Sorted list of all known variant ids. The kernel uses this for
    error responses when a caller submits an unknown variant."""
    return sorted(VARIANT_REGISTRY.keys())


def is_cloud_variant(variant_id: str) -> bool:
    """True when the variant is a cloud route (cloud-gemini, etc.)."""
    spec = VARIANT_REGISTRY.get(variant_id)
    if spec is not None:
        return spec.is_cloud
    return variant_id.startswith("cloud-")


def footprint_gb(variant_id: str) -> dict[str, float]:
    """Return ``{"disk": float, "gpu": float}`` for the preflight gate.

    Unknown variants fall back to a conservative worst-case (31B-scale)
    so the preflight is loud rather than silently optimistic.
    """
    spec = VARIANT_REGISTRY.get(variant_id)
    if spec is None:
        return {"disk": 30.0, "gpu": 20.0}
    return {"disk": spec.disk_gb, "gpu": spec.gpu_gb}


def hf_id(variant_id: str) -> Optional[str]:
    """Canonical google/* HF repo id for a variant, or None when the
    variant is cloud-only (cloud-gemini etc.) where there is nothing
    to download."""
    spec = VARIANT_REGISTRY.get(variant_id)
    if spec is None or not spec.hf_id:
        return None
    return spec.hf_id


def unsloth_alias(variant_id: str) -> Optional[str]:
    """Fallback Unsloth HF id used when the canonical google/* repo is
    gated. Used by the cache purge so both possible cache dirs get
    cleaned. Returns None when the variant has no Unsloth fallback."""
    spec = VARIANT_REGISTRY.get(variant_id)
    if spec is None or not spec.unsloth_alias:
        return None
    return spec.unsloth_alias


def to_ui_map() -> dict[str, dict[str, Any]]:
    """Legacy ``_VARIANT_INFO`` shape (display / size_gb / fits /
    category / load_eta) used by the picker UI. Recomputed from the
    registry each call so an upstream override cannot drift."""
    return {vid: spec.ui_dict() for vid, spec in VARIANT_REGISTRY.items()}


__all__ = [
    "BUILTIN_VARIANTS",
    "VARIANT_REGISTRY",
    "VariantSpec",
    "footprint_gb",
    "get_variant",
    "hf_id",
    "is_cloud_variant",
    "list_variant_ids",
    "to_ui_map",
    "unsloth_alias",
]
