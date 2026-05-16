from __future__ import annotations

import io
import json
import re
import shutil
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi.testclient import TestClient


PKG = Path(__file__).parents[1]
STATIC = PKG / "src" / "duecare" / "chat" / "static"
SAMPLES = STATIC / "samples"


def _client() -> TestClient:
    from duecare.chat.app import create_app

    return TestClient(create_app())


def _sample_manifest() -> dict:
    return json.loads((SAMPLES / "sample_manifest.json").read_text(encoding="utf-8"))


def test_workbench_inventory_endpoint_covers_pages_harnesses_samples_and_taxonomy():
    from duecare.chat.app import KO_BRANCHES, KO_TYPES
    from duecare.chat.portability import REQUIRED_CHAT_VERSION, REQUIRED_SAMPLE_FILES

    client = _client()
    response = client.get("/api/audit/workbench-inventory")
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["schema_version"] == "duecare.workbench_inventory.v1"
    assert data["counts"]["harnesses"] == 7
    assert data["counts"]["knowledge_types"] == len(KO_TYPES)
    assert data["counts"]["knowledge_branches"] == len(set(KO_BRANCHES.values()))
    assert data["counts"]["knowledge_types_with_catalog"] == len(KO_TYPES)
    assert data["knowledge"]["missing_type_catalog"] == []
    assert data["knowledge"]["extra_type_catalog"] == []
    assert data["portability"]["schema_version"] == "duecare.portability_contract.v1"
    assert data["portability"]["required_chat_version"] == REQUIRED_CHAT_VERSION
    assert data["portability"]["evaluation"]["ok"] is True
    assert data["portability"]["evaluation"]["failures"] == []
    assert data["portability"]["workbench_defaults"]["gemma_max_seq_len"] == 32768
    assert data["portability"]["workbench_defaults"]["primary_source_bundle"] == "case_files_media_rich_sample.zip"
    assert {term["term"] for term in data["portability"]["trust_boundary_terms"]}.issuperset(
        {"source_case_bundle", "knowledge_files", "redacted_submission", "hub_aggregate"}
    )
    assert set(REQUIRED_SAMPLE_FILES).issubset(
        set(data["portability"]["required_sample_files"])
    )
    assert {
        item["id"] for item in data["portability"]["reusable_primitives"]
    }.issuperset({
        "workbench_inventory",
        "knowledge_type_catalog",
        "sample_manifest",
        "harness_surface_contracts",
        "async_job_contract",
        "graph_edge_schema",
        "model_fit_profile",
        "trust_boundary_vocabulary",
        "activity_log",
        "knowledge_envelope_io",
    })
    assert data["samples"]["missing_referenced_samples"] == []
    assert data["samples"]["manifest_entries_without_file"] == []
    assert data["samples"]["unmanifested_sample_files"] == []
    assert {h["name"] for h in data["harnesses"]["harnesses"]} == {
        "chat",
        "process",
        "extraction",
        "anonymization",
        "search_safety",
        "search",
        "import_corpus",
    }
    assert any(e["path"] == "/api/knowledge/import" for e in data["import_export"]["endpoints"])
    assert any(e["path"] == "/api/knowledge/export" for e in data["import_export"]["endpoints"])


def test_knowledge_type_catalog_endpoint_covers_each_leaf_and_subtype_field():
    from duecare.chat.app import KO_BRANCHES, KO_TYPE_CATALOG, KO_TYPES

    assert set(KO_TYPE_CATALOG) == set(KO_TYPES)
    for ko_type, meta in KO_TYPE_CATALOG.items():
        assert KO_BRANCHES[ko_type]
        assert meta["purpose"], ko_type
        assert isinstance(meta["required_content_keys"], list), ko_type
        assert isinstance(meta["recommended_content_keys"], list), ko_type
        assert isinstance(meta["subtype_fields"], list), ko_type
        assert isinstance(meta["common_subtypes"], dict), ko_type

    client = _client()
    response = client.get("/api/knowledge/type-catalog")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["schema_version"] == "duecare.knowledge_type_catalog.v1"
    assert data["n_types"] == len(KO_TYPES)
    assert data["n_cataloged"] == len(KO_TYPES)
    assert data["missing"] == []
    assert data["extra"] == []
    assert data["types"]["extracted_fact"]["branch"] == "input_knowledge"
    assert "fact_type" in data["types"]["extracted_fact"]["subtype_fields"]
    assert data["types"]["entity_signal"]["purpose"].startswith("Non-PII signal")
    assert "pattern_name" in data["types"]["modus_operandi"]["required_content_keys"]
    assert "use_case" in data["types"]["evaluation_weighting"]["subtype_fields"]


