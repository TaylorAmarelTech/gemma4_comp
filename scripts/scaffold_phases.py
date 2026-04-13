#!/usr/bin/env python3
"""
scaffold_phases.py - Add src/phases/ subpackage matching docs/project_phases.md.

Idempotent: skips files that already exist. Safe to re-run.

Creates:
  src/phases/                 package
  src/phases/base.py          PhaseRunner protocol + PhaseReport schema
  src/phases/categories.py    the 4 capability tests (shared by all phases)
  src/phases/exploration/     Phase 1 runner + categories + configs
  src/phases/comparison/      Phase 2 runner + model list
  src/phases/enhancement/     Phase 3 runner + RAG + ablation stubs
  src/phases/implementation/  Phase 4 API + UI + monitors stubs
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


FILES: dict[str, str] = {

    # =======================================================================
    # Top-level phase package
    # =======================================================================

    "src/phases/__init__.py": '''"""Phase runners. See docs/project_phases.md.

Four phases, each a thin orchestration layer over the shared component
modules (src/data, src/attacks, src/grading, src/inference, etc.):

  1. exploration    - out-of-the-box Gemma 4 baseline
  2. comparison     - cross-model head-to-head
  3. enhancement    - RAG + fine-tune + ablation
  4. implementation - live API + UI + monitors
"""

from .base import PhaseRunner, PhaseReport

__all__ = ["PhaseRunner", "PhaseReport"]
''',

    "src/phases/base.py": '''"""PhaseRunner protocol and PhaseReport schema.

Every phase runner implements this contract. See architecture.md §21.5.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class PhaseReport(BaseModel):
    """Produced at the end of every phase run. Persisted to reports/."""

    phase_id: Literal["exploration", "comparison", "enhancement", "implementation"]
    started_at: datetime
    ended_at: datetime | None = None
    status: Literal["running", "completed", "failed"] = "running"

    # Artifact paths keyed by short name
    artifacts: dict[str, Path] = Field(default_factory=dict)

    # Headline metrics (per capability test + aggregate)
    metrics: dict[str, float] = Field(default_factory=dict)

    # Reproducibility
    git_sha: str = ""
    dataset_version: str = ""
    config_hash: str = ""

    # Human-readable
    summary: str = ""
    notes: list[str] = Field(default_factory=list)


@runtime_checkable
class PhaseRunner(Protocol):
    """A phase runner orchestrates components to produce a PhaseReport."""

    phase_id: str
    config_path: Path

    def run(self) -> PhaseReport:
        """Execute the phase end-to-end and return the report."""
        ...

    def summary(self) -> str:
        """One-line summary for the CLI dashboard."""
        ...
''',

    "src/phases/categories.py": '''"""The four capability test categories shared by every phase.

See docs/project_phases.md section "The four test categories".
"""

from __future__ import annotations

from enum import StrEnum


class CapabilityTest(StrEnum):
    """The four tests we run in every phase."""

    GUARDRAILS = "response_policy_guardrails"
    ANONYMIZATION = "anonymization"
    CLASSIFICATION = "document_classification"
    FACT_EXTRACTION = "key_fact_extraction"


# Metric definitions per capability test. The phase runners populate these
# after running their configured model(s) over the test data.
CAPABILITY_METRICS: dict[CapabilityTest, list[str]] = {
    CapabilityTest.GUARDRAILS: [
        "grade_exact_match",
        "grade_within_1",
        "ordinal_mae",
        "ilo_indicator_recall",
        "ilo_indicator_precision",
        "documentation_ref_precision",
        "refusal_rate",
        "harmful_phrase_rate",
    ],
    CapabilityTest.ANONYMIZATION: [
        "pii_span_recall",
        "pii_span_precision",
        "false_positive_rate",
        "non_latin_script_recall",
        "foreign_name_recall",
    ],
    CapabilityTest.CLASSIFICATION: [
        "sector_accuracy",
        "corridor_accuracy",
        "ilo_indicator_f1_multilabel",
        "attack_category_f1",
        "difficulty_agreement",
    ],
    CapabilityTest.FACT_EXTRACTION: [
        "entity_f1_person",
        "entity_f1_organization",
        "entity_f1_location",
        "entity_f1_currency",
        "date_accuracy",
        "citation_accuracy",
    ],
}


