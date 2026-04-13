#!/usr/bin/env python3
"""
scaffold.py - Create the gemma4_comp module tree to match docs/architecture.md.

Idempotent: skips files that already exist. Run once at project setup, then
delete or keep as a reference. Non-destructive.

Usage: python scripts/scaffold.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# File contents
# ---------------------------------------------------------------------------
# Each entry: relative_path -> file_content
# Keep each file focused: docstring + protocol + minimal scaffolding only.
# Concrete implementations are left as TODO stubs.
# ---------------------------------------------------------------------------

FILES: dict[str, str] = {

    # =======================================================================
    # Package __init__.py files (structure)
    # =======================================================================

    "src/schemas/__init__.py": '''"""Shared Pydantic schemas. See docs/architecture.md section 3."""

from .base import (
    Grade,
    Severity,
    Difficulty,
    AttackCategory,
    ItemType,
    Provenance,
)
from .items import RawItem, StagingItem, ClassifiedItem, SafeItem
from .prompts import Issue, ResponseExample, Prompt
from .evaluation import EvaluationResult

__all__ = [
    "Grade",
    "Severity",
    "Difficulty",
    "AttackCategory",
    "ItemType",
    "Provenance",
    "RawItem",
    "StagingItem",
    "ClassifiedItem",
    "SafeItem",
    "Issue",
    "ResponseExample",
    "Prompt",
    "EvaluationResult",
]
''',

    "src/config/__init__.py": '''"""Pydantic Settings loader. See docs/architecture.md section 17."""
''',

    "src/data/__init__.py": '''"""Data layer: sources, ingest, classify, anonymize.

See docs/architecture.md sections 4-7.
"""
''',

    "src/data/sources/__init__.py": '''"""Data source connectors. See docs/architecture.md section 4."""

from .base import Source

__all__ = ["Source"]
''',

    "src/data/ingest/__init__.py": '''"""Ingestion: normalize, dedupe, stage. See docs/architecture.md section 5."""
''',

    "src/data/classify/__init__.py": '''"""Classification: sector, corridor, ILO indicators, attack category.

See docs/architecture.md section 6.
"""

from .base import Classifier

__all__ = ["Classifier"]
''',

    "src/data/anon/__init__.py": '''"""Anonymization layer. See docs/architecture.md section 7.

This layer is a hard gate: no PII may exit through the anonymizer.
"""
''',

    "src/data/anon/detectors/__init__.py": '''"""PII detectors. See docs/architecture.md section 7.3."""

from .base import Detector, PIISpan

__all__ = ["Detector", "PIISpan"]
''',

    "src/data/anon/strategies/__init__.py": '''"""Anonymization strategies. See docs/architecture.md section 7.4."""

from .base import AnonymizationStrategy

__all__ = ["AnonymizationStrategy"]
''',

    "src/data/stores/__init__.py": '''"""SQLite-backed stores for staging, clean, and audit data."""
''',

    "src/prompts/__init__.py": '''"""Prompt schema + store + generators. See docs/architecture.md section 8."""
''',

    "src/prompts/generator/__init__.py": '''"""Prompt generators: template, LLM-powered, from_case."""
''',

    "src/docs/__init__.py": '''"""Documentation index: ILO, IOM, Palermo, Kafala, POEA, TVPA, ..."""
''',

    "src/attacks/__init__.py": '''"""Adversarial harness. See docs/architecture.md section 9."""

from .base import BaseAttackStrategy
from .registry import AttackRegistry

__all__ = ["BaseAttackStrategy", "AttackRegistry"]
''',

    "src/attacks/strategies/__init__.py": '''"""Individual attack strategies. Each strategy registers itself on import."""
''',

    "src/attacks/chains/__init__.py": '''"""Multi-turn attack chains: crescendo, FITD, role chain, context poisoning."""
''',

    "src/grading/__init__.py": '''"""Response grading. See docs/architecture.md section 10."""

from .base import Grader

__all__ = ["Grader"]
''',

    "src/training/__init__.py": '''"""Fine-tuning pipeline. See docs/architecture.md section 11."""
''',

    "src/export/__init__.py": '''"""Model export: merge, GGUF, LiteRT, HF Hub publish.

