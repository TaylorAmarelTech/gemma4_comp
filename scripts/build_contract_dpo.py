#!/usr/bin/env python3
"""Contract-derived DPO pairs -- minimal-pair HARD NEGATIVES that teach a model to prefer the complete
reasoning chain, targeting the weak links (statute, action, citation coherence).

Our existing DPO set (build_lift_training_data.py) pairs chosen=harnessed vs rejected=baseline -- a broad
"harness vs bare" preference. This builds a SHARPER signal: from a gold trace that satisfies the reasoning
contract (reasoning_contract.py), construct the rejected by ABLATING exactly one chain link -- delete the
sentence(s) that carry the statute citation, or the protective action -- leaving everything else identical.

    chosen   = full gold trace (indicator + statute + action + resources)
    rejected = same trace MINUS the statute sentence   (or MINUS the action sentence)

So the only difference between chosen and rejected is the presence of the link we want the model to never
drop. That isolates the exact behaviour the board says is weakest (statute and protective-action links)
into a clean contrastive pair. For citation coherence, the rejected keeps the chain but swaps the cited
ILO convention to a real-but-irrelevant convention; the contract verifier confirms the citation becomes
invalid. For statute/action, the rejected is synthetic-by-DELETION only.

Propose-only + offline + deterministic: reads reports/training/reasoning_sft.jsonl, writes a SEPARATE
reports/training/contract_dpo.jsonl (+ manifest). No model, no network, no credits.

    python scripts/build_contract_dpo.py                 # build pairs over the gold reasoning set
    python scripts/build_contract_dpo.py --links statute # only the statute hard-negatives
Design: docs/research/training_methodology.md (reasoning contract)
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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))   # sibling-script imports
from reasoning_contract import verify_reasoning  # noqa: E402
from build_reasoning_targets import has_statute, _has_any, _ACTION_TERMS  # noqa: E402
from palermo_screening import citation_coherence as _citation_coherence  # noqa: E402

REASONING_SFT = _ROOT / "reports" / "training" / "reasoning_sft.jsonl"
OUT = _ROOT / "reports" / "training" / "contract_dpo.jsonl"
MANIFEST = _ROOT / "reports" / "training" / "contract_dpo_manifest.json"
ABLATABLE = ("statute", "action", "citation_coherence")
_DELETE_LINKS = ("statute", "action")
_CITATION_SWAP_LINK = "citation_coherence"
_REAL_ILO_CONVENTIONS = (29, 95, 138, 181, 188, 189, 190)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_PROMPT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_PATH_REPORT_KEYS = frozenset({"path", "output_path", "manifest_path", "sft", "out"})


def manifest_path_for(out_path: pathlib.Path) -> pathlib.Path:
    """Manifest path for a contract-DPO output, preserving the historical default filename."""
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

# Split into sentences but DON'T break on the "No." in "ILO Convention No. 29" (next char is a digit, not
# an uppercase letter / quote), so a citation sentence stays intact and is ablated as one unit.
_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"“])')


def _sentences(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    return [s for s in _SENT_SPLIT.split(text.strip()) if s.strip()]


def _carries(sentence: str, link: str) -> bool:
    if link == "statute":
        return has_statute(sentence)
    if link == "action":
        return _has_any(sentence, _ACTION_TERMS)
    raise ValueError(f"unsupported ablation link: {link}")


def ablate_link(text: str, link: str) -> "str | None":
    """Drop the sentence(s) carrying ``link`` from ``text``. Returns the reduced text only if at least one
    sentence was removed AND the link is genuinely gone from the result (a clean removal); else None."""
    sents = _sentences(text)
    kept = [s for s in sents if not _carries(s, link)]
    if len(kept) == len(sents) or not kept:
        return None                                   # nothing carried the link, or it was the whole reply
    reduced = " ".join(kept)
    return reduced if not _carries(reduced, link) else None


def _wrong_convention(expected: set[int], cited: set[int]) -> int | None:
    for convention in _REAL_ILO_CONVENTIONS:
        if convention not in expected and convention not in cited:
            return convention
    for convention in _REAL_ILO_CONVENTIONS:
        if convention not in expected:
            return convention
    return None


def _swap_one_convention(text: str, source: int, target: int) -> str | None:
    patterns = [
        (re.compile(rf"\b(C0?)({source})\b", re.I), lambda m: f"{m.group(1)}{target:03d}"),
        (re.compile(rf"\b((?:ILO\s+)?Convention\s+No\.\s*)({source})\b", re.I),
         lambda m: f"{m.group(1)}{target}"),
        (re.compile(rf"\b(No\.\s*)({source})\b", re.I), lambda m: f"{m.group(1)}{target}"),
    ]
    for pattern, repl in patterns:
        new_text, n = pattern.subn(repl, text, count=1)
        if n:
            return new_text
    return None


def swap_citation_to_wrong_convention(text: str) -> str | None:
    """Swap one governing ILO convention citation to a real-but-irrelevant one.

    The rejected remains fluent and still carries a statute citation, but
    ``palermo_screening.citation_coherence`` must become false. This directly
    targets citation-theatre failures: real citation, wrong indicator.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    before = _citation_coherence(text)
    if not before.get("coherent"):
        return None
    expected = {int(v) for v in before.get("expected_conventions", []) if isinstance(v, int)}
    cited = {int(v) for v in before.get("cited_conventions", []) if isinstance(v, int)}
    if not expected or not cited:
        return None
    swappable = [c for c in before.get("matched", []) if isinstance(c, int)]
    if not swappable:
        return None
    target = _wrong_convention(expected, cited)
    if target is None:
        return None
    for source in swappable:
        rejected = _swap_one_convention(text, int(source), target)
        if rejected and rejected != text:
            after = _citation_coherence(rejected)
            if after.get("cited_conventions") and not after.get("coherent"):
                return rejected
    return None