# Which components each capability test exercises. Used by phase runners
# to pick the right model calls and scorers.
COMPONENTS_PER_TEST: dict[CapabilityTest, list[str]] = {
    CapabilityTest.GUARDRAILS: [
        "src.inference",      # run the model
        "src.grading",        # score against graded examples
    ],
    CapabilityTest.ANONYMIZATION: [
        "src.inference",
        "src.data.anon",      # ground truth + verifier
    ],
    CapabilityTest.CLASSIFICATION: [
        "src.inference",
        "src.data.classify",  # taxonomy + scoring
    ],
    CapabilityTest.FACT_EXTRACTION: [
        "src.inference",
        "src.grading",        # custom extractor scorer
    ],
}
''',


    # =======================================================================
    # Phase 1 - Exploration
    # =======================================================================

    "src/phases/exploration/__init__.py": '''"""Phase 1: Gemma 4 Exploration. See docs/project_phases.md section 1."""

from .runner import ExplorationRunner

__all__ = ["ExplorationRunner"]
''',

    "src/phases/exploration/runner.py": '''"""Phase 1 runner - out-of-the-box Gemma 4 baseline.

See docs/project_phases.md Phase 1.

Responsibilities:
  - Load Gemma 4 E2B and E4B via the inference protocol
  - Run the 4 capability tests against the 21K public benchmark
  - Iterate on failure-mode clusters
  - Produce reports/phase1/baseline_gemma_*.md + failure_taxonomy.md
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.phases.base import PhaseReport
from src.phases.categories import CapabilityTest


class ExplorationRunner:
    phase_id = "exploration"

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def run(self) -> PhaseReport:
        report = PhaseReport(
            phase_id="exploration",
            started_at=datetime.now(),
        )
        # TODO: implement
        #   1. Load test data from src.data.sources.local_sqlite (the 21K benchmark)
        #   2. For each model in config (Gemma E2B, E4B):
        #      - For each CapabilityTest:
        #        - Run src.inference.TransformersJudge / LlamaCppJudge
        #        - Score with src.grading.*
        #        - Aggregate metrics
        #   3. Cluster failures, write failure_taxonomy.md
        #   4. Persist to data/phase1/baselines.sqlite
        report.status = "completed"
        report.ended_at = datetime.now()
        report.notes.append("TODO: Phase 1 runner stub")
        return report

    def summary(self) -> str:
        return "Phase 1 - Exploration: stub"
''',

    "src/phases/exploration/failure_clusterer.py": '''"""Cluster Phase 1 failures by category / sector / corridor / ILO indicator.

Produces reports/phase1/failure_taxonomy.md.

TODO: implement. See docs/project_phases.md Phase 1.
"""
''',


    # =======================================================================
    # Phase 2 - Comparison
    # =======================================================================

    "src/phases/comparison/__init__.py": '''"""Phase 2: Gemma 4 Comparison. See docs/project_phases.md section 2."""

from .runner import ComparisonRunner

__all__ = ["ComparisonRunner"]
''',

    "src/phases/comparison/runner.py": '''"""Phase 2 runner - cross-model head-to-head.

See docs/project_phases.md Phase 2.

Responsibilities:
  - Run the identical 4-capability test suite against the configured
    comparison field (Gemma 4, GPT-OSS, Qwen, Llama, Mistral, DeepSeek,
    closed references)
  - Produce reports/phase2/comparison_report.md + headline_table.md +
    per_corridor_breakdown.md
  - Publish the result SQLite as a public Kaggle Dataset
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.phases.base import PhaseReport


class ComparisonRunner:
    phase_id = "comparison"

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def run(self) -> PhaseReport:
        report = PhaseReport(
            phase_id="comparison",
            started_at=datetime.now(),
        )
        # TODO: implement
        #   1. Load the comparison field from model_list.py
        #   2. For each model:
        #      - Use appropriate provider adapter (OpenAI / Anthropic / Mistral /
        #        Ollama / local-gguf)
        #      - Run the 4-capability test suite
        #      - Collect metrics
        #   3. Compute head-to-head tables and per-corridor breakdowns
        #   4. Write reports and publish Kaggle Dataset
        report.status = "completed"
        report.ended_at = datetime.now()
        report.notes.append("TODO: Phase 2 runner stub")
        return report

    def summary(self) -> str:
        return "Phase 2 - Comparison: stub"
