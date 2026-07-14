#!/usr/bin/env python3
"""Training-data quality audit -- guard against overfitting, false patterns, fragile-fact memorization,
and jurisdiction-bound shortcuts BEFORE the GPU fine-tune.

A fine-tune is only as good as its data. This audits the assembled SFT/DPO splits
(organize_training_data.py output) for the failure modes a safety judge must avoid:

  1. OVERFITTING -- cross-split near-dup LEAKAGE: a held-out example that has a SimHash near-duplicate in
     train means the "generalisation" diagnostic is measuring memorisation, not transfer. Want 0.
  2. FALSE PATTERN (length shortcut) -- if DPO `chosen` is systematically much longer than `rejected`,
     the model learns "longer = preferred" instead of "grounded = preferred". Want a modest ratio.
  3. JURISDICTION-INDEPENDENCE -- does each typology appear across MULTIPLE corridors? A typology seen in
     only one corridor lets the model bind the pattern to that jurisdiction instead of learning the
     universal (ILO) indicator. Want broad corridor spread; flag single-corridor typologies.
  4. FRAGILE-FACT memorization -- gold (`chosen`) replies asserting volatile specifics (phone/hotline
     numbers, exact fee amounts, explicit dates) teach the model to memorise facts that go stale; those
     belong in tools/RAG. Want ~0 phone-like (the privacy scrub should catch them) + visibility on
     money/date specifics.

Reads the splits and writes reports/training/quality_audit.json with metrics + risk flags.
Offline/deterministic. By default the CLI remains informational for curation work; pass
`--require-clean` to return a nonzero status when any risk flag is present. The canonical
training engine always uses that strict gate before training or registration. Reuses
research_tools.dedup (SimHash) + the prompt sets for corridor/typology.

    python scripts/audit_training_quality.py
Design: docs/research/training_methodology.md (quality gates)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import sys
from collections import Counter, defaultdict
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_TRAIN = _ROOT / "reports" / "training"
FULL_SET = _ROOT / "reports" / "benchmark" / "full_promptset.json"
CURATED_SET = _ROOT / "configs" / "duecare" / "benchmarks" / "scheme_prompts.json"
OUT = _TRAIN / "quality_audit.json"
NEAR_DUP_DIST = 3   # SimHash Hamming distance counted as a leak (matches organize_training_data)
METADATA_ONLY_FORBIDDEN_FIELDS = frozenset({"messages", "prompt", "chosen", "rejected", "assistant", "text"})
GENERIC_CORRIDOR_VALUES = frozenset({"various", "mixed", "multiple", "multi-corridor", "global"})
QUALITY_AUDIT_SUMMARY_FIELDS = (
    "clean",
    "risk_flags",
    "sft_leaked",
    "dpo_leaked",
    "dense_single_corridor_typologies",
    "corridor_expansion_queue_count",
    "corridor_expansion_task_count",
    "corridor_expansion_queue_privacy_ok",
    "corridor_expansion_tasks_privacy_ok",
    "citation_incoherent",
    "citation_repair_queue_count",
    "citation_repair_queue_privacy_ok",
    "gold_phone_like",
)

# Reuse the deterministic SimHash near-dup (DRY); bridge the package src so this runs standalone.
_RT_SRC = _ROOT / "packages" / "duecare-llm-research-tools" / "src"
if _RT_SRC.exists() and str(_RT_SRC) not in sys.path:
    sys.path.insert(0, str(_RT_SRC))
try:
    from duecare.research_tools.dedup import simhash64, SimHashIndex
    _HAVE_SIMHASH = True
except Exception:  # noqa: BLE001
    _HAVE_SIMHASH = False
from palermo_screening import citation_coherence as _citation_coherence  # noqa: E402

# Fragile-fact patterns: volatile specifics a model should NOT memorize (they belong in tools/RAG).
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_MONEY = re.compile(r"(?:\$|usd|eur|php|aed|sar)\s?\d[\d,]*", re.I)
_DATE = re.compile(r"\b(?:20\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_PROMPT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _safe_relative_report_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _EMAIL.search(display) or _PHONE.search(display) or re.search(r"\b\d{9,}\b", display):
        return "redacted"
    if not _SAFE_RELATIVE_PATH.fullmatch(display):
        return "redacted"
    return display


def _display_report_path(raw_path: Any) -> str:
    if not raw_path:
        return "n/a"
    raw = str(raw_path)
    try:
        path = pathlib.Path(raw)
        if path.is_absolute():
            try:
                return _safe_relative_report_path(path.relative_to(_ROOT))
            except ValueError:
                return "external"
        return _safe_relative_report_path(pathlib.PurePosixPath(pathlib.PureWindowsPath(raw).as_posix()))
    except (OSError, RuntimeError, ValueError):
        return "redacted"


def _safe_prompt_id(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    if _EMAIL.search(text) or _PHONE.search(text) or re.search(r"\b\d{9,}\b", text):
        return ""
    return text if _SAFE_PROMPT_ID.fullmatch(text) else ""


def _metadata_safe_risk_flags(report: dict[str, Any]) -> list[str]:
    """Derive risk labels from numeric audit fields without copying raw audit text."""
    flags: list[str] = []
    leakage = report.get("overfitting_leakage") or {}
    sft_leak = leakage.get("sft") or {}
    if sft_leak.get("available") and sft_leak.get("ok") is False:
        flags.append(f"SFT cross-split leakage: {sft_leak.get('leaked')} heldout near-dups in train")
    dpo_leak = leakage.get("dpo") or {}
    if dpo_leak.get("available") and dpo_leak.get("ok") is False:
        flags.append(f"DPO cross-split leakage: {dpo_leak.get('leaked')}")

    length_bias = report.get("false_pattern_length_bias") or {}
    if length_bias.get("ok") is False:
        flags.append(
            f"DPO length bias: chosen/rejected ratio {length_bias.get('chosen_over_rejected_ratio')}"
        )

    corridor = report.get("jurisdiction_corridor_diversity") or {}
    if corridor.get("ok") is False:
        flags.append(
            f"{corridor.get('n_dense_single_corridor')} dense single-corridor typologies "
            f"(>={corridor.get('min_rows')} rows, jurisdiction shortcut risk)"
        )

    fragile = report.get("fragile_fact_assertions") or {}
    if fragile.get("ok_phone") is False:
        flags.append(f"{fragile.get('with_phone_like')} gold replies assert phone-like fragile facts")

    citation = report.get("citation_relevance") or {}
    if citation.get("ok") is False:
        flags.append(f"{citation.get('n_incoherent')} gold replies cite real-but-irrelevant conventions")
    return flags


def quality_audit_summary(path: pathlib.Path | None = None) -> dict[str, Any] | None:
    """Small, metadata-only summary of quality_audit.json for provenance surfaces."""
    path = path or OUT
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(report, dict):
        return None
    corridor = report.get("jurisdiction_corridor_diversity") or {}
    citation = report.get("citation_relevance") or {}
    fragile = report.get("fragile_fact_assertions") or {}
    leakage = report.get("overfitting_leakage") or {}
    return {
        "path": _display_report_path(path),
        "clean": bool(report.get("clean")),
        "risk_flags": _metadata_safe_risk_flags(report),
        "sft_leaked": (leakage.get("sft") or {}).get("leaked"),
        "dpo_leaked": (leakage.get("dpo") or {}).get("leaked"),
        "dense_single_corridor_typologies": corridor.get("n_dense_single_corridor"),
        "corridor_expansion_queue_count": corridor.get("corridor_expansion_queue_count"),
        "corridor_expansion_task_count": corridor.get("corridor_expansion_task_count"),
        "corridor_expansion_queue_privacy_ok": (
            (corridor.get("corridor_expansion_queue_privacy_scan") or {}).get("ok")
        ),
        "corridor_expansion_tasks_privacy_ok": (
            (corridor.get("corridor_expansion_tasks_privacy_scan") or {}).get("ok")
        ),
        "citation_incoherent": citation.get("n_incoherent"),
        "citation_repair_queue_count": citation.get("repair_queue_count"),
        "citation_repair_queue_privacy_ok": (
            (citation.get("repair_queue_privacy_scan") or {}).get("ok")
        ),
        "gold_phone_like": fragile.get("with_phone_like"),
    }


def _load_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def load_pid_meta(*paths: pathlib.Path) -> dict[str, dict]:
    """{prompt_id: {category, corridor}} from the first prompt set that exists."""
    for path in paths:
        if not path.exists():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        prompts = doc.get("prompts", doc)
        return {pid: {"category": str(p.get("category", "unknown")),
                      "corridor": str(p.get("corridor", "unknown"))}
                for p in prompts if isinstance(p, dict) and (pid := _safe_prompt_id(p.get("id")))}
    return {}


def _sft_user(row: dict) -> str:
    if not isinstance(row, dict):
        return ""
    messages = row.get("messages") or []
    if not isinstance(messages, list):
        return ""
    return next((_string_field(m, "content") for m in messages
                if isinstance(m, dict) and m.get("role") == "user"), "")


def _sft_assistant(row: dict) -> str:
    if not isinstance(row, dict):
        return ""
    messages = row.get("messages") or []
    if not isinstance(messages, list):
        return ""
    return next((_string_field(m, "content") for m in reversed(messages)
                if isinstance(m, dict) and m.get("role") == "assistant"), "")


def _string_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key, "")
    return value if isinstance(value, str) else ""


def _prompt_id(row: dict) -> str:
    if not isinstance(row, dict):
        return ""
    meta = row.get("_meta") or {}
    if not isinstance(meta, dict):
        return ""
    return _safe_prompt_id(meta.get("prompt_id"))


def _gold_entry(
    *,
    source: str,
    source_index: int,
    row: dict,
    text: str,
    pid_meta: dict[str, dict],
) -> dict[str, Any]:
    """Metadata-bearing gold reply for audit functions. Text is only used in-memory."""
    pid = _prompt_id(row)
    meta = pid_meta.get(pid, {})
    return {
        "source": source,
        "source_index": source_index,
        "prompt_id": pid,
        "category": str(meta.get("category", "unknown")),
        "corridor": str(meta.get("corridor", "unknown")),
        "text": text,
    }


def near_dup_leakage(train_texts: list[str], heldout_texts: list[str], *, max_dist: int = NEAR_DUP_DIST) -> dict:
    """Held-out texts with a SimHash near-dup in train (=> memorisation leak; want 0)."""
    if not _HAVE_SIMHASH:
        return {"available": False}
    idx = SimHashIndex((simhash64(t) for t in train_texts if t), bands=4)
    leaked = sum(1 for t in heldout_texts if t and idx.query_near(simhash64(t), max_dist=max_dist))
    n = len([t for t in heldout_texts if t])
    return {"available": True, "heldout": n, "leaked": leaked,
            "leak_rate": round(leaked / n, 4) if n else None,
            "ok": leaked == 0}


def length_bias(dpo_rows: list[dict]) -> dict:
    """DPO chosen-vs-rejected length: a big chosen>>rejected gap is a length shortcut the model can game."""
    pairs = [
        (len(_string_field(r, "chosen")), len(_string_field(r, "rejected")))
        for r in dpo_rows if isinstance(r, dict)
    ]
    pairs = [(c, j) for c, j in pairs if c and j]
    if not pairs:
        return {"n": 0}
    c_mean = statistics.mean(c for c, _ in pairs)
    j_mean = statistics.mean(j for _, j in pairs)
    return {"n": len(pairs), "chosen_chars_mean": round(c_mean), "rejected_chars_mean": round(j_mean),
            "chosen_over_rejected_ratio": round(c_mean / j_mean, 2) if j_mean else None,
            "frac_chosen_longer": round(sum(c > j for c, j in pairs) / len(pairs), 3),
            # a ratio >~2.0 means length is a strong confound -- the DPO trunc fix keeps both sides full
            "ok": (c_mean / j_mean) <= 2.0 if j_mean else None}


def _coverage_gap(observed_corridors: list[str]) -> str:
    if not observed_corridors:
        return "no_specific_corridor"
    if all(c.lower() in GENERIC_CORRIDOR_VALUES for c in observed_corridors):
        return "generic_corridor_only"
    return "single_specific_corridor"


def _is_specific_corridor(corridor: str) -> bool:
    value = str(corridor or "").strip()
    return bool(value) and value.lower() not in GENERIC_CORRIDOR_VALUES | {"unknown"}


def _safe_task_component(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:48].strip("-") or "unknown"


def _split_corridor(corridor: str) -> tuple[str, str]:
    origin, sep, destination = str(corridor or "").partition("->")
    if not sep:
        return "", ""
    return origin.strip(), destination.strip()


def _corridor_expansion_tasks(expansion_queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for entry in expansion_queue:
        category = str(entry.get("category", "unknown"))
        coverage_gap = str(entry.get("coverage_gap", "unknown"))
        source = str(entry.get("suggestion_source", "unknown"))
        for corridor in entry.get("target_corridor_suggestions") or []:
            target_corridor = str(corridor)
            origin, destination = _split_corridor(target_corridor)
            tasks.append({
                "task_id": (
                    "corridor-expansion-"
                    f"{_safe_task_component(category)}-"
                    f"{_safe_task_component(target_corridor)}"
                ),
                "category": category,
                "target_corridor": target_corridor,
                "origin": origin,
                "destination": destination,
                "coverage_gap": coverage_gap,
                "suggestion_source": source,
                "suggested_min_synthetic_rows": 3,
                "required_metadata_fields": [
                    "id",
                    "category",
                    "corridor",
                    "source",
                    "privacy_review",
                ],
                "scenario_constraints": [
                    "synthetic_or_public_only",
                    "no_names",
                    "no_contacts",
                    "no_case_details",
                    "include_ilo_indicator",
                    "include_jurisdiction_context",
                ],
                "acceptance_checks": [
                    "metadata_only",
                    "privacy_scan_ok",
                    "non_duplicate_id",
                    "corridor_matches_target",
                    "typology_matches_category",
                ],
                "curation_hint": (
                    "Stage vetted synthetic or public-source rows for this typology and corridor; "
                    "keep worker-identifying details out of generated artifacts."
                ),
            })
    return tasks


def corridor_diversity(rows: list[dict], pid_meta: dict[str, dict], *, min_rows: int = 10) -> dict:
    """Per-typology corridor spread -- the jurisdiction-shortcut guard.

    Only a typology with >= `min_rows` training rows ALL sitting in a single real corridor is a genuine
    shortcut risk: dense enough for the model to bind the pattern to that jurisdiction. Sparse typologies
    (< min_rows) and attack-STYLE categories (corridor not applicable -> 'unknown') can't span corridors
    meaningfully, so they are reported, not flagged. (The universal layer the model should learn is the
    ILO-11 indicator, which the distilled targets carry regardless of corridor; this guards against the
    data accidentally letting a corridor stand in for an indicator.)"""
    rows_by_cat: Counter = Counter()
    corr_by_cat: dict[str, set] = defaultdict(set)
    corr_counts_by_cat: dict[str, Counter] = defaultdict(Counter)
    candidate_corridors_by_cat: dict[str, set] = defaultdict(set)
    candidate_corridors: set = set()
    corridors: set = set()
    for meta in pid_meta.values():
        category = str(meta.get("category", "unknown"))
        corridor = str(meta.get("corridor", "unknown"))
        if _is_specific_corridor(corridor):
            candidate_corridors_by_cat[category].add(corridor)
            candidate_corridors.add(corridor)
    for r in rows:
        pid = _prompt_id(r)
        meta = pid_meta.get(pid)
        if not meta:
            continue
        category = meta["category"]
        corridor = meta["corridor"]
        rows_by_cat[category] += 1
        if corridor != "unknown":
            corr_by_cat[category].add(corridor)
            corr_counts_by_cat[category][corridor] += 1
            corridors.add(corridor)
    dense_single = sorted(c for c, n in rows_by_cat.items()
                          if n >= min_rows and len(corr_by_cat.get(c, set())) == 1)
    all_corridors = sorted(c for c in candidate_corridors if _is_specific_corridor(c))
    expansion_queue = []
    for category in dense_single:
        observed = sorted(corr_by_cat.get(category, set()))
        observed_specific = {c for c in observed if _is_specific_corridor(c)}
        category_candidates = sorted(
            c for c in candidate_corridors_by_cat.get(category, set())
            if c not in observed_specific
        )
        if category_candidates:
            suggestions = category_candidates[:5]
            suggestion_source = "category_prompt_metadata"
        else:
            suggestions = [c for c in all_corridors if c not in observed_specific][:5]
            suggestion_source = "global_prompt_metadata"
        expansion_queue.append({
            "category": category,
            "train_rows": rows_by_cat[category],
            "observed_corridors": observed,
            "observed_corridor_counts": {c: corr_counts_by_cat[category][c] for c in observed},
            "n_observed_corridors": len(observed),
            "coverage_gap": _coverage_gap(observed),
            "category_specific_candidate_count": len(category_candidates),
            "suggestion_source": suggestion_source,
            "needed_distinct_corridors": 2,
            "target_corridor_suggestions": suggestions,
            "n_target_corridor_suggestions": len(suggestions),
            "expansion_hint": (
                "Add vetted, privacy-safe prompts for this typology in at least one additional corridor "
                "so the training split teaches the indicator rather than the jurisdiction."
            ),
        })
    expansion_privacy_scan = _metadata_privacy_scan(
        expansion_queue,
        root_key="corridor_expansion_queue",
    )
    expansion_tasks = _corridor_expansion_tasks(expansion_queue)
    expansion_tasks_privacy_scan = _metadata_privacy_scan(
        expansion_tasks,
        root_key="corridor_expansion_tasks",
    )
    multi = sum(1 for cs in corr_by_cat.values() if len(cs) >= 2)
    sparse = sum(1 for n in rows_by_cat.values() if n < min_rows)
    return {"distinct_corridors": len(corridors), "typologies": len(rows_by_cat),
            "distinct_specific_corridors": len(all_corridors),
            "multi_corridor_typologies": multi, "sparse_typologies": sparse, "min_rows": min_rows,
            "dense_single_corridor_typologies": dense_single[:20],
            "n_dense_single_corridor": len(dense_single),
            "corridor_expansion_queue": expansion_queue,
            "corridor_expansion_queue_count": len(expansion_queue),
            "corridor_expansion_queue_metadata_only": True,
            "corridor_expansion_queue_privacy_scan": expansion_privacy_scan,
            "corridor_expansion_tasks": expansion_tasks,
            "corridor_expansion_task_count": len(expansion_tasks),
            "corridor_expansion_tasks_metadata_only": True,
            "corridor_expansion_tasks_privacy_scan": expansion_tasks_privacy_scan,
            "ok": (
                len(dense_single) == 0
                and expansion_privacy_scan["ok"]
                and expansion_tasks_privacy_scan["ok"]
            )}


def fragile_fact_assertions(gold_texts: list[str]) -> dict:
    """Gold replies asserting volatile specifics (phone/money/date) -- fragile facts that should be hedged
    / deferred to tools, not memorised. phone should be ~0 (privacy scrub); money/date are informational."""
    n = len([t for t in gold_texts if t])
    phone = sum(1 for t in gold_texts if t and _PHONE.search(t))
    money = sum(1 for t in gold_texts if t and _MONEY.search(t))
    date = sum(1 for t in gold_texts if t and _DATE.search(t))
    return {"n": n, "with_phone_like": phone, "with_money_amount": money, "with_explicit_date": date,
            "phone_rate": round(phone / n, 4) if n else None,
            "ok_phone": phone == 0}   # phones must be scrubbed; money/date are visibility-only


def _metadata_privacy_scan(entries: list[dict[str, Any]], *, root_key: str = "metadata") -> dict[str, Any]:
    findings: dict[str, list[str]] = {
        "forbidden_field_paths": [],
        "email_like_paths": [],
        "phone_like_paths": [],
        "long_digit_paths": [],
    }
    email = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_path = f"{path}.{key}"
                if str(key) in METADATA_ONLY_FORBIDDEN_FIELDS:
                    findings["forbidden_field_paths"].append(key_path)
                walk(item, key_path)
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                walk(item, f"{path}[{idx}]")
        elif isinstance(value, str):
            field = path.rsplit(".", 1)[-1]
            if field == "prompt_id" and _safe_prompt_id(value):
                return
            if email.search(value):
                findings["email_like_paths"].append(path)
            if _PHONE.search(value):
                findings["phone_like_paths"].append(path)
            if re.search(r"\b\d{9,}\b", value):
                findings["long_digit_paths"].append(path)

    walk({root_key: entries}, "$")
    counts = {key.replace("_paths", ""): len(value) for key, value in findings.items()}
    findings["counts"] = counts
    findings["ok"] = not any(counts.values())
    return findings


def _coerce_gold_entry(item: Any, index: int) -> dict[str, Any]:
    if isinstance(item, dict):
        return {
            "source": str(item.get("source", "gold")),
            "source_index": int(item.get("source_index", index)),
            "prompt_id": _safe_prompt_id(item.get("prompt_id")),
            "category": str(item.get("category", "unknown")),
            "corridor": str(item.get("corridor", "unknown")),
            "text": _string_field(item, "text"),
        }
    return {
        "source": "gold",
        "source_index": index,
        "prompt_id": "",
        "category": "unknown",
        "corridor": "unknown",
        "text": item if isinstance(item, str) else "",
    }


def _citation_repair_entry(entry: dict[str, Any], coherence: dict[str, Any], *, index: int) -> dict[str, Any]:
    return {
        "index": index,
        "source": entry["source"],
        "source_index": entry["source_index"],
        "prompt_id": entry["prompt_id"],
        "category": entry["category"],
        "corridor": entry["corridor"],
        "mapped_signals": coherence["mapped_signals"],
        "cited_conventions": coherence["cited_conventions"],
        "expected_conventions": coherence["expected_conventions"],
        "matched": coherence["matched"],
        "coherent": coherence["coherent"],
        "repair_hint": (
            "Replace or remove real-but-irrelevant ILO convention citations so at least one cited "
            "convention governs the mapped exploitation signal."
        ),
    }


def citation_relevance(gold_texts: list[Any]) -> dict[str, Any]:
    """Gold replies should not teach real-but-irrelevant legal citations.

    Report only structured citation metadata, not raw answer text, so the audit remains safe to store.
    """
    rows: list[dict[str, Any]] = []
    by_source: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_signal: Counter[str] = Counter()
    by_cited: Counter[str] = Counter()
    by_expected: Counter[str] = Counter()
    for idx, item in enumerate(gold_texts):
        entry = _coerce_gold_entry(item, idx)
        text = entry["text"]
        if not text:
            continue
        coh = _citation_coherence(text)
        if coh["mapped_signals"] and coh["cited_conventions"]:
            repair_entry = _citation_repair_entry(entry, coh, index=idx)
            rows.append(repair_entry)
            if not coh["coherent"]:
                by_source[repair_entry["source"]] += 1
                by_category[repair_entry["category"]] += 1
                by_signal.update(str(s) for s in repair_entry["mapped_signals"])
                by_cited.update(str(c) for c in repair_entry["cited_conventions"])
                by_expected.update(str(c) for c in repair_entry["expected_conventions"])
    bad = [r for r in rows if not r["coherent"]]
    repair_queue = bad
    privacy_scan = _metadata_privacy_scan(repair_queue, root_key="repair_queue")
    return {"n_checkable": len(rows), "n_incoherent": len(bad),
            "incoherent_rate": round(len(bad) / len(rows), 4) if rows else None,
            "examples": bad[:5],
            "repair_queue": repair_queue,
            "repair_queue_count": len(repair_queue),
            "repair_queue_metadata_only": True,
            "repair_queue_privacy_scan": privacy_scan,
            "by_source": {k: by_source[k] for k in sorted(by_source)},
            "by_category": {k: by_category[k] for k in sorted(by_category)},
            "by_mapped_signal": {k: by_signal[k] for k in sorted(by_signal)},
            "by_cited_convention": {k: by_cited[k] for k in sorted(by_cited, key=lambda v: int(v))},
            "by_expected_convention": {k: by_expected[k] for k in sorted(by_expected, key=lambda v: int(v))},
            "ok": len(bad) == 0 and privacy_scan["ok"]}


def audit() -> dict[str, Any]:
    pid_meta = load_pid_meta(FULL_SET, CURATED_SET)
    sft_tr, sft_ho = _load_jsonl(_TRAIN / "sft_train.jsonl"), _load_jsonl(_TRAIN / "sft_heldout.jsonl")
    dpo_tr, dpo_ho = _load_jsonl(_TRAIN / "dpo_train.jsonl"), _load_jsonl(_TRAIN / "dpo_heldout.jsonl")
    sft_leak = near_dup_leakage([_sft_user(r) for r in sft_tr], [_sft_user(r) for r in sft_ho])
    dpo_leak = near_dup_leakage([_string_field(r, "prompt") for r in dpo_tr],
                                [_string_field(r, "prompt") for r in dpo_ho])
    gold_entries = [
        _gold_entry(source="sft_train", source_index=idx, row=row,
                    text=_sft_assistant(row), pid_meta=pid_meta)
        for idx, row in enumerate(sft_tr)
    ] + [
        _gold_entry(source="dpo_train_chosen", source_index=idx, row=row,
                    text=_string_field(row, "chosen"), pid_meta=pid_meta)
        for idx, row in enumerate(dpo_tr)
    ]
    gold = [entry["text"] for entry in gold_entries]
    report = {
        "inputs": {"sft_train": len(sft_tr), "sft_heldout": len(sft_ho),
                   "dpo_train": len(dpo_tr), "dpo_heldout": len(dpo_ho), "pid_meta": len(pid_meta)},
        "overfitting_leakage": {"sft": sft_leak, "dpo": dpo_leak},
        "false_pattern_length_bias": length_bias(dpo_tr),
        "jurisdiction_corridor_diversity": corridor_diversity(sft_tr + dpo_tr, pid_meta),
        "fragile_fact_assertions": fragile_fact_assertions(gold),
        "citation_relevance": citation_relevance(gold_entries),
        "note": ("pre-train quality audit: leak (overfit) want 0; length ratio (false pattern) want <=2.0; "
                 "single-corridor typologies (jurisdiction shortcut) want few; phone-like in gold (fragile "
                 "fact) want 0; real-but-irrelevant legal citations want 0. Universal ILO indicators are "
                 "taught; volatile facts belong in tools/RAG."),
    }
    report["risk_flags"] = _metadata_safe_risk_flags(report)
    report["clean"] = not report["risk_flags"]
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stdout", action="store_true", help="also print the full JSON report")
    ap.add_argument(
        "--require-clean",
        action="store_true",
        help="return nonzero when the audit has any risk flags (required before training/registration)",
    )
    args = ap.parse_args(argv)
    rep = audit()
    if args.stdout:
        print(json.dumps(rep, indent=2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    inp = rep["inputs"]
    if not (inp["sft_train"] or inp["dpo_train"]):
        print("[quality-audit] no training splits -- run scripts/organize_training_data.py first")
        return 1
    print(f"[quality-audit] sft {inp['sft_train']}tr/{inp['sft_heldout']}ho dpo {inp['dpo_train']}tr/"
          f"{inp['dpo_heldout']}ho | leak(sft)={rep['overfitting_leakage']['sft'].get('leaked')} "
          f"len-ratio={rep['false_pattern_length_bias'].get('chosen_over_rejected_ratio')} "
          f"dense-single-corridor={rep['jurisdiction_corridor_diversity'].get('n_dense_single_corridor')} "
          f"gold-phone={rep['fragile_fact_assertions'].get('with_phone_like')} "
          f"citation-incoherent={rep['citation_relevance'].get('n_incoherent')}")
    print(
        f"[quality-audit] {'CLEAN' if rep['clean'] else 'FLAGS: ' + '; '.join(rep['risk_flags'])} "
        f"-> {_display_report_path(OUT)}"
    )
    if args.require_clean and not rep["clean"]:
        print("[quality-audit] BLOCKED: --require-clean was set; resolve all risk flags before training")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
