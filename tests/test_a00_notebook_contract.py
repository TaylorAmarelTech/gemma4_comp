from __future__ import annotations

import json
import py_compile
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
A00 = ROOT / "kaggle" / "A-00-omni-experiment-workbench" / "kernel.py"
A00_README = ROOT / "kaggle" / "A-00-omni-experiment-workbench" / "README.md"
A00_METADATA = ROOT / "kaggle" / "A-00-omni-experiment-workbench" / "kernel-metadata.json"
TRAINING_DATA_TEMPLATE = ROOT / "kaggle" / "shared-datasets" / "training-data"


def test_a00_compiles():
    py_compile.compile(str(A00), doraise=True)


def test_a00_training_path_enforces_shared_contract_and_sft_then_dpo():
    text = A00.read_text(encoding="utf-8")
    assert "from duecare.chat.training_contract import (" in text
    assert "validate_training_rows(" in text
    assert "training data failed blocking gates" in text
    assert 'manifest.get("safe_to_train") is not True' in text
    assert '"heldout_prompt_sha256"' in text
    assert '"heldout_lineage_ids"' in text
    assert "evaluation_lineage_ids=heldout_lineage_ids" in text
    assert '"artifact_sha256"' in text
    assert "A00_PINNED_MODEL_REVISIONS" in text
    assert "provide an immutable base_model_revision" in text
    assert "pin_adapter_revision(OUTPUT_DIR)" in text
    assert "from trl import DPOConfig, DPOTrainer" in text
    assert 'if "dpo" in METHOD:' in text
    assert '"executed_stages": executed_stages' in text
    assert "training_completion_manifest.json" in text
    assert "hidden model chain-of-thought" in text
    assert "is neither requested nor stored" in text


def test_a00_public_version_and_external_import_boundaries_are_documented():
    text = " ".join(A00_README.read_text(encoding="utf-8").split())
    for marker in [
        "kernel version `14`",
        "2026-07-14",
        "reports a terminal execution status",
        "taylorsamarel/duecare-proof-finetuning-data",
        "24 SFT rows, 24 preference rows, 4 validation rows, and 4 test rows",
        "not the full 78k+ prompt corpus",
        "External importer is intake, not approval",
        "A loose JSONL may be inspected",
        "deliberately authored visible rationales",
        "hidden chain-of-thought is not an import target",
        "never sets `safe_to_train` on its own",
    ]:
        assert marker in text

    metadata = json.loads(A00_METADATA.read_text(encoding="utf-8"))
    assert metadata["dataset_sources"] == ["taylorsamarel/duecare-proof-finetuning-data"]


def test_training_dataset_surface_is_template_only_and_not_publishable():
    readme = TRAINING_DATA_TEMPLATE / "README.md"
    metadata_template = TRAINING_DATA_TEMPLATE / "dataset-metadata.template.json"
    assert readme.is_file()
    assert metadata_template.is_file()
    assert not (TRAINING_DATA_TEMPLATE / "dataset-metadata.json").exists()

    payload_files = [
        path
        for path in TRAINING_DATA_TEMPLATE.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jsonl", ".csv", ".parquet", ".arrow"}
    ]
    assert payload_files == []

    metadata = json.loads(metadata_template.read_text(encoding="utf-8"))
    assert metadata["_template_status"] == "documentation-only-not-publishable"
    assert metadata["id"].startswith("REPLACE_")
    assert metadata["licenses"][0]["name"].startswith("REPLACE_")

    text = " ".join(readme.read_text(encoding="utf-8").split())
    for marker in [
        "documentation-only and not publishable",
        "intentionally uses `dataset-metadata.template.json`",
        "instead of Kaggle's active",
        "External import contract",
        "deliberately authored model-visible rationales",
        "hidden chain-of-thought must not be requested",
        "never sets `safe_to_train` by itself",
    ]:
        assert marker in text


def test_a00_retains_archived_appendix_workflow_registry():
    text = A00.read_text(encoding="utf-8")
    workflow_ids = set(re.findall(r'"(a\d{2}_[a-z0-9_]+)": \{', text))
    assert len(workflow_ids) == 25
    for slot in range(1, 25):
        assert any(w.startswith(f"a{slot:02d}_") for w in workflow_ids)


def test_a00_core_routes_are_registered():
    text = A00.read_text(encoding="utf-8")
    for route in [
        "/api/a00/model/load",
        "/api/a00/run-batch",
        "/api/a00/import-export",
        "/api/a00/report",
        "/api/a00/synthetic/generate",
        "/api/a00/train",
        "/api/a00/workflows/run",
        "/api/a00/research/upload",
    ]:
        assert route in text


