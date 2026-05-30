"""Test the HTML lift-report generator (synthetic data, no agents)."""
from __future__ import annotations

import importlib
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

rep = importlib.import_module("build_lift_report")


def test_report_renders_lift_table_and_egregious_example(tmp_path, monkeypatch):
    ckpt = tmp_path / "ck.jsonl"
    out = tmp_path / "report.html"
    bench = tmp_path / "bench"
    bench.mkdir()
    reports = tmp_path / "reports"
    reports.mkdir()
    monkeypatch.setattr(rep, "_CKPT", ckpt)
    monkeypatch.setattr(rep, "_OUT", out)
    monkeypatch.setattr(rep, "_BENCH", bench)
    monkeypatch.setattr(rep, "_ROOT", tmp_path)

    # one prompt, gemma: harmful baseline (low), good harnessed (high)
    cells = []
    for dim, b, h in [("scheme_detection.x", 1.0, 9.0), ("response_quality.y", 2.0, 8.0)]:
        cells.append({"prompt_id": "p1", "model": "gemma", "arm": "baseline", "dim": dim, "score": b})
        cells.append({"prompt_id": "p1", "model": "gemma", "arm": "harnessed", "dim": dim, "score": h})
    ckpt.write_text("\n".join(json.dumps(c) for c in cells), encoding="utf-8")
    (bench / "harness_lift_prompts_500.json").write_text(
        json.dumps({"prompts": [{"id": "p1", "text": "worker fee question"}]}), encoding="utf-8")
    (reports / "x.responses.jsonl").write_text("\n".join(json.dumps(r) for r in [
        {"prompt_id": "p1", "model": "gemma", "arm": "baseline", "response": "Yes you can deduct it."},
        {"prompt_id": "p1", "model": "gemma", "arm": "harnessed", "response": "That is debt bondage; refuse."},
    ]), encoding="utf-8")

    path = rep.build()
    htmltext = path.read_text(encoding="utf-8")
    assert "Harness-Lift Report" in htmltext
    assert "gemma" in htmltext
    assert "+7.00" in htmltext or "+7.0" in htmltext          # lift = 8.5 - 1.5 = +7.0
    assert "Yes you can deduct it." in htmltext               # egregious baseline shown
    assert "That is debt bondage" in htmltext                 # harnessed counterpart shown
    assert "BASELINE" in htmltext and "HARNESSED" in htmltext