def test_every_static_sample_reference_exists_and_is_cataloged():
    manifest_names = {entry["name"] for entry in _sample_manifest()["entries"]}
    sample_files = {
        p.name
        for p in SAMPLES.iterdir()
        if p.is_file() and p.name != "sample_manifest.json"
    }
    assert sample_files == manifest_names

    referenced: set[str] = set()
    for page in STATIC.glob("*.html"):
        text = page.read_text(encoding="utf-8", errors="replace")
        referenced.update(re.findall(r"/static/samples/([^\"'<>\s)]+)", text))

    missing_files = [name for name in referenced if not (SAMPLES / name).exists()]
    missing_manifest = [
        name
        for name in referenced
        if name != "sample_manifest.json" and name not in manifest_names
    ]
    assert not missing_files
    assert not missing_manifest


def test_sample_manifest_names_primary_artifacts_for_each_workflow():
    entries = {entry["name"]: entry for entry in _sample_manifest()["entries"]}
    assert entries["case_files_media_rich_sample.zip"]["artifact_kind"] == "source_case_bundle"
    assert "process" in entries["case_files_media_rich_sample.zip"]["primary_for"]
    assert "knowledge" in entries["case_files_media_rich_sample.zip"]["primary_for"]
    assert entries["knowledge_files_sample.zip"]["artifact_kind"] == "knowledge_files"
    assert "share" in entries["knowledge_files_sample.zip"]["primary_for"]
    assert entries["search_intake_examples_sample.zip"]["artifact_kind"] == "search_intake"
    assert entries["prompt_eval_training_seed_sample.zip"]["artifact_kind"] == "prompt_eval_training_seed"


def test_each_sample_zip_opens_and_matches_manifest_expectations():
    from duecare.chat.app import KO_TYPES

    for entry in _sample_manifest()["entries"]:
        path = SAMPLES / entry["name"]
        assert path.exists(), entry["name"]
        assert path.stat().st_size > 0
        if entry["artifact_kind"] == "single_envelope_example":
            env = json.loads(path.read_text(encoding="utf-8"))
            assert env["schema_version"] == "1.0"
            assert env["knowledge_object_type"] in KO_TYPES
            assert isinstance(env["content"], dict)
            assert isinstance(env.get("provenance"), dict)
            continue
        if path.suffix.lower() != ".zip":
            continue

        with zipfile.ZipFile(path) as zf:
            names = [name for name in zf.namelist() if not name.endswith("/")]
            assert names, entry["name"]
            if entry.get("expects_readme"):
                assert any("readme" in name.lower() for name in names), entry["name"]
            if entry.get("expects_manifest_or_metadata"):
                assert any(
                    "manifest" in name.lower() or "metadata" in name.lower()
                    for name in names
                ), entry["name"]

            if entry["artifact_kind"] == "knowledge_files":
                envelope_names = [
                    name
                    for name in names
                    if name.endswith(".json")
                    and "/" in name
                    and not name.lower().endswith("manifest.json")
                ]
                assert envelope_names, entry["name"]
                for envelope_name in envelope_names:
                    ko_type, leaf = envelope_name.split("/", 1)
                    env = json.loads(zf.read(envelope_name))
                    assert ko_type in KO_TYPES
                    assert env["schema_version"] == "1.0"
                    assert env["knowledge_object_type"] == ko_type
                    assert leaf == env["id"] + ".json"
                    assert isinstance(env["content"], dict)


