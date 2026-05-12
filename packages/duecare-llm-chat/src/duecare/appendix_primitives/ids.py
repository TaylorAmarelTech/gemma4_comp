"""Canonical RunID generator.

Format: ``{slot}_{purpose}_{variant}_{iso_ts}`` -- variant optional.
See docs/data_primitives.md section 1.6.
"""
from __future__ import annotations

import time


def make_run_id(
    slot: str,
    purpose: str,
    variant: str = "",
    iso_ts: str | None = None,
) -> str:
    """Generate a canonical RunID.

    Args:
        slot: 2-3 char kernel slug -- ``'a01'``, ``'a14'``, ``'03'``.
        purpose: short underscore-cased descriptor -- ``'stock'``,
            ``'harnessed'``, ``'compare'``, ``'ugc'``, ``'synth'``,
            ``'export'``.
        variant: optional model / adapter slug -- ``'e2b-it'``,
            ``'e4b-it'``, ``'safetyjudge-v1'``. Omit if not meaningful.
        iso_ts: override timestamp for deterministic testing.
            Otherwise current UTC.

    Returns:
        Underscore-joined RunID. Example:
        ``make_run_id('a01', 'stock', 'e2b-it')`` ->
        ``'a01_e2b-it_stock_2026-05-12T19-30-00Z'``.

    Raises:
        ValueError: when ``slot`` or ``purpose`` is empty.
    """
    if not slot:
        raise ValueError("slot must be non-empty")
    if not purpose:
        raise ValueError("purpose must be non-empty")
    ts = iso_ts or time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    parts: list[str] = [slot]
    if variant:
        parts.append(variant)
    parts.append(purpose)
    parts.append(ts)
    return "_".join(parts)