See docs/architecture.md section 12.
"""
''',

    "src/inference/__init__.py": '''"""Runtime judges (llama.cpp / transformers / LiteRT).

See docs/architecture.md section 13.
"""

from .base import Judge

__all__ = ["Judge"]
''',

    "src/eval/__init__.py": '''"""Evaluation harness. See docs/architecture.md section 14."""
''',

    "src/eval/suites/__init__.py": '''"""Test suite loaders: regulatory_evasion, debt_bondage, moral_framing, ..."""
''',

    "src/demo/__init__.py": '''"""FastAPI demo app. See docs/architecture.md section 15."""
''',

    "src/observability/__init__.py": '''"""Logging, metrics, audit. See docs/architecture.md section 16."""
''',


    # =======================================================================
    # Shared schemas (section 3 of the architecture)
    # =======================================================================

    "src/schemas/base.py": '''"""Shared enums, base types, and Provenance.

All cross-component Pydantic models import from here.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Grade(StrEnum):
    WORST = "worst"
    BAD = "bad"
    NEUTRAL = "neutral"
    GOOD = "good"
    BEST = "best"

    @property
    def ordinal(self) -> int:
        return {"worst": 0, "bad": 1, "neutral": 2, "good": 3, "best": 4}[self.value]


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Difficulty(StrEnum):
    BASIC = "basic"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class AttackCategory(StrEnum):
    COGNITIVE = "cognitive"
    AUTHORITY = "authority"
    FRAMING = "framing"
    ENCODING = "encoding"
    MULTI_TURN = "multi_turn"
    REGULATORY = "regulatory"
    MORAL_RELIGIOUS = "moral_religious"
    FINANCIAL = "financial"


class ItemType(StrEnum):
    PROMPT = "prompt"
    RESPONSE = "response"
    CASE = "case"
    DOCUMENT = "document"
    LAW = "law"
    STATUTE = "statute"


class Provenance(BaseModel):
    """Tracks a record's full journey from source to final split.

    Every record in the pipeline carries one of these. The pipeline refuses
    to write a record without a populated Provenance.
    """

    source_id: str
    source_row_id: str
    ingested_at: datetime
    ingestion_script_version: str
    classifier_versions: dict[str, str] = Field(default_factory=dict)
    anonymizer_version: str | None = None
    anonymizer_actions: list[str] = Field(default_factory=list)
    split: str | None = None
    checksum: str
''',

    "src/schemas/items.py": '''"""Item lifecycle schemas: Raw -> Staging -> Classified -> Safe.

See docs/architecture.md section 3.2.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import AttackCategory, Difficulty, ItemType, Provenance


class RawItem(BaseModel):
    """Direct output of a Source connector. Untrusted, unstructured."""

    id: str
    type: ItemType
    content: dict
    provenance: Provenance


class StagingItem(BaseModel):
    """Post-normalization, pre-classification.

    Has canonical `text` + `structured` fields and a content checksum.
    Duplicates (by checksum) are linked via `duplicate_of`.
    """

    id: str
    type: ItemType
    text: str
    structured: dict = Field(default_factory=dict)
    provenance: Provenance
    duplicate_of: str | None = None


class ClassifiedItem(BaseModel):
    """Post-classification. Carries labels but still contains raw PII."""

    id: str
    type: ItemType
    text: str
    structured: dict = Field(default_factory=dict)
    sector: str | None = None
    corridor: str | None = None
    ilo_indicators: list[str] = Field(default_factory=list)
    attack_categories: list[AttackCategory] = Field(default_factory=list)
    difficulty: Difficulty | None = None
    classifier_confidence: dict[str, float] = Field(default_factory=dict)
    unclassified: bool = False
    provenance: Provenance


class SafeItem(BaseModel):
    """Post-anonymization. The only item type allowed downstream of anon.

    Nothing that has not passed through the anonymization verifier may be
    written as a SafeItem.
    """

    id: str
    type: ItemType
    text: str  # redacted
    structured: dict = Field(default_factory=dict)  # redacted
    sector: str | None = None
    corridor: str | None = None
    ilo_indicators: list[str] = Field(default_factory=list)
    attack_categories: list[AttackCategory] = Field(default_factory=list)
    difficulty: Difficulty | None = None
    provenance: Provenance
    anon_version: str
    anon_passed_verifier: bool
''',

    "src/schemas/prompts.py": '''"""Prompt, ResponseExample, and Issue schemas.

