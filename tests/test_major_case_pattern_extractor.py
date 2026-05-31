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


def test_committed_major_case_pattern_artifacts_are_pii_safe():
    out_dir = _ROOT / "configs" / "duecare" / "benchmarks" / "major_case_patterns"
    assert out_dir.exists()
    assert mc.validate_outputs_for_pii(out_dir) == []

    dims = json.loads((out_dir / "derived_dimensions.json").read_text(encoding="utf-8"))
    prompts = [json.loads(line) for line in (out_dir / "derived_prompts.jsonl").read_text(encoding="utf-8").splitlines()]
    facts = [json.loads(line) for line in (out_dir / "knowledge_facts.jsonl").read_text(encoding="utf-8").splitlines()]

    assert len(dims["dimensions"]) >= 10
    assert len(prompts) >= 20
    assert len(facts) >= 10
    assert all(p["metadata"]["pii_policy"] == "placeholders_only_no_case_snippets" for p in prompts)
