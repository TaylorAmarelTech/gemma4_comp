"""Tests for scripts/audit_knowledge_vocabularies.py."""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "audit_knowledge_vocabularies.py"
_spec = importlib.util.spec_from_file_location("audit_knowledge_vocabularies", _SCRIPT)
akv = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(akv)


def _write_env(root: Path, leaf: str, name: str, content: dict) -> Path:
    path = root / leaf / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "id": name,
        "knowledge_object_type": leaf,
        "content": content,
    }), encoding="utf-8")
    return path


def test_load_vocabulary_uses_ast_without_importing_chat_package():
    vocab = akv.load_vocabulary()

    assert "fee_camouflage" in vocab.indicators
    assert "passport_retention" in vocab.indicators
    assert "wage_assignment" in vocab.indicators
    assert "employment" in vocab.stages
    assert vocab.indicator_aliases["fee-bondage"] == "fee_bondage"
    assert vocab.indicator_aliases["wage assignment"] == "wage_assignment"
    assert vocab.indicator_aliases["deception"] == "deceptive_recruitment"
    assert vocab.indicator_aliases["withholding_of_wages"] == "withheld_wages"
    assert vocab.indicator_aliases["restriction_of_movement"] == "movement_restriction"
    assert vocab.indicator_aliases["retention_of_identity_documents"] == "passport_retention"
    assert vocab.stage_aliases["arrival"] == "arrival_and_placement"


def test_audit_store_buckets_canonical_alias_and_unknown_tokens(tmp_path):
    _write_env(tmp_path, "extracted_fact", "one", {
        "indicators": ["fee_camouflage", "FeeBondage", "wage assignment", "mystery_signal"],
        "applies_to_indicators": ["passport"],
        "risk_indicators": ["jurisdiction shopping", "untracked_risk"],
        "signal_types": [
            "deception",
            "contract substitution",
            "withholding_of_wages",
            "restriction_of_movement",
            "retention_of_identity_documents",
        ],
        "corridor": "PH-HK",
        "corridors": ["ph/hk", "not-a-corridor"],
        "journey_stage": "arrival",
        "stages": ["employment", "unknown_stage"],
    })

    result = akv.audit_store(tmp_path, akv.load_vocabulary())

    assert result.envelopes_scanned == 1
    assert result.canonical["fee_camouflage"] == 1
    assert result.canonical["PH-HK"] == 1
    assert result.canonical["employment"] == 1
    assert result.known_alias["FeeBondage"] == 1
    assert result.alias_targets["FeeBondage"] == "fee_bondage"
    assert result.known_alias["wage assignment"] == 1
    assert result.alias_targets["wage assignment"] == "wage_assignment"
    assert result.known_alias["passport"] == 1
    assert result.alias_targets["passport"] == "passport_retention"
    assert result.known_alias["jurisdiction shopping"] == 1
    assert result.alias_targets["jurisdiction shopping"] == "jurisdiction_shopping"
    assert result.known_alias["deception"] == 1
    assert result.alias_targets["deception"] == "deceptive_recruitment"
    assert result.known_alias["contract substitution"] == 1
    assert result.alias_targets["contract substitution"] == "deceptive_recruitment"
    assert result.known_alias["withholding_of_wages"] == 1
    assert result.alias_targets["withholding_of_wages"] == "withheld_wages"
    assert result.known_alias["restriction_of_movement"] == 1
    assert result.alias_targets["restriction_of_movement"] == "movement_restriction"
    assert result.known_alias["retention_of_identity_documents"] == 1
    assert result.alias_targets["retention_of_identity_documents"] == "passport_retention"
    assert result.known_alias["ph/hk"] == 1
    assert result.alias_targets["ph/hk"] == "PH-HK"
    assert result.known_alias["arrival"] == 1
    assert result.alias_targets["arrival"] == "arrival_and_placement"
    assert result.unknown["mystery_signal"] == 1
    assert result.unknown["untracked_risk"] == 1
    assert result.unknown["not-a-corridor"] == 1
    assert result.unknown["unknown_stage"] == 1


def test_format_report_lists_unknown_paths_and_fields(tmp_path):
    _write_env(tmp_path, "extracted_fact", "one", {
        "indicators": ["new_signal"],
        "journey_stage": "arrival",
    })
    result = akv.audit_store(tmp_path, akv.load_vocabulary())

    report = akv.format_report(result)

    assert "Envelopes scanned: 1" in report
    assert "KNOWN_ALIAS" in report
    assert "arrival -> arrival_and_placement: 1" in report
    assert "UNKNOWN" in report
    assert "new_signal: 1" in report
    assert "one.json (indicators)" in report


def test_main_strict_returns_one_when_unknown_tokens_exist(tmp_path, capsys):
    _write_env(tmp_path, "extracted_fact", "one", {"indicators": ["new_signal"]})

    rc = akv.main(["--store-path", str(tmp_path), "--strict"])
    captured = capsys.readouterr()

    assert rc == 1
    assert "UNKNOWN" in captured.out
    assert "new_signal" in captured.out


def test_missing_store_is_non_blocking(tmp_path, capsys):
    missing = tmp_path / "missing"

    rc = akv.main(["--store-path", str(missing), "--strict"])
    captured = capsys.readouterr()

    assert rc == 0
    assert "No envelopes found" in captured.out


def test_script_imports_are_stdlib_only():
    tree = ast.parse(_SCRIPT.read_text(encoding="utf-8"))
    allowed = {
        "argparse",
        "ast",
        "collections",
        "dataclasses",
        "json",
        "os",
        "pathlib",
        "re",
        "sys",
        "typing",
    }
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
    non_stdlib = [name for name in imports if name and name.split(".")[0] not in allowed]

    assert non_stdlib == []
