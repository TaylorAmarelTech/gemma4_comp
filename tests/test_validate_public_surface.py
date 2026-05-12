from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_validator() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "validate_public_surface.py"
    spec = importlib.util.spec_from_file_location("validate_public_surface", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_file_allow_marker_accepts_header_html_comment() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# duecare-llm-research-tools",
            "",
            "<!-- audit-allow-file:drift",
            "reason: documents a real legacy symbol.",
            "-->",
            "",
            "Body text can include drift terms like OpenClaw.",
        ]
    )

    assert validator._has_file_allow(text)


def test_file_allow_marker_ignores_body_examples() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# Public-surface audit",
            "",
            "This doc explains how to allowlist a whole file.",
            "",
            "```markdown",
            "<!-- audit-allow-file:drift",
            "reason: example only.",
            "-->",
            "```",
        ]
    )

    assert not validator._has_file_allow(text)


def test_file_allow_marker_ignores_tilde_fence_examples() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# Public-surface audit",
            "",
            "~~~markdown",
            "<!-- audit-allow-file:drift",
            "reason: example only.",
            "-->",
            "~~~",
        ]
    )

    assert not validator._has_file_allow(text)


def test_file_allow_marker_ignores_comment_after_header_window() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# Audit docs",
            "line 2",
            "line 3",
            "line 4",
            "line 5",
            "line 6",
            "line 7",
            "line 8",
            "line 9",
            "line 10",
            "line 11",
            "line 12",
            "<!-- audit-allow-file:drift -->",
        ]
    )

    assert not validator._has_file_allow(text)


def test_file_allow_marker_ignores_non_comment_header_text() -> None:
    validator = _load_validator()

    text = "\n".join(
        [
            "# Audit docs",
            "The literal token audit-allow-file:drift is documented here.",
            "",
            "Body text.",
        ]
    )

    assert not validator._has_file_allow(text)


# ---- bundle_envelope_v1 helper: _line_or_above_has_allow -------------------

def test_line_allow_inline_match() -> None:
    validator = _load_validator()
    lines = [
        'payload = {',
        '    "aggregate": agg,  # audit-allow:drift -- phase result',
        '}',
    ]
    assert validator._line_or_above_has_allow(lines, 2)


def test_line_allow_directly_above_match() -> None:
    validator = _load_validator()
    lines = [
        '# audit-allow:drift -- legacy compat shim',
        '"aggregate": agg,',
    ]
    assert validator._line_or_above_has_allow(lines, 2)


def test_line_allow_two_above_is_rejected() -> None:
    validator = _load_validator()
    lines = [
        '# audit-allow:drift -- explanation',
        '# (continuation comment)',
        '"aggregate": agg,',
    ]
    assert not validator._line_or_above_has_allow(lines, 3)


def test_line_allow_out_of_range() -> None:
    validator = _load_validator()
    lines = ['"aggregate": agg,']
    assert not validator._line_or_above_has_allow(lines, 0)
    assert not validator._line_or_above_has_allow(lines, 5)


# ---- check_bundle_envelope_v1 -- end-to-end --------------------------------

def _setup_fake_kaggle(
    tmp_path: Path,
    validator: ModuleType,
    monkeypatch,
) -> Path:
    """Wire validator.ROOT + validator.KAGGLE to a clean tmp tree.

    Returns the KAGGLE dir that subsequent _write_fake_kernel calls
    should plant kernels under.
    """
    kaggle_dir = tmp_path / "kaggle"
    kaggle_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "KAGGLE", kaggle_dir)
    return kaggle_dir


def _write_fake_kernel(folder: Path, body: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "kernel.py").write_text(body, encoding="utf-8")


def test_bundle_envelope_clean_kernel(tmp_path: Path, monkeypatch) -> None:
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    _write_fake_kernel(
        kaggle / "A-99-clean",
        '\n'.join([
            'payload = {',
            '    "schema_version": "1.0",',
            '    "kernel_id": "a-99-clean",',
            '    "run_id": "a99_clean_2026-05-12T19-30-00Z",',
            '    "summary": {"n_results": 1},',
            '    "results": [],',
            '}',
        ]),
    )
    result = validator.check_bundle_envelope_v1()
    assert result.ok, result.findings


def test_bundle_envelope_detects_custom_schema_version(
    tmp_path: Path, monkeypatch,
) -> None:
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    _write_fake_kernel(
        kaggle / "A-99-bad-schema",
        '\n'.join([
            'payload = {',
            '    "schema_version": "duecare.custom.v9",',
            '}',
        ]),
    )
    result = validator.check_bundle_envelope_v1()
    assert any(
        f.rule == "bundle_envelope_v1.schema_version"
        for f in result.findings
    )


def test_bundle_envelope_detects_aggregate_only(
    tmp_path: Path, monkeypatch,
) -> None:
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    _write_fake_kernel(
        kaggle / "A-99-aggregate-only",
        '\n'.join([
            'payload = {',
            '    "kernel_id": "a-99",',
            '    "aggregate": {"n": 0},',
            '    "results": [],',
            '}',
        ]),
    )
    result = validator.check_bundle_envelope_v1()
    assert any(
        f.rule == "bundle_envelope_v1.aggregate"
        for f in result.findings
    )


