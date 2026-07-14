"""Shared quantitative experiment contracts for DueCare notebooks.

These constants keep comparison, synthetic-data, and fine-tune smoke paths
portable across Kernel 01, the active A-00 fine-tuning workbench, and the
live-demo notebook. Archived A-07 material is provenance, not an active path. Notebook
code may still provide bootstrapping fallbacks before the wheel is installed,
but successful runs should read these contracts rather than restating magic
numbers inline.
"""
from __future__ import annotations

from typing import Any

from duecare.chat.training_contract import PREFERENCE_REQUIRED_FIELDS, SFT_REQUIRED_FIELDS


BENCHMARK_RESPONSE_MAX_NEW_TOKENS = 1200

GENERATION_DEFAULTS: dict[str, Any] = {
    "temperature": 0.2,
    "top_p": 0.95,
    "top_k": 64,
    "max_new_tokens": BENCHMARK_RESPONSE_MAX_NEW_TOKENS,
    "evaluate": True,
    "llm_judge": False,
}

HARNESS_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "id": "none",
        "label": "No harness",
        "layers": [],
        "description": "Plain model call. Use as the baseline.",
    },
    {
        "id": "chat_full",
        "label": "Chat safety harness",
        "layers": ["persona", "grep", "rag", "tools", "online"],
        "description": "Primary chat harness with all safety layers enabled.",
    },
    {
        "id": "chat_no_online",
        "label": "Chat offline harness",
        "layers": ["persona", "grep", "rag", "tools"],
        "description": "Local-first chat harness without third-party search.",
    },
    {
        "id": "process",
        "label": "Bulk File Review",
        "layers": ["grep", "rag", "tools"],
        "description": "Bundle-processing harness for case files and graph evidence.",
    },
    {
        "id": "extraction",
        "label": "Knowledge extraction",
        "layers": ["grep", "rag"],
        "description": "Draft typed knowledge objects from source bundles or raw text.",
    },
    {
        "id": "anonymization",
        "label": "Anonymization gate",
        "layers": ["privacy_gate"],
        "description": "Redact PII before any external boundary.",
    },
    {
        "id": "search_safety",
        "label": "Search safety gate",
        "layers": ["privacy_gate", "query_rewrite"],
        "description": "Sanitize outbound search queries before third-party search.",
    },
    {
        "id": "search",
        "label": "Search utility",
        "layers": [],
        "description": "Utility search surface. Pair with search safety for privacy.",
    },
    {
        "id": "import_corpus",
        "label": "Import corpus utility",
        "layers": [],
        "description": "Evidence CRUD surface with audit metadata. No Gemma call required.",
    },
)

QUANTITATIVE_RUN_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "id": "bulk_text_25",
        "label": "Bulk text harness comparison",
        "purpose": "Run the same text prompts with and without the local chat harness and generate a report.",
        "prompt_set": "chat_safety_core",
        "limit": 25,
        "baseline_harness": "none",
        "treatment_harness": "chat_no_online",
        "generation": dict(GENERATION_DEFAULTS),
        "report_title": "DueCare harness lift: Gemma 4 stock vs stock+harness",
    },
    {
        "id": "bulk_text_50",
        "label": "Larger text harness comparison",
        "purpose": "Use when runtime allows a stronger 50-prompt comparison before recording.",
        "prompt_set": "chat_safety_120",
        "limit": 50,
        "baseline_harness": "none",
        "treatment_harness": "chat_no_online",
        "generation": dict(GENERATION_DEFAULTS),
        "report_title": "DueCare harness lift: 50-prompt text regression",
    },
    {
        "id": "tiny_lora_smoke",
        "label": "Tiny LoRA smoke comparison",
        "purpose": "Generate a small SFT/DPO bundle, create or run a tiny LoRA, then compare four arms.",
        "prompt_set": "chat_safety_core",
        "limit": 20,
        "synthetic_count": 24,
        "synthetic_profile": "rubric_polisher_24",
        "training_profile": "tiny_lora_smoke",
        "comparison_matrix": "stock_vs_finetuned_harness_matrix",
        "generation": dict(GENERATION_DEFAULTS),
    },
)

SYNTHETIC_GENERATION_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "id": "rubric_polisher_24",
        "label": "Rubric-polished SFT/DPO smoke seed",
        "source_prompt_set": "synthetic_seed",
        "count": 24,
        "harness_profile": "chat_no_online",
        "generator_mode": "rubric_polisher",
        "include_dpo": True,
        "include_knowledge_facts": True,
        "temperature": 0.7,
    },
    {
        "id": "harness_teacher_40",
        "label": "Harness-teacher synthetic training seed",
        "source_prompt_set": "synthetic_seed",
        "count": 40,
        "harness_profile": "chat_no_online",
        "generator_mode": "harness_teacher",
        "include_dpo": True,
        "include_knowledge_facts": True,
        "temperature": 0.7,
    },
)