See docs/architecture.md section 3.3.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Difficulty, Grade, Provenance, Severity


class Issue(BaseModel):
    """A specific problem with an LLM response."""

    type: str  # "missed_indicator", "provided_harmful_info", ...
    description: str
    severity: Severity
    documentation_ref: str | None = None


class ResponseExample(BaseModel):
    """A graded exemplar response for a prompt.

    A prompt may have up to 5 of these (one per Grade). They are the
    training signal for the safety judge.
    """

    text: str
    grade: Grade
    score: float  # 0.0 .. 1.0
    explanation: str
    issues: list[Issue] = Field(default_factory=list)
    documentation_refs: list[str] = Field(default_factory=list)


class Prompt(BaseModel):
    """A prompt in the safety benchmark.

    Every Prompt is addressable by id and carries its full provenance and
    graded response examples.
    """

    id: str
    text: str
    category: str  # attack category (registry key)
    subcategory: str | None = None
    sector: str | None = None
    corridor: str | None = None
    difficulty: Difficulty
    ilo_indicators: list[str] = Field(default_factory=list)
    attack_strategies: list[str] = Field(default_factory=list)
    graded_responses: dict[Grade, ResponseExample] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    provenance: Provenance
''',

    "src/schemas/cases.py": '''"""Real-world case schema. See docs/architecture.md section 3."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Provenance


class CaseSource(BaseModel):
    """A citation for a real-world case (news article, court doc, NGO report)."""

    title: str
    url: str | None = None
    publisher: str | None = None
    published_at: str | None = None
    type: str  # "news", "court_doc", "ngo_report", "academic", "official"


class RealWorldCase(BaseModel):
    """A documented, anonymized trafficking / forced-labor case.

    Real-world cases are used both as training data and as a source of
    grounded prompts via the from_case prompt generator.
    """

    id: str
    title: str
    summary: str
    sector: str | None = None
    corridor: str | None = None
    origin_country: str | None = None
    destination_country: str | None = None
    year: int | None = None
    exploitation_methods: list[str] = Field(default_factory=list)
    ilo_indicators: list[str] = Field(default_factory=list)
    victim_count: int | None = None
    sources: list[CaseSource] = Field(default_factory=list)
    documentation_refs: list[str] = Field(default_factory=list)
    derived_prompt_ids: list[str] = Field(default_factory=list)
    key_phrases: list[str] = Field(default_factory=list)
    anonymized: bool = True
    verified: bool = False
    provenance: Provenance
''',

    "src/schemas/documentation.py": '''"""Documentation index schema (ILO, IOM, Palermo, national law).

See docs/architecture.md section 3.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Provenance


class Provision(BaseModel):
    """A specific provision (section/article) inside a law or regulation."""

    identifier: str  # "Art. 7", "Sec. 6(a)", etc.
    title: str | None = None
    text: str
    key_terms: list[str] = Field(default_factory=list)