def test_a00_has_judge_facing_quick_proof_and_research_flow():
    text = A00.read_text(encoding="utf-8")
    for marker in [
        "Preconfigured Harness, Training, and Evaluation",
        "Custom",
        "runPreconfiguredPipeline",
        "preconfig-progress",
        "Evidence exports",
        "evidence-links",
        "Download evidence ZIP",
        "Open HTML report",
        "Judge model",
        "Ollama Cloud gpt-oss 20B judge",
        "OLLAMA_API_KEY",
        "OpenRouter OpenAI-compatible judge",
        "OPENROUTER_API_KEY",
        "openrouter",
        "GitHub Models judge",
        "GITHUB_MODELS_TOKEN",
        "github_models",
        "Groq judge",
        "GROQ_API_KEY",
        "groq",
        "Cerebras judge",
        "CEREBRAS_API_KEY",
        "cerebras",
        "Hugging Face Router judge",
        "HF_TOKEN",
        "huggingface",
        "OpenCode Zen judge",
        "OPENCODE_API_KEY",
        "opencode_zen",
        "Upstage judge",
        "UPSTAGE_API_KEY",
        "upstage",
        "SambaNova judge",
        "SAMBANOVA_API_KEY",
        "sambanova",
        "NVIDIA NIM judge",
        "NVIDIA_API_KEY",
        "nvidia",
        "LLM7 judge",
        "LLM7_API_KEY",
        "llm7",
        "openai_compatible",
        "RapidAPI chat-completions judge",
        "RAPIDAPI_CHAT_KEY",
        "rapidapi_chat",
        "RapidAPI text-generation judge",
        "RAPIDAPI_KEY",
        "rapidapi_text",
        "Claude Opus 4.7 judge",
        "Claude Opus 4.6 judge",
        "ANTHROPIC_API_KEY",
        "anthropic",
        "ollama_cloud",
        'id="preconfig-limit" type="number" min="1" max="50" value="4"',
        "Download visible Activity",
        "downloadVisibleActivityLog",
        "Download activity ZIP",
        "Activity Markdown",
        "A00_OUTPUTS_README.md",
        "A00_LATEST_OUTPUTS.json",
        "latest_report_evidence_bundle.zip",
        "latest_activity_bundle.zip",
        "Resume checkpoint",
        "Save every N steps",
        "resume_from_checkpoint",
        "training_resume_from_checkpoint",
        "checkpointing",
        "checkpoint_every",
        "a00.batch.checkpoint",
        'harness_profile: "chat_no_online"',
        'baseline_harness_profile: "none"',
        "judge_model_ref",
        "synthetic_count: synth",
        'generator_mode: "rubric_polisher"',
        "evaluate_outputs: true",
        "include_report: true",
        "execute_training: execute",
        "llm_judge: true",
        "grade_response_combined",
        "google/gemma-4-E2B-it",
        "Loading judge Gemma model for final evaluation",
        "Configuring Ollama judge for final evaluation",
        "Configuring Anthropic Claude judge for final evaluation",
        "Judging response",
        "Checking if any model is currently loaded",
        "Loading model with the shared Unsloth FastModel runtime",
        "model_prompt_sent_to_gemma",
        "prompt_response_pairs",
        "raw_prompt",
        "log_excerpt",
        "full_log_note",
        "Sending prompts to Gemma without the DueCare harness",
        "Sending prompts to Gemma with the DueCare harness",
        "Static settings used for this run",
        "Using Gemma 31B or a frontier model to draft and polish synthetic training rows may produce stronger training data",
        "A larger Gemma model or frontier model may produce stronger final grading",
        "Persona + GREP rules + RAG/context + deterministic tools",
        "Prompt -> Gemma-anonymized query -> search -> page markdown -> Gemma verification -> knowledge objects",
        "Combined rule-based score plus LLM judge",
        "Four-arm report: base, base+harness, fine-tuned, and fine-tuned+harness.",
        "precision bf16={{use_bf16}} fp16={{use_fp16}}",
        "Fine-tuning failed; review training log",
        "Benchmark, generate, fine-tune, compare.",
        "quickProof",
        "runRedteamProof",
        "anti_tip_redteam_regressions",
        "Local research graph",
        "PRIMARY_NOTEBOOK_AUDIT",
        "_ensure_sample_comparison_runs",
        "_extract_research_graph",
    ]:
        assert marker in text
    assert "Refresh status" not in text
    assert "teacher/base model" not in text
    assert "slice(0, 18000)" not in text
    assert "slice(-8)" not in text


def test_a00_has_synthetic_polish_and_training_smoke_path():
    text = A00.read_text(encoding="utf-8")
    for marker in [
        "RESPONSE_BLUEPRINT",
        "MEMORY_TOOL_POLICY",
        "rubric_polisher",
        "_polish_training_response",
        "generatePolished",
        "finetuneSmoke",
        "_install_model_training_stack",
    ]:
        assert marker in text


def test_a00_preconfigured_page_exposes_only_guided_controls():
    text = A00.read_text(encoding="utf-8")
    start = text.split('<div class="panel a00-choice a00-preconfigured preconfig-card"', 1)[1]
    preconfigured_card = start.split('<div class="panel a00-choice custom-card"', 1)[0]

    assert 'id="preconfig-model"' in preconfigured_card
    assert 'id="preconfig-limit"' in preconfigured_card
    assert 'id="preconfig-judge-model"' not in preconfigured_card
    assert "Judge model" not in preconfigured_card
    assert 'id="pipeline-judge-source"' in text
    assert 'id="pipeline-judge-ref"' in text


def test_a00_reports_dimension_level_evidence():
    text = A00.read_text(encoding="utf-8")
    for marker in [
        "Dimension-Level Evidence",
        "dimension_summary",
        "mean_score_0_10",
        "Mean dynamic weight",
        "Prompt, Output, And Judgment Appendix",
        "Static Report Charts",
        "prompt_response_csv",
        "score_chart_svg",
        "latency_chart_svg",
        "evidence_manifest",
        "evidence_zip",
        "writeup_ready_outputs",
        "WeasyPrint unavailable; wrote fallback PDF summary",
        "artifactLinksHtml",
        "updateEvidenceLinksFromObject",
        "jobArtifactLinks",
        "activityArtifactLinks",
        "Download evidence ZIP",
        "Download activity ZIP",
        "output_index",
    ]:
        assert marker in text
