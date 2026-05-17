from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_harness_ecosystem_doc_enumerates_broad_harness_families():
    text = _read("docs/harness_ecosystem.md")
    required_phrases = [
        "Registered harness surfaces",
        "Broader harness families",
        "Content safety response harness",
        "Search anonymization harness",
        "Post-search verification harness",
        "Anonymization/deanonymization review harness",
        "Knowledge ingestion harness",
        "Civil-society fact intake harness",
        "Research graph harness",
        "Synthetic data generator harness",
        "Rubric-polish harness",
        "Fine-tuning harness",
        "Evaluation/judge harness",
        "Report/export harness",
        "Model runtime primitive",
    ]
    for phrase in required_phrases:
        assert phrase in text
    assert "`post_search_verification`" in text
    assert "Post-search verification harness | Search result to extraction/chat flow" not in text
    assert "Planned hardening." not in text


def test_public_copy_uses_harness_ecosystem_language():
    paths = [
        "apps/duecare-ai.com/app/templates/index.html",
        "apps/duecare-ai.com/app/templates/harness.html",
        "apps/duecare-ai.com/app/templates/mission.html",
        "apps/duecare-ai.com/app/templates/why-gemma.html",
        "packages/duecare-llm-server/src/duecare/server/static/index.html",
        "packages/duecare-llm-chat/src/duecare/chat/static/getting-started.html",
        "packages/duecare-llm-chat/src/duecare/chat/static/index.html",
    ]
    combined = "\n".join(_read(path) for path in paths).lower()
    assert "harness ecosystem" in combined
    assert "run the gemma 4 safety harness" not in combined
    assert "duecare is a gemma 4 safety harness" not in combined


def test_ecosystem_overview_no_longer_claims_one_harness():
    text = _read("docs/ecosystem_overview.md")
    assert "single content-safety harness" not in text
    assert "one harness, four user layers" not in text
    assert "harness ecosystem" in text


def test_legacy_notebook_era_docs_are_archived():
    archive = ROOT / "docs" / "_archive" / "2026-05-16-legacy-notebook-era"
    for name in [
        "notebook_index.md",
        "smoke_test_report_2026-05-02.md",
        "SUBMISSION_READINESS_AUDIT.md",
        "appendix_artifact_schema.md",
        "appendix_experiment_ladder.md",
        "bench_and_tune_readiness.md",
        "bench_and_tune_walkthrough.md",
        "data_compatibility_plan.md",
        "data_primitives.md",
        "data_surface_inventory.md",
        "notebook_qa_companion.md",
        "release_checklist_v0_14_5.md",
        "REPORT_CARD.md",
        "rubric_evaluation_v07.md",
        "submission_gate_checklist.md",
        "submission_surface_audit_2026-05-10.md",
        "004-six-plus-five-notebook-shape.md",
        "006-two-plus-eleven-notebook-shape.md",
    ]:
        assert not (ROOT / "docs" / name).exists(), name
        assert (archive / name).exists(), name
    assert (archive / "project_status.md").exists()


def test_current_kaggle_state_points_to_three_active_kernels():
    text = _read("docs/current_kaggle_notebook_state.md")
    assert "exactly three script kernels" in text
    assert "kaggle/01-duecare-exploration-workbench/" in text
    assert "kaggle/02-live-demo/" in text
    assert "kaggle/A-00-omni-experiment-workbench/" in text
    assert "not the active submission path" in text


def test_system_components_doc_defines_stable_critical_paths():
    text = _read("docs/system_components_and_critical_paths.md")
    required = [
        "Current Active Scope",
        "Main Components",
        "Harness Definition",
        "Registered Harnesses",
        "Knowledge And Logic Objects",
        "Critical Paths",
        "Kernel 01 Exploration",
        "Kernel 02 Live Demo",
        "A-00 Quantitative Proof",
        "Online Search Safety",
        "Training Flywheel",
        "Users And Use Cases",
        "Drift Rules",
        "`post_search_verification`",
        "Exact catalog sizes belong in runtime APIs",
    ]
    for phrase in required:
        assert phrase in text