class Documentation(BaseModel):
    """A legal or regulatory document referenced by prompts and grades.

    Examples: ILO C181, UN Palermo Protocol, Saudi Labor Law Art. 40,
    Philippines RA 8042 Sec. 6, TVPA.
    """

    id: str
    title: str
    type: str  # "law", "regulation", "guideline", "convention", "report"
    organization: str
    summary: str
    full_text: str | None = None
    source_url: str | None = None
    jurisdiction: str  # "international", "regional", "national"
    countries: list[str] = Field(default_factory=list)
    effective_date: str | None = None
    topics: list[str] = Field(default_factory=list)
    ilo_indicators: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    key_provisions: list[Provision] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    provenance: Provenance
''',

    "src/schemas/attacks.py": '''"""Attack strategy and chain schemas.

Runtime strategy objects live in src/attacks/; these are the data-model
sidecars used for persistence, configuration, and cross-component messaging.

See docs/architecture.md section 3 and section 9.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import AttackCategory


class AttackStrategyMeta(BaseModel):
    """Metadata describing an attack strategy. One per registered strategy."""

    id: str
    name: str
    category: AttackCategory
    description: str
    version: str
    indicators: list[str] = Field(default_factory=list)
    parameters_schema: dict = Field(default_factory=dict)  # JSON Schema


class AttackChainMeta(BaseModel):
    """Metadata describing a multi-turn attack chain."""

    id: str
    name: str
    description: str
    n_turns: int
    strategy_ids: list[str] = Field(default_factory=list)
    version: str
''',

    "src/schemas/evaluation.py": '''"""Evaluation result schema.

See docs/architecture.md section 3.4.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .base import Grade
from .prompts import Issue


class EvaluationResult(BaseModel):
    """The output of a Grader or a runtime Judge.

    All runtime judges (llama.cpp, transformers, LiteRT) and all Graders
    produce one of these. Serves as the shared contract between training-
    time scoring and inference-time scoring.
    """

    prompt_id: str
    candidate_response: str
    grade: Grade
    score: float  # 0.0 .. 1.0
    explanation: str
    issues: list[Issue] = Field(default_factory=list)
    missed_indicators: list[str] = Field(default_factory=list)
    documentation_refs: list[str] = Field(default_factory=list)
    similarity_scores: dict[Grade, float] = Field(default_factory=dict)
    judge_model: str
    judge_method: str  # "llama_cpp" | "transformers" | "litert" | "rule_based" | ...
    eval_duration_ms: int = 0
''',

    "src/schemas/training.py": '''"""Training dataset + run record schemas.

See docs/architecture.md sections 3 and 11.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DatasetSplit(BaseModel):
    """Describes a concrete train/val/test split produced by the prepare step."""

    version: str
    created_at: datetime
    train_path: str
    val_path: str
    test_path: str
    n_train: int
    n_val: int
    n_test: int
    stratified_by: list[str]
    held_out_by: str
    seed: int
    category_distribution: dict[str, int] = Field(default_factory=dict)
    grade_distribution: dict[str, int] = Field(default_factory=dict)
    corridor_distribution: dict[str, int] = Field(default_factory=dict)


class TrainRecord(BaseModel):
    """One fine-tuning run. Persisted to runs/ table for audit + reproducibility."""

    run_id: str
    git_sha: str
    config_hash: str
    dataset_version: str
    base_model: str
    started_at: datetime
    ended_at: datetime | None = None
    status: str  # "running" | "completed" | "failed"
    final_metrics: dict = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
''',


    # =======================================================================
    # Protocol base files (one per component with a protocol)
    # =======================================================================

    "src/data/sources/base.py": '''"""Source protocol. See docs/architecture.md section 4.1."""

from __future__ import annotations

from typing import Iterator, Protocol, runtime_checkable

from src.schemas.items import RawItem


@runtime_checkable
class Source(Protocol):
    """Abstract source connector.

    Every concrete source is read-only and yields RawItems lazily. Sources
    must set a stable `id` so provenance tracking works across runs.
    """

    id: str
    name: str
    version: str
    description: str

    def fetch(self) -> Iterator[RawItem]:
        """Yield raw items lazily. Must not load everything into memory."""
        ...

    def count(self) -> int | None:
        """Total items available, or None if unknown. Used for progress bars."""
        ...

    def healthcheck(self) -> bool:
        """Return True if the source is reachable and readable right now."""
        ...
''',

    "src/data/classify/base.py": '''"""Classifier protocol. See docs/architecture.md section 6.2."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.schemas.items import ClassifiedItem, StagingItem