def test_bundle_envelope_accepts_canonical_plus_alias(
    tmp_path: Path, monkeypatch,
) -> None:
    """Rollover state: BOTH canonical + legacy alias present is fine."""
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    _write_fake_kernel(
        kaggle / "A-99-rollover",
        '\n'.join([
            'payload = {',
            '    "schema_version": "1.0",',
            '    "summary": {"n": 0},',
            '    "aggregate": {"n": 0},',
            '    "results": [],',
            '    "proposals": [],',
            '}',
        ]),
    )
    result = validator.check_bundle_envelope_v1()
    assert result.ok, result.findings


def test_bundle_envelope_detects_legacy_results_aliases(
    tmp_path: Path, monkeypatch,
) -> None:
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    _write_fake_kernel(
        kaggle / "A-99-proposals-only",
        '\n'.join([
            'payload = {',
            '    "kernel_id": "a-99",',
            '    "summary": {},',
            '    "proposals": [],',
            '}',
        ]),
    )
    result = validator.check_bundle_envelope_v1()
    assert any(
        f.rule == "bundle_envelope_v1.results_alt"
        for f in result.findings
    )


def test_bundle_envelope_honors_inline_allow_marker(
    tmp_path: Path, monkeypatch,
) -> None:
    """An audit-allow:drift inline marker suppresses the finding."""
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    _write_fake_kernel(
        kaggle / "A-99-allow-marker",
        '\n'.join([
            'payload = {',
            '    "kernel_id": "a-99",',
            '    "aggregate": {"n": 0},  # audit-allow:drift -- phase key',
            '}',
        ]),
    )
    result = validator.check_bundle_envelope_v1()
    assert result.ok, result.findings


# ---- check_bundle_envelope_manifest_checksums ------------------------------

def test_manifest_checksums_clean_kernel(tmp_path: Path, monkeypatch) -> None:
    """Kernel with both manifest.json AND checksums map -- no finding."""
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    monkeypatch.setattr(
        validator, "_MANIFEST_CHECKSUM_GRANDFATHERED", frozenset()
    )
    _write_fake_kernel(
        kaggle / "A-99-clean",
        '\n'.join([
            'import zipfile, json',
            'with zipfile.ZipFile("/tmp/out.zip", "w") as z:',
            '    z.writestr("manifest.json", json.dumps({',
            '        "schema_version": "1.0",',
            '        "checksums": {"results.json": "abc123"},',
            '    }))',
        ]),
    )
    result = validator.check_bundle_envelope_manifest_checksums()
    assert result.ok, result.findings


def test_manifest_checksums_flags_missing_map(
    tmp_path: Path, monkeypatch,
) -> None:
    """Kernel writing manifest.json without a checksums map is flagged."""
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    monkeypatch.setattr(
        validator, "_MANIFEST_CHECKSUM_GRANDFATHERED", frozenset()
    )
    _write_fake_kernel(
        kaggle / "A-99-no-checksums",
        '\n'.join([
            'import zipfile, json',
            'with zipfile.ZipFile("/tmp/out.zip", "w") as z:',
            '    z.writestr("manifest.json", json.dumps({',
            '        "schema_version": "1.0",',
            '        "kernel_id": "a-99",',
            '    }))',
        ]),
    )
    result = validator.check_bundle_envelope_manifest_checksums()
    assert any(
        f.rule == "bundle_envelope_v1.manifest_checksums"
        for f in result.findings
    )


def test_manifest_checksums_skips_grandfathered(
    tmp_path: Path, monkeypatch,
) -> None:
    """Folders on the grandfathered list are skipped even when drifted."""
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    _write_fake_kernel(
        kaggle / "A-99-grandfathered",
        '\n'.join([
            'import zipfile, json',
            'with zipfile.ZipFile("/tmp/out.zip", "w") as z:',
            '    z.writestr("manifest.json", json.dumps({',
            '        "schema_version": "1.0",',
            '    }))',
        ]),
    )
    monkeypatch.setattr(
        validator, "_MANIFEST_CHECKSUM_GRANDFATHERED",
        frozenset({"kaggle/A-99-grandfathered/kernel.py"}),
    )
    result = validator.check_bundle_envelope_manifest_checksums()
    assert result.ok, result.findings


def test_manifest_checksums_honors_inline_allow_marker(
    tmp_path: Path, monkeypatch,
) -> None:
    """An audit-allow:drift comment near the writestr suppresses the find."""
    validator = _load_validator()
    kaggle = _setup_fake_kaggle(tmp_path, validator, monkeypatch)
    monkeypatch.setattr(
        validator, "_MANIFEST_CHECKSUM_GRANDFATHERED", frozenset()
    )
    _write_fake_kernel(
        kaggle / "A-99-allow",
        '\n'.join([
            'import zipfile, json',
            'with zipfile.ZipFile("/tmp/out.zip", "w") as z:',
            '    # audit-allow:drift -- export-asset manifest, not v1.0 bundle',
            '    z.writestr("manifest.json", json.dumps({',
            '        "schema_version": "1.0",',
            '    }))',
        ]),
    )
    result = validator.check_bundle_envelope_manifest_checksums()
    assert result.ok, result.findings
