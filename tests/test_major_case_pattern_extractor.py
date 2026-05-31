from __future__ import annotations

import importlib
import json
import pathlib
import re
import sys
import zipfile

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

mc = importlib.import_module("major_case_pattern_extractor")


def _read_outputs(out_dir: pathlib.Path) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8")
        for p in out_dir.iterdir()
        if p.suffix in {".json", ".jsonl", ".md"}
    )


def test_extracts_patterns_without_emitting_pii_or_filenames(tmp_path):
    source = tmp_path / "source_cases"
    source.mkdir()
    raw_file = source / "case_jane_smith_private.txt"
    raw_file.write_text(
        "Jane Smith, john.doe@example.com, +1 202 555 0188, passport AB1234567. "
        "The agency called the recruitment fee a training fee and processing fee. "
        "The employer kept the passport for safekeeping, deducted repayment from salary, "
        "said she cannot leave, and threatened blacklist or deportation if she complains.",
        encoding="utf-8",
    )

    summary = mc.analyze_cases(source)
    out_dir = tmp_path / "out"
    mc.write_outputs(summary, out_dir)

    assert summary["pattern_counts"]["document_retention_control"] == 1
    assert summary["pattern_counts"]["debt_bondage_fee_stack"] == 1
    assert summary["pattern_counts"]["safekeeping_euphemism"] == 1
    assert summary["pattern_counts"]["training_orientation_fee_wrapper"] == 1
    assert summary["privacy"]["pii_redactions"]["email"] >= 1
    assert summary["privacy"]["pii_redactions"]["phone"] >= 1
    assert summary["privacy"]["pii_redactions"]["passport"] >= 1

    combined = _read_outputs(out_dir)
    assert "john.doe@example.com" not in combined
    assert "+1 202 555 0188" not in combined
    assert "AB1234567" not in combined
    assert "Jane Smith" not in combined
    assert "case_jane_smith_private" not in combined
    assert str(source) not in combined
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", combined)

    dims = json.loads((out_dir / "derived_dimensions.json").read_text(encoding="utf-8"))
    prompts = [json.loads(line) for line in (out_dir / "derived_prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    facts = [json.loads(line) for line in (out_dir / "knowledge_facts.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(d["id"].endswith(".safekeeping_euphemism") for d in dims["dimensions"])
    assert any("[WORKER]" in p["text"] and p["metadata"]["synthetic"] for p in prompts)
    assert any(f["fact_type"] == "camouflage_pattern" for f in facts)

    refs = summary["source_ids_by_pattern"]["document_retention_control"]
    assert refs and all(re.fullmatch(r"src_[a-f0-9]{16}", ref) for ref in refs)


def test_reads_docx_text_and_tracks_skipped_binary_extensions(tmp_path):
    source = tmp_path / "source_cases"
    source.mkdir()
    docx = source / "arrival_packet.docx"
    with zipfile.ZipFile(docx, "w") as zf:
        zf.writestr(
            "word/document.xml",
            "<w:document><w:body><w:t>Upon arrival the worker was told to sign a new contract "
            "with changed salary and a different job.</w:t></w:body></w:document>",
        )
    (source / "scan.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    summary = mc.analyze_cases(source)

    assert summary["pattern_counts"]["contract_or_role_substitution"] == 1
    assert summary["skipped_by_ext"][".png"] == 1
    assert summary["files_seen"] == 2


def test_detects_document_harvesting_and_visa_pretext(tmp_path):
    source = tmp_path / "source_cases"
    source.mkdir()
    (source / "document_upload.txt").write_text(
        "The recruiter asks [WORKER] to upload documents, including a passport copy, "
        "selfie, and bank account screenshot. They call the charge visa processing "
        "and document processing for travel documents.",
        encoding="utf-8",
    )

    summary = mc.analyze_cases(source)

    assert summary["pattern_counts"]["document_harvesting_identity_misuse"] == 1
    assert summary["pattern_counts"]["visa_travel_document_pretext"] == 1


def test_noisy_single_terms_do_not_trigger_cooccurrence_rules(tmp_path):
    source = tmp_path / "source_cases"
    source.mkdir()
    (source / "generic_vendor_audit.txt").write_text(
        "The vendor policy mentions an audit and a normal contract, but no worker control, "
        "payroll intermediary, or labor-supply chain.",
        encoding="utf-8",
    )

    summary = mc.analyze_cases(source)

    assert "subcontractor_chain_obscuring" not in summary["pattern_counts"]
    assert "evidence_suppression_or_audit_staging" not in summary["pattern_counts"]


def test_public_research_facts_have_required_source_metadata():
    facts = mc.public_research_facts()
    assert len(facts) >= 20
    required = {
        "id", "fact_type", "statement", "source_title", "publisher", "url",
        "accessed_date", "jurisdictions", "sectors", "related_indicators",
        "related_behavior_ids", "related_camouflage_ids", "confidence",
    }
    for fact in facts:
        assert required <= set(fact)
        assert fact["url"].startswith("https://")
        assert fact["source"] == "public_research"
        assert fact["statement"]


def test_scenario_mixer_is_deterministic_and_placeholder_safe(tmp_path):
    source = tmp_path / "source_cases"
    source.mkdir()
    (source / "fee_case.txt").write_text(
        "A worker describes a recruitment fee, processing fee, salary deduction, "
        "and a consent form saying the deduction is voluntary.",
        encoding="utf-8",
    )
    summary = mc.analyze_cases(source)

    first = mc.scenario_mix_prompts(summary, target=24, seed=7)
    second = mc.scenario_mix_prompts(summary, target=24, seed=7)

    assert first == second
    assert len(first) == 24
    assert len({p["text"] for p in first}) == 24
    assert all(p["metadata"]["synthetic"] for p in first)
    assert all("[WORKER]" in p["text"] or "[SECTOR:" in p["text"] for p in first)
    assert all(p["metadata"]["dimension_ids"] for p in first)
    assert {p["metadata"]["response_trap"] for p in first}


def test_harness_lift_prompt_merge_is_deterministic_and_synthetic(tmp_path):
    source = tmp_path / "source_cases"
    source.mkdir()
    (source / "mixed_case.txt").write_text(
        "A recruiter describes a recruitment fee, visa processing, passport copy upload, "
        "and a voluntary waiver with salary deduction.",
        encoding="utf-8",
    )
    summary = mc.analyze_cases(source)

    merged = mc.harness_lift_prompts(summary)
    again = mc.harness_lift_prompts(summary)

    assert merged == again
    assert len(merged) >= 200
    assert len({p["text"] for p in merged}) == len(merged)
    assert all(p["metadata"]["harness_lift_ready"] for p in merged)
    assert all(p["metadata"]["synthetic"] for p in merged)
    assert all(p["metadata"]["pii_policy"] == "placeholders_only_no_case_snippets" for p in merged)


def test_committed_major_case_pattern_artifacts_are_pii_safe():
    out_dir = _ROOT / "configs" / "duecare" / "benchmarks" / "major_case_patterns"
    assert out_dir.exists()
    assert mc.validate_outputs_for_pii(out_dir) == []

    dims = json.loads((out_dir / "derived_dimensions.json").read_text(encoding="utf-8"))
    prompts = [json.loads(line) for line in (out_dir / "derived_prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    scenario_prompts = [json.loads(line) for line in (out_dir / "scenario_mix_prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    harness_prompts = [json.loads(line) for line in (out_dir / "harness_lift_prompts_major_case.jsonl").read_text(encoding="utf-8").splitlines()]
    facts = [json.loads(line) for line in (out_dir / "knowledge_facts.jsonl").read_text(encoding="utf-8").splitlines()]
    public_facts = [json.loads(line) for line in (out_dir / "public_research_facts.jsonl").read_text(encoding="utf-8").splitlines()]
    coverage = json.loads((out_dir / "coverage_report.json").read_text(encoding="utf-8"))

    assert len(dims["dimensions"]) >= 30
    assert len(prompts) >= 20
    assert len(scenario_prompts) >= 200
    assert len(harness_prompts) >= 250
    assert len({p["text"] for p in harness_prompts}) == len(harness_prompts)
    assert all(p["metadata"]["harness_lift_ready"] for p in harness_prompts)
    assert len(facts) >= 50
    assert len(public_facts) >= 20
    assert all(p["metadata"]["pii_policy"] == "placeholders_only_no_case_snippets" for p in prompts)
    assert all(p["metadata"]["pii_policy"] == "placeholders_only_no_case_snippets" for p in scenario_prompts)
    assert coverage["targets"]["dimensions_ge_30"]
    assert coverage["targets"]["scenario_prompts_ge_200"]
    assert coverage["targets"]["harness_prompts_ge_250"]
    assert coverage["targets"]["knowledge_facts_ge_50"]
    assert coverage["targets"]["public_research_facts_ge_20"]
