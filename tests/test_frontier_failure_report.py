"""Tests for scripts/build_frontier_failure_report.py -- failure-rate analysis + themed report.

Offline: synthetic per-dimension cells + prompt metadata, no network.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fr = _load("build_frontier_failure_report", _ROOT / "scripts" / "build_frontier_failure_report.py")

_META = {"p1": {"category": "business_framed", "difficulty": "hard"},
         "p2": {"category": "jurisdictional", "difficulty": "easy"}}


def _cells():
    out = []
    for pid in ("p1", "p2"):
        # legal_specificity: baseline FAILS (3<5), harnessed passes (8)
        # government_regulator_contact: both fail (2<5) -- harness doesn't help it
        for dim, base, harn in [("legal_specificity", 3.0, 8.0),
                                ("government_regulator_contact", 2.0, 2.0)]:
            out += [{"prompt_id": pid, "model": "m", "arm": "baseline", "dim": dim, "score": base},
                    {"prompt_id": pid, "model": "m", "arm": "harnessed", "dim": dim, "score": harn}]
    return out


def test_fail_rate_is_share_below_midpoint():
    assert fr._fail_rate([3.0, 8.0, 2.0]) == 2 / 3       # 3 and 2 are < 5
    assert fr._fail_rate([]) == 0.0


def test_bar_renders_percentage():
    b = fr._bar(0.5, width=10)
    assert "50%" in b and "█" in b and "░" in b


def test_theme_map_assigns_each_dimension_to_one_theme():
    counts = Counter(d for dims in fr.THEMES.values() for d in dims)
    dups = [d for d, n in counts.items() if n > 1]
    assert not dups, f"dimensions in >1 theme: {dups}"


def test_build_report_has_themes_categories_difficulty_and_honest_conclusions(tmp_path):
    md = fr.build_report(_cells(), _META, out_path=tmp_path / "r.md")
    assert "failure analysis" in md.lower()
    for section in ("Failure rate by theme", "by exploitation type", "Failure rate by difficulty",
                    "Conclusions"):
        assert section in md, section
    # the helped theme (legal, 100%->0%) and the un-helped theme (contacts, 100%->100%) both appear
    assert "Legal grounding / specificity" in md and "Protective contacts & procedure" in md
    # difficulty buckets come from metadata (the category table needs n>=30, not met by a tiny set)
    assert "**hard**" in md or "**easy**" in md


def test_load_prompt_meta(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"prompts": [{"id": "x", "category": "a", "difficulty": "hard"}]}', encoding="utf-8")
    m = fr.load_prompt_meta(p)
    assert m["x"]["category"] == "a" and m["x"]["difficulty"] == "hard"


def test_load_prompt_meta_skips_malformed_and_incomplete_entries(tmp_path):
    good = tmp_path / "good.json"
    bad = tmp_path / "bad.json"
    good.write_text(json.dumps({
        "prompts": [
            {"id": "x", "category": "a", "difficulty": "hard"},
            {"category": "missing_id", "difficulty": "easy"},
            {"id": {"private": "worker@example.com"}, "category": "structured_id", "difficulty": "hard"},
            {"id": "y", "category": {"private": "worker@example.com"}, "difficulty": ["hard"]},
            ["not", "an", "object"],
        ]
    }), encoding="utf-8")
    bad.write_text("{not-json", encoding="utf-8")

    m = fr.load_prompt_meta([bad, good])

    assert m == {
        "x": {"category": "a", "difficulty": "hard"},
        "y": {"category": "unknown", "difficulty": "unknown"},
    }


def test_build_report_redacts_sensitive_public_labels(tmp_path):
    model = "worker@example.com-case-123456789"
    category = "private@example.com-case-987654321"
    difficulty = "call +1 555 0100"
    cells = []
    meta = {}
    for i in range(15):
        pid = f"p{i}"
        meta[pid] = {"category": category, "difficulty": difficulty}
        for row in _cells():
            row = dict(row)
            row["prompt_id"] = pid
            row["model"] = model
            cells.append(row)

    md = fr.build_report(cells, meta, out_path=tmp_path / "r.md")

    assert model not in md
    assert category not in md
    assert difficulty not in md
    assert "`redacted`" in md


def test_main_success_console_redacts_sensitive_output_path(tmp_path, capsys):
    ckpt = tmp_path / "perdim.jsonl"
    ckpt.write_text("\n".join(json.dumps(row) for row in _cells()), encoding="utf-8")
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({
        "prompts": [
            {"id": "p1", "category": "business_framed", "difficulty": "hard"},
            {"id": "p2", "category": "jurisdictional", "difficulty": "easy"},
        ]
    }), encoding="utf-8")
    out = tmp_path / "worker@example.com-case-123456789" / "frontier_failure.md"

    assert fr.main(["--ckpt", str(ckpt), "--corpus", str(corpus), "--out", str(out)]) == 0

    printed = capsys.readouterr().err
    assert out.exists()
    assert "report -> external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed


def test_main_missing_cells_console_redacts_sensitive_checkpoint_path(tmp_path, capsys):
    ckpt = tmp_path / "worker@example.com-case-123456789" / "missing.jsonl"

    assert fr.main(["--ckpt", str(ckpt), "--out", str(tmp_path / "out.md")]) == 1

    printed = capsys.readouterr().err
    assert "no per-dimension cells in external" in printed
    assert str(tmp_path) not in printed
    assert "worker@example.com" not in printed
    assert "case-123456789" not in printed
