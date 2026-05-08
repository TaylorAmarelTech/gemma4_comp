"""Curator-block loaders for the harness.

Magic-string lists that are tuned by NGOs / jurists / researchers are
stored as versioned JSON files in this directory rather than hardcoded
in __init__.py. Each file uses the curator-block envelope:

    {
      "schema":       "duecare-<thing>/v1",
      "version":      "1.0.0",
      "last_updated": "YYYY-MM-DD",
      "curator":      "Duecare team (or org name)",
      "notes":        "free-text description of the file's purpose",
      "entries":      [...]  // schema-specific entries
    }

This module provides:
  - load_curator_block(path) -> dict      # parses + validates the envelope
  - get_entries(block)        -> list     # convenience to extract entries
  - load_classifier_signals() -> tuple    # typed loaders for each file
  - load_usecase_affinity()   -> dict
  - load_authoritative_statutes() -> list[str]
  - load_known_statute_sections() -> dict[str, tuple[int, int]]

Loaders are pure: no side effects on import. The harness module calls
them at module init to populate the same module-level constants used
by callers, so existing call sites keep working without change.

Failure mode: if a file is missing or malformed, loaders return an
empty payload and log a warning. The grader will keep working, but
with reduced coverage. We do NOT raise — a curator's bad commit
shouldn't crash production grading.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

_HARNESS_DIR = Path(__file__).parent

CLASSIFIER_SIGNALS_PATH     = _HARNESS_DIR / "_classifier_signals.json"
USECASE_AFFINITY_PATH       = _HARNESS_DIR / "_usecase_affinity.json"
AUTHORITATIVE_STATUTES_PATH = _HARNESS_DIR / "_authoritative_statutes.json"
KNOWN_STATUTE_SECTIONS_PATH = _HARNESS_DIR / "_known_statute_sections.json"
EVALUATION_QUESTIONS_PATH   = _HARNESS_DIR / "_evaluation_questions.json"
INTENT_AFFINITY_PATH        = _HARNESS_DIR / "_intent_affinity.json"
INTENT_SIGNALS_PATH         = _HARNESS_DIR / "_intent_signals.json"
COUNTRY_HINTS_PATH          = _HARNESS_DIR / "_country_hints.json"
GRADER_CONFIG_PATH          = _HARNESS_DIR / "_grader_config.json"
BASELINE_GAUGE_PATH         = _HARNESS_DIR / "_baseline_gauge.json"
RUBRIC_HINTS_PATH           = _HARNESS_DIR / "_rubric_hints.json"
PERSONAS_PATH               = _HARNESS_DIR / "_personas.json"

# Only schema + version are universally required. The body shape
# differs per block type: classifier_signals/authoritative_statutes/
# known_statute_sections use `entries`, but evaluation_questions uses
# `questions`, intent_affinity uses `intents`, country_hints uses
# `countries`, grader_config uses `thresholds` + `feature_flags`,
# baseline_gauge uses `stock` + `harnessed`, rubric_hints uses
# `hints`, usecase_affinity uses `use_cases`. Requiring `entries`
# universally fired a spurious warning for 8/11 files on every
# /api/governance request — caught in live Kaggle test 2026-05-07.
_REQUIRED_ENVELOPE_KEYS = ("schema", "version")


def load_curator_block(path: os.PathLike | str) -> dict[str, Any]:
    """Read + validate a curator-block JSON file. Returns the parsed
    envelope on success; an empty dict on any failure (with a log
    warning). Never raises."""
    p = Path(path)
    if not p.exists():
        _log.warning("curator block missing: %s", p)
        return {}
    try:
        block = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("curator block %s parse failed: %s", p, e)
        return {}
    if not isinstance(block, dict):
        _log.warning("curator block %s is not a dict", p)
        return {}
    missing = [k for k in _REQUIRED_ENVELOPE_KEYS if k not in block]
    if missing:
        _log.warning("curator block %s missing keys %s", p, missing)
        return {}
    return block


def get_entries(block: dict[str, Any]) -> list[Any]:
    """Convenience: pull out the entries list, or [] if missing/wrong type."""
    e = block.get("entries", [])
    return list(e) if isinstance(e, list) else []


def load_classifier_signals() -> tuple[tuple[str, str, float], ...]:
    """Return a tuple of (use_case, signal, weight) tuples. Schema:
    duecare-classifier-signals/v1.

    Each entry must have `use_case` (string), `signal` (string), and
    `weight` (float). Entries missing any field are skipped. The
    `signal` is lowercased here so substring checks against
    lowercased prompt text are direct."""
    block = load_curator_block(CLASSIFIER_SIGNALS_PATH)
    out: list[tuple[str, str, float]] = []
    for entry in get_entries(block):
        if not isinstance(entry, dict):
            continue
        uc = entry.get("use_case")
        sig = entry.get("signal")
        w = entry.get("weight")
        if not isinstance(uc, str) or not isinstance(sig, str):
            continue
        try:
            wf = float(w)
        except (TypeError, ValueError):
            continue
        out.append((uc, sig.lower(), wf))
    return tuple(out)


def load_usecase_affinity() -> dict[str, dict[str, float]]:
    """Return {use_case: {dim_id: weight}}. Schema:
    duecare-usecase-affinity/v1.

    Entries here are NESTED rather than a flat list — the JSON shape is
    {"use_cases": {<uc>: {<dim_id>: {"weight": float, "rationale": ...}}}}.
    We collapse to the simple {uc: {dim: weight}} dict the grader
    expects.
    """
    if not USECASE_AFFINITY_PATH.exists():
        _log.warning("curator block missing: %s", USECASE_AFFINITY_PATH)
        return {}
    try:
        block = json.loads(USECASE_AFFINITY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("usecase-affinity parse failed: %s", e)
        return {}
    use_cases = block.get("use_cases") if isinstance(block, dict) else None
    if not isinstance(use_cases, dict):
        return {}
    out: dict[str, dict[str, float]] = {}
    for uc, dims in use_cases.items():
        if not isinstance(dims, dict):
            continue
        per_dim: dict[str, float] = {}
        for dim_id, spec in dims.items():
            if isinstance(spec, dict) and "weight" in spec:
                try:
                    per_dim[dim_id] = float(spec["weight"])
                except (TypeError, ValueError):
                    continue
            else:
                # Allow shorthand: {"dim_id": 1.5}
                try:
                    per_dim[dim_id] = float(spec)
                except (TypeError, ValueError):
                    continue
        out[uc] = per_dim
    out.setdefault("_default", {})
    return out


def load_authoritative_statutes() -> list[str]:
    """Return list of lowercase statute strings. Schema:
    duecare-authoritative-statutes/v1."""
    block = load_curator_block(AUTHORITATIVE_STATUTES_PATH)
    out: list[str] = []
    for entry in get_entries(block):
        if isinstance(entry, dict):
            n = entry.get("name")
            if isinstance(n, str) and n:
                out.append(n.lower())
        elif isinstance(entry, str):
            out.append(entry.lower())
    return out


def load_known_statute_sections() -> dict[str, tuple[int, int]]:
    """Return {key: (min, max)}. Schema:
    duecare-known-statute-sections/v1."""
    block = load_curator_block(KNOWN_STATUTE_SECTIONS_PATH)
    out: dict[str, tuple[int, int]] = {}
    for entry in get_entries(block):
        if not isinstance(entry, dict):
            continue
        key = entry.get("key")
        try:
            mn = int(entry.get("min"))
            mx = int(entry.get("max"))
        except (TypeError, ValueError):
            continue
        if isinstance(key, str) and key:
            out[key] = (mn, mx)
    return out


def load_evaluation_questions() -> dict[str, dict[str, str]]:
    """Return {dim_id: {"question": str, "hint": str}}. Schema:
    duecare-evaluation-questions/v1.

    These are the dimension-focused yes/no questions sent to the LLM
    evaluator (the framework called 'LLM-as-judge' in academic
    literature: G-Eval, MT-Bench, Prometheus, Auto-J). The naming
    here is 'evaluation_questions' to avoid confusion with contest
    judges — they are NOT related.

    Top-level shape is {"questions": {dim_id: {...}}}, not "entries".
    """
    if not EVALUATION_QUESTIONS_PATH.exists():
        _log.warning("curator block missing: %s", EVALUATION_QUESTIONS_PATH)
        return {}
    try:
        block = json.loads(EVALUATION_QUESTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("evaluation-questions parse failed: %s", e)
        return {}
    qs = block.get("questions") if isinstance(block, dict) else None
    if not isinstance(qs, dict):
        return {}
    out: dict[str, dict[str, str]] = {}
    for dim_id, spec in qs.items():
        if not isinstance(dim_id, str) or not isinstance(spec, dict):
            continue
        q = spec.get("question", "")
        h = spec.get("hint", "")
        if isinstance(q, str) and isinstance(h, str) and q:
            out[dim_id] = {"question": q, "hint": h}
    return out




def load_intent_affinity() -> dict[str, dict[str, float]]:
    """Return {intent: {dim_id: weight}}. Schema:
    duecare-intent-affinity/v1.

    Top-level shape is {"intents": {intent: {dim: {weight, rationale}}}}.
    """
    if not INTENT_AFFINITY_PATH.exists():
        _log.warning("curator block missing: %s", INTENT_AFFINITY_PATH)
        return {}
    try:
        block = json.loads(INTENT_AFFINITY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("intent-affinity parse failed: %s", e)
        return {}
    intents = block.get("intents") if isinstance(block, dict) else None
    if not isinstance(intents, dict):
        return {}
    out: dict[str, dict[str, float]] = {}
    for intent, dims in intents.items():
        if not isinstance(dims, dict):
            continue
        per_dim: dict[str, float] = {}
        for dim_id, spec in dims.items():
            if isinstance(spec, dict) and "weight" in spec:
                try:
                    per_dim[dim_id] = float(spec["weight"])
                except (TypeError, ValueError):
                    continue
            else:
                try:
                    per_dim[dim_id] = float(spec)
                except (TypeError, ValueError):
                    continue
        out[intent] = per_dim
    out.setdefault("_default", {})
    return out


def load_intent_signals() -> dict[str, list[tuple[str, float]]]:
    """Return {intent: [(phrase_lower, weight), ...]}. Schema:
    duecare-intent-signals/v1.

    Top-level shape is {"intents": {intent: {phrases: [{text, weight}]}}}.
    """
    if not INTENT_SIGNALS_PATH.exists():
        _log.warning("curator block missing: %s", INTENT_SIGNALS_PATH)
        return {}
    try:
        block = json.loads(INTENT_SIGNALS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("intent-signals parse failed: %s", e)
        return {}
    intents = block.get("intents") if isinstance(block, dict) else None
    if not isinstance(intents, dict):
        return {}
    out: dict[str, list[tuple[str, float]]] = {}
    for intent, spec in intents.items():
        if not isinstance(spec, dict):
            continue
        phrases = spec.get("phrases", [])
        rows: list[tuple[str, float]] = []
        for p in phrases:
            if not isinstance(p, dict):
                continue
            text = p.get("text")
            try:
                w = float(p.get("weight", 1.0))
            except (TypeError, ValueError):
                continue
            if isinstance(text, str) and text:
                rows.append((text.lower(), w))
        out[intent] = rows
    return out


def load_country_hints() -> dict[str, list[str]]:
    """Return {country_code: [hint_str, ...]}. Schema:
    duecare-country-hints/v1.

    Top-level shape is {"countries": {code: {name, hints: [...]}}}.
    """
    if not COUNTRY_HINTS_PATH.exists():
        _log.warning("curator block missing: %s", COUNTRY_HINTS_PATH)
        return {}
    try:
        block = json.loads(COUNTRY_HINTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("country-hints parse failed: %s", e)
        return {}
    countries = block.get("countries") if isinstance(block, dict) else None
    if not isinstance(countries, dict):
        return {}
    out: dict[str, list[str]] = {}
    for code, spec in countries.items():
        if not isinstance(code, str):
            continue
        if isinstance(spec, dict):
            hints = spec.get("hints", [])
        elif isinstance(spec, list):
            hints = spec
        else:
            continue
        if isinstance(hints, list):
            out[code] = [h for h in hints if isinstance(h, str)]
    return out


def load_rubric_hints() -> dict[str, str]:
    """Return {dim_id: hint_string}. Schema:
    duecare-rubric-hints/v1.

    Top-level shape is {"hints": {dim_id: <string>}}. The UI renders
    these inline below each FAIL/PARTIAL row in the grade modal.
    """
    if not RUBRIC_HINTS_PATH.exists():
        return {}
    try:
        block = json.loads(RUBRIC_HINTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("rubric-hints parse failed: %s", e)
        return {}
    hints = block.get("hints") if isinstance(block, dict) else None
    if not isinstance(hints, dict):
        return {}
    out: dict[str, str] = {}
    for dim_id, val in hints.items():
        if isinstance(dim_id, str) and isinstance(val, str) and val:
            out[dim_id] = val
    return out


def load_personas() -> list[dict]:
    """Return the curator-curated persona library. Schema:
    duecare-personas/v1.

    Each entry: {id, name, audience, tagline, text}. The UI's persona
    library lists these alongside the kernel default + the user's
    localStorage-stored custom personas. Missing or malformed file
    returns an empty list — the kernel default still works.
    """
    if not PERSONAS_PATH.exists():
        return []
    try:
        block = json.loads(PERSONAS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("personas parse failed: %s", e)
        return []
    entries = block.get("entries") if isinstance(block, dict) else None
    if not isinstance(entries, list):
        return []
    out: list[dict] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        if not e.get("id") or not e.get("name") or not e.get("text"):
            continue
        out.append({
            "id":       str(e["id"]),
            "name":     str(e["name"]),
            "audience": str(e.get("audience") or ""),
            "tagline":  str(e.get("tagline") or ""),
            "text":     str(e["text"]),
        })
    return out


def load_baseline_gauge() -> dict[str, Any]:
    """Return parsed baseline-gauge block (stock + harnessed reference
    numbers for the score-card gauge). Schema:
    duecare-baseline-gauge/v1.

    Returns the raw dict so the API can pass it straight through to
    the UI without per-field projection. Empty dict on parse failure.
    """
    if not BASELINE_GAUGE_PATH.exists():
        return {}
    try:
        return json.loads(BASELINE_GAUGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("baseline-gauge parse failed: %s", e)
        return {}


def load_grader_config() -> dict[str, Any]:
    """Return parsed grader-config block. Schema:
    duecare-grader-config/v1.

    Returns {"thresholds": {key: value}, "feature_flags": {key: bool}}.
    Each top-level value is unwrapped from its nested {"value": ...,
    "rationale": ...} envelope so callers see flat scalars.
    """
    if not GRADER_CONFIG_PATH.exists():
        return {"thresholds": {}, "feature_flags": {}}
    try:
        block = json.loads(GRADER_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        _log.warning("grader-config parse failed: %s", e)
        return {"thresholds": {}, "feature_flags": {}}
    thresholds: dict[str, Any] = {}
    flags: dict[str, bool] = {}
    for k, v in (block.get("thresholds") or {}).items():
        if isinstance(v, dict) and "value" in v:
            thresholds[k] = v["value"]
        else:
            thresholds[k] = v
    for k, v in (block.get("feature_flags") or {}).items():
        if isinstance(v, dict) and "value" in v:
            flags[k] = bool(v["value"])
        else:
            flags[k] = bool(v)
    return {"thresholds": thresholds, "feature_flags": flags}
