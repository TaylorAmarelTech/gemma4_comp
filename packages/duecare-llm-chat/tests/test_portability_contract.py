from __future__ import annotations


def test_portability_contract_module_evaluates_current_app():
    from duecare.chat.app import KO_TYPE_CATALOG, KO_TYPES, create_app
    from duecare.chat.portability import (
        REQUIRED_APP_ENDPOINTS,
        REQUIRED_CHAT_VERSION,
        REQUIRED_KO_TYPES,
        REQUIRED_SAMPLE_FILES,
        portability_contract_payload,
        reference_portability_contract_payload,
        verify_app_contract,
        version_key,
    )

    assert version_key("0.17.0") >= version_key(REQUIRED_CHAT_VERSION)
    assert len(KO_TYPES) >= REQUIRED_KO_TYPES
    assert len(KO_TYPE_CATALOG) >= REQUIRED_KO_TYPES
    assert "/api/audit/workbench-inventory" in REQUIRED_APP_ENDPOINTS
    assert "/api/portability" in REQUIRED_APP_ENDPOINTS
    assert "/api/experiment-contract" in REQUIRED_APP_ENDPOINTS
    assert "/api/knowledge/type-catalog" in REQUIRED_APP_ENDPOINTS
    assert "case_files_media_rich_sample.zip" in REQUIRED_SAMPLE_FILES

    reference = reference_portability_contract_payload()
    assert reference["evaluation"]["ok"] is True
    assert reference["self_audit_minimum_counts"]["n_grep_rules"] == 100
    assert reference["workbench_defaults"]["gemma_max_seq_len"] == 32768
    assert reference["workbench_defaults"]["primary_source_bundle"] == "case_files_media_rich_sample.zip"
    assert {term["term"] for term in reference["trust_boundary_terms"]}.issuperset(
        {"source_case_bundle", "knowledge_files", "redacted_submission", "hub_aggregate"}
    )
    assert {profile["id"] for profile in reference["model_variant_profiles"]}.issuperset(
        {"e2b-it", "e4b-it", "26b-a4b-it", "31b-it", "jailbroken-e4b"}
    )
    assert {phase["id"] for phase in reference["process_phases"]}.issuperset(
        {"upload", "inventory", "ocr_layout", "gemma_edges", "review"}
    )
    edge_contract = reference["graph_edge_contract"]
    assert edge_contract["schema_version"] == "duecare.graph_edge.v1"
    assert {"source_file", "extractors", "confidence", "local_only"}.issubset(
        set(edge_contract["required_fields"])
    )
    assert {item["artifact_kind"] for item in reference["knowledge_io_contracts"]}.issuperset(
        {"source_case_bundle", "knowledge_files", "redacted_submission"}
    )
    assert reference["public_setup_lanes"] == [
        "Platform safety",
        "NGO & regulator",
        "Individual worker / mobile",
        "Researcher",
        "Anonymized knowledge sharing",
        "Developer / integration partner",
    ]
    assert {item["id"] for item in reference["onboarding_paths"]} == {
        "kaggle_judge",
        "ngo_regulator",
        "worker_mobile",
        "researcher",
        "developer_integrator",
        "benchmark_user",
    }
    network = reference["local_node_network_contract"]
    assert network["schema_version"] == "duecare.local_node_network.v1"
    assert set(network["shareable_outputs"]).issuperset(
        {"anonymized_fact_objects", "graph_edges", "risk_signal_counts"}
    )
    assert "raw_pii" in network["never_share"]
    experiment = reference["quantitative_experiment_contract"]
    assert experiment["schema_version"] == "duecare.experiment_contract.v1"
    assert experiment["quantitative_run_profiles"]["bulk_text_25"]["limit"] == 25
    assert experiment["training_profiles"]["tiny_lora_smoke"]["max_steps"] == 60
    assert {
        arm["id"]
        for arm in experiment["comparison_matrices"]["stock_vs_finetuned_harness_matrix"]["arms"]
    } == {"stock", "stock_harness", "finetuned", "finetuned_harness"}
    assert {item["id"] for item in reference["core_notebooks"]} == {"01", "02", "03", "04"}

    app = create_app()
    payload = verify_app_contract(
        app,
        ko_types_count=len(KO_TYPES),
        ko_catalog_count=len(KO_TYPE_CATALOG),
    )
    assert payload["schema_version"] == "duecare.portability_contract.v1"
    assert payload["evaluation"]["ok"] is True
    assert payload["evaluation"]["failures"] == []
    from fastapi.testclient import TestClient

    api_payload = TestClient(app).get("/api/portability")
    assert api_payload.status_code == 200
    assert api_payload.json()["evaluation"]["ok"] is True
    experiment_payload = TestClient(app).get("/api/experiment-contract")
    assert experiment_payload.status_code == 200
    assert experiment_payload.json()["schema_version"] == "duecare.experiment_contract.v1"

    route_paths = {getattr(route, "path", "") for route in app.routes}
    direct = portability_contract_payload(
        route_paths=route_paths,
        ko_types_count=len(KO_TYPES),
        ko_catalog_count=len(KO_TYPE_CATALOG),
    )
    assert direct["evaluation"]["missing_routes"] == []
    assert direct["evaluation"]["missing_samples"] == []
    assert {p["id"] for p in direct["reusable_primitives"]}.issuperset(
        {"graph_edge_schema", "async_job_contract", "activity_log"}
    )