def test_knowledge_import_export_round_trip_uses_knowledge_files_name(monkeypatch):
    client_root = Path.cwd() / ".pytest-tmp-local" / "inventory-import-export"
    shutil.rmtree(client_root, ignore_errors=True)
    monkeypatch.setenv("DUECARE_KNOWLEDGE_ROOT", str(client_root))
    client = _client()

    sample = SAMPLES / "knowledge_files_sample.zip"
    try:
        imported = client.post(
            "/api/knowledge/import",
            files={"file": (sample.name, io.BytesIO(sample.read_bytes()), "application/zip")},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json()["n_rejected"] == 0

        exported = client.get("/api/knowledge/export")
        assert exported.status_code == 200, exported.text
        assert "knowledge_files.zip" in exported.headers.get("content-disposition", "")
        with zipfile.ZipFile(io.BytesIO(exported.content)) as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert any(name.startswith("grep_rule/") for name in names)
            assert any(name.startswith("rag_doc/") for name in names)
    finally:
        shutil.rmtree(client_root, ignore_errors=True)


def test_harness_specs_and_knowledge_manifests_are_complete():
    from duecare.chat.app import KO_TYPES
    from duecare.chat.harnesses import all_harnesses
    from duecare.chat.harnesses.base import HarnessSpec

    for module in all_harnesses():
        name = getattr(module, "name")
        spec = getattr(module, "spec")
        assert isinstance(spec, HarnessSpec), name
        assert spec.workflow, name
        assert spec.prompt_sets, name
        assert spec.knowledge_flow, name
        assert spec.model_fit, name
        assert (Path(module.__file__).parent / "README.md").exists(), name
        assert set(getattr(module, "consumes", ())).issubset(KO_TYPES), name
        assert set(getattr(module, "emits", ())).issubset(KO_TYPES), name

    by_name = {getattr(module, "name"): module for module in all_harnesses()}
    assert {"extracted_fact", "entity_signal", "modus_operandi"}.issubset(
        set(by_name["process"].emits)
    )
    assert {"rag_doc", "ngo_directory", "extracted_fact", "entity_signal", "modus_operandi"}.issubset(
        set(by_name["extraction"].emits)
    )


def test_taxonomy_docs_and_pages_do_not_carry_stale_leaf_counts():
    checked = [
        Path("docs/knowledge_module_schema.md"),
        Path("docs/adr/007-knowledge-object-taxonomy.md"),
        STATIC / "getting-started.html",
        STATIC / "knowledge.html",
        STATIC / "status.html",
        Path("apps/duecare-ai.com/app/templates/hub.html"),
        Path("apps/duecare-ai.com/app/templates/technical-docs.html"),
    ]
    for path in checked:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "21 leaf" not in text, str(path)
        assert "21 leaves" not in text, str(path)
        assert "6 branches" not in text, str(path)
        assert "6-branch" not in text, str(path)
        assert "28" in text or "live taxonomy" in text, str(path)


def test_public_and_kernel_taxonomy_pages_name_all_branches():
    pages = [
        STATIC / "getting-started.html",
        STATIC / "knowledge.html",
        STATIC / "status.html",
        Path("apps/duecare-ai.com/app/templates/hub.html"),
        Path("apps/duecare-ai.com/app/templates/technical-docs.html"),
    ]
    required = [
        "matching_knowledge",
        "grounding_knowledge",
        "reasoning_knowledge",
        "evaluation_knowledge",
        "tool_knowledge",
        "input_knowledge",
        "output_knowledge",
    ]
    for path in pages:
        text = path.read_text(encoding="utf-8", errors="replace")
        missing = [branch for branch in required if branch not in text]
        assert not missing, f"{path}: {missing}"


def test_getting_started_and_knowledge_link_type_catalog():
    for path in [STATIC / "getting-started.html", STATIC / "knowledge.html", STATIC / "ui-audit.html"]:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert "/api/knowledge/type-catalog" in text, str(path)


def test_manifest_static_pages_and_same_origin_assets_are_reachable():
    client = _client()
    manifest = json.loads((STATIC / "ui_audit_manifest.json").read_text(encoding="utf-8"))
    checked_routes: set[str] = set()

    for page in manifest["static_pages"]:
        route = page["route"]
        response = client.get(route)
        assert response.status_code == 200, route
        assert len(response.text) > 100, route
        checked_routes.add(route)

        for ref in re.findall(r"""(?:href|src)=["'](/static/[^"']+)["']""", response.text):
            parsed = urlparse(ref)
            asset_path = parsed.path
            if asset_path in checked_routes:
                continue
            asset_response = client.get(asset_path)
            assert asset_response.status_code == 200, f"{route} -> {asset_path}"
            checked_routes.add(asset_path)


def test_full_workbench_core_paths_and_primary_samples_serve():
    client = _client()
    for route in [
        "/",
        "/static/index.html",
        "/static/process.html",
        "/static/knowledge.html",
        "/static/search.html",
        "/static/share.html",
        "/api/version",
        "/api/portability",
        "/api/experiment-contract",
        "/api/audit/workbench-inventory",
        "/api/knowledge/type-catalog",
    ]:
        response = client.get(route)
        assert response.status_code == 200, route

    sample = client.get("/static/samples/case_files_media_rich_sample.zip")
    assert sample.status_code == 200
    assert sample.content[:2] == b"PK"


def test_minimal_shell_artifact_links_preserve_nested_output_paths(tmp_path):
    from duecare.chat.kernel_shell import _render_summary_html

    nested = tmp_path / "reports" / "results.json"
    nested.parent.mkdir()
    nested.write_text("{}", encoding="utf-8")
    summary = {
        "title": "Nested artifact smoke",
        "artifacts": [{"name": "results.json", "path": str(nested)}],
    }

    html_out = _render_summary_html(summary, "test-kernel", artifact_root=tmp_path)
    assert 'href="/artifact/reports/results.json"' in html_out
    assert 'href="/artifact/results.json"' not in html_out
    assert "\u00e2" not in html_out
    assert "\u00c2\u00b7" not in html_out


def test_minimal_shell_exposes_reusable_contract_endpoints():
    from duecare.chat.kernel_shell import build_minimal_shell

    app, _ = build_minimal_shell(
        {"title": "Shell contract smoke", "results": []},
        kernel_id="contract-smoke",
        background=False,
        tunnel=False,
    )
    client = TestClient(app)

    portability = client.get("/api/portability")
    assert portability.status_code == 200, portability.text
    payload = portability.json()
    assert payload["schema_version"] == "duecare.portability_contract.v1"
    assert payload["served_by"] == "minimal-shell"
    assert payload["kernel"] == "contract-smoke"
    assert payload["evaluation"]["ok"] is True

    experiment = client.get("/api/experiment-contract")
    assert experiment.status_code == 200, experiment.text
    exp_payload = experiment.json()
    assert exp_payload["schema_version"] == "duecare.experiment_contract.v1"
    assert exp_payload["quantitative_run_profiles"]["bulk_text_25"]["limit"] == 25


def test_minimal_shell_serves_standard_paths_and_blocks_artifact_escape(tmp_path):
    from duecare.chat.kernel_shell import build_minimal_shell

    nested = tmp_path / "nested" / "result.json"
    nested.parent.mkdir()
    nested.write_text('{"ok": true}', encoding="utf-8")
    app, public_url = build_minimal_shell(
        {
            "title": "Shell path simulation",
            "lede": "local endpoint path simulation",
            "artifacts": [{"name": "result.json", "path": str(nested)}],
        },
        kernel_id="path-sim",
        artifact_root=tmp_path,
        background=False,
        tunnel=False,
    )
    client = TestClient(app)

    assert public_url is None
    for route in [
        "/",
        "/summary",
        "/api/version",
        "/api/portability",
        "/api/experiment-contract",
        "/api/model-info",
        "/api/brand",
        "/api/dc-logs",
        "/api/dc-logs/stats",
        "/artifact/nested/result.json",
    ]:
        response = client.get(route)
        assert response.status_code == 200, route

    assert client.get("/artifact/../kernel.py").status_code in {403, 404}