def test_claude_drift_review_prompt_exists():
    text = _read("docs/claude_north_star_drift_review_prompt.md")
    required = [
        "North-Star Drift",
        "system_components_and_critical_paths.md",
        "fragile live inventory",
        "Gemma4Runtime",
        "post-search verification harness",
        "activity logs, reports, checkpoints",
        "Verdict: PASS, PARTIAL, or FAIL",
    ]
    for phrase in required:
        assert phrase in text


def test_harness_pattern_active_integration_uses_current_three_kernel_scope():
    text = _read("docs/harness_pattern.md")
    assert "## Active Kaggle Integration" in text
    assert "`01-duecare-exploration-workbench`" in text
    assert "`02-live-demo`" in text
    assert "`A-00-omni-experiment-workbench`" in text
    assert "Legacy minimal-shell kernels" in text
    assert "A-10" not in text


def test_current_entry_docs_do_not_present_archived_appendix_scope():
    for path in [
        "docs/FOR_PEER_REVIEW.md",
        "docs/USER_TODO.md",
        "docs/readiness_dashboard.md",
        "docs/two_week_submission_plan.md",
        "docs/user_walkthrough.md",
        "docs/gemma4_feature_showcase.md",
        "docs/project_status.md",
        "docs/authors_notes.md",
        "docs/REPO_LAYOUT.md",
        "docs/writeup_draft.md",
        "docs/system_map.md",
        "docs/rubric_alignment.md",
    ]:
        text = _read(path)
        assert "kaggle/01-duecare-exploration-workbench/" in text
        assert "kaggle/02-live-demo/" in text
        assert "kaggle/A-00-omni-experiment-workbench/" in text
        assert "24 appendix" not in text
        assert "2 core public Kaggle notebooks" not in text
        assert "A-01..A-11" not in text
        assert "bench_and_tune_readiness.md" not in text
        assert "bench_and_tune_walkthrough.md" not in text
        assert "rubric_evaluation_v07.md" not in text
        assert "submission_gate_checklist.md" not in text
        assert "REPORT_CARD.md" not in text
    adr_index = _read("docs/adr/README.md")
    assert "004-six-plus-five-notebook-shape.md" not in adr_index
    assert "006-two-plus-eleven-notebook-shape.md" not in adr_index
    assert "docs/_archive/2026-05-16-legacy-notebook-era/" in adr_index


def test_current_navigation_uses_a00_proof_path_not_legacy_bench_docs():
    combined = "\n".join(
        _read(path)
        for path in [
            "docs/index.md",
            "docs/appendices/README.md",
            "docs/readiness_dashboard.md",
            "docs/two_week_submission_plan.md",
            "docs/user_walkthrough.md",
            "docs/gemma4_feature_showcase.md",
            "docs/project_status.md",
            "docs/system_map.md",
            "docs/rubric_alignment.md",
        ]
    )
    assert "FOR_PEER_REVIEW.md#a-00-proof-path" in combined
    assert "bench_and_tune_readiness.md" not in combined
    assert "bench_and_tune_walkthrough.md" not in combined
    assert "submission_gate_checklist.md" not in combined
    assert "notebook_qa_companion.md" not in combined


def test_active_docs_do_not_carry_known_stale_corpus_counts():
    stale = [
        "161 GREP",
        "162 GREP",
        "46 RAG",
        "54 RAG",
        "55 RAG",
        "46-doc RAG",
        "55-doc RAG",
        "46-document",
        "55-document",
        "54-doc RAG",
        "161 rules",
        "162 rules",
        "161 hand-curated",
        "162 hand-curated",
        "Primary harnesses (5",
        "existing 5 harnesses",
        "The 7 harnesses",
        "7 harnesses",
        "6-layer harness",
        "six-layer harness",
        "Seven registered harnesses",
        "Eight registered harnesses",
        "seven registered harnesses",
        "eight registered harnesses",
    ]
    offenders: list[str] = []
    for path in (ROOT / "docs").rglob("*.md"):
        if "_archive" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in stale:
            if phrase in text:
                offenders.append(f"{path.relative_to(ROOT)}: {phrase}")
    assert offenders == []


