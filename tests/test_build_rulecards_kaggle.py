from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = _ROOT / "scripts" / "build_rulecards_kaggle.py"
SPEC = importlib.util.spec_from_file_location("build_rulecards_kaggle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["build_rulecards_kaggle"] = MODULE
SPEC.loader.exec_module(MODULE)


def test_redact_patterns_withholds_regex_but_keeps_metadata() -> None:
    card = {
        "rule_id": "usury_pattern_high_apr",
        "severity": "high",
        "authoritative_sources": ["ILO C029"],
        "antecedent": {"patterns": [r"\b(\d{2,3})\s*%\s*apr\b"], "all_required": False,
                       "min_capture_value": 30},
    }
    out = MODULE._redact_patterns(card)
    ant = out["antecedent"]
    assert "patterns" not in ant
    assert ant["pattern_count"] == 1
    assert ant["patterns_redacted"] is True
    # research metadata is preserved
    assert out["authoritative_sources"] == ["ILO C029"]
    assert ant["min_capture_value"] == 30


def test_public_deck_never_leaks_raw_regex(tmp_path: Path) -> None:
    out = tmp_path / "rc"
    MODULE.build(out, force=False)
    deck_path = out / "dataset" / "rulecard-deck.json"
    raw = deck_path.read_text(encoding="utf-8")
    deck = json.loads(raw)
    assert deck["patterns_redacted"] is True
    # No card retains the raw 'patterns' list, and known regex fragments are absent.
    assert all("patterns" not in (c.get("antecedent") or {}) for c in deck["cards"])
    for fragment in (r"\b(\d", "deduct|deduction", "p.a.|apr", "\\s*%\\s*"):
        assert fragment not in raw
    # The flat CSV also carries no patterns column.
    csv_head = (out / "dataset" / "rulecards.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "pattern" not in csv_head.lower()


def test_public_metadata_has_usability_and_dualuse_disclosure(tmp_path: Path) -> None:
    out = tmp_path / "rc"
    MODULE.build(out, force=False)
    meta = json.loads((out / "dataset" / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert 20 <= len(meta["subtitle"]) <= 80
    assert 3 <= len(meta["keywords"]) <= 6
    readme = (out / "dataset" / "README.md").read_text(encoding="utf-8")
    assert "Dual-use safeguard" in readme
    assert "pattern_count" in readme
