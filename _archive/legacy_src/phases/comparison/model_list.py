"""Comparison field for Phase 2.

See docs/project_phases.md section 2.3.

The model list is intentionally code, not config, so changes require a
commit and are reviewable. Keep the field small and locked early.
"""

from __future__ import annotations

from pydantic import BaseModel


class ComparisonModel(BaseModel):
    id: str                         # stable short id used in reports
    display_name: str
    provider: str                   # "transformers" | "llama_cpp" | "openai" | "anthropic" | "mistral" | "ollama"
    model_id: str                   # HF Hub id or API model id
    size_b: float | None = None     # parameter count in billions, if known
    quantization: str | None = None # "q4_k_m" | "q5_k_m" | "q8_0" | None
    access: str = "local"           # "local" | "api"
    primary_subject: bool = False   # True for Gemma variants
    reference_only: bool = False    # True for closed-model upper bounds


COMPARISON_FIELD: list[ComparisonModel] = [
    ComparisonModel(
        id="gemma_4_e2b",
        display_name="Gemma 4 E2B (stock)",
        provider="transformers",
        model_id="google/gemma-4-e2b-it",
        size_b=2.0,
        primary_subject=True,
    ),
    ComparisonModel(
        id="gemma_4_e4b",
        display_name="Gemma 4 E4B (stock)",
        provider="transformers",
        model_id="google/gemma-4-e4b-it",
        size_b=4.0,
        primary_subject=True,
    ),
    ComparisonModel(
        id="gpt_oss_20b",
        display_name="GPT-OSS-20B",
        provider="transformers",
        model_id="openai/gpt-oss-20b",
        size_b=20.0,
    ),
    ComparisonModel(
        id="qwen_2_5_7b",
        display_name="Qwen2.5 7B Instruct",
        provider="transformers",
        model_id="Qwen/Qwen2.5-7B-Instruct",
        size_b=7.0,
    ),
    ComparisonModel(
        id="qwen_2_5_32b",
        display_name="Qwen2.5 32B Instruct",
        provider="transformers",
        model_id="Qwen/Qwen2.5-32B-Instruct",
        size_b=32.0,
    ),
    ComparisonModel(
        id="llama_3_1_8b",
        display_name="Llama 3.1 8B Instruct",
        provider="transformers",
        model_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
        size_b=8.0,
    ),
    ComparisonModel(
        id="mistral_small",
        display_name="Mistral Small",
        provider="mistral",
        model_id="mistral-small-latest",
        access="api",
    ),
    ComparisonModel(
        id="deepseek_v3",
        display_name="DeepSeek V3",
        provider="openai",  # DeepSeek uses OpenAI-compatible API
        model_id="deepseek-chat",
        size_b=671.0,
        access="api",
    ),
    ComparisonModel(
        id="gpt_4o_mini",
        display_name="GPT-4o mini",
        provider="openai",
        model_id="gpt-4o-mini",
        access="api",
        reference_only=True,
    ),
    ComparisonModel(
        id="claude_haiku_4_5",
        display_name="Claude Haiku 4.5",
        provider="anthropic",
        model_id="claude-haiku-4-5-20251001",
        access="api",
        reference_only=True,
    ),
]