def test_public_static_copy_avoids_hardcoded_catalog_counts():
    stale = [
        "161 deterministic risk rules",
        "161 hand-curated",
        "Four families. 161 rules.",
        "<b>Rules</b> 161",
        "The 7 harnesses",
        "five PRIMARY harnesses",
        "two SECONDARY harnesses",
        "26-kernel roster",
        "26 Kaggle script kernels",
        "All 26 Kaggle kernels",
        "all 6 harness layers",
        "6-card index",
        "5 tools + corridor",
        "207-prompt offline reference",
    ]
    roots = [
        ROOT / "packages" / "duecare-llm-chat" / "src" / "duecare" / "chat" / "static",
        ROOT / "apps" / "duecare-ai.com" / "app" / "templates",
    ]
    offenders: list[str] = []
    for root in roots:
        for path in root.rglob("*"):
            if path.suffix.lower() not in {".html", ".js"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for phrase in stale:
                if phrase in text:
                    offenders.append(f"{path.relative_to(ROOT)}: {phrase}")
    assert offenders == []


def test_current_public_docs_avoid_fragile_inventory_counts():
    checked = [
        "docs/FOR_KAGGLE_JUDGES.md",
        "docs/FOR_PEER_REVIEW.md",
        "docs/index.md",
        "docs/architecture.md",
        "docs/architecture/README.md",
        "docs/architecture/duecare_harness.md",
        "docs/architecture/duecare_eval.md",
        "docs/architecture/duecare_trainer.md",
        "docs/architecture/duecare_mobile.md",
        "docs/component_diagram.md",
        "docs/deployment_local.md",
        "docs/deployment_enterprise.md",
        "docs/embedding_guide.md",
        "docs/product_definition.md",
        "docs/video_script.md",
        "docs/workbench_audit.md",
        "docs/youtube_description.md",
        "docs/system_components_and_critical_paths.md",
    ]
    stale = [
        "46-dim",
        "46 dims",
        "46 dimensions",
        "65-test",
        "587 prompts",
        "26-entry",
        "9-variant",
        "all six harness",
        "all 6 harness",
        "6 toggle tiles",
        "4 grading modes",
        "5 tools",
        "11 viewer",
        "11 dedicated",
        "26 contact",
        "20 corridors",
        "11 languages",
        "11 ILO",
        "6 required",
        "54 classifier",
        "72 backing",
        "Existing layer counts",
    ]
    offenders: list[str] = []
    for path in checked:
        text = _read(path)
        for phrase in stale:
            if phrase in text:
                offenders.append(f"{path}: {phrase}")
    assert offenders == []


def test_modernized_architecture_docs_point_trainer_to_a00():
    combined = "\n".join(
        _read(path)
        for path in [
            "docs/FOR_KAGGLE_JUDGES.md",
            "docs/android_app_architecture.md",
            "docs/anonymization_policy.md",
            "docs/architecture.md",
            "docs/architecture/README.md",
            "docs/architecture/duecare_trainer.md",
            "docs/architecture/duecare_eval.md",
            "docs/compatibility.md",
            "docs/component_diagram.md",
            "docs/deployment_local.md",
            "docs/harness_pattern.md",
            "docs/product_definition.md",
            "docs/gemma4_model_guide.md",
            "docs/research_server_architecture.md",
        ]
    )
    assert "kaggle/A-00-omni-experiment-workbench/" in combined
    assert "kaggle/A-07-bench-and-tune" not in combined
    assert "kaggle/A-11-grading-evaluation" not in combined
    assert "kaggle/A-01-chat-playground" not in combined
    assert "kaggle/A-05-gemma-content-classification-evaluation" not in combined