TRAINING_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "id": "tiny_lora_smoke",
        "label": "Tiny LoRA smoke run",
        "base_model_ref": "google/gemma-4-E2B-it",
        "base_model_revision": "9dbdf8a839e4e9e0eb56ed80cc8886661d3817cf",
        "adapter_name": "duecare-a00-smoke-e2b-lora",
        "method": "sft_then_dpo",
        "execute": False,
        "max_steps": 60,
        "learning_rate": 2e-4,
        "max_seq_length": 4096,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 8,
        "warmup_steps": 5,
        "lora_r": 16,
        "lora_alpha": 16,
        "lora_dropout": 0.0,
        "random_state": 3407,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "dpo_max_steps": 30,
        "dpo_learning_rate": 5e-6,
        "dpo_beta": 0.1,
    },
    {
        "id": "a00_t4_standard_sft",
        "label": "A-00 T4 standard SFT",
        "base_model_ref": "google/gemma-4-E4B-it",
        "base_model_revision": "a4c2d58be94dda072b918d9db64ee85c8ed34e3f",
        "max_examples": 200,
        "num_epochs": 2,
        "learning_rate": 2e-4,
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 4,
        "warmup_ratio": 0.03,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "max_seq_length": 4096,
    },
    {
        "id": "a00_t4_standard_dpo",
        "label": "A-00 T4 standard DPO",
        "max_pairs": 100,
        "num_epochs": 1,
        "learning_rate": 5e-6,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 4,
        "beta": 0.1,
    },
)

UPLOAD_LIMITS: dict[str, int] = {
    "max_jsonl_rows": 20_000,
    "max_text_chars": 20_000,
    "max_zip_bytes": 200_000_000,
    "max_jsonl_bytes": 200_000_000,
    "max_jsonl_line_chars": 200_000,
    "max_member_bytes": 100_000_000,
    "max_uncompressed_bytes": 500_000_000,
    "max_upload_files": 8,
}

COMPARISON_MATRICES: tuple[dict[str, Any], ...] = (
    {
        "id": "stock_vs_finetuned_harness_matrix",
        "label": "Stock vs fine-tuned vs harness matrix",
        "arms": [
            {"id": "stock", "model_kind": "stock", "harness_profile": "none"},
            {"id": "stock_harness", "model_kind": "stock", "harness_profile": "chat_no_online"},
            {"id": "finetuned", "model_kind": "finetuned", "harness_profile": "none"},
            {"id": "finetuned_harness", "model_kind": "finetuned", "harness_profile": "chat_no_online"},
        ],
        "primary_metrics": [
            "mean_score_pct",
            "dimension_lift_pp",
            "unsafe_fail_rate",
            "citation_grounding_rate",
            "mean_seconds",
        ],
    },
)