@runtime_checkable
class Classifier(Protocol):
    """Assigns labels to a StagingItem, producing a ClassifiedItem.

    Classifiers must populate `classifier_confidence` with a per-label
    confidence score. If the classifier abstains on a label, it should
    leave the field as None (or empty list) and record a zero confidence.
    A classifier must never silently drop an item.
    """

    name: str
    version: str

    def classify(self, item: StagingItem) -> ClassifiedItem:
        ...
''',

    "src/data/anon/detectors/base.py": '''"""PII detector protocol.

See docs/architecture.md section 7.3.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class PIISpan(BaseModel):
    """A single detected PII span inside a text."""

    start: int
    end: int
    category: str  # "phone", "passport", "given_name", "address", ...
    text: str
    confidence: float


@runtime_checkable
class Detector(Protocol):
    """Detects PII in text and returns a list of spans.

    Detectors are composable: multiple detectors run over the same text
    and their spans are merged + deduped by the anonymization pipeline.
    """

    name: str
    version: str

    def detect(self, text: str) -> list[PIISpan]:
        ...
''',

    "src/data/anon/strategies/base.py": '''"""Anonymization strategy protocol.

See docs/architecture.md section 7.4.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.data.anon.detectors.base import PIISpan


@runtime_checkable
class AnonymizationStrategy(Protocol):
    """Applies an anonymization transform to a text, guided by detected spans.

    Strategies are composable: a pipeline may apply the Redactor to phone
    numbers, the Tokenizer to names, and the Generalizer to locations, all
    in one pass.
    """

    name: str
    version: str

    def apply(self, text: str, spans: list[PIISpan]) -> str:
        ...
''',

    "src/attacks/base.py": '''"""Attack strategy protocol. See docs/architecture.md section 9.1."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.schemas.base import AttackCategory
from src.schemas.prompts import Prompt


@runtime_checkable
class BaseAttackStrategy(Protocol):
    """An attack strategy that mutates a base Prompt into an adversarial variant.

    Strategies are pure functions over Prompts. They do not call any LLM.
    Multi-turn behavior lives in src/attacks/chains/ instead, where a chain
    is allowed to call a `judge_fn` between turns.
    """

    id: str  # registry key
    name: str  # human-readable
    category: AttackCategory
    description: str
    version: str

    def mutate(self, prompt: Prompt, **kwargs) -> Prompt:
        """Return a new Prompt with the attack strategy applied."""
        ...

    def validate(self, mutated: Prompt) -> bool:
        """Return True if the mutation preserved invariants (length, schema)."""
        ...

    def get_indicators(self) -> list[str]:
        """ILO indicators this strategy is designed to test."""
        ...
''',

    "src/attacks/registry.py": '''"""AttackRegistry. See docs/architecture.md section 9.2.

