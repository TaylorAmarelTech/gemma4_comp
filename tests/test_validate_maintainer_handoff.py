from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_maintainer_handoff.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_maintainer_handoff", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


vmh = _load_module()


def test_live_handoff_documents_validate():
    result = vmh.validate(ROOT)

    assert result["ok"], [check for check in result["checks"] if not check["ok"]]


def test_missing_markers_are_reported_by_name():
    markers = ("## First 30 Minutes", "## Sources Of Truth")

    assert vmh.missing_markers("## First 30 Minutes\n", markers) == [
        "## Sources Of Truth"
    ]


def test_sensitive_scan_and_summary_never_echo_payloads():
    email = "maintainer@example.org"
    token = "sk-exampletoken12345"
    local_path = "C:\\Users\\person\\Documents\\private.txt"
    counts = vmh.sensitive_category_counts(f"{email} {token} {local_path}")
    summary = vmh.summarize_category_counts(counts)

    assert counts == {
        "email_address": 1,
        "windows_user_path": 1,
        "secret_token": 1,
    }
    assert summary == "email_address=1, secret_token=1, windows_user_path=1"
    assert email not in summary
    assert token not in summary
    assert local_path not in summary


def test_local_link_validator_accepts_existing_and_rejects_missing(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    existing = docs / "existing.md"
    existing.write_text("# Existing\n", encoding="utf-8")
    source = docs / "source.md"
    source.write_text(
        "[existing](existing.md) [anchor](#section) "
        "[external](https://example.org) [missing](missing.md)\n",
        encoding="utf-8",
    )

    assert vmh.broken_local_links(source, tmp_path) == ["missing.md"]


def test_unchecked_acceptance_boxes_are_not_placeholders():
    assert vmh.placeholder_category_counts("- [ ] Complete the transfer\n") == {}


def test_deployment_contract_rejects_a_competing_pages_workflow(tmp_path):
    workflow = tmp_path / ".github" / "workflows" / "pages.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("uses: actions/deploy-pages@v4\n", encoding="utf-8")

    findings = vmh.deployment_contract_findings(tmp_path)

    assert "competing Pages deploy workflow exists" in findings


def test_public_continuity_surface_reports_missing_route(tmp_path):
    findings = vmh.public_continuity_surface_findings(tmp_path)

    assert "project status route missing" in findings
