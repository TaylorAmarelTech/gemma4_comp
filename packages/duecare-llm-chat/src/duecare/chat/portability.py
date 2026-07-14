"""Reusable workbench portability contract.

The Kaggle notebooks should agree on package version, endpoint surface,
sample artifacts, and knowledge-object coverage. This module keeps that
contract importable outside the large FastAPI app so focused notebooks can
verify compatibility without copying page-specific UI code.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from duecare.chat.experiment_contracts import experiment_contract_payload


REQUIRED_CHAT_VERSION = "0.17.0"
REQUIRED_KO_TYPES = 28
SELF_AUDIT_MINIMUM_COUNTS: dict[str, int] = {
    "n_grep_rules": 100,
    "n_rag_docs": 30,
    "n_dimensions": 20,
}

REQUIRED_APP_ENDPOINTS: tuple[str, ...] = (
    "/api/version",
    "/api/brand",
    "/api/health-check",
    "/api/harnesses",
    "/api/portability",
    "/api/experiment-contract",
    "/api/audit/workbench-inventory",
    "/api/knowledge/taxonomy",
    "/api/knowledge/type-catalog",
    "/api/knowledge/import",
    "/api/knowledge/export",
    "/api/process/batch/start",
    "/api/process/batch/status/{job_id}",
    "/api/process/graph-extract/start",
    "/api/process/graph-extract/status/{job_id}",
    "/api/search/sanitize",
    "/api/anonymize",
)

REQUIRED_SAMPLE_FILES: tuple[str, ...] = (
    "sample_manifest.json",
    "case_files_streamlined_demo.zip",
    "case_files_media_rich_sample.zip",
    "knowledge_files_sample.zip",
    "knowledge_source_examples_sample.zip",
    "search_intake_examples_sample.zip",
    "prompt_eval_training_seed_sample.zip",
)

WORKBENCH_DEFAULTS: dict[str, Any] = {
    "default_gemma_variant": "e4b-it",
    "gemma_max_seq_len": 32768,
    "streamlined_process_demo_bundle": "case_files_streamlined_demo.zip",
    "primary_source_bundle": "case_files_media_rich_sample.zip",
    "primary_knowledge_files": "knowledge_files_sample.zip",
    "primary_training_seed": "prompt_eval_training_seed_sample.zip",
    "default_processing_path": "start -> poll status -> inspect graph -> verify/edit -> ask/export",
    "default_rag_mode": "hybrid_when_embedder_available_bm25_fallback",
    "default_privacy_posture": "local_first_redact_before_share",
}

MODEL_VARIANT_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "id": "e2b-it",
        "label": "Gemma 4 E2B-it",
        "hf_id": "unsloth/gemma-4-E2B-it",
        "google_hf_id": "google/gemma-4-E2B-it",
        "runtime_size_b": 2.0,
        "runtime_size_gb": 2.0,
        "hardware": "single T4",
        "category": "on-device",
        "load_eta": "~20-30 sec",
        "fit": "fast text QA, deterministic harness review, small smoke tests",
        "caution": "weaker for exhaustive graph-edge generation and long multimodal evidence review",
    },
    {
        "id": "e4b-it",
        "label": "Gemma 4 E4B-it",
        "hf_id": "unsloth/gemma-4-E4B-it",
        "google_hf_id": "google/gemma-4-E4B-it",
        "runtime_size_b": 4.0,
        "runtime_size_gb": 4.0,
        "hardware": "single T4",
        "category": "on-device",
        "load_eta": "~30-60 sec",
        "fit": "default interactive demo, chat harness, compare, knowledge drafting",
        "caution": "use OCR/layout first for media-heavy case folders",
    },
    {
        "id": "26b-a4b-it",
        "label": "Gemma 4 26B-A4B-it",
        "hf_id": "unsloth/gemma-4-26B-A4B-it",
        "google_hf_id": "google/gemma-4-26b-a4b-it",
        "runtime_size_b": 26.0,
        "runtime_size_gb": 14.0,
        "hardware": "T4 x2 (4-bit)",
        "category": "on-device",
        "load_eta": "~6-15 min first run; ~3-5 min cached",
        "fit": "larger local review budgets, richer graph-edge proposals, stronger grading",
        "caution": "first load can be slow; use async processing and visible progress",
    },
    {
        "id": "31b-it",
        "label": "Gemma 4 31B-it",
        "hf_id": "unsloth/gemma-4-31B-it",
        "google_hf_id": "google/gemma-4-31b-it",
        "runtime_size_b": 31.0,
        "runtime_size_gb": 18.0,
        "hardware": "T4 x2 (4-bit)",
        "category": "on-device",
        "load_eta": "~15-25 min first run; ~5-8 min cached",
        "fit": "highest-quality local reasoning and multimodal/vision-adjacent workflows where supported",
        "caution": "requires careful GPU memory planning and may need cached weights",
    },
    {
        "id": "jailbroken-31b",
        "label": "Gemma 4 31B (abliterated)",
        "hf_id": "dealignai/Gemma-4-31B-JANG_4M-CRACK",
        "google_hf_id": "",
        "runtime_size_b": 31.0,
        "runtime_size_gb": 18.0,
        "hardware": "T4 x2 (4-bit)",
        "category": "jailbroken",
        "load_eta": "~15-25 min first run; repo quirks possible",
        "fit": "adversarial proof that the safety harness, not only base alignment, changes behavior",
        "caution": "use for controlled red-team demonstrations only",
    },
    {
        "id": "jailbroken-e4b",
        "label": "Gemma 4 E4B (abliterated)",
        "hf_id": "mlabonne/Gemma-4-E4B-it-abliterated",
        "google_hf_id": "",
        "runtime_size_b": 4.0,
        "runtime_size_gb": 4.0,
        "hardware": "single T4",
        "category": "jailbroken",
        "load_eta": "~30-60 sec",
        "fit": "fast adversarial proof path",
        "caution": "use for controlled red-team demonstrations only",
    },
    {
        "id": "cloud-gemini",
        "label": "Gemini API (cloud)",
        "hf_id": "",
        "google_hf_id": "",
        "runtime_size_b": 0.0,
        "runtime_size_gb": 0.0,
        "hardware": "no GPU",
        "category": "cloud",
        "load_eta": "instant",
        "fit": "optional BYOK comparison when local-only constraints are relaxed",
        "caution": "not used for raw case processing in the local-first demo path",
    },
    {
        "id": "cloud-openai",
        "label": "OpenAI-compatible API (cloud)",
        "hf_id": "",
        "google_hf_id": "",
        "runtime_size_b": 0.0,
        "runtime_size_gb": 0.0,
        "hardware": "no GPU",
        "category": "cloud",
        "load_eta": "instant",
        "fit": "optional BYOK comparison when local-only constraints are relaxed",
        "caution": "not used for raw case processing in the local-first demo path",
    },
    {
        "id": "cloud-ollama",
        "label": "Ollama (cloud/local)",
        "hf_id": "",
        "google_hf_id": "",
        "runtime_size_b": 0.0,
        "runtime_size_gb": 0.0,
        "hardware": "configured host",
        "category": "cloud",
        "load_eta": "instant",
        "fit": "local or hosted model adapter route",
        "caution": "quality depends on configured model",
    },
)

TRUST_BOUNDARY_TERMS: tuple[dict[str, str], ...] = (
    {
        "term": "source_case_bundle",
        "label": "Source case bundle",
        "meaning": "Uploaded evidence such as chats, PDFs, screenshots, receipts, scans, CSVs, or DOCX files for local processing.",
    },
    {
        "term": "knowledge_files",
        "label": "Knowledge files",
        "meaning": "Reviewed KnowledgeObject envelopes imported/exported as a ZIP; not raw case material.",
    },
    {
        "term": "redacted_submission",
        "label": "Redacted submission",
        "meaning": "Sanitized facts or knowledge proposals reviewed locally before any hub POST.",
    },
    {
        "term": "hub_aggregate",
        "label": "Hub aggregate",
        "meaning": "Anonymized, k-safe, non-PII trend or fact intended for server-side review and sharing.",
    },
)

PROCESS_PHASES: tuple[dict[str, str], ...] = (
    {"id": "upload", "label": "Upload", "owner": "browser", "done_when": "file bytes accepted"},
    {"id": "stage", "label": "Stage in kernel", "owner": "kernel", "done_when": "source bundle copied to local working directory"},
    {"id": "inventory", "label": "Inventory files", "owner": "process harness", "done_when": "folder, file, extension, and parent document records exist"},
    {"id": "parse", "label": "Parse and chunk", "owner": "process harness", "done_when": "text chunks, PDF pages, and media work items are queued"},
    {"id": "ocr_layout", "label": "OCR and layout", "owner": "local OCR/layout backend", "done_when": "OCR text, page items, and bbox candidates are attached or marked unavailable"},
    {"id": "deterministic_extract", "label": "Deterministic extraction", "owner": "GREP/entity pipeline", "done_when": "rules, entities, payments, locations, dates, and journey points are linked"},
    {"id": "gemma_edges", "label": "Gemma edge pass", "owner": "Gemma 4", "done_when": "model-proposed typed edges are reviewed or marked fallback"},
    {"id": "review", "label": "Reviewer verification", "owner": "user", "done_when": "reviewer confirms, edits, exports, or promotes findings"},
)

GRAPH_EDGE_CONTRACT: dict[str, Any] = {
    "schema_version": "duecare.graph_edge.v1",
    "required_fields": [
        "edge_id",
        "source_node",
        "target_node",
        "relation_type",
        "source_file",
        "extractors",
        "confidence",
        "local_only",
    ],
    "recommended_fields": [
        "page",
        "chunk_id",
        "page_item_id",
        "bbox",
        "quote",
        "amount",
        "currency",
        "date",
        "journey_stage",
        "review_status",
    ],
    "extractor_values": [
        "filename",
        "folder_path",
        "csv_parser",
        "pdf_text",
        "ocr",
        "layout",
        "grep",
        "entity_regex",
        "gemma4_text",
        "gemma4_vision",
        "reviewer",
    ],
    "review_status_values": ["unreviewed", "confirmed", "edited", "rejected"],
}

KNOWLEDGE_IO_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "artifact_kind": "source_case_bundle",
        "filename_pattern": "*.zip | *.csv | *.jsonl | *.txt | *.pdf | images | office docs",
        "meaning": "Raw or synthetic evidence for local processing. Not imported as knowledge without review.",
        "primary_endpoint": "/api/process/batch/start",
    },
    {
        "artifact_kind": "knowledge_files",
        "filename_pattern": "knowledge_files.zip",
        "meaning": "ZIP of reviewed KnowledgeObject envelopes in <knowledge_object_type>/<id>.json paths.",
        "primary_endpoint": "/api/knowledge/import",
    },
    {
        "artifact_kind": "redacted_submission",
        "filename_pattern": "redacted_submission.json",
        "meaning": "Sanitized proposal for hub submission after local redaction and review.",
        "primary_endpoint": "/api/anonymize",
    },
)

PUBLIC_SETUP_LANES: tuple[str, ...] = (
    "Platform safety",
    "NGO & regulator",
    "Individual worker / mobile",
    "Researcher",
    "Anonymized knowledge sharing",
    "Developer / integration partner",
)

ONBOARDING_PATHS: tuple[dict[str, Any], ...] = (
    {
        "id": "kaggle_judge",
        "label": "Kaggle judge",
        "start_here": "Run kaggle/01-duecare-exploration-workbench, then open /static/getting-started.html and /static/process.html.",
        "portable_artifacts": [
            "case_files_media_rich_sample.zip",
            "knowledge_files_sample.zip",
            "process replay JSON",
            "comparison export",
        ],
        "local_boundary": "Raw sample bundles, model traces, and graph drafts stay in the Kaggle kernel unless exported.",
        "verification": "Run scripts/validate_main_kaggle_kernels.py and scripts/validate_public_surface.py before publishing.",
    },
    {
        "id": "ngo_regulator",
        "label": "NGO & regulator",
        "start_here": "Use Bulk File Review, Knowledge Extraction, Templates, and Anonymization & Sharing as a local case-review node.",
        "portable_artifacts": [
            "reviewed evidence graph",
            "redacted referral draft",
            "knowledge_files.zip",
            "redacted_submission.json",
        ],
        "local_boundary": "Case files, worker names, contacts, and unreviewed notes remain local to the office or regulator.",
        "verification": "Confirm Step 3 review gates before templates, graph questions, or hub submission.",
    },
    {
        "id": "worker_mobile",
        "label": "Individual worker / mobile",
        "start_here": "Use a local or mobile instance for private answers, saved notes, and plain-language evidence preparation.",
        "portable_artifacts": [
            "private note export",
            "worker-support answer",
            "NGO intake draft",
        ],
        "local_boundary": "Personal history and device-held notes are never network submissions by default.",
        "verification": "Prefer locally versioned knowledge objects for law, fee, and contact claims.",
    },
    {
        "id": "researcher",
        "label": "Researcher",
        "start_here": "Import reviewed knowledge packs, run Search Safety, and produce aggregate corridor or risk-signal reports.",
        "portable_artifacts": [
            "aggregate signal table",
            "public-source knowledge proposal",
            "benchmark row",
            "graph export",
        ],
        "local_boundary": "Only de-identified facts, counts, and public-source references leave the research workspace.",
        "verification": "Keep row-level provenance, source URLs, hashes, and review status on every exported object.",
    },
    {
        "id": "developer_integrator",
        "label": "Developer / integration partner",
        "start_here": "Install duecare-llm-chat, call /api/portability, and reuse the shared chrome, model service, and harness contracts.",
        "portable_artifacts": [
            "portability contract JSON",
            "type catalog",
            "sample manifest",
            "API route inventory",
        ],
        "local_boundary": "Integrations should keep tenant data inside the tenant-owned review environment unless a redaction gate sends a submission.",
        "verification": "Run pytest collection, focused chat tests, and the public-surface validator after route or UI changes.",
    },
    {
        "id": "benchmark_user",
        "label": "Benchmark user",
        "start_here": "Use kaggle/03-universal-llm-benchmark or kaggle/04-kaggle-community-benchmark for optional proof runs.",
        "portable_artifacts": [
            "benchmark prompts",
            "judge rubric",
            "model comparison table",
            "benchmark_rows",
        ],
        "local_boundary": "Benchmark rows should be synthetic, public-source, or anonymized; raw case files are not benchmark inputs.",
        "verification": "Record model, harness profile, dataset version, grader version, and git SHA with every result.",
    },
)

LOCAL_NODE_NETWORK_CONTRACT: dict[str, Any] = {
    "schema_version": "duecare.local_node_network.v1",
    "purpose": (
        "Let many independent local nodes convert sensitive case material into "
        "reviewed, anonymized intelligence without centralizing raw worker files."
    ),
    "local_inputs": [
        "source_case_bundle",
        "folder_hierarchy",
        "document_pages",
        "paragraph_chunks",
        "tables",
        "media_assets",
        "caseworker_notes",
    ],
    "shareable_outputs": [
        "anonymized_fact_objects",
        "graph_edges",
        "risk_signal_counts",
        "benchmark_rows",
        "knowledge_pack_updates",
    ],
    "never_share": [
        "raw_pii",
        "worker_contact_details",
        "unredacted_documents",
        "private caseworker_notes",
        "unreviewed_model_drafts",
    ],
    "review_gates": [
        "process_review_confirmation",
        "knowledge_object_promotion",
        "regex_redaction",
        "optional_gemma_residual_pii_review",
        "literal_submit_confirmation",
    ],
    "aggregation_value": (
        "Repeated anonymized fact objects and evidence edges expose corridor, "
        "fee, document-control, and coercion patterns that a single local "
        "office cannot see alone."
    ),
}

CORE_NOTEBOOKS: tuple[dict[str, str], ...] = (
    {
        "id": "01",
        "path": "kaggle/01-duecare-exploration-workbench",
        "status": "active",
        "role": "full workbench and portability source of truth",
        "serves": "all harnesses, samples, taxonomy, inventory, and UI audit",
    },
    {
        "id": "02",
        "path": "kaggle/02-live-demo",
        "status": "active",
        "role": "focused live product demonstration",
        "serves": "scripted but live Gemma 4 interaction over the same contract",
    },
    {
        "id": "03",
        "path": "kaggle/03-universal-llm-benchmark",
        "status": "optional",
        "role": "optional universal LLM benchmark",
        "serves": "external API benchmarking with DueCare prompts and judge rubrics",
    },
    {
        "id": "04",
        "path": "kaggle/04-kaggle-community-benchmark",
        "status": "optional",
        "role": "optional Kaggle community benchmark",
        "serves": "community benchmark tasks that can use Kaggle model proxy quota",
    },
)

REUSABLE_PRIMITIVES: tuple[dict[str, str], ...] = (
    {
        "id": "workbench_inventory",
        "label": "Workbench inventory endpoint",
        "purpose": "Live pages, harnesses, sample assets, import/export routes, and taxonomy counts.",
    },
    {
        "id": "knowledge_type_catalog",
        "label": "Knowledge type catalog",
        "purpose": "Canonical purpose, keys, subtype fields, and examples for every knowledge leaf.",
    },
    {
        "id": "sample_manifest",
        "label": "Sample manifest",
        "purpose": "Names source case bundles, knowledge files, search examples, and training/eval seeds.",
    },
    {
        "id": "harness_surface_contracts",
        "label": "Harness surface contracts",
        "purpose": "Declares each harness' inputs, outputs, routes, model role, and examples.",
    },
    {
        "id": "async_job_contract",
        "label": "Async job contract",
        "purpose": "Uses start/status polling for large local uploads so Cloudflare timeouts do not hide progress.",
    },
    {
        "id": "graph_edge_schema",
        "label": "Graph edge schema",
        "purpose": "Keeps edges tied to file, page/chunk, extractor, confidence, quote/bbox, and local-only provenance.",
    },
    {
        "id": "model_fit_profile",
        "label": "Model fit profile",
        "purpose": "Explains which Gemma variants are suitable for text, OCR-assisted media, vision, grading, and graph edges.",
    },
    {
        "id": "trust_boundary_vocabulary",
        "label": "Trust-boundary vocabulary",
        "purpose": "Separates source case bundles, knowledge files, redacted submissions, and hub-bound aggregate facts.",
    },
    {
        "id": "activity_log",
        "label": "Activity log primitive",
        "purpose": "Shows API calls, phases, errors, and exports consistently at the bottom of workflow pages.",
    },
    {
        "id": "knowledge_envelope_io",
        "label": "Import/export envelope contract",
        "purpose": "Knowledge files are ZIPs of reviewed KnowledgeObject envelopes plus README/metadata.",
    },
)

NOTEBOOK_REUSE_TARGETS: tuple[dict[str, str], ...] = (
    {
        "notebook": "02-live-demo",
        "reuse": "Call live inventory/type-catalog endpoints and reuse the media-rich PH-HK sample story.",
    },
    {
        "notebook": "03-universal-llm-benchmark",
        "reuse": "Consume prompts, harness profiles, judge rubrics, and graph-edge schema for optional external API comparisons.",
    },
    {
        "notebook": "04-kaggle-community-benchmark",
        "reuse": "Reuse synthetic or anonymized benchmark rows while keeping raw case bundles out of benchmark inputs.",
    },
    {
        "notebook": "archived A-series notebooks",
        "reuse": "Keep prior A-00 and appendix experiments in kaggle/_archive for provenance, not active judging validation.",
    },
    {
        "notebook": "archived appendix kernels",
        "reuse": "Keep prior experimental slices in kaggle/_archive/notebooks for reference, not active submission validation.",
    },
)


def version_key(version: str) -> tuple[int, int, int]:
    """Return a sortable three-part version tuple."""
    parts: list[int] = []
    for token in (version or "").replace("-", ".").split("."):
        digits = "".join(ch for ch in token if ch.isdigit())
        if digits:
            parts.append(int(digits))
        if len(parts) == 3:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def default_samples_root() -> Path:
    return Path(__file__).resolve().parent / "static" / "samples"


def model_variant_map() -> dict[str, dict[str, Any]]:
    return {str(item["id"]): dict(item) for item in MODEL_VARIANT_PROFILES}


def model_variant_ui_map() -> dict[str, dict[str, Any]]:
    return {
        key: {
            "display": value["label"],
            "size_gb": value["runtime_size_gb"],
            "fits": value["hardware"],
            "category": value["category"],
            "load_eta": value["load_eta"],
        }
        for key, value in model_variant_map().items()
    }


def sample_artifact_map() -> dict[str, str]:
    return {
        "primary_source_bundle": WORKBENCH_DEFAULTS["primary_source_bundle"],
        "primary_knowledge_files": WORKBENCH_DEFAULTS["primary_knowledge_files"],
        "primary_training_seed": WORKBENCH_DEFAULTS["primary_training_seed"],
        "knowledge_source_examples": "knowledge_source_examples_sample.zip",
        "search_intake_examples": "search_intake_examples_sample.zip",
    }


def notebook_role_map() -> dict[str, dict[str, str]]:
    return {item["id"]: dict(item) for item in CORE_NOTEBOOKS}


def onboarding_path_map() -> dict[str, dict[str, Any]]:
    return {item["id"]: dict(item) for item in ONBOARDING_PATHS}


def local_node_network_contract() -> dict[str, Any]:
    return dict(LOCAL_NODE_NETWORK_CONTRACT)


def evaluate_portability_contract(
    *,
    route_paths: Iterable[str] = (),
    ko_types_count: int = 0,
    ko_catalog_count: int = 0,
    samples_root: Path | None = None,
) -> dict[str, Any]:
    """Evaluate route, taxonomy, catalog, and sample coverage."""
    route_path_set = set(route_paths)
    root = samples_root or default_samples_root()
    missing_routes = [
        path for path in REQUIRED_APP_ENDPOINTS if path not in route_path_set
    ]
    missing_samples = [
        name for name in REQUIRED_SAMPLE_FILES if not (root / name).is_file()
    ]
    failures: list[str] = []
    if missing_routes:
        failures.append("missing routes: " + ", ".join(missing_routes))
    if ko_types_count < REQUIRED_KO_TYPES:
        failures.append(f"knowledge types {ko_types_count} < required {REQUIRED_KO_TYPES}")
    if ko_catalog_count < REQUIRED_KO_TYPES:
        failures.append(f"type catalog {ko_catalog_count} < required {REQUIRED_KO_TYPES}")
    if missing_samples:
        failures.append("missing samples: " + ", ".join(missing_samples))
    return {
        "ok": not failures,
        "failures": failures,
        "counts": {
            "required_routes": len(REQUIRED_APP_ENDPOINTS),
            "served_routes": len(route_path_set),
            "required_knowledge_types": REQUIRED_KO_TYPES,
            "knowledge_types": ko_types_count,
            "knowledge_types_with_catalog": ko_catalog_count,
            "required_samples": len(REQUIRED_SAMPLE_FILES),
            "missing_samples": len(missing_samples),
        },
        "missing_routes": missing_routes,
        "missing_samples": missing_samples,
    }


def portability_contract_payload(
    *,
    route_paths: Iterable[str] = (),
    ko_types_count: int = 0,
    ko_catalog_count: int = 0,
    samples_root: Path | None = None,
) -> dict[str, Any]:
    """Return the machine-readable portability contract and current status."""
    evaluation = evaluate_portability_contract(
        route_paths=route_paths,
        ko_types_count=ko_types_count,
        ko_catalog_count=ko_catalog_count,
        samples_root=samples_root,
    )
    return {
        "schema_version": "duecare.portability_contract.v1",
        "required_chat_version": REQUIRED_CHAT_VERSION,
        "required_knowledge_types": REQUIRED_KO_TYPES,
        "self_audit_minimum_counts": dict(SELF_AUDIT_MINIMUM_COUNTS),
        "required_endpoints": list(REQUIRED_APP_ENDPOINTS),
        "required_sample_files": list(REQUIRED_SAMPLE_FILES),
        "workbench_defaults": dict(WORKBENCH_DEFAULTS),
        "model_variant_profiles": list(MODEL_VARIANT_PROFILES),
        "trust_boundary_terms": list(TRUST_BOUNDARY_TERMS),
        "process_phases": list(PROCESS_PHASES),
        "graph_edge_contract": dict(GRAPH_EDGE_CONTRACT),
        "knowledge_io_contracts": list(KNOWLEDGE_IO_CONTRACTS),
        "public_setup_lanes": list(PUBLIC_SETUP_LANES),
        "onboarding_paths": list(ONBOARDING_PATHS),
        "local_node_network_contract": dict(LOCAL_NODE_NETWORK_CONTRACT),
        "quantitative_experiment_contract": experiment_contract_payload(),
        "core_notebooks": list(CORE_NOTEBOOKS),
        "reusable_primitives": list(REUSABLE_PRIMITIVES),
        "notebook_reuse_targets": list(NOTEBOOK_REUSE_TARGETS),
        "evaluation": evaluation,
    }


def reference_portability_contract_payload() -> dict[str, Any]:
    """Return the expected full-workbench contract without needing an app."""
    return portability_contract_payload(
        route_paths=REQUIRED_APP_ENDPOINTS,
        ko_types_count=REQUIRED_KO_TYPES,
        ko_catalog_count=REQUIRED_KO_TYPES,
    )


def verify_app_contract(
    app: Any,
    *,
    ko_types_count: int = 0,
    ko_catalog_count: int = 0,
    samples_root: Path | None = None,
) -> dict[str, Any]:
    """Evaluate a FastAPI app's route table against the reusable contract."""
    route_paths = {getattr(route, "path", "") for route in getattr(app, "routes", [])}
    return portability_contract_payload(
        route_paths=route_paths,
        ko_types_count=ko_types_count,
        ko_catalog_count=ko_catalog_count,
        samples_root=samples_root,
    )
