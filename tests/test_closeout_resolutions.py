from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_closeout_resolution_receipt as builder  # noqa: E402
import validate_closeout_resolutions as validator  # noqa: E402


def _receipt() -> dict:
    return json.loads(builder.RECEIPT_PATH.read_text(encoding="utf-8"))


def test_canonical_closeout_receipt_is_valid_current_and_complete() -> None:
    result = validator.validate()

    assert result == {"ok": True, "items": 11, "findings": []}


def test_rendered_receipt_names_every_item_and_claim_boundary() -> None:
    data = _receipt()
    rendered = builder.render_receipt(data)

    assert rendered == builder.DOCUMENT_PATH.read_text(encoding="utf-8")
    assert "zero current" in rendered
    assert "not mean every proposed activity was" in rendered.replace("\n", " ")
    for item in data["items"]:
        assert f'<a id="{item["id"]}"></a>' in rendered
        assert item["claim_boundary"] in rendered


def test_placeholder_and_missing_evidence_are_rejected_without_echoing_payload() -> None:
    data = copy.deepcopy(_receipt())
    data["items"][0]["decision"] = "TBD"
    data["items"][1]["evidence"] = ["private/missing-secret.txt"]

    findings = validator.validate_receipt(data)

    assert any("unresolved token category=tbd" in finding for finding in findings)
    assert all("TBD" not in finding for finding in findings)
    assert any("evidence missing" in finding for finding in findings)


def test_missing_or_reordered_inherited_item_is_rejected() -> None:
    data = copy.deepcopy(_receipt())
    data["items"] = list(reversed(data["items"]))

    findings = validator.validate_receipt(data)

    assert "item ids or order do not match the inherited 11-item scope" in findings


def test_malformed_outcome_types_return_findings_instead_of_crashing() -> None:
    data = copy.deepcopy(_receipt())
    data["items"][0]["outcome"] = []
    data["items"][0]["reversible"] = "no"

    findings = validator.validate_receipt(data)

    assert "provider-usage-reconciliation outcome invalid" in findings
    assert "provider-usage-reconciliation reversible invalid" in findings
