from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_deferred_work_register as builder  # noqa: E402
import validate_deferred_work as validator  # noqa: E402


def _registry() -> dict:
    return json.loads(builder.REGISTRY_PATH.read_text(encoding="utf-8"))


def test_canonical_deferred_work_register_is_valid_and_current() -> None:
    result = validator.validate()

    assert result["ok"] is True
    assert result["items"] >= 10
    assert result["findings"] == []


def test_rendered_document_names_every_item_and_exact_acceptance_boundary() -> None:
    data = _registry()
    rendered = builder.render_registry(data)

    assert rendered == builder.DOCUMENT_PATH.read_text(encoding="utf-8")
    assert "Empty fields, fabricated approvals, guessed versions" in rendered
    assert "**Ready for model-free repository work:** None." in rendered
    for item in data["items"]:
        assert f'<a id="{item["id"]}"></a>' in rendered
        assert item["acceptance_gates"][0] in rendered


def test_unresolved_token_is_rejected_without_echoing_its_value() -> None:
    data = _registry()
    data["items"][0]["reason"] = "TBD"

    findings = validator.validate_registry(data)

    assert any("unresolved token category=tbd" in finding for finding in findings)
    assert all("TBD" not in finding for finding in findings)


def test_missing_and_cyclic_dependencies_are_rejected() -> None:
    data = copy.deepcopy(_registry())
    first = data["items"][0]
    second = data["items"][1]
    first["depends_on"] = [second["id"]]
    second["depends_on"] = [first["id"], "not-a-real-item"]

    findings = validator.validate_registry(data)

    assert any("dependency missing" in finding for finding in findings)
    assert any("dependency cycle" in finding for finding in findings)


def test_ready_local_item_must_remain_offline_and_zero_credit() -> None:
    data = copy.deepcopy(_registry())
    ready = data["items"][0]
    ready["status"] = "ready_local"
    ready["model_credit_policy"] = "zero_only"
    ready["network_policy"] = "owner_authorized_write"

    findings = validator.validate_registry(data)

    assert f"{ready['id']} ready_local boundary invalid" in findings


def test_malformed_field_types_return_findings_instead_of_crashing(tmp_path: Path) -> None:
    data = copy.deepcopy(_registry())
    data["items"][0]["priority"] = []
    data["items"][0]["status"] = {}
    registry = tmp_path / "deferred.json"
    registry.write_text(json.dumps(data), encoding="utf-8")

    result = validator.validate(registry, tmp_path / "DEFERRED_WORK.md", ROOT)

    assert result["ok"] is False
    assert result["findings"]
    assert any("priority invalid" in finding for finding in result["findings"])
    assert any("status invalid" in finding for finding in result["findings"])
