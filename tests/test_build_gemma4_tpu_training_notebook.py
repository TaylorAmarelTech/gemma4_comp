from __future__ import annotations

import importlib.util
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_gemma4_tpu_training_notebook.py"
SPEC = importlib.util.spec_from_file_location("gemma4_tpu_notebook", SCRIPT)
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def _source_text(path: Path) -> str:
    notebook = nbformat.read(path, as_version=4)
    return "\n".join(str(cell.source) for cell in notebook.cells)


def test_tpu_notebook_has_bounded_fallback_attempts(tmp_path: Path) -> None:
    manifest = builder.build(tmp_path / "kernel")
    notebook = _source_text(tmp_path / "kernel" / "notebook.ipynb")

    assert manifest["code_cells_compiled"] is True
    assert len(manifest["model_sources"]) >= 3
    assert len(manifest["accelerator_resolution_order"]) >= 2
    assert manifest["fallback_attempt_timeout_seconds"] == 1800
    assert "DUECARE_TPU_ATTEMPT_TIMEOUT_SECONDS" in notebook
    assert "timeout=attempt_timeout_seconds" in notebook
    assert "except subprocess.TimeoutExpired" in notebook
    assert '"timed_out": timed_out' in notebook


def test_tpu_notebook_keeps_claim_boundaries(tmp_path: Path) -> None:
    builder.build(tmp_path / "kernel")
    notebook = _source_text(tmp_path / "kernel" / "notebook.ipynb")

    assert "victim-identification" in notebook
    assert "field-detection" in notebook
    assert "deterministic_source_grounded_remix" in notebook
    assert "free_standing_fictional_generation" in notebook
