from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient


SAMPLES = (
    Path(__file__).parents[1]
    / "src"
    / "duecare"
    / "chat"
    / "static"
    / "samples"
)


def _zip_names(name: str) -> list[str]:
    with zipfile.ZipFile(SAMPLES / name) as zf:
        return [n for n in zf.namelist() if not n.endswith("/")]


def test_static_sample_catalog_contains_rich_downloadables():
    expected = {
        "case_files_sample.zip",
        "case_files_media_rich_sample.zip",
        "knowledge_bundle_sample.zip",
        "knowledge_pack_rich_sample.zip",
        "knowledge_source_examples_sample.zip",
        "search_intake_examples_sample.zip",
        "prompt_eval_training_seed_sample.zip",
    }
    missing = [name for name in expected if not (SAMPLES / name).exists()]
    assert not missing
    assert all((SAMPLES / name).stat().st_size > 1000 for name in expected)


def test_rich_knowledge_pack_uses_importable_envelope_paths():
    from duecare.chat.app import KO_TYPES

    names = _zip_names("knowledge_pack_rich_sample.zip")
    assert "README.txt" in names
    envelope_names = [n for n in names if n.endswith(".json")]
    assert len(envelope_names) >= 25

    types_seen: set[str] = set()
    with zipfile.ZipFile(SAMPLES / "knowledge_pack_rich_sample.zip") as zf:
        for name in envelope_names:
            ko_type, leaf = name.split("/", 1)
            env = json.loads(zf.read(name))
            assert ko_type in KO_TYPES
            assert env["schema_version"] == "1.0"
            assert env["knowledge_object_type"] == ko_type
            assert leaf == env["id"] + ".json"
            assert isinstance(env["content"], dict)
            types_seen.add(ko_type)

    assert {
        "grep_rule",
        "rag_doc",
        "ngo_directory",
        "modus_operandi",
        "evaluation_dimension",
        "tool_definition",
        "fact_template",
        "submission_schema",
    }.issubset(types_seen)


def test_knowledge_source_examples_parse_for_drafting():
    from duecare.chat.app import create_app

    client = TestClient(create_app())
    sample = SAMPLES / "knowledge_source_examples_sample.zip"
    response = client.post(
        "/api/knowledge/source-file",
        files={"file": (sample.name, io.BytesIO(sample.read_bytes()), "application/zip")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["n_rows_total"] >= 6
    assert body["n_media_assets"] >= 2
    assert "Knowledge source upload" in body["raw_text"]
    assert "retaliation" in body["raw_text"].lower()
    assert "salary deduction" in body["raw_text"].lower()


def test_search_and_training_seed_samples_have_expected_assets():
    search_names = _zip_names("search_intake_examples_sample.zip")
    assert "queries/public_source_queries.jsonl" in search_names
    assert "results/source_cards.json" in search_names
    assert any(n.startswith("draft_envelopes/rag_doc/") for n in search_names)
    assert "manifest/repeatability_manifest.json" in search_names

    training_names = _zip_names("prompt_eval_training_seed_sample.zip")
    assert "prompt_sets/use_case_prompts.jsonl" in training_names
    assert "prompt_sets/adversarial_prompts.jsonl" in training_names
    assert "rubrics/evaluation_dimensions.json" in training_names
    assert "training/synthetic_sft_pairs.jsonl" in training_names
    assert "training/preference_pairs.jsonl" in training_names
    assert "training/tool_call_examples.jsonl" in training_names
    assert "manifest/finetune_seed_manifest.json" in training_names


def test_pages_link_downloadable_sample_packs():
    from duecare.chat.app import create_app

    client = TestClient(create_app())
    knowledge = client.get("/static/knowledge.html")
    assert knowledge.status_code == 200
    assert "knowledge_source_examples_sample.zip" in knowledge.text
    assert "knowledge_pack_rich_sample.zip" in knowledge.text
    assert "Download sample bundle" not in knowledge.text

    search = client.get("/static/search.html")
    assert search.status_code == 200
    assert "search_intake_examples_sample.zip" in search.text
    assert "prompt_eval_training_seed_sample.zip" in search.text

    compare = client.get("/static/compare.html")
    assert compare.status_code == 200
    assert "prompt_eval_training_seed_sample.zip" in compare.text