Strategies register themselves on import via @AttackRegistry.register("id").
"""

from __future__ import annotations

from typing import Iterator

from src.attacks.base import BaseAttackStrategy
from src.schemas.prompts import Prompt


class AttackRegistry:
    """Central registry of attack strategies.

    Strategies register themselves on import. The registry is populated at
    application startup by importing src.attacks.strategies.
    """

    _strategies: dict[str, BaseAttackStrategy] = {}

    @classmethod
    def register(cls, strategy_id: str):
        """Decorator: register a strategy class under `strategy_id`."""
        def decorator(strategy_cls):
            cls._strategies[strategy_id] = strategy_cls()
            return strategy_cls
        return decorator

    @classmethod
    def get(cls, strategy_id: str) -> BaseAttackStrategy:
        if strategy_id not in cls._strategies:
            raise KeyError(f"Unknown attack strategy: {strategy_id}")
        return cls._strategies[strategy_id]

    @classmethod
    def all_ids(cls) -> list[str]:
        return sorted(cls._strategies.keys())

    @classmethod
    def all(cls) -> Iterator[BaseAttackStrategy]:
        for sid in cls.all_ids():
            yield cls._strategies[sid]

    @classmethod
    def apply(
        cls,
        prompt: Prompt,
        strategy_ids: list[str],
    ) -> list[Prompt]:
        """Apply each strategy to the base prompt, returning mutated variants."""
        results: list[Prompt] = []
        for sid in strategy_ids:
            strategy = cls.get(sid)
            mutated = strategy.mutate(prompt)
            if not strategy.validate(mutated):
                raise ValueError(f"Strategy {sid} produced invalid mutation")
            results.append(mutated)
        return results
''',

    "src/grading/base.py": '''"""Grader protocol. See docs/architecture.md section 10.1."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.schemas.evaluation import EvaluationResult
from src.schemas.prompts import Prompt


@runtime_checkable
class Grader(Protocol):
    """Scores a candidate response against a prompt and returns an EvaluationResult.

    Graders are the core signal source: they are used both to populate
    graded response examples for the training dataset and to evaluate the
    fine-tuned judge at benchmark time.
    """

    name: str
    version: str

    def grade(self, prompt: Prompt, candidate_response: str) -> EvaluationResult:
        ...
''',

    "src/inference/base.py": '''"""Judge protocol. See docs/architecture.md section 13.1."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.schemas.evaluation import EvaluationResult


@runtime_checkable
class Judge(Protocol):
    """Runtime judge: loads a fine-tuned model and scores (prompt, response) pairs.

    Implementations:
      - LlamaCppJudge      (primary, loads GGUF via llama-cpp-python)
      - TransformersJudge  (for eval baselines, full precision)
      - LiteRTJudge        (stretch goal, mobile/edge)
    """

    name: str
    model_version: str
    runtime: str  # "llama_cpp" | "transformers" | "litert"

    def warmup(self) -> None:
        """Optional: warm up the runtime before serving traffic."""
        ...

    def evaluate(self, prompt: str, candidate_response: str) -> EvaluationResult:
        ...

    def close(self) -> None:
        """Release underlying resources (model handles, file descriptors)."""
        ...
''',


    # =======================================================================
    # Config loader
    # =======================================================================

    "src/config/loader.py": '''"""Global settings loader. See docs/architecture.md section 17."""

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
''',


    # =======================================================================
    # CLI entry point
    # =======================================================================

    "src/__main__.py": '''"""Package entry point: `python -m src <command>`."""

from src.cli import app

if __name__ == "__main__":
    app()
''',

    "src/cli.py": '''"""CLI entry points. One command per pipeline stage.