POST_TRAINING_BEST_PRACTICES: tuple[dict[str, Any], ...] = (
    {
        "id": "start_with_sft",
        "label": "Start with supervised fine-tuning",
        "practice": (
            "Use SFT for the first measurable domain lift: cited refusals, "
            "corridor-specific response structure, JSON/KnowledgeObject output, "
            "and complaint-safety framing."
        ),
        "why": (
            "SFT is simpler to debug than preference optimization and gives a "
            "clear before/after comparison against stock Gemma and stock+harness."
        ),
        "applies_to": ["tiny_lora_smoke", "a00_t4_standard_sft"],
        "source_refs": ["google_gemma_tuning", "hf_trl_sft", "hf_peft_lora"],
    },
    {
        "id": "keep_eval_split_frozen",
        "label": "Freeze held-out evaluation prompts",
        "practice": (
            "Keep benchmark prompts separate from synthetic training rows. "
            "Never train on the exact prompts used for the report."
        ),
        "why": (
            "The demo needs to show real generalization and harness lift, not "
            "memorization of the scorecard."
        ),
        "applies_to": ["bulk_text_25", "bulk_text_50", "tiny_lora_smoke"],
        "source_refs": ["self_instruct", "instructgpt"],
    },
    {
        "id": "use_quality_filters",
        "label": "Filter synthetic rows before training",
        "practice": (
            "Drop duplicate prompts, invalid JSON, unsafe operational advice, "
            "uncited legal claims, surviving PII, and rows with unclear labels."
        ),
        "why": (
            "Synthetic data is only useful when the generator is paired with "
            "deduplication, validity checks, and safety/rubric filters."
        ),
        "applies_to": ["rubric_polisher_24", "harness_teacher_40"],
        "source_refs": ["self_instruct", "hf_trl_sft"],
    },
    {
        "id": "mix_positive_and_negative_examples",
        "label": "Include refusals, safe alternatives, and weak-answer contrasts",
        "practice": (
            "For each harmful or evasive prompt family, include an ideal answer, "
            "a rejected weak answer when creating preference pairs, and rationale "
            "metadata tied to grader dimensions."
        ),
        "why": (
            "The model should learn both what to say and what not to validate, "
            "especially around fee camouflage, retaliation risk, and jurisdiction "
            "shopping."
        ),
        "applies_to": ["rubric_polisher_24", "harness_teacher_40", "a00_t4_standard_dpo"],
        "source_refs": ["instructgpt", "dpo", "constitutional_ai"],
    },
    {
        "id": "prefer_dpo_before_full_rl",
        "label": "Use DPO-style preference tuning before heavier RL",
        "practice": (
            "Use DPO for the first local preference-optimization pass. Treat PPO/"
            "RLHF/GRPO as later work that requires stronger reward-model and "
            "evaluation infrastructure."
        ),
        "why": (
            "DPO consumes chosen/rejected pairs directly and avoids a separate "
            "reward-model training loop, which is more practical for a Kaggle "
            "smoke path."
        ),
        "applies_to": ["a00_t4_standard_dpo"],
        "source_refs": ["dpo", "hf_trl_dpo", "instructgpt"],
    },
    {
        "id": "preserve_harness_separation",
        "label": "Evaluate fine-tuning and harnessing separately",
        "practice": (
            "Always report stock, stock+harness, fine-tuned, and fine-tuned+harness "
            "arms using the same prompt set and grading rubric."
        ),
        "why": (
            "This distinguishes model-weight improvements from deterministic "
            "guardrail/retrieval/tooling improvements."
        ),
        "applies_to": ["stock_vs_finetuned_harness_matrix"],
        "source_refs": ["instructgpt", "google_gemma_tuning"],
    },
    {
        "id": "privacy_and_license_gate",
        "label": "Gate data by privacy, provenance, and licensing",
        "practice": (
            "Use synthetic or properly licensed public-source material. Redact "
            "real personal data before training-row creation; record source, "
            "license basis, and generation method."
        ),
        "why": (
            "The submission's core privacy claim depends on not training on raw "
            "worker case files or unverifiable personal data."
        ),
        "applies_to": ["rubric_polisher_24", "harness_teacher_40", "tiny_lora_smoke"],
        "source_refs": ["google_gemma_tuning"],
    },
)

TRAINING_DATA_SCHEMAS: dict[str, dict[str, Any]] = {
    "sft_jsonl": {
        "required_fields": list(SFT_REQUIRED_FIELDS),
        "message_roles": ["system", "user", "assistant"],
        "recommended_fields": [
            "source_refs",
            "knowledge_pack_refs",
            "prompt_family",
            "difficulty",
            "expected_citations",
            "grader_dimensions",
            "created_at",
            "sha256",
            "structured_rationale",
            "model_revision",
            "harness_version",
            "rubric_version",
        ],
    },
    "preference_jsonl": {
        "required_fields": list(PREFERENCE_REQUIRED_FIELDS),
        "recommended_fields": [
            "rubric_delta",
            "unsafe_failure_modes",
            "knowledge_pack_refs",
            "source_refs",
            "created_at",
            "sha256",
        ],
    },
}

TRAINING_QUALITY_GATES: tuple[dict[str, Any], ...] = (
    {
        "id": "json_schema_valid",
        "label": "JSONL schema valid",
        "blocking": True,
        "check": "Every SFT/preference row validates against the declared training data schema.",
    },
    {
        "id": "pii_absent",
        "label": "No raw PII in training rows",
        "blocking": True,
        "check": "PII detector finds no raw phone, email, passport, national ID, or personal address fields.",
    },
    {
        "id": "heldout_not_train",
        "label": "No held-out prompt leakage",
        "blocking": True,
        "check": "Training row prompt hashes do not overlap with evaluation prompt hashes.",
    },
    {
        "id": "citation_grounded",
        "label": "Legal claims grounded",
        "blocking": True,
        "check": "Rows that make legal claims include expected source or knowledge-pack references.",
    },
    {
        "id": "unsafe_advice_filtered",
        "label": "Operational harm filtered",
        "blocking": True,
        "check": "Rejected rows or weak-answer contrasts may contain bad advice only as rejected examples, never as chosen SFT assistant outputs.",
    },
    {
        "id": "deduplicated",
        "label": "Prompt and answer deduplicated",
        "blocking": False,
        "check": "Near-duplicate prompts and assistant outputs are removed or capped by prompt family.",
    },
    {
        "id": "balanced_prompt_families",
        "label": "Prompt families balanced",
        "blocking": False,
        "check": "Fee camouflage, passport retention, contract substitution, retaliation risk, worker help, and regulator/platform use cases are represented.",
    },
    {
        "id": "row_integrity",
        "label": "Immutable row hashes",
        "blocking": True,
        "check": "Every row's SHA-256 matches its canonical content.",
    },
    {
        "id": "provenance_licensed",
        "label": "Provenance and license declared",
        "blocking": True,
        "check": "Every training row declares a lineage group and license basis.",
    },
    {
        "id": "hidden_reasoning_absent",
        "label": "No hidden reasoning extraction",
        "blocking": True,
        "check": "Only answer text or deliberately authored structured rationale is allowed; hidden-thought markup is rejected.",
    },
)