''',

    "src/phases/comparison/model_list.py": '''"""Comparison field for Phase 2.

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
''',


    # =======================================================================
    # Phase 3 - Enhancement
    # =======================================================================

    "src/phases/enhancement/__init__.py": '''"""Phase 3: Gemma 4 Enhancement. See docs/project_phases.md section 3."""

from .runner import EnhancementRunner

__all__ = ["EnhancementRunner"]
''',

    "src/phases/enhancement/runner.py": '''"""Phase 3 runner - RAG + fine-tune + ablation.

See docs/project_phases.md Phase 3.

Three enhancement tracks + a 4-configuration ablation:
  A. Stock Gemma 4 E4B                       (baseline, from Phase 1)
  B. Stock + RAG                             ("RAG only")
  C. Fine-tuned Gemma 4 E4B                  ("fine-tune only")
  D. Fine-tuned + RAG                        ("hybrid")
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.phases.base import PhaseReport


class EnhancementRunner:
    phase_id = "enhancement"

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def run(self) -> PhaseReport:
        report = PhaseReport(
            phase_id="enhancement",
            started_at=datetime.now(),
        )
        # TODO: implement
        #   1. Build fact database from _reference/framework/src/scraper/seeds/
        #      via src.phases.enhancement.fact_db
        #   2. Build FAISS index via src.phases.enhancement.rag
        #   3. Prepare training splits (held out by source_case_id)
        #   4. Run Unsloth + LoRA fine-tune via src.training.finetune
        #   5. Export merged fp16 -> GGUF via src.export
        #   6. Run ablation over configs A/B/C/D via src.phases.enhancement.ablation
        #   7. Generate model card via src.export.model_card
        #   8. Publish to HF Hub via src.export.publish
        report.status = "completed"
        report.ended_at = datetime.now()
        report.notes.append("TODO: Phase 3 runner stub")
        return report

    def summary(self) -> str:
        return "Phase 3 - Enhancement: stub"
''',

    "src/phases/enhancement/fact_db.py": '''"""Build the Phase 3 RAG fact database.

Ingests all 176 scraper seed modules from _reference/framework/src/scraper/seeds/
plus ILO / IOM / Palermo Protocol / Kafala / POEA documentation, emits a
SQLite fact database with stable ids and source attribution.

Schema:
  facts(id PK, text, fact_type, source_module, jurisdiction, metadata JSON)

TODO: implement. See docs/project_phases.md Phase 3.2a.
"""
''',

    "src/phases/enhancement/rag.py": '''"""Retriever + FAISS index for the Phase 3 RAG pipeline.

Contract:

    class Retriever(Protocol):
        def retrieve(self, query: str, k: int = 5) -> list[FactHit]: ...

    class FactHit(BaseModel):
        text: str
        source_module: str
        fact_type: str
        score: float
        citation: str

TODO: implement using sentence-transformers + FAISS.
See docs/project_phases.md Phase 3.2a.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class FactHit(BaseModel):
    text: str
    source_module: str
    fact_type: str
    score: float
    citation: str


@runtime_checkable
class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 5) -> list[FactHit]: ...
''',

    "src/phases/enhancement/ablation.py": '''"""Run the 4-configuration ablation study.

A. Stock Gemma 4 E4B
B. Stock + RAG
C. Fine-tuned Gemma 4 E4B
D. Fine-tuned + RAG

For each config, run the 4 capability tests from src.phases.categories.
Produce reports/phase3/ablation.md.

TODO: implement.
"""
''',


    # =======================================================================
    # Phase 4 - Implementation
    # =======================================================================

    "src/phases/implementation/__init__.py": '''"""Phase 4: Gemma 4 Use Case / Implementation.

See docs/project_phases.md section 4.

Ships:
  1. Public API endpoint (/v1/evaluate, /classify, /anonymize, /extract_facts)
  2. Web demo UI with /compare page
  3. Optional: social media monitor (Reddit) or chat monitor (Discord)
"""

from .runner import ImplementationRunner

__all__ = ["ImplementationRunner"]
''',

    "src/phases/implementation/runner.py": '''"""Phase 4 runner - spin up the live demo + API.

