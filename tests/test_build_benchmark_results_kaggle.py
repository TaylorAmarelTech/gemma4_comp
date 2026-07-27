from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = _ROOT / "scripts" / "build_benchmark_results_kaggle.py"
SPEC = importlib.util.spec_from_file_location("build_benchmark_results_kaggle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["build_benchmark_results_kaggle"] = MODULE
SPEC.loader.exec_module(MODULE)

_SENTINEL = "SYNTHETIC-PROMPT-TEXT-THAT-MUST-STAY-OUT-OF-PUBLISHED-FILES"


def _panel(tmp_path: Path) -> Path:
    rows = []
    for i in range(6):
        pid = f"P{i:03d}"
        for judge in ("gpt-oss:120b", "glm-5.2"):
            rows.append({"model": "gemma4:31b", "arm": "baseline", "prompt_id": pid,
                         "judge": judge, "score_0_100": 40.0,
                         "components": {"A": 8, "B": 8, "C": 8, "D": 8, "E": 8}})
            rows.append({"model": "gemma4:31b", "arm": "harness_core", "prompt_id": pid,
                         "judge": judge, "score_0_100": 80.0,
                         "components": {"A": 16, "B": 16, "C": 16, "D": 16, "E": 16}})
    path = tmp_path / "panel.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def _promptset(tmp_path: Path) -> Path:
    prompts = [
        {"id": f"P{i:03d}", "text": _SENTINEL,
         "category": "labor_trafficking", "corridor": "NP->QA",
         "difficulty": "medium", "source": "seed"}
        for i in range(6)
    ]
    path = tmp_path / "promptset.json"
    path.write_text(json.dumps({"version": "test", "prompts": prompts}), encoding="utf-8")
    return path


def test_build_produces_safe_grades_dataset(tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = MODULE.build(out, force=False, panel_path=_panel(tmp_path),
                          promptset_path=_promptset(tmp_path))
    assert result["grade_rows"] == 24
    assert result["graded_prompts"] == 6
    dataset = out / "dataset"
    grades = (dataset / "panel_grades.csv").read_text(encoding="utf-8")
    assert grades.splitlines()[0] == "model,arm,prompt_id,judge,score_0_100,A,B,C,D,E"
    # Prompt text must never leak into any published file.
    for name in ("panel_grades.csv", "prompt_metadata.csv", "harness_lift_analysis.json"):
        assert _SENTINEL not in (dataset / name).read_text(encoding="utf-8")
    manifest = json.loads((dataset / "release-manifest.json").read_text(encoding="utf-8"))
    assert manifest["contains_response_text_or_pii"] is False
    assert manifest["grade_rows"] == 24


def test_metadata_has_usability_fields_and_column_schema(tmp_path: Path) -> None:
    out = tmp_path / "out"
    MODULE.build(out, force=False, panel_path=_panel(tmp_path),
                 promptset_path=_promptset(tmp_path))
    meta = json.loads((out / "dataset" / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert meta["subtitle"] and len(meta["description"]) > 200
    # Kaggle caps keywords at 6 and requires a 20-80 char subtitle.
    assert 3 <= len(meta["keywords"]) <= 6
    assert 20 <= len(meta["subtitle"]) <= 80
    grades_resource = next(r for r in meta["resources"] if r["path"] == "panel_grades.csv")
    field_names = {f["name"] for f in grades_resource["schema"]["fields"]}
    assert {"model", "arm", "prompt_id", "judge", "score_0_100", "A", "E"} <= field_names
    assert all(f["description"] for f in grades_resource["schema"]["fields"])


def test_emits_two_runnable_notebooks_with_dataset_source(tmp_path: Path) -> None:
    out = tmp_path / "out"
    MODULE.build(out, force=False, panel_path=_panel(tmp_path),
                 promptset_path=_promptset(tmp_path))
    nb_dirs = sorted(p.name for p in (out / "notebooks").iterdir())
    assert nb_dirs == ["duecare-judge-agreement", "duecare-reproduce-harness-lift"]
    for slug in nb_dirs:
        meta_path = out / "notebooks" / slug / "kernel-metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["dataset_sources"] == [MODULE.DATASET_ID]
        assert meta["enable_internet"] is False
        nb = json.loads((out / "notebooks" / slug / "notebook.ipynb").read_text(encoding="utf-8"))
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), f"{slug}:cell", "exec")