def test_portability_model_and_sample_helpers_are_canonical():
    from duecare.chat.gemma4_runtime import resolve_model_ref, variant_from_ref
    from duecare.chat.portability import (
        model_variant_map,
        model_variant_ui_map,
        onboarding_path_map,
        notebook_role_map,
        sample_artifact_map,
    )

    models = model_variant_map()
    ui_models = model_variant_ui_map()
    assert models["e4b-it"]["google_hf_id"] == "google/gemma-4-4b-it"
    assert ui_models["e4b-it"]["display"] == "Gemma 4 E4B-it"
    assert ui_models["cloud-gemini"]["category"] == "cloud"
    assert variant_from_ref("google/gemma-4-E2B-it") == "e2b-it"
    resolved, variant, source = resolve_model_ref("hf", "google/gemma-4-E2B-it")
    assert resolved == "unsloth/gemma-4-E2B-it"
    assert variant == "e2b-it"
    assert source == "hf"

    from duecare.chat.runtime_chrome import runtime_model_topbar_html

    topbar = runtime_model_topbar_html(title="DueCare A-00")
    assert "_dc-runtime-topbar" in topbar
    assert "runtime-model-name" in topbar
    assert "runtime-model-select" in topbar
    assert "runtime-model-modal" in topbar
    assert "runtime-model-button" in topbar
    assert "_dc-shutdown-btn" in topbar
    a00_topbar = runtime_model_topbar_html(
        title="DueCare A-00",
        include_model_selector=False,
        include_custom_controls=False,
    )
    assert "_dc-runtime-topbar" in a00_topbar
    assert "runtime-model-name" in a00_topbar
    assert "_dc-shutdown-btn" in a00_topbar
    assert "runtime-model-select" not in a00_topbar
    assert "runtime-model-modal" not in a00_topbar
    assert "runtime-model-button" not in a00_topbar
    assert "Custom controls" not in a00_topbar

    samples = sample_artifact_map()
    assert samples["primary_source_bundle"] == "case_files_media_rich_sample.zip"
    assert samples["primary_knowledge_files"] == "knowledge_files_sample.zip"

    notebooks = notebook_role_map()
    assert notebooks["01"]["role"].startswith("full workbench")
    assert notebooks["01"]["status"] == "active"
    assert notebooks["03"]["status"] == "optional"
    assert notebooks["04"]["path"].endswith("04-kaggle-community-benchmark")

    onboarding = onboarding_path_map()
    assert onboarding["kaggle_judge"]["start_here"].startswith("Run kaggle/01")
    assert "knowledge_files.zip" in onboarding["ngo_regulator"]["portable_artifacts"]
    assert "benchmark_rows" in onboarding["benchmark_user"]["portable_artifacts"]


def test_portability_contract_reports_missing_routes_and_samples(tmp_path):
    from duecare.chat.portability import evaluate_portability_contract

    result = evaluate_portability_contract(
        route_paths=("/api/version",),
        ko_types_count=1,
        ko_catalog_count=1,
        samples_root=tmp_path,
    )
    assert result["ok"] is False
    assert "/api/knowledge/type-catalog" in result["missing_routes"]
    assert "case_files_media_rich_sample.zip" in result["missing_samples"]
    assert result["failures"]


def test_experiment_contract_helpers_are_canonical():
    from duecare.chat.experiment_contracts import (
        comparison_matrix_map,
        experiment_contract_payload,
        harness_profile_map,
        quantitative_run_profile_map,
        synthetic_generation_profile_map,
        training_profile_map,
        upload_limit_map,
    )

    profiles = harness_profile_map()
    assert profiles["chat_full"]["layers"] == ["persona", "grep", "rag", "tools", "online"]
    assert profiles["none"]["layers"] == []

    runs = quantitative_run_profile_map()
    assert runs["bulk_text_25"]["baseline_harness"] == "none"
    assert runs["bulk_text_25"]["treatment_harness"] == "chat_no_online"
    assert runs["tiny_lora_smoke"]["synthetic_count"] == 24

    synthetic = synthetic_generation_profile_map()
    assert synthetic["rubric_polisher_24"]["generator_mode"] == "rubric_polisher"
    assert synthetic["rubric_polisher_24"]["harness_profile"] == "chat_no_online"

    training = training_profile_map()
    assert training["tiny_lora_smoke"]["base_model_ref"] == "google/gemma-4-E2B-it"
    assert training["a07_t4_standard_sft"]["max_examples"] == 200

    limits = upload_limit_map()
    assert limits["max_zip_bytes"] == 200_000_000

    matrix = comparison_matrix_map()["stock_vs_finetuned_harness_matrix"]
    assert [arm["id"] for arm in matrix["arms"]] == [
        "stock",
        "stock_harness",
        "finetuned",
        "finetuned_harness",
    ]

    payload = experiment_contract_payload()
    assert payload["generation_defaults"]["max_new_tokens"] == 1200
    assert "sft_jsonl" in payload["training_data_schemas"]
    assert "preference_jsonl" in payload["training_data_schemas"]
    assert {gate["id"] for gate in payload["training_quality_gates"]}.issuperset(
        {"pii_absent", "heldout_not_train", "citation_grounded"}
    )
    assert {item["id"] for item in payload["post_training_best_practices"]}.issuperset(
        {"start_with_sft", "prefer_dpo_before_full_rl", "preserve_harness_separation"}
    )
    assert "google_gemma_tuning" in payload["post_training_source_refs"]
