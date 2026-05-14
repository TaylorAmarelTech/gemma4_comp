from __future__ import annotations

import py_compile
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
A00 = ROOT / "kaggle" / "A-00-omni-experiment-workbench" / "kernel.py"
PITCH = ROOT / "kaggle" / "03-duecare-video-pitch" / "kernel.py"


def test_a00_and_video_pitch_compile():
    py_compile.compile(str(A00), doraise=True)
    py_compile.compile(str(PITCH), doraise=True)


def test_a00_exposes_every_appendix_workflow():
    text = A00.read_text(encoding="utf-8")
    workflow_ids = set(re.findall(r'"(a\d{2}_[a-z0-9_]+)": \{', text))
    assert len(workflow_ids) == 25
    for slot in range(1, 25):
        assert any(w.startswith(f"a{slot:02d}_") for w in workflow_ids)


def test_a00_core_routes_are_registered():
    text = A00.read_text(encoding="utf-8")
    for route in [
        "/api/a00/model/load",
        "/api/a00/run-batch",
        "/api/a00/import-export",
        "/api/a00/report",
        "/api/a00/synthetic/generate",
        "/api/a00/train",
        "/api/a00/workflows/run",
        "/api/a00/research/upload",
    ]:
        assert route in text


def test_a00_has_judge_facing_quick_proof_and_research_flow():
    text = A00.read_text(encoding="utf-8")
    for marker in [
        "Recommended proof path",
        "quickProof",
        "runRedteamProof",
        "anti_tip_redteam_regressions",
        "Local research graph",
        "PRIMARY_NOTEBOOK_AUDIT",
        "_ensure_sample_comparison_runs",
        "_extract_research_graph",
    ]:
        assert marker in text


def test_a00_has_synthetic_polish_and_training_smoke_path():
    text = A00.read_text(encoding="utf-8")
    for marker in [
        "RESPONSE_BLUEPRINT",
        "MEMORY_TOOL_POLICY",
        "rubric_polisher",
        "_polish_training_response",
        "generatePolished",
        "finetuneSmoke",
    ]:
        assert marker in text


def test_a00_reports_dimension_level_evidence():
    text = A00.read_text(encoding="utf-8")
    for marker in [
        "Dimension-Level Evidence",
        "dimension_summary",
        "mean_score_0_10",
        "Mean dynamic weight",
    ]:
        assert marker in text