def _user_text(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    messages = row.get("messages") or []
    if not isinstance(messages, list):
        return ""
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""


def _assistant_text(row: Any) -> str:
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


def _safe_prompt_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or _has_sensitive_display_text(text):
        return None
    return text if _SAFE_PROMPT_ID.fullmatch(text) else None


def _pair_key(prompt: str, chosen: str, rejected: str) -> tuple[str, str, str]:
    return (prompt.strip(), chosen.strip(), rejected.strip())


def _string_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key, "")
    return value if isinstance(value, str) else ""


def _valid_pair_shape(row: dict[str, Any]) -> bool:
    return all(_string_field(row, key).strip() for key in ("prompt", "chosen", "rejected"))


def _duplicate_pair_rows(pairs: list[dict[str, Any]]) -> int:
    counts = Counter(
        _pair_key(_string_field(p, "prompt"), _string_field(p, "chosen"), _string_field(p, "rejected"))
        for p in pairs if _valid_pair_shape(p)
    )
    return sum(n - 1 for n in counts.values() if n > 1)


def _sum_int_values(values: Any) -> int | None:
    if not isinstance(values, dict):
        return None
    total = 0
    for value in values.values():
        try:
            total += int(value)
        except (TypeError, ValueError):
            return None
    return total


def _pair_integrity(
    pairs: list[dict[str, Any]],
    *,
    min_steps: int,
) -> tuple[dict[str, int], list[str]]:
    """Re-verify generated pair rows so the manifest proves more than counts."""
    counts: Counter[str] = Counter()
    for pair in pairs:
        prompt = _string_field(pair, "prompt").strip()
        chosen = _string_field(pair, "chosen").strip()
        rejected = _string_field(pair, "rejected").strip()
        meta = pair.get("_meta") if isinstance(pair.get("_meta"), dict) else {}
        link = str(meta.get("ablated_link") or "")

        if not prompt or not chosen or not rejected:
            counts["invalid_pair_shape"] += 1
            continue
        if chosen == rejected:
            counts["unchanged_rejected"] += 1
        expected_source = "contract_citation_swap" if link == _CITATION_SWAP_LINK else "contract_ablation"
        if meta.get("source") != expected_source:
            counts["wrong_source"] += 1
        if link not in ABLATABLE:
            counts["invalid_ablated_link"] += 1
            continue

        chosen_verdict = verify_reasoning(chosen, min_steps=min_steps)
        rejected_verdict = verify_reasoning(rejected, min_steps=min_steps)
        if not chosen_verdict.satisfied:
            counts["chosen_not_contract_satisfied"] += 1
        if link == _CITATION_SWAP_LINK:
            if not chosen_verdict.citation_valid:
                counts["chosen_citation_invalid"] += 1
            if rejected_verdict.citation_valid:
                counts["rejected_citation_still_valid"] += 1
            if not rejected_verdict.steps.get("statute"):
                counts["rejected_missing_statute_after_swap"] += 1
        else:
            if len(rejected) >= len(chosen):
                counts["rejected_not_shorter"] += 1
            if not _carries(chosen, link):
                counts["chosen_missing_ablated_link"] += 1
            if _carries(rejected, link):
                counts["rejected_still_carries_ablated_link"] += 1
            if rejected_verdict.steps.get(link):
                counts["rejected_contract_still_has_ablated_link"] += 1
            if rejected_verdict.n_steps >= chosen_verdict.n_steps:
                counts["chain_not_reduced"] += 1
        if meta.get("chain_chosen") != chosen_verdict.n_steps:
            counts["chain_chosen_mismatch"] += 1
        if meta.get("chain_rejected") != rejected_verdict.n_steps:
            counts["chain_rejected_mismatch"] += 1

    issue_map = {
        "invalid_pair_shape": "contract_dpo_pair_invalid_shape",
        "unchanged_rejected": "contract_dpo_pair_rejected_unchanged",
        "rejected_not_shorter": "contract_dpo_pair_rejected_not_shorter",
        "wrong_source": "contract_dpo_pair_wrong_source",
        "invalid_ablated_link": "contract_dpo_pair_invalid_ablated_link",
        "chosen_missing_ablated_link": "contract_dpo_pair_chosen_missing_ablated_link",
        "rejected_still_carries_ablated_link": "contract_dpo_pair_rejected_still_carries_ablated_link",
        "chosen_not_contract_satisfied": "contract_dpo_pair_chosen_not_contract_satisfied",
        "rejected_contract_still_has_ablated_link": "contract_dpo_pair_rejected_contract_still_has_ablated_link",
        "chain_not_reduced": "contract_dpo_pair_chain_not_reduced",
        "chain_chosen_mismatch": "contract_dpo_pair_chain_chosen_mismatch",
        "chain_rejected_mismatch": "contract_dpo_pair_chain_rejected_mismatch",
        "chosen_citation_invalid": "contract_dpo_pair_chosen_citation_invalid",
        "rejected_citation_still_valid": "contract_dpo_pair_rejected_citation_still_valid",
        "rejected_missing_statute_after_swap": "contract_dpo_pair_rejected_missing_statute_after_swap",
    }
    issues = [issue_map[key] for key in sorted(issue_map) if counts[key]]
    return {key: counts[key] for key in sorted(counts)}, issues