In Phase 4 the "runner" doesn't run a one-shot analysis - it boots and
supervises the live demo. `run()` starts the FastAPI server and returns
a report that includes the live URL.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.phases.base import PhaseReport


class ImplementationRunner:
    phase_id = "implementation"

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def run(self) -> PhaseReport:
        report = PhaseReport(
            phase_id="implementation",
            started_at=datetime.now(),
        )
        # TODO: implement
        #   1. Load the Phase 3 GGUF via src.inference.llama_cpp
        #   2. Initialize the in-process RAG retriever from src.phases.enhancement.rag
        #   3. Mount the FastAPI app from src.phases.implementation.api + web
        #   4. Start uvicorn on the configured port
        #   5. Write the live URL into the report
        report.status = "completed"
        report.ended_at = datetime.now()
        report.notes.append("TODO: Phase 4 runner stub")
        return report

    def summary(self) -> str:
        return "Phase 4 - Implementation: stub"
''',

    "src/phases/implementation/api.py": '''"""Phase 4 REST API endpoints.

Routes:
  POST /v1/evaluate     - (prompt, candidate_response) -> EvaluationResult
  POST /v1/classify     - text -> {sector, corridor, ilo_indicators, attack_category}
  POST /v1/anonymize    - text -> {redacted_text, spans, actions}
  POST /v1/extract_facts - text -> list[Fact]
  GET  /v1/healthz      - model version, uptime
  GET  /docs            - OpenAPI spec (auto)

TODO: implement. See docs/project_phases.md Phase 4.2a.
"""
''',

    "src/phases/implementation/web.py": '''"""Phase 4 demo web UI.

Pages:
  /          - landing with large text box and 4 output panels
  /examples  - curated scenario gallery
  /compare   - side-by-side stock Gemma vs. enhanced Gemma (killer demo)
  /about     - writeup / video / HF Hub / submission links

TODO: implement. See docs/project_phases.md Phase 4.2b.
"""
''',

    "src/phases/implementation/compare.py": '''"""The /compare page logic.

Loads both stock Gemma 4 E4B and the Phase 3 fine-tuned variant, runs
both on the same input, returns a side-by-side EvaluationResult pair.
This is the visual centerpiece of the hackathon video.

TODO: implement. See docs/project_phases.md Phase 4.2b.
"""
''',

    "src/phases/implementation/monitors/__init__.py": '''"""Optional social-media and chat monitors (P1/P2 stretch)."""
''',

    "src/phases/implementation/monitors/reddit.py": '''"""Reddit post monitor (P1 stretch).

Polls configured subreddits via PRAW, scores posts using the live API,
writes structured alerts to a dashboard. Read-only, alerting-only, never
auto-acts. See docs/project_phases.md Phase 4.2c.

TODO: implement.
"""
''',

    "src/phases/implementation/monitors/discord.py": '''"""Discord chat monitor (P2 stretch).

Opt-in bot that lurks in invited channels, flags grooming / recruitment
patterns to the channel moderator. Never responds publicly. See
docs/project_phases.md Phase 4.2d.

TODO: implement.
"""
''',


    # =======================================================================
    # Config stubs
    # =======================================================================

    "configs/phases/exploration.yaml": '''# Phase 1 - Exploration configuration
# See docs/project_phases.md Phase 1

phase_id: exploration

models:
  - id: gemma_4_e2b
    display_name: "Gemma 4 E2B (stock)"
    provider: transformers
    model_id: google/gemma-4-e2b-it
  - id: gemma_4_e4b
    display_name: "Gemma 4 E4B (stock)"
    provider: transformers
    model_id: google/gemma-4-e4b-it

test_suites:
  - name: public_benchmark_21k
    path: _reference/trafficking-llm-benchmark-gitlab
  - name: legacy_kaggle_red_team
    path: _reference/trafficking_llm_benchmark/legacy_kaggle_tests/my_red_team_tests.json

capability_tests:
  - response_policy_guardrails
  - anonymization
  - document_classification
  - key_fact_extraction

sampling:
  smoke_test_size: 100  # start here before the full 21K run
  full_size: null       # null = run everything

output:
  reports_dir: reports/phase1
  data_dir: data/phase1
