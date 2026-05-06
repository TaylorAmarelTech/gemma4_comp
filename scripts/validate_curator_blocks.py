"""scripts/validate_curator_blocks.py — schema + cross-reference check for the
12 curator-JSON files that drive the Duecare grader.

Stakeholder-friendly. Catches the malformed-PR class of bugs at edit time
rather than at runtime grading. Run from repo root:

  python scripts/validate_curator_blocks.py
  python scripts/validate_curator_blocks.py --strict   # exit non-zero on warnings too

Use cases:
  - NGO caseworker adds a Tagalog signal to _classifier_signals.json:
      checks the signal isn't empty, weight is a number, language tag is
      one of the supported BCP 47 codes, no duplicate of an existing
      signal+use_case pair.
  - Jurist updates a statute's section range in _known_statute_sections.json:
      checks min <= max, both ints, key is non-empty.
  - Researcher tunes a use-case affinity in _usecase_affinity.json:
      checks the dim_id exists in _rubric_universal.json (no ghost dims).
  - Curator adds a new evaluation question in _evaluation_questions.json:
      checks it covers a real rubric dim + has both question + hint.

Exits 0 on success, 1 on any error. Prints a human-readable report.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_DIR = REPO_ROOT / "packages/duecare-llm-chat/src/duecare/chat/harness"


# Curator-block envelope contract (every file must have these keys).
ENVELOPE_KEYS_REQUIRED = ("schema", "version", "last_updated", "curator", "notes")

# The expected rubric file (used as ground-truth for dim-id cross-refs).
RUBRIC_PATH = HARNESS_DIR / "_rubric_universal.json"


def _load(path: Path) -> dict[str, Any] | None:
    """Parse a JSON file; return None on failure with an error printed."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"  PARSE ERROR in {path.name}: {e}")
        return None


def _check_envelope(name: str, block: dict[str, Any]) -> list[str]:
    """Verify the curator-block envelope has all required metadata fields."""
    errs: list[str] = []
    for k in ENVELOPE_KEYS_REQUIRED:
        if k not in block:
            errs.append(f"{name}: missing envelope key {k!r}")
    if "schema" in block and not isinstance(block["schema"], str):
        errs.append(f"{name}: schema must be a string")
    if "version" in block and not isinstance(block["version"], str):
        errs.append(f"{name}: version must be a string")
    return errs


