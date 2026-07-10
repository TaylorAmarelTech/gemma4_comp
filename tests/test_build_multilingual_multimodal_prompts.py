"""Tests for scripts/build_multilingual_multimodal_prompts.py -- language + multimodal coverage (propose-only)."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mm = _load("build_multilingual_multimodal_prompts",
           _ROOT / "scripts" / "build_multilingual_multimodal_prompts.py")


def _fake_translator(prompt, *, model="", max_tokens=0, temperature=0.0):
    """Offline stand-in: returns schema-correct JSON, echoing the target language so variants differ."""
    lang = "target"
    m = re.search(r"produce THREE (.+?) variants", prompt)
    if m:
        lang = m.group(1).strip()
    return json.dumps({
        "translation": f"{lang}: full translation body",
        "code_switched": f"{lang}/English: code-switched body",
        "colloquial": f"{lang}: casual slang body",
    })


# ── (a) multilingual generation with a fake caller ──
def test_languages_for_corridor_origin_and_destination():
    langs = mm.languages_for_corridor("Philippines->Saudi Arabia")
    assert ("Tagalog", "tl") in langs           # origin language
    assert ("Arabic", "ar") in langs            # Gulf destination language
    assert ("Chinese", "zh") in mm.languages_for_corridor("Philippines->Hong Kong")
    assert mm.languages_for_corridor("various") == []   # no corridor -> no forced language


def test_multilingual_variants_schema_and_lineage():
    scenarios = [{
        "id": "s1", "text": "A recruiter is holding my passport until I repay a placement fee.",
        "category": "passport_confiscation", "corridor": "Philippines->Saudi Arabia",
        "difficulty": "medium", "source": "seed",
    }]
    items = mm.generate_multilingual_variants(scenarios, model="fake", caller=_fake_translator)

    # Philippines->Saudi Arabia => Tagalog + Arabic; 3 variant kinds each => 6 items
    assert len(items) == 6
    assert {it["language"] for it in items} == {"Tagalog", "Arabic"}
    assert {it["variant_kind"] for it in items} == {"full_translation", "code_switched", "colloquial_slang"}
    for it in items:
        # base schema preserved
        for field in ("id", "text", "category", "corridor", "difficulty", "source"):
            assert it.get(field), f"missing base field {field}"
        assert it["text"].strip()                       # never empty
        assert it["source_id"] == "s1"                  # lineage preserved
        assert it["source_text_en"].startswith("A recruiter")
        assert it["source"] == "multilingual_synthetic"
        assert it["_synthetic"] is True
    # unique ids per (language, variant)
    assert len({it["id"] for it in items}) == 4


def test_languages_override_forces_fixed_set_and_limit():
    scenarios = [{"id": "s2", "text": "hello", "corridor": "various", "category": "x", "source": "seed"}]
    override = [("Hindi", "hi"), ("Vietnamese", "vi")]
    items = mm.generate_multilingual_variants(scenarios, caller=_fake_translator,
                                              languages_override=override, limit_langs=1)
    # limit_langs=1 keeps only the first override language, 2 variants
    assert {it["language"] for it in items} == {"Hindi"}
    assert len(items) == 2


# ── (b) multimodal specs validate (required fields, synthetic-only, no PII) ──
def test_multimodal_specs_are_valid_and_synthetic():
    specs = mm.generate_multimodal_specs(corridors=["Nepal->Qatar"], n_per_kind=1)
    kinds = {s["image_kind"] for s in specs}
    assert kinds == set(mm.MULTIMODAL_TEMPLATES)         # all three image kinds covered
    for s in specs:
        assert mm.validate_multimodal_spec(s) == []      # required fields + synthetic + no PII
        assert s["modality"] == "image"
        assert s["_synthetic"] is True
        assert s["expected_indicators"]                  # non-empty indicator list
        assert not mm.has_pii(s["synthetic_image_description"])
        assert s["source"] == "multimodal_synthetic"


def test_multimodal_validation_flags_missing_fields_and_pii():
    good = mm.generate_multimodal_specs(corridors=["Nepal->Qatar"], n_per_kind=1)[0]

    leaky = dict(good)
    leaky["synthetic_image_description"] = good["synthetic_image_description"] + " contact agent@example.com"
    assert "pii_detected" in mm.validate_multimodal_spec(leaky)

    phone_leak = dict(good)
    phone_leak["instruction"] = good["instruction"] + " call +63 917 555 0100 now"
    assert "pii_detected" in mm.validate_multimodal_spec(phone_leak)

    missing = dict(good)
    missing["expected_indicators"] = []
    problems = mm.validate_multimodal_spec(missing)
    assert "empty:expected_indicators" in problems

    not_synth = dict(good)
    not_synth["_synthetic"] = False
    assert "not_marked_synthetic" in mm.validate_multimodal_spec(not_synth)


def test_generate_multimodal_specs_drops_invalid_by_default():
    # every emitted spec must be valid (validate=True path)
    specs = mm.generate_multimodal_specs(n_per_kind=3)
    assert specs
    assert all(mm.validate_multimodal_spec(s) == [] for s in specs)


# ── (c) staged output lands under reports/ with propose-only markers ──
def test_stage_writes_propose_only_markers(tmp_path):
    items = [{"id": "ML-abc", "text": "body", "language": "Tagalog", "variant_kind": "full_translation"}]
    path = mm.stage(items, task="multilingual-prompts", model="fake",
                    name="unit_ml.json", proposals_dir=tmp_path)

    assert path.parent == tmp_path                       # redirected staging honored
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["_synthetic"] is True
    assert payload["_propose_only"] is True
    assert payload["n"] == len(items)
    assert payload["items"] == items
    assert payload["task"] == "multilingual-prompts"


def test_stage_restores_original_proposals_dir(tmp_path):
    before = mm._LG.PROPOSALS_DIR
    mm.stage([{"id": "x"}], task="t", model="m", name="unit.json", proposals_dir=tmp_path)
    assert mm._LG.PROPOSALS_DIR == before               # module global restored after redirect


def test_main_dry_run_offline_both_modes(tmp_path):
    # tiny synthetic registry so multilingual mode needs no big file and no network
    registry = tmp_path / "reg.json"
    registry.write_text(json.dumps({"prompts": [
        {"id": "p1", "text": "My employer withholds my wages.", "category": "wage_deduction",
         "corridor": "Nepal->Qatar", "difficulty": "medium", "source": "seed"},
    ]}), encoding="utf-8")
    proposals = tmp_path / "proposals"

    rc = mm.main([
        "--mode", "both", "--dry-run", "--n", "1", "--mm-per-kind", "1",
        "--registry", str(registry), "--proposals-dir", str(proposals),
    ])
    assert rc == 0

    ml = json.loads((proposals / "multilingual_prompts.json").read_text(encoding="utf-8"))
    mmspecs = json.loads((proposals / "multimodal_prompt_specs.json").read_text(encoding="utf-8"))
    assert ml["_propose_only"] is True and ml["n"] >= 1
    assert mmspecs["_propose_only"] is True and mmspecs["n"] >= 1
    # multilingual items carry language + lineage; multimodal items validate clean
    assert all(it.get("language") and it.get("source_id") == "p1" for it in ml["items"])
    assert all(mm.validate_multimodal_spec(s) == [] for s in mmspecs["items"])
