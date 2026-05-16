"""Minimal Gemma 4 chat playground."""
from __future__ import annotations

from duecare.chat.app import create_app, run_server
from duecare.chat.classifier import create_classifier_app
from duecare.chat.portability import (
    REQUIRED_APP_ENDPOINTS,
    REQUIRED_CHAT_VERSION,
    REQUIRED_KO_TYPES,
    REQUIRED_SAMPLE_FILES,
    SELF_AUDIT_MINIMUM_COUNTS,
    model_variant_map,
    model_variant_ui_map,
    notebook_role_map,
    portability_contract_payload,
    reference_portability_contract_payload,
    sample_artifact_map,
    verify_app_contract,
)
from duecare.chat.experiment_contracts import (
    comparison_matrix_map,
    experiment_contract_payload,
    harness_profile_map,
    quantitative_run_profile_map,
    synthetic_generation_profile_map,
    training_profile_map,
    upload_limit_map,
)

__all__ = [
    "create_app",
    "run_server",
    "create_classifier_app",
    "REQUIRED_APP_ENDPOINTS",
    "REQUIRED_CHAT_VERSION",
    "REQUIRED_KO_TYPES",
    "REQUIRED_SAMPLE_FILES",
    "SELF_AUDIT_MINIMUM_COUNTS",
    "model_variant_map",
    "model_variant_ui_map",
    "notebook_role_map",
    "portability_contract_payload",
    "reference_portability_contract_payload",
    "sample_artifact_map",
    "verify_app_contract",
    "comparison_matrix_map",
    "experiment_contract_payload",
    "harness_profile_map",
    "quantitative_run_profile_map",
    "synthetic_generation_profile_map",
    "training_profile_map",
    "upload_limit_map",
]
