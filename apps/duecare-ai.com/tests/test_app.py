from __future__ import annotations

import json
import re

from app.main import create_app, detect_pii
from fastapi.testclient import TestClient


def test_detect_pii_blocks_obvious_contact_details() -> None:
    assert detect_pii("Contact worker@example.org for details") == {"email"}
    assert "phone" in detect_pii("Call +1 555 123 4567 immediately")
    assert "identity_document" in detect_pii("Passport A1234567 was retained")


def test_health_status_uses_file_storage(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["storage"] == "file"
    assert payload["storage_ok"] is True
    assert payload["git_commit"] is None
    assert (tmp_path / "signals.jsonl").exists()


def test_health_status_exposes_only_a_sanitized_render_commit_prefix(monkeypatch, tmp_path) -> None:
    full_commit = "ABCDEF0123456789ABCDEF0123456789ABCDEF01"
    monkeypatch.setenv("RENDER_GIT_COMMIT", full_commit)
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["git_commit"] == "abcdef012345"
    assert full_commit.lower() not in response.text

    monkeypatch.setenv("RENDER_GIT_COMMIT", "../../not-a-commit")
    assert client.get("/healthz").json()["git_commit"] is None


def test_robots_and_sitemap_are_served(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    robots = client.get("/robots.txt")
    sitemap = client.get("/sitemap.xml")

    assert robots.status_code == 200
    assert "Disallow: /admin" in robots.text
    assert "Sitemap: https://duecare-ai.com/sitemap.xml" in robots.text
    assert sitemap.status_code == 200
    assert "https://duecare-ai.com/" in sitemap.text
    assert "https://duecare-ai.com/docs" in sitemap.text
    assert "https://duecare-ai.com/grep-rules" in sitemap.text
    assert "https://duecare-ai.com/training-data-flywheel" in sitemap.text


def test_public_website_pages_render_design_templates(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    expected = {
        "/": "Gemma 4 safety ecosystem",
        "/components": "The full system, with honest labels.",
        "/grep-rules": "Rules fire <em>before</em> the model speaks.",
        "/tools": "Six tools. All local. All draft-only.",
        "/context": "Knowledge moves. Cases don't.",
        "/use-cases": "Six ways teams put DueCare to work.",
        "/training-data-flywheel": "Turn measured harness lift into reviewable training data.",
        "/dashboard": "The live hub. Not the model chat UI.",
    }

    for path, marker in expected.items():
        response = client.get(path)

        assert response.status_code == 200, f"{path} returned {response.status_code}"
        assert marker in response.text, f"{path} missing marker {marker!r}"


def test_homepage_story_keeps_each_explanation_in_the_content_column(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    step_blocks = re.findall(
        r'<li>\s*<div class="step-copy">.*?'
        r'<h4 class="step-title">.*?</h4>\s*'
        r'<p class="step-body">.*?</p>\s*</div>\s*</li>',
        response.text,
        flags=re.DOTALL,
    )
    assert len(step_blocks) == 3
    assert "grid-template-columns: 28px minmax(0, 1fr)" in response.text
    assert '<section id="story" class="tight" aria-labelledby="story-heading"' in response.text


def test_study_and_finetuning_pages_keep_model_and_deployment_claims_separate(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    study = client.get("/study-2026-07")
    finetuning = client.get("/finetuning")

    assert study.status_code == 200
    assert "workstation/server-class model evaluated locally" in study.text
    assert "evaluation also does not establish phone deployment" in study.text
    assert "separately converted and validated smaller Gemma" in study.text
    assert "four sufficiently sampled models shown in this study" in study.text
    assert "not a claim that every response refused or cited correctly" in study.text
    assert "Harnessed, every one refused" not in study.text
    assert "gitignored <code>panel.jsonl</code>" in study.text
    assert "not the large raw response and grade files" in study.text
    assert "committed benchmark artifacts" not in study.text
    assert "Reproduce every number" not in study.text
    assert "the open, on-device deployment" not in study.text
    assert "runs Gemma&nbsp;4 <em>entirely on the worker&rsquo;s device</em>" not in study.text
    assert "The scored study is English-only" in study.text

    assert finetuning.status_code == 200
    assert "a full trained adapter remains pending" in finetuning.text
    assert "No Gemma adapter, merged weights, or independent model-lift result is published yet." in finetuning.text
    assert "no graphics processing unit (GPU) fine-tuning ran" in finetuning.text
    assert "single GPU step" not in finetuning.text


def test_training_data_flywheel_states_release_and_reasoning_boundaries(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/training-data-flywheel")

    assert response.status_code == 200
    assert "Two advanced Kaggle datasets are public" in response.text
    assert (
        "Nine public training-data Kaggle notebooks load, verify, explain, visualize"
        in response.text
    )
    assert "supervised fine-tuning (SFT) data first" in response.text
    assert "private hidden chain-of-thought" in response.text
    assert "complete final answers, citations, harness traces" in response.text
    assert "Already have a file?" in response.text
    assert "A loose file stays inspection-only" in response.text
    assert "prompt hash and lineage identifier" in response.text
    assert "791 supervised fine-tuning rows, 791 preference pairs, 1,582 reward labels" in response.text
    assert "25,600 supervised fine-tuning training rows, 25,600 preference-training rows" in response.text
    assert "the proof dataset" in response.text
    assert "Current Kaggle Dataset publication unit" in response.text
    assert "Both public advanced datasets meet this packaging contract" in response.text
    assert "kaggle/A-00-omni-experiment-workbench" in response.text
    assert "kaggle/shared-datasets/training-data" in response.text
    assert "docs/training_and_finetuning.md" in response.text
    assert "No Gemma fine-tuning, graphics-processing-unit run, production adapter" in response.text
    assert "www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation" in response.text
    assert "www.kaggle.com/code/taylorsamarel/duecare-training-data-loading-quickstart" in response.text
    assert "www.kaggle.com/datasets/taylorsamarel/duecare-proof-finetuning-data" in response.text
    assert "www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus" in response.text
    assert "www.kaggle.com/datasets/taylorsamarel/duecare-multiperspective-finetuning-corpus" in response.text


def test_training_data_flywheel_is_linked_from_public_training_surfaces(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    for path in ("/", "/docs", "/finetuning", "/kernels", "/use-cases"):
        response = client.get(path)

        assert response.status_code == 200
        assert 'href="/training-data-flywheel"' in response.text

    assert 'class="docs-card" href="/finetuning"' in client.get("/docs").text
    kernels = client.get("/kernels").text
    assert "July dataset-attached update" in kernels
    assert "public learning and analysis notebooks" in kernels
    assert "Public training-data learning route" in kernels
    assert "www.kaggle.com/code/taylorsamarel/duecare-training-data-quality-dashboard" in kernels
    assert "Latest run: COMPLETE" in kernels
    assert "Latest run: CANCEL_ACKNOWLEDGED" in kernels
    assert "Public URL not verified" in kernels
    assert "duecare-prompt-intent-and-attack-explorer" in kernels


def test_public_schema_urls_linked_from_technical_docs_resolve(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    for kind in ("pack", "tool", "signal", "audit", "feedback"):
        response = client.get(f"/schema/{kind}/1.json")
        assert response.status_code == 200
        payload = response.json()
        assert payload["$id"] == f"https://duecare-ai.com/schema/{kind}/1.json"
        assert payload["additionalProperties"] is False

    context = client.get("/schema/v1")
    assert context.status_code == 200
    assert context.json()["schema_version"] == 1
    assert client.get("/schema/unknown/1.json").status_code == 404


def test_demo_recording_and_admin_pages_render(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    recording = client.get("/demo-recording")
    admin = client.get("/admin")

    assert recording.status_code == 200
    assert "Five system surfaces in under three minutes" in recording.text
    assert "no inference wait" in recording.text
    assert admin.status_code == 200
    assert "Token-gated troubleshooting" in admin.text
    assert "DUECARE_ADMIN_TOKEN" in admin.text


def test_demo_priority_examples_are_public_and_pii_safe(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/api/demo/priority-examples")

    assert response.status_code == 200
    payload = response.json()
    examples = payload["examples"]
    assert len(examples) == 6
    surfaces = {example["surface"] for example in examples}
    assert "platform moderation" in surfaces
    assert "worker mobile chat and opt-in sharing" in surfaces
    assert "research upload, graph, and anonymized factoids" in surfaces
    assert detect_pii(json.dumps(payload)) == set()
    assert payload["finetuning_best_practices"]["sample_data_needed"] is True


def test_hub_tools_manifest_is_gemma_callable_and_read_only(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/api/hub/tools/manifest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["orchestration_model"].startswith("Local or Kaggle-hosted Gemma 4")
    tools = payload["tools"]
    assert tools

    expected_tools = {
        "get_hub_status",
        "list_pack_summaries",
        "list_packs",
        "get_pack_details",
        "list_pack_versions",
        "sync_packs",
        "get_aggregate_trends",
    }
    assert {tool["name"] for tool in tools} == expected_tools

    for tool in tools:
        assert tool["method"] == "GET"
        assert tool["safety_level"] == "read_only_public"
        assert tool["parameters"]["type"] == "object"
        assert "properties" in tool["parameters"]
        assert "required" in tool["parameters"]
        assert tool["examples"]


def test_hub_tools_manifest_excludes_sensitive_or_write_tools(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    payload = client.get("/api/hub/tools/manifest").json()
    rendered = json.dumps(payload).lower()
    tool_names = {tool["name"] for tool in payload["tools"]}

    forbidden_tool_name_parts = {
        "admin",
        "email",
        "forget",
        "ingest",
        "local_kb",
        "retract",
        "signal",
        "submit",
        "update",
    }
    for name in tool_names:
        for forbidden in forbidden_tool_name_parts:
            assert forbidden not in name

    assert "/api/admin" not in rendered
    assert "/api/local-kb" not in rendered
    assert "/api/hub/client/submission" not in rendered
    assert "/api/hub/signals" not in rendered
    assert "/api/hub/opencrawl/updates" not in rendered
    assert "/api/hub/automation/inbound-email" not in rendered


def test_hub_tools_manifest_parameters_do_not_require_pii(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    payload = client.get("/api/hub/tools/manifest").json()
    pii_parameter_fragments = {
        "address",
        "body",
        "contact",
        "email",
        "name",
        "passport",
        "phone",
        "raw",
    }

    for tool in payload["tools"]:
        properties = tool["parameters"]["properties"]
        for parameter_name in properties:
            for fragment in pii_parameter_fragments:
                assert fragment not in parameter_name.lower(), (
                    f"Tool {tool['name']} exposes PII-like parameter {parameter_name}"
                )

    list_packs = next(tool for tool in payload["tools"] if tool["name"] == "list_packs")
    params = list_packs["parameters"]["properties"]
    assert {"kind", "status", "jurisdiction", "corridor", "tag", "latest_only"} <= set(params)
    assert params["latest_only"]["type"] == "boolean"
    assert list_packs["parameters"]["required"] == []


def test_every_design_route_renders(tmp_path) -> None:
    """Every entry in PAGE_ROUTES must serve a 200 with linked CSS."""
    from app.main import PAGE_ROUTES

    client = TestClient(create_app(data_dir=tmp_path))
    for path in PAGE_ROUTES:
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        assert "/static/styles.css" in response.text, f"{path} did not link the design CSS"


def test_public_notebook_catalogs_link_verified_deterministic_notebook(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    slug = "duecare-deterministic-verification"

    assert slug in client.get("/data").text
    assert slug in client.get("/kernels").text


def test_package_detail_is_an_explicit_preview_with_real_navigation(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/packages-detail")

    assert response.status_code == 200
    assert "Illustrative corridor-pack schema" in response.text
    assert "not a downloadable or verified pack" in response.text
    assert 'href="#"' not in response.text
    assert "/knowledge-packs" in response.text
    assert "duecare-deterministic-verification" in response.text


def test_project_status_page_keeps_release_and_training_claims_separate(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/project-status")

    assert response.status_code == 200
    assert "12 / 12 pass" in response.text
    assert "0 items" in response.text
    assert "remain unpublished on PyPI" in response.text
    assert "2 / 2 pass" in response.text
    assert "4,669 passed" in response.text
    assert "Model/flywheel stack" in response.text and "cost-stopped" in response.text
    assert "auxiliary discovery and server-automation callers" in response.text
    assert "does not claim its historical provider usage was zero" in response.text
    assert "strict training lane is excluded from closeout claims" in response.text
    assert "All 75 content slots are honestly unfilled" in response.text
    assert "provider-budget coverage" in response.text
    assert "Independent per-package semantic versions" in response.text
    assert "PROVIDER_BUDGETING" in response.text
    assert "docs-deploy.yml" in response.text
    assert "duecare-site-build.yml" in response.text
    assert "duecare-ai-site" in response.text
    assert "source_revision" in response.text
    assert "CLAUDE_CODE_HANDOFF" in response.text
    assert "MAINTAINER_HANDOFF" in response.text
    assert "PROJECT_TRANSITION_PLAN" in response.text
    assert "DEFERRED_WORK" in response.text
    assert "CLOSEOUT_RESOLUTIONS_2026_07_28" in response.text
    assert "validated deferred-work register" in response.text
    assert "Kimi K3" in response.text
    assert "Meta Muse Spark 1.1" in response.text
    assert "Containers serve software, not autonomous outreach" in response.text
    assert "The hub plans; a curator contacts" in response.text
    assert "364 review items, zero human ratings" in response.text
    assert "it cannot send" in response.text
    assert "HTTP 402" in response.text
    assert "500-item campaign is hash-bound and category-balanced" in response.text
    assert "never merged into a claim of human validation" in response.text
    assert "One domain implementation, a reusable capability-gap pattern" in response.text
    assert "Kimi K3 plus two kinds of judging" in response.text
    assert "1,500 calls planned; zero results invented" in response.text
    assert "Gemini 3.1 Pro" in response.text
    assert "7,296,582 input tokens" in response.text
    assert "capability_gap_blueprint" in response.text
    assert "model_failure_run_readiness" in response.text
    assert "overflow-wrap: break-word" in response.text
    assert "Post-competition decision: pages plus independently governed nodes" in response.text
    assert "Render and the centralized hub stay available through competition grading" in response.text
    assert "kaggle_final_closeout_post" in response.text
    assert "POST_COMPETITION_HOSTING_TRANSITION" in response.text


def test_stats_page_discloses_beta_data_and_uses_live_counters(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/stats")

    assert response.status_code == 200
    assert "Beta data notice" in response.text
    assert "synthetic/composite demo previews" in response.text
    assert "not field prevalence metrics" in response.text
    assert "14,208" not in response.text
    assert "3.1M" not in response.text
    assert "live tail" not in response.text.lower()

    posted = client.post(
        "/api/hub/signals",
        json={
            "source": "synthetic_demo",
            "jurisdiction": "Philippines / Hong Kong",
            "corridor": "PH-HK domestic work",
            "risk_tags": ["fee_excess"],
            "summary": "Synthetic aggregate pattern for the stats page counter without person-specific details.",
            "consent_basis": "synthetic_demo",
        },
    )
    assert posted.status_code == 202

    updated = client.get("/stats")
    assert (
        '<div class="cell" data-metric="accepted-signals"><div class="lbl">Accepted signals</div>'
        '<div class="val">1</div>'
    ) in updated.text


def test_admin_logs_are_token_gated_and_redacted(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DUECARE_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("DUECARE_HUB_ADMIN_TOKEN", raising=False)
    client = TestClient(create_app(data_dir=tmp_path))

    disabled = client.get("/api/admin/logs")
    assert disabled.status_code == 403

    monkeypatch.setenv("DUECARE_ADMIN_TOKEN", "test-admin-token")
    unauthorized = client.get("/api/admin/logs", headers={"X-DueCare-Admin-Token": "wrong"})
    assert unauthorized.status_code == 401

    state = client.app.state.duecare
    state.store.append(
        "updates.jsonl",
        {
            "id": "cli_demo_redaction",
            "received_at": "2026-05-08T12:00:00+00:00",
            "kind": "context",
            "summary": "Demo update includes worker@example.org and +1 555 123 4567 for redaction testing.",
            "contact_email": "worker@example.org",
            "payload": {"free_text": "passport A1234567"},
            "status": "needs_review",
            "automation": {"verdict": "needs_curator_review", "intent": "pack_update"},
        },
    )

    response = client.get("/api/admin/logs", headers={"X-DueCare-Admin-Token": "test-admin-token"})

    assert response.status_code == 200
    body = response.json()
    rendered = json.dumps(body)
    assert "worker@example.org" not in rendered
    assert "+1 555 123 4567" not in rendered
    assert "passport A1234567" not in rendered
    assert "[REDACTED_EMAIL]" in rendered
    assert body["updates"][0]["contact_email"] == "[REDACTED]"
    assert body["updates"][0]["payload"] == {"suppressed": True, "keys": ["free_text"]}


def test_use_cases_audiences_appear_in_design_order(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.get("/use-cases")

    assert response.status_code == 200
    ordered = [
        "Platform safety screening",
        "NGO &amp; regulator copilot",
        "Individual worker / mobile",
        "Researcher",
        "Anonymized knowledge sharing",
        "Developer / integration partner",
    ]
    positions = [response.text.index(name) for name in ordered]
    assert positions == sorted(positions)


def test_accepts_anonymized_signal_and_persists(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/signals",
        json={
            "source": "synthetic_demo",
            "jurisdiction": "Philippines / Hong Kong",
            "corridor": "PH-HK domestic work",
            "language": "English",
            "risk_tags": ["recruitment_fee", "document_retention"],
            "summary": "Synthetic aggregate pattern describing high recruitment fees and document pressure without person-specific details.",
            "evidence_hashes": ["sha256:synthetic-demo-pattern-001"],
            "consent_basis": "synthetic_demo",
            "pack_version": "0.14.x",
        },
    )

    assert response.status_code == 202
    assert response.json()["accepted"] is True

    second_client = TestClient(create_app(data_dir=tmp_path))
    status = second_client.get("/api/hub/status").json()
    assert status["signal_count"] == 1
    assert status["counters"]["risk:recruitment_fee"] == 1


def test_rejects_raw_pii_in_signal(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/signals",
        json={
            "source": "synthetic_demo",
            "jurisdiction": "Philippines",
            "summary": "This includes a direct email address worker@example.org and should be rejected.",
            "consent_basis": "synthetic_demo",
        },
    )

    assert response.status_code == 422


def test_accepts_opencrawl_update_as_proposal(tmp_path, monkeypatch) -> None:
    # The inbound POST is open (crawlers/automation submit proposals); the GET
    # that lists the raw proposal log is admin-gated (it can carry consented
    # submitter contact emails), so reading it back requires the admin token.
    monkeypatch.setenv("DUECARE_ADMIN_TOKEN", "test-admin-token")
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/opencrawl/updates",
        json={
            "source_name": "Synthetic public regulator page",
            "source_url": "https://example.org/public-advisory",
            "proposed_pack_kind": "contacts",
            "jurisdiction": "Hong Kong",
            "change_summary": "Synthetic public-source update proposing clearer complaint-routing language for curator review.",
            "extracted_public_facts": ["Synthetic public-source update; curator review required."],
            "content_hash": "synthetic-public-hash-001",
            "crawler_version": "opencrawl-demo/0.1",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "proposed"
    updates = client.get(
        "/api/hub/opencrawl/updates",
        headers={"X-DueCare-Admin-Token": "test-admin-token"},
    ).json()
    assert len(updates) == 1

    # Without the admin token the raw-log read is rejected.
    assert client.get("/api/hub/opencrawl/updates").status_code == 401


def test_pack_registry_list_and_filter(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    all_packs = client.get("/api/hub/packs").json()
    assert all_packs["count"] >= 4
    kinds = {pack["@type"] for pack in all_packs["packs"]}
    assert {"ContextPack", "GrepRulePack", "ContactPack", "RubricPack"} <= kinds
    assert "fees" in all_packs["available_tags"]

    grep_only = client.get("/api/hub/packs?kind=GrepRulePack").json()
    assert grep_only["count"] >= 1
    assert all(pack["@type"] == "GrepRulePack" for pack in grep_only["packs"])

    phl_only = client.get("/api/hub/packs?jurisdiction=PHL").json()
    assert any(pack["id"] == "phl-kwt-domestic" for pack in phl_only["packs"])

    fee_packs = client.get("/api/hub/packs?tag=fees").json()
    assert fee_packs["count"] >= 1
    assert all("fees" in pack["tags"] for pack in fee_packs["packs"])


def test_pack_registry_get_latest_and_pin(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    latest = client.get("/api/hub/packs/phl-kwt-domestic").json()
    assert latest["id"] == "phl-kwt-domestic"
    assert latest["@type"] == "ContextPack"
    assert "content" in latest

    pinned = client.get("/api/hub/packs/phl-kwt-domestic/1.7.2").json()
    assert pinned["version"] == "1.7.2"

    versions = client.get("/api/hub/packs/phl-kwt-domestic/versions").json()
    assert versions["count"] >= 1

    missing = client.get("/api/hub/packs/does-not-exist")
    assert missing.status_code == 404

    invalid = client.get("/api/hub/packs/InvalidPackId")
    assert invalid.status_code == 400
    assert "pack_id" in invalid.json()["detail"]


def test_pack_registry_sync(tmp_path) -> None:
    from urllib.parse import quote

    client = TestClient(create_app(data_dir=tmp_path))

    full = client.get("/api/hub/sync").json()
    assert full["count"] >= 4
    assert full["next_cursor"] is not None

    # The cursor contains a `+` for the timezone offset; URL-encode it so
    # the query parser doesn't strip it to a space.
    delta = client.get(f"/api/hub/sync?since={quote(full['next_cursor'], safe='')}").json()
    assert delta["count"] == 0


def test_knowledge_packs_runtime_projection(tmp_path) -> None:
    """GET /api/knowledge/packs returns the runtime projection on-device
    consumers (the A-00 kernel) execute: {slug, version, trust, rules, facts}
    drawn from the same registry as /api/hub/packs."""
    client = TestClient(create_app(data_dir=tmp_path))

    resp = client.get("/api/knowledge/packs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["vetted_only"] is True
    assert body["count"] == len(body["packs"]) >= 4

    by_slug = {pack["slug"]: pack for pack in body["packs"]}
    # Every pack carries the flat runtime contract the kernel reads.
    for pack in body["packs"]:
        assert {"slug", "version", "trust", "rules", "facts"} <= set(pack)

    # GrepRulePack -> executable GREP rules (and no facts).
    fee = by_slug["global-fee-rules"]
    assert fee["trust"] == "vetted"
    assert fee["rules"] and all(rule["pattern"] for rule in fee["rules"])
    assert any(rule["id"] == "fee_request_explicit" for rule in fee["rules"])
    assert fee["facts"] == []

    # ContextPack -> RAG facts from sections (and no rules).
    corridor = by_slug["phl-kwt-domestic"]
    assert corridor["rules"] == []
    assert corridor["facts"] and all(fact["text"] for fact in corridor["facts"])

    # ContactPack -> contacts surface as facts tagged with their role.
    contacts = by_slug["global-contacts"]
    assert any("regulator" in fact["tags"] for fact in contacts["facts"])


def test_knowledge_packs_vetted_flag_and_filters(tmp_path) -> None:
    """vetted defaults true; vetted=false widens the set; the kind /
    jurisdiction filters compose exactly as on /api/hub/packs."""
    client = TestClient(create_app(data_dir=tmp_path))

    vetted = client.get("/api/knowledge/packs?vetted=true").json()
    every = client.get("/api/knowledge/packs?vetted=false").json()
    assert vetted["vetted_only"] is True
    assert every["vetted_only"] is False
    assert every["count"] >= vetted["count"]
    assert all(pack["trust"] == "vetted" for pack in vetted["packs"])

    grep = client.get("/api/knowledge/packs?kind=GrepRulePack").json()
    assert grep["count"] >= 1
    assert all(pack["rules"] for pack in grep["packs"])

    phl = client.get("/api/knowledge/packs?jurisdiction=PHL").json()
    assert any(pack["slug"] == "phl-kwt-domestic" for pack in phl["packs"])


def test_retract_unvetted_submission(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    posted = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "summary": "Public-source advisory describes a fee cap update for the test corridor.",
            "consent_public_proposal": True,
        },
    ).json()
    submission_id = posted["id"]

    retract = client.post(
        "/api/hub/client/submission/retract",
        json={"submission_id": submission_id, "reason": "operator changed their mind"},
    )
    assert retract.status_code == 200
    payload = retract.json()
    assert payload["retracted"] is True
    assert payload["new_status"] == "retracted"

    # A second retract attempt finds the record but blocks because it is no
    # longer in proposed / needs_review status.
    second = client.post(
        "/api/hub/client/submission/retract",
        json={"submission_id": submission_id},
    )
    assert second.status_code == 409


def test_retract_unknown_submission_404(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    response = client.post(
        "/api/hub/client/submission/retract",
        json={"submission_id": "cli_not_a_real_id"},
    )
    assert response.status_code == 404


def test_local_kb_ingest_and_list(tmp_path, monkeypatch) -> None:
    # Local KB lives in its own SQLite file; redirect to a tmp dir for
    # test isolation.
    monkeypatch.setenv("DUECARE_LOCAL_KB", str(tmp_path / "local-kb.db"))
    monkeypatch.setenv("DUECARE_LOCAL_KB_SALT", "test-salt")

    # Reload the local_kb module so the env var picks up the new path.
    import importlib

    from app import local_kb as _lk

    importlib.reload(_lk)

    client = TestClient(create_app(data_dir=tmp_path))

    # The route binds to a LocalKB() instance created at app build time, which
    # captured the old default. To work around without restructuring main.py,
    # we point the binding at the same path manually.
    from app import main as _main

    _main._kb = _lk.LocalKB(_lk.DEFAULT_KB_PATH)

    response = client.post(
        "/api/local-kb/ingest",
        json={
            "text": "Composite recruiter case in the PHL-KWT corridor describing fee patterns and an agency named ExampleCo.",
            "source_filename": "test-case-001.txt",
            "corridor": "PHL-KWT",
            "sector": "domestic-work",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"].startswith("case_")
    assert body["status"] == "processed"
    assert body["corridor"] == "PHL-KWT"

    cases = client.get("/api/local-kb/cases").json()
    assert cases["count"] >= 1

    stats = client.get("/api/local-kb/stats").json()
    assert stats["n_cases"] >= 1


def test_local_kb_redacts_pii_from_stored_summary(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DUECARE_LOCAL_KB", str(tmp_path / "local-kb-redact.db"))
    monkeypatch.setenv("DUECARE_LOCAL_KB_SALT", "test-salt")

    import importlib

    from app import local_kb as _lk

    importlib.reload(_lk)

    client = TestClient(create_app(data_dir=tmp_path))
    from app import main as _main

    _main._kb = _lk.LocalKB(_lk.DEFAULT_KB_PATH)

    response = client.post(
        "/api/local-kb/ingest",
        json={
            "text": "Composite worker wrote worker@example.org and +1 555 123 4567 in a demo case about an agency named ExampleCo.",
            "source_filename": "worker@example.org.txt",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "worker@example.org" not in body["summary"]
    assert "+1 555 123 4567" not in body["summary"]
    assert "[REDACTED_EMAIL]" in body["summary"]
    assert "[REDACTED_PHONE]" in body["summary"]

    stored = client.get(f"/api/local-kb/cases/{body['case_id']}").json()
    assert "worker@example.org" not in stored["summary"]
    assert stored["source_filename"] == "[REDACTED_EMAIL]"


def test_local_kb_forget(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DUECARE_LOCAL_KB", str(tmp_path / "local-kb-forget.db"))

    import importlib

    from app import local_kb as _lk

    importlib.reload(_lk)

    client = TestClient(create_app(data_dir=tmp_path))
    from app import main as _main

    _main._kb = _lk.LocalKB(_lk.DEFAULT_KB_PATH)

    client.post(
        "/api/local-kb/ingest",
        json={
            "text": "Demo case content for forget test, with at least the minimum length.",
            "source_filename": "tmp.txt",
        },
    )
    forgotten = client.post("/api/local-kb/forget").json()
    assert forgotten["ok"] is True
    after = client.get("/api/local-kb/stats").json()
    assert after["n_cases"] == 0


def test_client_submission_endpoint(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "deployment_id": "test-suite",
            "organization": "Test NGO",
            "summary": "Public-source update on placement-fee cap for the demo corridor; please review.",
            "consent_public_proposal": True,
        },
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["status"] in {"proposed", "needs_review"}
    assert payload["automation_verdict"] in {"accept", "needs_curator_review"}


def test_client_submission_accepts_labeling_envelope(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "deployment_id": "test-suite",
            "summary": "Public-source update on placement-fee cap for the demo corridor; please review.",
            "visibility": "aggregate_only",
            "attribution_mode": "pseudonymous_deployment",
            "submitter": {
                "tenant_id_hash": "sha256:test-tenant",
                "public_attribution": False,
            },
            "labels": [
                {
                    "key": "region",
                    "value": "Southeast Asia",
                    "source": "manual_submitter",
                    "confidence": 1.0,
                    "public_safe": True,
                },
                {
                    "key": "corridor",
                    "value": "PHL-KWT",
                    "source": "local_model_suggested",
                    "confidence": 0.82,
                    "public_safe": False,
                },
            ],
            "consent": {
                "share_sanitized_object": True,
                "share_aggregate_trends": True,
                "allow_recontact": False,
                "allow_training_use": False,
                "allow_public_display": False,
            },
            "consent_public_proposal": True,
        },
    )

    assert response.status_code == 202
    receipt = response.json()
    record = client.app.state.duecare.store.read_all("updates.jsonl")[-1]
    assert receipt["accepted"] is True
    assert "tenant_id_hash" not in json.dumps(receipt)
    assert record["visibility"] == "aggregate_only"
    assert record["attribution_mode"] == "pseudonymous_deployment"
    assert record["submitter"]["tenant_id_hash"] == "sha256:test-tenant"
    assert record["submitter"]["public_attribution"] is False
    assert [label["source"] for label in record["labels"]] == ["manual_submitter", "local_model_suggested"]
    assert record["consent"]["allow_training_use"] is False
    assert record["consent"]["allow_public_display"] is False


def test_anonymous_submission_rejects_attribution_fields(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "summary": "Anonymous public-source update on a regulator clarification.",
            "visibility": "private_review",
            "attribution_mode": "anonymous",
            "submitter": {
                "organization_registry_id": "ngo-001",
                "display_name": "Example NGO",
                "public_attribution": True,
            },
            "consent_public_proposal": True,
        },
    )

    assert response.status_code == 422
    assert "anonymous" in str(response.json()["detail"]).lower()


def test_local_only_and_public_visibility_constraints(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    local_only = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "summary": "This object should remain local and must not reach the hub.",
            "visibility": "local_only",
            "attribution_mode": "anonymous",
            "consent_public_proposal": True,
        },
    )
    assert local_only.status_code == 422

    public_without_consent = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "summary": "Public pack proposal without explicit display consent.",
            "visibility": "pack_public",
            "attribution_mode": "anonymous",
            "consent": {"allow_public_display": False},
            "consent_public_proposal": True,
        },
    )
    assert public_without_consent.status_code == 422


def test_client_submission_rejects_recursive_payload_pii(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "custom",
            "summary": "Public-source update with unsafe nested payload content.",
            "visibility": "private_review",
            "attribution_mode": "anonymous",
            "payload": {
                "nested": {
                    "contact": "worker@example.org",
                    "phone": "+1 555 123 4567",
                },
                "passport_ref": "A1234567",
            },
            "consent_public_proposal": True,
        },
    )

    assert response.status_code == 422
    assert "pii" in str(response.json()["detail"]).lower()


def test_client_submission_rejects_payload_pii_in_keys(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "custom",
            "summary": "Public-source update with unsafe payload key content.",
            "visibility": "private_review",
            "attribution_mode": "anonymous",
            "payload": {
                "worker@example.org": "reported public-source recruitment terms",
            },
            "consent_public_proposal": True,
        },
    )

    assert response.status_code == 422
    assert "pii" in str(response.json()["detail"]).lower()


def test_client_submission_rejects_too_deep_payload(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))
    nested: dict[str, object] = {"leaf": "public-source pack candidate"}
    for _ in range(25):
        nested = {"nested": nested}

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "custom",
            "summary": "Public-source update with excessive nested payload depth for validation.",
            "visibility": "private_review",
            "attribution_mode": "anonymous",
            "payload": nested,
            "consent_public_proposal": True,
        },
    )

    assert response.status_code == 422
    assert "nesting" in str(response.json()["detail"]).lower()


def test_client_submission_rejects_oversized_payload(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "custom",
            "summary": "Public-source update with an oversized payload for validation.",
            "visibility": "private_review",
            "attribution_mode": "anonymous",
            "payload": {"public_context": "x" * 101_000},
            "consent_public_proposal": True,
        },
    )

    assert response.status_code == 422
    assert "payload exceeds" in str(response.json()["detail"]).lower()


def test_contact_email_validation_and_publication_consent(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    invalid = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "partner",
            "summary": "Partner proposal with malformed contact metadata.",
            "visibility": "private_review",
            "attribution_mode": "organization_tagged",
            "organization": "Example NGO",
            "contact_email": "not-an-email",
            "consent_public_proposal": True,
        },
    )
    assert invalid.status_code == 422

    private_contact = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "partner",
            "summary": "Partner proposal with private contact metadata.",
            "visibility": "private_review",
            "attribution_mode": "organization_tagged",
            "organization": "Example NGO",
            "contact_email": "private@example.org",
            "contact_publication_consent": False,
            "consent_public_proposal": True,
        },
    )
    assert private_contact.status_code == 202
    private_record = client.app.state.duecare.store.read_all("updates.jsonl")[-1]
    assert private_record["contact_email"] is None
    assert private_record["contact_email_sha256"]

    public_contact = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "partner",
            "summary": "Partner proposal with consented public contact metadata.",
            "visibility": "pack_public",
            "attribution_mode": "organization_tagged",
            "organization": "Example NGO",
            "contact_email": "public@example.org",
            "contact_publication_consent": True,
            "consent": {"allow_public_display": True},
            "consent_public_proposal": True,
        },
    )
    assert public_contact.status_code == 202
    public_record = client.app.state.duecare.store.read_all("updates.jsonl")[-1]
    assert public_record["contact_email"] == "public@example.org"


def test_client_submission_rejects_pii(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "summary": "Worker email is alice@example.org and they reported the issue.",
            "consent_public_proposal": True,
        },
    )
    assert response.status_code == 422


def test_client_submission_requires_consent(tmp_path) -> None:
    client = TestClient(create_app(data_dir=tmp_path))

    response = client.post(
        "/api/hub/client/submission",
        json={
            "kind": "context",
            "summary": "Public-source advisory describes a regulator clarification on fees.",
            "consent_public_proposal": False,
        },
    )
    assert response.status_code == 422
