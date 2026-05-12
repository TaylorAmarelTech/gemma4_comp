"""DueCare v1.0 BundleEnvelope primitives.

Canonical data shapes shared across all DueCare appendix kernels.
Importing kernels: A-01 .. A-20 + main notebook 03.
See docs/data_primitives.md for the contract.
"""
from __future__ import annotations

from duecare.appendix_primitives.audit import validate_canonical
from duecare.appendix_primitives.envelopes import (
    BundleEnvelope,
    HarnessGrep,
    HarnessOnline,
    HarnessPersona,
    HarnessRag,
    HarnessTools,
    HarnessTrace,
    PerRow,
)
from duecare.appendix_primitives.ids import make_run_id
from duecare.appendix_primitives.io import read_v1_bundle, write_v1_bundle

__all__ = [
    "BundleEnvelope",
    "HarnessGrep",
    "HarnessOnline",
    "HarnessPersona",
    "HarnessRag",
    "HarnessTools",
    "HarnessTrace",
    "PerRow",
    "make_run_id",
    "read_v1_bundle",
    "validate_canonical",
    "write_v1_bundle",
]
