#!/usr/bin/env python3
"""Reasoning-chain target builder -- gate + annotate distilled SFT targets on the
indicator -> statute -> graded-action -> resources chain.

A good migrant-worker-safety reply is NOT a bare refusal. It walks an explicit chain:

  1. INDICATOR  -- names the exploitation indicator (one of the ILO's 11 forced-labour indicators).
  2. STATUTE    -- cites the controlling law / ILO convention.
  3. ACTION     -- a clear graded decision: refuse to operationalize harm AND/OR tell the worker what
                   to do (keep copies, don't sign, don't pay, you are not obligated).
  4. RESOURCES  -- points to protective help (embassy, regulator, hotline, NGO, file a complaint).

This reads the organized SFT train targets (reports/training/sft_train.jsonl from organize_training_data.py),
deterministically detects which of the four chain links each teacher reply contains -- reusing the
project's own vocabulary (migrant_taxonomy ILO indicators + citation_accuracy + refusal_detector) --
scores chain completeness 0-4, verifies that cited ILO conventions govern the named indicators, ANNOTATES
every row, and KEEPS only the targets that exemplify the chain (>= --min-chain links). So the fine-tune
learns to answer with details + relevant citations + a concrete action + resources, never "a refusal
without details or citations" or a real-but-irrelevant legal citation.

Propose-only and additive: reads sft_train.jsonl, writes a SEPARATE reports/training/reasoning_sft.jsonl +
reasoning_manifest.json -- it never mutates or destroys the source set or the held-out split. Offline,
deterministic (no model, no network), so the curation is reproducible.

    python scripts/build_reasoning_targets.py --min-chain 3
    python scripts/build_reasoning_targets.py --validate     # print the manifest only, write nothing
Design: docs/research/training_regimes_and_systems.md
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
# Sibling scripts -- importable however this script is run or imported.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from citation_accuracy import citation_stats as _citation_stats  # noqa: E402
from palermo_screening import citation_coherence as _citation_coherence  # noqa: E402
from refusal_detector import classify as _classify, FORMAT_FAILURE  # noqa: E402
try:
    from migrant_taxonomy import ILO_INDICATORS as _ILO  # canonical 11 forced-labour indicators
except Exception:  # noqa: BLE001 -- standalone without the taxonomy: fall back to the hardcoded set below
    _ILO = ()

SFT_IN = _ROOT / "reports" / "training" / "sft_train.jsonl"
OUT = _ROOT / "reports" / "training" / "reasoning_sft.jsonl"
MANIFEST = _ROOT / "reports" / "training" / "reasoning_manifest.json"
DEFAULT_MIN_CHAIN = 3   # of 4 links -- a target may miss at most one link (e.g. resources) and still teach
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_PATH_REPORT_KEYS = frozenset({"path", "output_path", "manifest_path", "sft", "out"})


def manifest_path_for(out_path: pathlib.Path) -> pathlib.Path:
    """Manifest path for a reasoning-target output, preserving the historical default filename."""
    try:
        if out_path.resolve() == OUT.resolve():
            return MANIFEST
    except OSError:
        pass
    return out_path.with_name(f"{out_path.stem}_manifest.json")


def _has_sensitive_display_text(text: str) -> bool:
    return bool(
        _EMAIL.search(text)
        or _PHONE.search(text)
        or _LOCAL_PATH_HINT.search(text)
        or re.search(r"\b\d{9,}\b", text)
    )


def _safe_relative_report_path(path: pathlib.PurePath) -> str:
    display = path.as_posix()
    if not display or display.startswith("../") or "/../" in display:
        return "redacted"
    if _has_sensitive_display_text(display):
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


def _display_manifest(value: Any, *, key: str = "") -> Any:
    if isinstance(value, dict):
        return {item_key: _display_manifest(item_value, key=str(item_key))
                for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_display_manifest(item, key=key) for item in value]
    if isinstance(value, str) and (key in _PATH_REPORT_KEYS or key.endswith("_path")):
        return _display_report_path(value)
    if isinstance(value, str) and _has_sensitive_display_text(value):
        return "redacted"
    return value

# INDICATOR: the canonical ILO 11 (as phrases) plus the colloquial phrasings a model actually emits.
_INDICATOR_TERMS = tuple(sorted({ind.replace("_", " ") for ind in _ILO} | {
    "abuse of vulnerability", "deception", "deceiv", "false promise", "restriction of movement",
    "freedom of movement", "confined", "kafala", "isolation", "physical", "sexual violence",
    "intimidat", "threat", "deport", "retention of", "passport", "identity document",
    "document confiscat", "confiscat", "withholding of wages", "withheld", "unpaid wage", "wage theft",
    "debt bondage", "bonded", "abusive conditions", "excessive overtime", "no rest day",
    "recruitment fee", "contract substitution", "forced labour", "forced labor", "coerc", "trafficking",
}))
# ACTION: a graded decision -- a refusal to operationalize harm, or concrete protective guidance/directive.
_ACTION_TERMS = (
    "cannot help", "can't help", "cannot assist", "can't assist", "won't help", "will not help",
    "unable to assist", "i will not", "i refuse", "refuse to", "decline to", "not obligated",
    "you are not required", "you have the right", "you should", "you should not", "do not sign",
    "don't sign", "do not agree", "keep copies", "keep a copy", "request a copy", "ask for a copy",
    "document everything", "gather evidence", "do not pay", "don't pay", "do not hand over",
    "never hand over", "do not give", "i recommend", "i'd recommend", "i would recommend",
    "it is advisable", "advisable to", "report this", "report it", "seek legal", "seek advice",
    "consult a", "insist on", "stop and",
)
# RESOURCES: where to get protective help (distinct terms; ILO/IOM excluded -- they read as statute cites).
_RESOURCE_TERMS = (
    "hotline", "helpline", "embassy", "consulate", "regulator", "labour office", "labor office",
    "authorities", "ngo", "file a complaint", "report to", "report it", "contact the", "contact a",
    "contact your", "national referral", "police", "trade union", "migrant resource",
    "support organization", "support organisation", "seek help", "reach out to",
)


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    if not isinstance(text, str):
        return False
    low = text.lower()
    return any(term in low for term in terms)


def has_indicator(text: str) -> bool:
    """The reply names an exploitation indicator (ILO 11 or a colloquial equivalent)."""
    return _has_any(text, _INDICATOR_TERMS)


def has_statute(text: str) -> bool:
    """The reply cites a law: an ILO convention number or a statute section reference."""
    if not isinstance(text, str):
        return False
    cs = _citation_stats(text)
    return cs.get("n_conventions", 0) > 0 or cs.get("n_section_refs", 0) > 0


def has_action(text: str) -> bool:
    """A graded decision: the reply isn't a format failure (empty/trace/too-short) and states a refusal
    or a directive. A grounded REFUSAL counts -- refusing to operationalize harm is the desired action
    (refusal_detector treats 'refusal' as context-dependent, NOT a format failure)."""
    if not isinstance(text, str):
        return False
    _useful, reason = _classify(text)
    return reason not in FORMAT_FAILURE and _has_any(text, _ACTION_TERMS)


def has_resources(text: str) -> bool:
    """The reply points the worker to protective help."""
    return _has_any(text, _RESOURCE_TERMS)


def chain_links(text: str) -> dict[str, bool]:
    """{indicator, statute, action, resources} presence for one reply."""
    return {"indicator": has_indicator(text), "statute": has_statute(text),
            "action": has_action(text), "resources": has_resources(text)}


def _citation_checkable(coherence: dict[str, Any]) -> bool:
    return bool(coherence.get("mapped_signals") and coherence.get("cited_conventions"))


def citation_relevant(text: str) -> bool:
    """True unless the reply names a mapped signal, cites ILO convention(s), and none govern the signal."""
    if not isinstance(text, str):
        return False
    return bool(_citation_coherence(text)["coherent"])


def _assistant_text(row: Any) -> str:
    """The assistant (teacher) reply from a chat-format SFT row (last assistant turn)."""
    if not isinstance(row, dict):
        return ""
    messages = row.get("messages") or []
    if not isinstance(messages, list):
        return ""
    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""


def _meta_dict(row: dict) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    meta = row.get("_meta") or {}
    return dict(meta) if isinstance(meta, dict) else {}


def _safe_citation_example(row: dict, coherence: dict[str, Any]) -> dict[str, Any]:
    """Structured citation metadata only; never include the raw assistant text."""
    return {
        "prompt_id": _meta_dict(row).get("prompt_id"),
        "mapped_signals": coherence.get("mapped_signals", []),
        "cited_conventions": coherence.get("cited_conventions", []),
        "expected_conventions": coherence.get("expected_conventions", []),
        "matched": coherence.get("matched", []),
        "coherent": coherence.get("coherent", False),
    }


def build(
    rows: list[dict],
    *,
    min_chain: int = DEFAULT_MIN_CHAIN,
    require_citation_relevance: bool = True,
    contract: str = "off",
    output_path: pathlib.Path = OUT,
) -> dict[str, Any]:
    """Annotate each SFT row with its reasoning-chain links + completeness; keep those with
    >= ``min_chain`` of 4 links and, by default, no real-but-irrelevant ILO convention citation.
    Pure / offline. Returns {"rows", "manifest"}."""
    if contract not in {"off", "strict"}:
        raise ValueError(f"unsupported contract mode: {contract}")
    verify_reasoning = None
    if contract == "strict":
        from reasoning_contract import verify_reasoning as _verify_reasoning  # noqa: PLC0415
        verify_reasoning = _verify_reasoning
    kept: list[dict] = []
    dist: Counter[int] = Counter()
    link_counts: Counter[str] = Counter()
    citation_checkable = 0
    citation_incoherent = 0
    dropped_incoherent = 0
    contract_checked = 0
    dropped_contract = 0
    incoherent_examples: list[dict[str, Any]] = []
    contract_violation_examples: list[dict[str, Any]] = []
    for r in rows:
        text = _assistant_text(r)
        links = chain_links(text)
        coherence = _citation_coherence(text)
        if _citation_checkable(coherence):
            citation_checkable += 1
            if not coherence["coherent"]:
                citation_incoherent += 1
        n = sum(links.values())
        dist[n] += 1
        for k, present in links.items():
            if present:
                link_counts[k] += 1
        if n >= min_chain:
            if require_citation_relevance and links["statute"] and not coherence["coherent"]:
                dropped_incoherent += 1
                if len(incoherent_examples) < 10:
                    incoherent_examples.append(_safe_citation_example(r, coherence))
                continue
            if verify_reasoning is not None:
                contract_checked += 1
                verdict = verify_reasoning(
                    text,
                    min_steps=4,
                    require_triad=True,
                    require_core_remedies=True,
                )
                if not verdict.satisfied:
                    dropped_contract += 1
                    if len(contract_violation_examples) < 10:
                        contract_violation_examples.append({
                            "prompt_id": _meta_dict(r).get("prompt_id"),
                            "n_steps": verdict.n_steps,
                            "citation_valid": verdict.citation_valid,
                            "palermo_triad_complete": verdict.palermo.get("triad_complete", False),
                            "core_remedies_complete": verdict.core_remedies.get("complete", True),
                            "violations": list(verdict.violations),
                        })
                    continue
            out = dict(r)
            meta = _meta_dict(out)
            meta["chain_links"] = links
            meta["chain_completeness"] = n
            meta["contract"] = contract
            out["_meta"] = meta
            kept.append(out)
    manifest = {
        "input": len(rows), "kept": len(kept), "min_chain": min_chain,
        "output_path": _display_report_path(output_path),
        "manifest_path": _display_report_path(manifest_path_for(output_path)),
        "require_citation_relevance": require_citation_relevance,
        "contract": contract,
        "contract_checked": contract_checked,
        "dropped_contract": dropped_contract,
        "contract_violation_examples": contract_violation_examples,
        "citation_relevance_checkable": citation_checkable,
        "citation_relevance_incoherent": citation_incoherent,
        "dropped_incoherent_citations": dropped_incoherent,
        "incoherent_citation_examples": incoherent_examples,
        "completeness_distribution": {str(k): dist[k] for k in sorted(dist)},
        "link_presence": {k: link_counts.get(k, 0) for k in ("indicator", "statute", "action", "resources")},
        "note": ("additive curation of organize_training_data's sft_train.jsonl: keeps targets that exemplify "
                 "the indicator->statute->action->resources chain (>= min_chain of 4 links) so the fine-tune "
                 "learns details + relevant citations + action + resources, never a bare refusal or a "
                 "real-but-irrelevant legal citation. Optional strict contract mode also requires the "
                 "full reasoning contract, Palermo triad, and mandatory core remedies. Detectors reuse "
                 "migrant_taxonomy ILO indicators + citation_accuracy + refusal_detector + "
                 "palermo_screening.citation_coherence; offline/deterministic."),
    }
    return {"rows": kept, "manifest": manifest}


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sft", type=pathlib.Path, default=SFT_IN, help="distilled SFT targets to curate")
    ap.add_argument("--min-chain", type=int, default=DEFAULT_MIN_CHAIN,
                    help="min of 4 chain links (indicator/statute/action/resources) to keep a target")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--allow-incoherent-citations", action="store_true",
                    help="legacy mode: keep chain-qualified rows even when cited conventions do not govern "
                         "the named indicator")
    ap.add_argument("--contract", choices=("off", "strict"), default="off",
                    help="strict additionally requires reasoning_contract with Palermo triad + core remedies")
    ap.add_argument("--validate", action="store_true", help="print the manifest only; write nothing")
    args = ap.parse_args(argv)

    rows = _load_jsonl(args.sft)
    if not rows:
        print(f"[reasoning-targets] no SFT train split at {_display_report_path(args.sft)} "
              "-- run build_lift_training_data.py, then organize_training_data.py")
        return 1
    doc = build(rows, min_chain=args.min_chain,
                require_citation_relevance=not args.allow_incoherent_citations,
                contract=args.contract,
                output_path=args.out)
    m = doc["manifest"]
    if args.validate:
        print(json.dumps(_display_manifest(m), indent=2))
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in doc["rows"]), encoding="utf-8")
    manifest_path_for(args.out).write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(f"[reasoning-targets] {m['input']} targets -> kept {m['kept']} with >= {args.min_chain}/4 chain "
          f"links | links present: {m['link_presence']} | dist {m['completeness_distribution']} "
          f"-> {_display_report_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
