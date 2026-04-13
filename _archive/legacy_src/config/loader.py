"""Global settings loader. See docs/architecture.md section 17."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global settings. Paths are project-relative by default.

    Secrets come from environment variables only (prefixed GEMMA4_).
    Everything else lives in configs/*.yaml.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GEMMA4_", extra="ignore")

    # File paths (relative to project root; override via GEMMA4_*)
    staging_db_path: Path = Path("data/staging.sqlite")
    clean_db_path: Path = Path("data/clean.sqlite")
    audit_db_path: Path = Path("data/audit.sqlite")
    prompt_db_path: Path = Path("data/prompts.sqlite")
    models_dir: Path = Path("models")
    reports_dir: Path = Path("data/reports")
    logs_dir: Path = Path("logs")

    # Config files
    sources_config: Path = Path("configs/sources.yaml")
    classification_config: Path = Path("configs/classification.yaml")
    anonymization_config: Path = Path("configs/anonymization.yaml")
    attacks_config: Path = Path("configs/attacks.yaml")
    grading_config: Path = Path("configs/grading.yaml")
    training_config: Path = Path("configs/training_e4b.yaml")
    export_config: Path = Path("configs/export.yaml")
    eval_config: Path = Path("configs/eval.yaml")
    demo_config: Path = Path("configs/demo.yaml")

    # Secrets (from env only)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    mistral_api_key: str | None = None
    huggingface_token: str | None = None


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return a cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
