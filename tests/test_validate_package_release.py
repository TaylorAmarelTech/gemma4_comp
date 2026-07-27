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


def test_current_mixed_versions_fail_a_coordinated_release_tag():
    _, findings = vpr.validate("packages-v0.1.0")

    assert any(finding.check == "coordinated version" for finding in findings)


def test_generic_release_tag_is_rejected():
    _, findings = vpr.validate("v0.1.0")

    assert any(finding.check == "release tag" for finding in findings)
