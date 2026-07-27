from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_package_release.py"


def _load_module():
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("validate_package_release", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


vpr = _load_module()


def test_workspace_release_surface_is_reconciled():
    packages, findings = vpr.validate()

    assert len(packages) == 18
    assert not findings


def test_independent_release_tag_selects_one_matching_package():
    packages, findings = vpr.validate("package-duecare-llm-chat-v0.17.0")

    assert not findings
    assert vpr.selected_directories(
        packages, tag="package-duecare-llm-chat-v0.17.0"
    ) == ["duecare-llm-chat"]


def test_release_tag_version_must_match_manifest_and_pyproject():
    _, findings = vpr.validate("package-duecare-llm-chat-v0.1.0")

    assert any(finding.check == "release tag version" for finding in findings)


def test_manual_all_selection_uses_canonical_build_order():
    packages, findings = vpr.validate(package="all")

    assert not findings
    assert vpr.selected_directories(packages) == vpr.DEFAULT_BUILD_ORDER


def test_generic_release_tag_is_rejected():
    _, findings = vpr.validate("v0.1.0")

    assert any(finding.check == "release tag" for finding in findings)
