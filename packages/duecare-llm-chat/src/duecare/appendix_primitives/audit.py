"""validate_canonical(bundle_dict) -> list of drift findings.

Drop-in audit any kernel can call at emit time::

    findings = validate_canonical(payload)
    if findings:
        print('DRIFT:', findings)

See docs/data_primitives.md section 3 (drift table) for the rules.
"""
from __future__ import annotations

from typing import Any

from duecare.appendix_primitives.envelopes import BundleEnvelope

LEGACY_RESULTS_KEYS: tuple[str, ...] = ("ingested", "proposals", "packs_built")


def validate_canonical(bundle: dict[str, Any]) -> list[str]:
    """Return drift findings for a bundle dict. Empty list = canonical.

    Findings are short strings; the caller decides whether to print,
    raise, or accumulate into a CI report. The check is permissive
    about extras (BundleEnvelope uses extra='allow') and about
    rollover state (both canonical + legacy alias present is OK).
    """
    findings: list[str] = []
    sv = bundle.get("schema_version")
    if sv != "1.0":
        findings.append(
            f"schema_version drift: {sv!r} (expected '1.0')"
        )
    if "summary" not in bundle and "aggregate" in bundle:
        findings.append(
            "uses 'aggregate' instead of canonical 'summary'"
        )
    if "results" not in bundle:
        for alt in LEGACY_RESULTS_KEYS:
            if alt in bundle:
                findings.append(
                    f"uses '{alt}[]' instead of canonical 'results[]'"
                )
    try:
        BundleEnvelope.model_validate(bundle)
    except Exception as exc:
        findings.append(
            "BundleEnvelope.model_validate failed: "
            f"{type(exc).__name__}: {str(exc)[:200]}"
        )
    return findings