POST_TRAINING_SOURCE_REFS: dict[str, dict[str, str]] = {
    "google_gemma_tuning": {
        "label": "Google Gemma model fine-tuning guide",
        "url": "https://ai.google.dev/gemma/docs/tune",
    },
    "hf_trl_sft": {
        "label": "Hugging Face TRL SFTTrainer documentation",
        "url": "https://huggingface.co/docs/trl/en/sft_trainer",
    },
    "hf_trl_dpo": {
        "label": "Hugging Face TRL DPOTrainer documentation",
        "url": "https://huggingface.co/docs/trl/en/dpo_trainer",
    },
    "hf_peft_lora": {
        "label": "Hugging Face PEFT LoRA documentation",
        "url": "https://huggingface.co/docs/peft/developer_guides/lora",
    },
    "self_instruct": {
        "label": "Self-Instruct synthetic instruction generation paper",
        "url": "https://arxiv.org/abs/2212.10560",
    },
    "instructgpt": {
        "label": "Training language models to follow instructions with human feedback",
        "url": "https://arxiv.org/abs/2203.02155",
    },
    "dpo": {
        "label": "Direct Preference Optimization paper",
        "url": "https://arxiv.org/abs/2305.18290",
    },
    "constitutional_ai": {
        "label": "Constitutional AI / RLAIF paper",
        "url": "https://arxiv.org/abs/2212.08073",
    },
}


def harness_profile_map() -> dict[str, dict[str, Any]]:
    return {str(item["id"]): {k: v for k, v in item.items() if k != "id"} for item in HARNESS_PROFILES}


def quantitative_run_profile_map() -> dict[str, dict[str, Any]]:
    return {str(item["id"]): dict(item) for item in QUANTITATIVE_RUN_PROFILES}


def synthetic_generation_profile_map() -> dict[str, dict[str, Any]]:
    return {str(item["id"]): dict(item) for item in SYNTHETIC_GENERATION_PROFILES}


def training_profile_map() -> dict[str, dict[str, Any]]:
    return {str(item["id"]): dict(item) for item in TRAINING_PROFILES}


def upload_limit_map() -> dict[str, int]:
    return dict(UPLOAD_LIMITS)


def comparison_matrix_map() -> dict[str, dict[str, Any]]:
    return {str(item["id"]): dict(item) for item in COMPARISON_MATRICES}


def post_training_best_practices() -> list[dict[str, Any]]:
    return [dict(item) for item in POST_TRAINING_BEST_PRACTICES]


def training_quality_gates() -> list[dict[str, Any]]:
    return [dict(item) for item in TRAINING_QUALITY_GATES]


def model_preset_list(model_variants: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    keys = ["e2b-it", "e4b-it", "26b-a4b-it", "31b-it", "jailbroken-e4b"]
    return [
        {
            "label": model_variants[key]["label"],
            "ref": model_variants[key].get("google_hf_id") or model_variants[key]["hf_id"],
            "source": "hf",
            "notes": model_variants[key]["fit"],
        }
        for key in keys
        if key in model_variants
    ]


def experiment_contract_payload() -> dict[str, Any]:
    return {
        "schema_version": "duecare.experiment_contract.v1",
        "generation_defaults": dict(GENERATION_DEFAULTS),
        "harness_profiles": harness_profile_map(),
        "quantitative_run_profiles": quantitative_run_profile_map(),
        "synthetic_generation_profiles": synthetic_generation_profile_map(),
        "training_profiles": training_profile_map(),
        "upload_limits": upload_limit_map(),
        "comparison_matrices": comparison_matrix_map(),
        "post_training_best_practices": post_training_best_practices(),
        "training_data_schemas": dict(TRAINING_DATA_SCHEMAS),
        "training_quality_gates": training_quality_gates(),
        "post_training_source_refs": dict(POST_TRAINING_SOURCE_REFS),
    }