def _validate_classifier_signals(block: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Each entry: {use_case, signal, weight, lang?, added_by?, added_date?,
    rationale?}. use_case must be one of USE_CASES. signal must be lowercase.
    Weight must be a positive number. lang (if present) should be a BCP 47
    code from supported_languages."""
    errs: list[str] = []
    warns: list[str] = []
    use_cases = (
        "worker_asking", "ngo_intake", "lawyer_research",
        "regulator_audit", "journalist_fact_check",
        "researcher_tagging", "adversarial_recruiter",
    )
    supported = block.get("supported_languages", {}) or {}
    seen: set[tuple[str, str]] = set()  # (use_case, signal_lower)
    for i, e in enumerate(block.get("entries", []) or []):
        prefix = f"_classifier_signals.json[entry {i}]"
        if not isinstance(e, dict):
            errs.append(f"{prefix}: not a dict"); continue
        uc = e.get("use_case")
        sig = e.get("signal")
        w = e.get("weight")
        if uc not in use_cases:
            errs.append(f"{prefix}: use_case={uc!r} must be one of {use_cases}")
        if not isinstance(sig, str) or not sig.strip():
            errs.append(f"{prefix}: signal must be a non-empty string")
            continue
        if sig != sig.lower():
            warns.append(f"{prefix}: signal {sig!r} should be lowercase")
        try:
            wf = float(w)
            if wf <= 0:
                warns.append(f"{prefix}: weight={wf} should be > 0")
        except (TypeError, ValueError):
            errs.append(f"{prefix}: weight must be a number, got {w!r}")
            continue
        # Duplicate detection
        key = (uc, sig.lower())
        if key in seen:
            errs.append(f"{prefix}: duplicate ({uc}, {sig!r})")
        seen.add(key)
        # Language tag
        lang = e.get("lang")
        if lang is not None:
            if not isinstance(lang, str):
                errs.append(f"{prefix}: lang must be a string, got {type(lang).__name__}")
            elif supported and lang not in supported:
                warns.append(f"{prefix}: lang={lang!r} not in supported_languages "
                                f"({sorted(supported.keys())})")
    return errs, warns


def _validate_usecase_affinity(block: dict[str, Any], known_dims: set[str]
                                  ) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    use_cases = block.get("use_cases", {}) or {}
    if not isinstance(use_cases, dict):
        errs.append("_usecase_affinity.json: 'use_cases' must be a dict")
        return errs, warns
    for uc, dims in use_cases.items():
        if not isinstance(dims, dict):
            errs.append(f"_usecase_affinity[{uc}]: must be a dict of dim_id → spec")
            continue
        for dim_id, spec in dims.items():
            if dim_id not in known_dims:
                warns.append(f"_usecase_affinity[{uc}][{dim_id}]: unknown dim_id "
                              f"(not in _rubric_universal.json)")
            if isinstance(spec, dict):
                w = spec.get("weight")
                try:
                    float(w)
                except (TypeError, ValueError):
                    errs.append(f"_usecase_affinity[{uc}][{dim_id}]: weight must be a number")
            else:
                try:
                    float(spec)
                except (TypeError, ValueError):
                    errs.append(f"_usecase_affinity[{uc}][{dim_id}]: must be a number or {{weight,...}}")
    return errs, warns


def _validate_authoritative_statutes(block: dict[str, Any]
                                        ) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(block.get("entries", []) or []):
        prefix = f"_authoritative_statutes.json[entry {i}]"
        if isinstance(e, dict):
            n = e.get("name")
        elif isinstance(e, str):
            n = e
        else:
            errs.append(f"{prefix}: not a dict or string")
            continue
        if not isinstance(n, str) or not n.strip():
            errs.append(f"{prefix}: name must be non-empty string")
            continue
        if n != n.lower():
            warns.append(f"{prefix}: name {n!r} should be lowercase for substring matching")
        key = n.lower()
        if key in seen:
            warns.append(f"{prefix}: duplicate name {n!r}")
        seen.add(key)
    return errs, warns


def _validate_known_statute_sections(block: dict[str, Any]
                                        ) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(block.get("entries", []) or []):
        prefix = f"_known_statute_sections.json[entry {i}]"
        if not isinstance(e, dict):
            errs.append(f"{prefix}: not a dict")
            continue
        key = e.get("key")
        if not isinstance(key, str) or not key.strip():
            errs.append(f"{prefix}: key must be non-empty string")
            continue
        try:
            mn = int(e["min"])
            mx = int(e["max"])
        except (KeyError, TypeError, ValueError):
            errs.append(f"{prefix}: min and max must both be ints")
            continue
        if mn > mx:
            errs.append(f"{prefix}: min ({mn}) > max ({mx})")
        if key.lower() in seen:
            warns.append(f"{prefix}: duplicate key {key!r}")
        seen.add(key.lower())
    return errs, warns


def _validate_evaluation_questions(block: dict[str, Any], known_dims: set[str]
                                       ) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    qs = block.get("questions", {}) or {}
    if not isinstance(qs, dict):
        errs.append("_evaluation_questions.json: 'questions' must be a dict")
        return errs, warns
    covered = set(qs.keys())
    missing = known_dims - covered
    extra = covered - known_dims
    if missing:
        errs.append(f"_evaluation_questions.json: missing entries for dims {sorted(missing)}")
    if extra:
        warns.append(f"_evaluation_questions.json: entries for unknown dims {sorted(extra)} "
                      f"(not in _rubric_universal.json)")
    for dim_id, spec in qs.items():
        if not isinstance(spec, dict):
            errs.append(f"_evaluation_questions[{dim_id}]: must be a dict")
            continue
        for k in ("question", "hint"):
            v = spec.get(k)
            if not isinstance(v, str) or not v.strip():
                errs.append(f"_evaluation_questions[{dim_id}][{k}]: must be non-empty string")
    return errs, warns


def _validate_intent_affinity(block: dict[str, Any], known_dims: set[str]
                                  ) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    intents = block.get("intents", {}) or {}
    if not isinstance(intents, dict):
        errs.append("_intent_affinity.json: 'intents' must be a dict")
        return errs, warns
    for intent, dims in intents.items():
        if not isinstance(dims, dict):
            errs.append(f"_intent_affinity[{intent}]: must be a dict")
            continue
        for dim_id, spec in dims.items():
            if dim_id not in known_dims:
                warns.append(f"_intent_affinity[{intent}][{dim_id}]: unknown dim_id")
    return errs, warns


def _validate_intent_signals(block: dict[str, Any]) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    intents = block.get("intents", {}) or {}
    if not isinstance(intents, dict):
        errs.append("_intent_signals.json: 'intents' must be a dict")
        return errs, warns
    for intent, spec in intents.items():
        if not isinstance(spec, dict):
            errs.append(f"_intent_signals[{intent}]: must be a dict")
            continue
        phrases = spec.get("phrases", [])
        if not isinstance(phrases, list):
            errs.append(f"_intent_signals[{intent}]: phrases must be a list")
            continue
        for j, p in enumerate(phrases):
            if not isinstance(p, dict):
                errs.append(f"_intent_signals[{intent}][{j}]: must be a dict")
                continue
            if not isinstance(p.get("text"), str) or not p["text"].strip():
                errs.append(f"_intent_signals[{intent}][{j}]: text must be non-empty string")
    return errs, warns


def _validate_country_hints(block: dict[str, Any]) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    countries = block.get("countries", {}) or {}
    if not isinstance(countries, dict):
        errs.append("_country_hints.json: 'countries' must be a dict")
        return errs, warns
    for code, spec in countries.items():
        if not isinstance(code, str) or len(code) > 4:
            warns.append(f"_country_hints[{code}]: country code should be 2-3 letter ISO")
        if isinstance(spec, dict):
            hints = spec.get("hints", [])
        elif isinstance(spec, list):
            hints = spec
        else:
            errs.append(f"_country_hints[{code}]: spec must be dict or list")
            continue
        if not isinstance(hints, list) or not hints:
            errs.append(f"_country_hints[{code}]: hints must be a non-empty list")
    return errs, warns


def _validate_grader_config(block: dict[str, Any]) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    thresholds = block.get("thresholds", {}) or {}
    flags = block.get("feature_flags", {}) or {}
    for k, v in thresholds.items():
        if isinstance(v, dict):
            if "value" not in v:
                errs.append(f"_grader_config.thresholds[{k}]: missing 'value'")
        # Plain scalars are also allowed; skip
    for k, v in flags.items():
        if isinstance(v, dict):
            if "value" not in v:
                errs.append(f"_grader_config.feature_flags[{k}]: missing 'value'")
            elif not isinstance(v.get("value"), bool):
                warns.append(f"_grader_config.feature_flags[{k}]: value should be bool")
    return errs, warns


def _validate_rubric_hints(block: dict[str, Any], known_dims: set[str]
                              ) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    hints = block.get("hints", {}) or {}
    if not isinstance(hints, dict):
        errs.append("_rubric_hints.json: 'hints' must be a dict")
        return errs, warns
    missing = known_dims - set(hints.keys())
    extra = set(hints.keys()) - known_dims
    if missing:
        warns.append(f"_rubric_hints.json: no hints for dims {sorted(missing)} "
                      f"(UI will fall back to in-JS const)")
    if extra:
        warns.append(f"_rubric_hints.json: hints for unknown dims {sorted(extra)}")
    for dim_id, hint in hints.items():
        if not isinstance(hint, str) or not hint.strip():
            errs.append(f"_rubric_hints[{dim_id}]: hint must be non-empty string")
    return errs, warns


def _validate_baseline_gauge(block: dict[str, Any]) -> tuple[list[str], list[str]]:
    errs: list[str] = []
    warns: list[str] = []
    for k in ("stock", "harnessed"):
        spec = block.get(k)
        if not isinstance(spec, dict):
            errs.append(f"_baseline_gauge.{k}: must be a dict")
            continue
        if "value" not in spec or not isinstance(spec["value"], (int, float)):
            errs.append(f"_baseline_gauge.{k}.value: must be a number")
        if "label" not in spec:
            warns.append(f"_baseline_gauge.{k}.label: missing")
    return errs, warns


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                            help="Exit non-zero on warnings too")
    args = parser.parse_args()

    print("Duecare curator-block validator")
    print(f"  harness dir: {HARNESS_DIR}")
    print()

    # Load the rubric first — it's the cross-reference ground-truth
    rubric = _load(RUBRIC_PATH)
    if not rubric:
        print(f"FATAL: cannot load {RUBRIC_PATH}")
        return 1
    known_dims = {d["id"] for d in rubric.get("dimensions", [])}
    print(f"  rubric: {rubric.get('version', '?')}, {len(known_dims)} dims")
    print()

    files = [
        ("_classifier_signals.json",
            lambda b: _validate_classifier_signals(b)),
        ("_usecase_affinity.json",
            lambda b: _validate_usecase_affinity(b, known_dims)),
        ("_authoritative_statutes.json",
            lambda b: _validate_authoritative_statutes(b)),
        ("_known_statute_sections.json",
            lambda b: _validate_known_statute_sections(b)),
        ("_evaluation_questions.json",
            lambda b: _validate_evaluation_questions(b, known_dims)),
        ("_intent_affinity.json",
            lambda b: _validate_intent_affinity(b, known_dims)),
        ("_intent_signals.json",
            lambda b: _validate_intent_signals(b)),
        ("_country_hints.json",
            lambda b: _validate_country_hints(b)),
        ("_grader_config.json",
            lambda b: _validate_grader_config(b)),
        ("_rubric_hints.json",
            lambda b: _validate_rubric_hints(b, known_dims)),
        ("_baseline_gauge.json",
            lambda b: _validate_baseline_gauge(b)),
    ]

    total_err = 0
    total_warn = 0
    for filename, validator in files:
        path = HARNESS_DIR / filename
        block = _load(path)
        if block is None:
            print(f"  [SKIP] {filename} — missing or unparseable")
            total_err += 1
            continue
        env_errs = _check_envelope(filename, block)
        body_errs, body_warns = validator(block)
        errs = env_errs + body_errs
        warns = body_warns
        marker = "OK   " if not errs and not warns else \
                 "WARN " if not errs else \
                 "FAIL "
        n_entries = (len(block.get("entries", []) or [])
                     or len(block.get("hints", {}) or {})
                     or len(block.get("questions", {}) or {})
                     or len(block.get("intents", {}) or {})
                     or len(block.get("countries", {}) or {})
                     or len(block.get("use_cases", {}) or {}))
        print(f"  [{marker}] {filename:38} v{block.get('version','?'):8} "
              f"({n_entries:>3} entries)  err={len(errs)} warn={len(warns)}")
        for e in errs: print(f"           {e}")
        for w in warns: print(f"           (warn) {w}")
        total_err += len(errs)
        total_warn += len(warns)

    print()
    print(f"TOTAL: {total_err} errors, {total_warn} warnings")
    if total_err > 0:
        return 1
    if args.strict and total_warn > 0:
        print("(--strict: warnings escalated to failure)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