See docs/architecture.md section 2 (scripts/) and section 20 (release checklist).
"""

from __future__ import annotations

import typer

app = typer.Typer(
    name="gemma4_comp",
    help="Gemma 4 migrant-worker safety judge pipeline.",
    no_args_is_help=True,
)


@app.command()
def ingest() -> None:
    """Run source fetch + normalize + stage."""
    typer.echo("TODO: wire up src.data.ingest pipeline")


@app.command()
def classify() -> None:
    """Run classifier ensemble over the staging DB."""
    typer.echo("TODO: wire up src.data.classify pipeline")


@app.command()
def anonymize() -> None:
    """Run the anonymization gate: detect, redact, verify, quarantine."""
    typer.echo("TODO: wire up src.data.anon pipeline")


@app.command("build-prompts")
def build_prompts() -> None:
    """Build the prompt store from the clean DB."""
    typer.echo("TODO: wire up src.prompts pipeline")


@app.command()
def prepare() -> None:
    """Build the train/val/test JSONL splits for Unsloth."""
    typer.echo("TODO: wire up src.training.prepare")


@app.command()
def finetune() -> None:
    """Run the Unsloth + LoRA fine-tune."""
    typer.echo("TODO: wire up src.training.finetune")


@app.command()
def export(
    target: str = typer.Option("gguf", help="gguf | litert | all"),
) -> None:
    """Export the fine-tuned model to GGUF and/or LiteRT."""
    typer.echo(f"TODO: wire up src.export for target={target}")


@app.command()
def evaluate(
    model: str = typer.Option(..., help="Path to the judge model or 'stock'"),
) -> None:
    """Run the evaluation harness and produce a report."""
    typer.echo(f"TODO: wire up src.eval.runner for model={model}")


@app.command()
def serve(
    port: int = typer.Option(8080, help="Port to bind"),
) -> None:
    """Run the FastAPI demo app."""
    typer.echo(f"TODO: wire up src.demo.app on port={port}")


if __name__ == "__main__":
    app()
''',


    # =======================================================================
    # Top-level scripts directory marker
    # =======================================================================

    "scripts/README.md": '''# scripts/

Orchestration scripts - one per pipeline stage. These are thin wrappers
over the src/ modules and exist to make the pipeline runnable without
memorizing module paths.

| # | Script | Stage | See |
|---|---|---|---|
| 00 | `00_ingest.py` | Source fetch + normalize + stage | `src/data/ingest/` |
| 01 | `01_classify.py` | Classify staging items | `src/data/classify/` |
| 02 | `02_anonymize.py` | PII detection + redaction + verify | `src/data/anon/` |
| 03 | `03_build_prompts.py` | Populate prompt store from clean DB | `src/prompts/` |
| 04 | `04_prepare_training_data.py` | Build Unsloth JSONL splits | `src/training/prepare.py` |
| 05 | `05_finetune.py` | Unsloth + LoRA fine-tune | `src/training/finetune.py` |
| 06 | `06_export.py` | Merge LoRA, quantize GGUF, publish | `src/export/` |
| 07 | `07_evaluate.py` | Run benchmark + generate report | `src/eval/` |
| 08 | `08_publish.py` | Push model to HF Hub, update writeup | `src/export/publish.py` |

One-shot scripts:
- `scaffold.py` - creates the src/ module tree (run once at setup)
- `scaffold.py` is idempotent and safe to re-run.
''',

    # Empty placeholder configs dir (just a README so git tracks the dir)
    "configs/README.md": '''# configs/

Version-controlled YAML configuration files, one per component.
See `docs/architecture.md` section 17 (Cross-cutting: Configuration).

| File | Loaded by |
|---|---|
| `sources.yaml` | `src/data/sources/registry.py` |
| `classification.yaml` | `src/data/classify/*` |
| `anonymization.yaml` | `src/data/anon/*` |
| `attacks.yaml` | `src/attacks/registry.py` |
| `grading.yaml` | `src/grading/*` |
| `training_e4b.yaml` | `src/training/finetune.py` |
| `export.yaml` | `src/export/*` |
| `eval.yaml` | `src/eval/runner.py` |
| `demo.yaml` | `src/demo/app.py` |

Secrets (API keys) never live here - they come from environment variables
with the `GEMMA4_` prefix.
''',

    # tests/ markers
    "tests/__init__.py": '',
    "tests/unit/__init__.py": '',
    "tests/integration/__init__.py": '',
    "tests/README.md": '''# tests/

Test layout per `docs/architecture.md` section 18:

- `unit/` - per-module unit tests, no I/O
- `integration/` - pipeline tests against real SQLite + small fixtures
- `fixtures/` - `mini_benchmark.sqlite`, `sample_items.json`, etc.
''',
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    created = 0
    skipped = 0
    for rel_path, content in FILES.items():
        p = ROOT / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            print(f"SKIP   {rel_path}")
            skipped += 1
            continue
        p.write_text(content, encoding="utf-8")
        print(f"CREATE {rel_path}")
        created += 1

    print()
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")
    print(f"Total:   {len(FILES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