def _contract_manifest_issues(
    *,
    pairs: list[dict[str, Any]],
    eligible_gold: int,
    by_link: Counter[str],
    duplicate_output_pair_rows: int,
    pair_integrity_issues: list[str],
) -> list[str]:
    issues: list[str] = []
    if eligible_gold <= 0:
        issues.append("contract_dpo_no_eligible_gold")
    if not pairs:
        issues.append("contract_dpo_no_pairs")
    if duplicate_output_pair_rows:
        issues.append("contract_dpo_duplicate_output_pairs")
    link_total = _sum_int_values(by_link)
    if link_total is None:
        issues.append("contract_dpo_link_counts_invalid")
    elif link_total != len(pairs):
        issues.append("contract_dpo_link_count_mismatch")
    issues.extend(pair_integrity_issues)
    return issues


def build_pairs(
    rows: list[dict],
    *,
    links: tuple[str, ...] = ABLATABLE,
    min_steps: int = 4,
    output_path: pathlib.Path = OUT,
) -> dict[str, Any]:
    """For each gold trace that satisfies the contract, emit one hard-negative DPO pair per requested link.

    ``statute`` and ``action`` delete the sentence carrying that link. ``citation_coherence`` keeps the
    citation sentence but swaps the convention number to a real, irrelevant convention.
    """
    pairs: list[dict] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    by_link: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    metadata_sanitized: Counter[str] = Counter()
    n_eligible = 0
    for r in rows:
        chosen = _assistant_text(r)
        prompt = _user_text(r)
        if not chosen or not prompt:
            continue
        v = verify_reasoning(chosen, min_steps=min_steps)
        if not v.satisfied:
            continue                                  # only ablate from clean, full-chain gold traces
        n_eligible += 1
        raw_pid = _meta_dict(r).get("prompt_id")
        pid = _safe_prompt_id(raw_pid)
        if raw_pid and pid is None:
            metadata_sanitized["prompt_id"] += 1
        for link in links:
            if link == _CITATION_SWAP_LINK:
                rejected = swap_citation_to_wrong_convention(chosen)
                source = "contract_citation_swap"
                if rejected is None:
                    skipped["citation_swap_unavailable"] += 1
                    continue
            else:
                if not v.steps.get(link):
                    continue
                rejected = ablate_link(chosen, link)
                source = "contract_ablation"
            if rejected is None or rejected.strip() == chosen.strip():
                continue
            key = _pair_key(prompt, chosen, rejected)
            if key in seen_pairs:
                skipped["duplicate_pair"] += 1
                continue
            seen_pairs.add(key)
            rv = verify_reasoning(rejected, min_steps=min_steps)
            pairs.append({
                "prompt": prompt, "chosen": chosen, "rejected": rejected,
                "_meta": {"prompt_id": pid, "ablated_link": link, "source": source,
                          "chain_chosen": v.n_steps, "chain_rejected": rv.n_steps},
            })
            by_link[link] += 1
    duplicate_output_pair_rows = _duplicate_pair_rows(pairs)
    pair_integrity_counts, pair_integrity_issues = _pair_integrity(pairs, min_steps=min_steps)
    contract_manifest_issues = _contract_manifest_issues(
        pairs=pairs,
        eligible_gold=n_eligible,
        by_link=by_link,
        duplicate_output_pair_rows=duplicate_output_pair_rows,
        pair_integrity_issues=pair_integrity_issues,
    )
    manifest = {
        "input": len(rows), "eligible_gold": n_eligible, "pairs": len(pairs),
        "output_path": _display_report_path(output_path),
        "manifest_path": _display_report_path(manifest_path_for(output_path)),
        "min_steps": min_steps, "by_ablated_link": {k: by_link[k] for k in sorted(by_link)},
        "skipped": {k: skipped[k] for k in sorted(skipped)},
        "metadata_sanitized": {k: metadata_sanitized[k] for k in sorted(metadata_sanitized)},
        "skipped_duplicate_pairs": skipped["duplicate_pair"],
        "duplicate_output_pair_rows": duplicate_output_pair_rows,
        "pair_integrity_counts": pair_integrity_counts,
        "pair_integrity_issues": pair_integrity_issues,
        "contract_manifest_issues": contract_manifest_issues,
        "safe_to_train": not contract_manifest_issues,
        "note": ("contract-derived hard-negative DPO: chosen = a contract-satisfying gold trace, rejected = "
                 "the same trace with either statute/action sentence(s) deleted or a governing convention "
                 "swapped to a real-but-irrelevant convention. This isolates missing-link and citation-theatre "
                 "failures into minimal contrastive pairs. The CLI refuses to write unless at least one "
                 "eligible gold trace yields at least one verified hard-negative pair. Offline/deterministic; "
                 "reuses reasoning_contract + palermo_screening.citation_coherence."),
    }
    return {"pairs": pairs, "manifest": manifest}


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
    ap.add_argument("--sft", type=pathlib.Path, default=REASONING_SFT, help="gold reasoning traces")
    ap.add_argument("--links", nargs="+", default=list(ABLATABLE), choices=list(ABLATABLE),
                    help="which chain links to ablate into hard negatives")
    ap.add_argument("--min-steps", type=int, default=4, help="contract strictness for an eligible gold trace")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--validate", action="store_true", help="print the manifest only; write nothing")
    args = ap.parse_args(argv)

    rows = _load_jsonl(args.sft)
    if not rows:
        print(
            f"[contract-dpo] no reasoning traces at {_display_report_path(args.sft)} "
            "-- run build_reasoning_targets.py first"
        )
        return 1
    doc = build_pairs(rows, links=tuple(args.links), min_steps=args.min_steps, output_path=args.out)
    m = doc["manifest"]
    if args.validate:
        print(json.dumps(_display_manifest(m), indent=2))
        return 0 if m["safe_to_train"] else 1
    if not m["safe_to_train"]:
        print(json.dumps(_display_manifest(m), indent=2))
        print("[contract-dpo] unsafe contract-DPO shape; refusing to write training JSONL")
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in doc["pairs"]), encoding="utf-8")
    manifest_path_for(args.out).write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(f"[contract-dpo] {m['eligible_gold']} eligible gold traces -> {m['pairs']} hard-negative pairs "
          f"{m['by_ablated_link']} -> {_display_report_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