''',

    "configs/phases/comparison.yaml": '''# Phase 2 - Comparison configuration
# See docs/project_phases.md Phase 2

phase_id: comparison

# Model list is in src/phases/comparison/model_list.py (code, not config).
# This file just enables/disables tiers and sets budgets.

enabled_tiers:
  local_open: true       # Gemma, GPT-OSS, Qwen, Llama
  api_open: true         # Mistral, DeepSeek
  api_closed_reference: true  # GPT-4o-mini, Claude Haiku (reference only)

budgets:
  max_api_spend_usd: 200
  max_hours_total: 24

capability_tests:
  - response_policy_guardrails
  - anonymization
  - document_classification
  - key_fact_extraction

output:
  reports_dir: reports/phase2
  data_dir: data/phase2
  publish_kaggle_dataset: true
''',

    "configs/phases/enhancement.yaml": '''# Phase 3 - Enhancement configuration
# See docs/project_phases.md Phase 3

phase_id: enhancement

base_model: unsloth/gemma-4-e4b-bnb-4bit

rag:
  enabled: true
  embedding_model: sentence-transformers/all-mpnet-base-v2
  chunk_strategy: fact_object
  top_k: 5
  fact_sources:
    - _reference/framework/src/scraper/seeds
    # add ILO / IOM documentation bundles here when available

finetune:
  enabled: true
  framework: unsloth
  max_seq_length: 4096
  load_in_4bit: true
  lora_r: 16
  lora_alpha: 32
  lora_dropout: 0.0
  lora_target_modules:
    - q_proj
    - k_proj
    - v_proj
    - o_proj
    - gate_proj
    - up_proj
    - down_proj
  per_device_train_batch_size: 2
  gradient_accumulation_steps: 4
  learning_rate: 2.0e-4
  num_train_epochs: 2
  warmup_ratio: 0.03
  lr_scheduler_type: cosine
  weight_decay: 0.01
  optim: adamw_8bit
  seed: 3407

ablation:
  configs:
    - id: A_stock
      rag: false
      finetune: false
    - id: B_rag_only
      rag: true
      finetune: false
    - id: C_finetune_only
      rag: false
      finetune: true
    - id: D_hybrid
      rag: true
      finetune: true

export:
  gguf_quantizations:
    - q4_k_m
    - q5_k_m
    - q8_0
  publish_to_hf_hub: true
  hf_repo: taylorsamarel/gemma-4-e4b-safetyjudge-v0.1

output:
  reports_dir: reports/phase3
  data_dir: data/phase3
  models_dir: models/gemma-4-e4b-safetyjudge-v0.1
''',

    "configs/phases/implementation.yaml": '''# Phase 4 - Implementation configuration
# See docs/project_phases.md Phase 4

phase_id: implementation

model:
  # Paths are resolved relative to models_dir; picks one quantization at boot.
  gguf_path: models/gemma-4-e4b-safetyjudge-v0.1/gguf/q5_k_m.gguf
  context_length: 4096
  n_gpu_layers: 0  # CPU by default, so it runs anywhere

server:
  host: 0.0.0.0
  port: 8080
  workers: 1

rate_limit:
  per_ip_per_minute: 10
  max_input_chars: 4000

abuse_mitigations:
  topic_classifier_enabled: true
  reject_off_topic: true
  research_demo_disclaimer: true

endpoints:
  evaluate: true
  classify: true
  anonymize: true
  extract_facts: true
  examples_gallery: true
  compare_page: true  # stock-vs-enhanced comparison
  about_page: true

monitors:
  reddit:
    enabled: false  # flip to true in week 4 if time permits
    subreddits:
      - r/migrantworkers  # example
      - r/humanrights     # example
    poll_interval_seconds: 300
  discord:
    enabled: false  # P2 stretch

output:
  reports_dir: reports/phase4
''',
}


def main() -> int:
    created = 0
    skipped = 0
    for rel, content in FILES.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists():
            print(f"SKIP   {rel}")
            skipped += 1
            continue
        p.write_text(content, encoding="utf-8")
        print(f"CREATE {rel}")
        created += 1
    print()
    print(f"Created: {created}")
    print(f"Skipped: {skipped}")
    print(f"Total:   {len(FILES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
