#!/usr/bin/env python3
"""Build a DPO training variant that mixes base harness preferences with contract hard negatives.

Inputs:
  reports/training/dpo_train.jsonl      -- ordinary harnessed-vs-baseline preference pairs
  reports/training/contract_dpo.jsonl   -- strict reasoning-contract ablation pairs

Output:
  reports/training/dpo_train_plus_contract.jsonl
  reports/training/dpo_train_plus_contract_manifest.json

The output is a separate gitignored training arm, not a mutation of the base DPO split. Every row keeps
its original prompt/chosen/rejected payload, and receives metadata identifying the component it came from.
The manifest fails closed if either component is missing, malformed, duplicated, lacks contract-link
metadata, or if the base-DPO / contract-DPO source manifests are missing / unsafe / stale.

Offline + deterministic. No model, no network, no credits.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from collections import Counter
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
TRAIN_DIR = _ROOT / "reports" / "training"
DPO_TRAIN = TRAIN_DIR / "dpo_train.jsonl"
CONTRACT_DPO = TRAIN_DIR / "contract_dpo.jsonl"
ORGANIZE_MANIFEST = TRAIN_DIR / "organize_manifest.json"
OUT = TRAIN_DIR / "dpo_train_plus_contract.jsonl"
CONTRACT_LINKS = {"statute", "action"}
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")
_SAFE_MANIFEST_ISSUE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,120}$")
_PATH_REPORT_KEYS = frozenset({"path", "base_path", "output_path", "manifest_path", "base_dpo", "contract_dpo"})


def manifest_path_for(out_path: pathlib.Path) -> pathlib.Path:
    return out_path.with_name(f"{out_path.stem}_manifest.json")


MANIFEST = manifest_path_for(OUT)


def source_manifest_path_for(path: pathlib.Path) -> pathlib.Path:
    return path.with_name(f"{path.stem}_manifest.json")


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


def _same_path(left: str | None, right: pathlib.Path | None) -> bool:
    if not left or right is None:
        return False
    try:
        return pathlib.Path(left).resolve() == pathlib.Path(right).resolve()
    except OSError:
        return False


def _load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def load_source_manifest(path: pathlib.Path) -> dict[str, Any]:
    manifest_path = source_manifest_path_for(path)
    if not manifest_path.exists():
        return {"path": str(manifest_path), "missing": True}
    try:
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"path": str(manifest_path), "error": f"invalid JSON: {exc}"}
    if isinstance(doc, dict):
        doc = dict(doc)
        doc["path"] = str(manifest_path)
        return doc
    return {"path": str(manifest_path), "error": "manifest root is not an object"}


def load_manifest(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "missing": True}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"path": str(path), "error": f"invalid JSON: {exc}"}
    if isinstance(doc, dict):
        doc = dict(doc)
        doc["path"] = str(path)
        return doc
    return {"path": str(path), "error": "manifest root is not an object"}


def _meta_dict(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    meta = row.get("_meta") or {}
    return dict(meta) if isinstance(meta, dict) else {}


def _valid_pair(row: dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False
    return all(_string_field(row, key).strip() for key in ("prompt", "chosen", "rejected"))


def _pair_key(row: dict[str, Any]) -> tuple[str, str, str]:
    if not isinstance(row, dict):
        return ("", "", "")
    return (
        _string_field(row, "prompt").strip(),
        _string_field(row, "chosen").strip(),
        _string_field(row, "rejected").strip(),
    )


def _string_field(row: dict[str, Any], key: str) -> str:
    value = row.get(key, "")
    return value if isinstance(value, str) else ""


def _tag(row: dict[str, Any], component: str) -> dict[str, Any]:
    out = dict(row)
    meta = _meta_dict(out)
    meta["dpo_variant"] = {
        "name": "base_plus_contract",
        "component": component,
        "source": "build_dpo_mix_variant.py",
    }
    out["_meta"] = meta
    return out


def _duplicate_pair_rows(rows: list[dict[str, Any]]) -> int:
    counts = Counter(_pair_key(row) for row in rows if _valid_pair(row))
    return sum(n - 1 for n in counts.values() if n > 1)


def _sum_int_values(values: Any) -> int | None:
    if not isinstance(values, dict):
        return None
    total = 0
    for key, value in values.items():
        if not isinstance(key, str) or key not in CONTRACT_LINKS:
            return None
        try:
            total += int(value)
        except (TypeError, ValueError):
            return None
    return total


def _normalised_int_counts(values: Any) -> dict[str, int] | None:
    if not isinstance(values, dict):
        return None
    out: dict[str, int] = {}
    for key, value in values.items():
        if not isinstance(key, str) or key not in CONTRACT_LINKS:
            return None
        try:
            out[key] = int(value)
        except (TypeError, ValueError):
            return None
    return {key: out[key] for key in sorted(out)}


def _sanitized_manifest_issues(value: Any) -> list[str]:
    if not value:
        return []
    if not isinstance(value, list):
        return ["manifest_issue_redacted"]
    issues: list[str] = []
    for item in value:
        if (
            isinstance(item, str)
            and _SAFE_MANIFEST_ISSUE_CODE.fullmatch(item)
            and not _has_sensitive_display_text(item)
        ):
            issues.append(item)
        else:
            issues.append("manifest_issue_redacted")
    return issues


def _valid_contract_link(value: Any) -> str | None:
    return value if isinstance(value, str) and value in CONTRACT_LINKS else None


def _contract_row_metadata_issues(
    contract_rows: list[dict[str, Any]],
    contract_manifest: dict[str, Any] | None,
) -> tuple[dict[str, int], list[str]]:
    """Validate contract-DPO input row provenance before tagging the mixed variant."""
    counts: Counter[str] = Counter()
    by_link: Counter[str] = Counter()
    for row in contract_rows:
        meta = row.get("_meta")
        if not isinstance(meta, dict):
            counts["missing_meta"] += 1
            meta = {}
        if meta.get("source") != "contract_ablation":
            counts["wrong_source"] += 1
        link = _valid_contract_link(meta.get("ablated_link"))
        if link:
            by_link[link] += 1
        elif meta.get("ablated_link"):
            counts["invalid_ablated_link"] += 1
        else:
            counts["missing_ablated_link"] += 1

    issues: list[str] = []
    if counts["missing_meta"]:
        issues.append("contract_row_missing_meta")
    if counts["wrong_source"]:
        issues.append("contract_row_wrong_source")
    if counts["missing_ablated_link"]:
        issues.append("contract_row_missing_ablated_link")
    if counts["invalid_ablated_link"]:
        issues.append("contract_row_invalid_ablated_link")

    source_links = _normalised_int_counts((contract_manifest or {}).get("by_ablated_link"))
    if source_links is not None:
        actual_links = {key: by_link[key] for key in sorted(by_link)}
        if actual_links != source_links:
            issues.append("contract_row_link_counts_mismatch_source_manifest")

    return {key: counts[key] for key in sorted(counts)}, issues


def build_mix(
    base_rows: list[dict[str, Any]],
    contract_rows: list[dict[str, Any]],
    *,
    base_manifest: dict[str, Any] | None = None,
    base_path: pathlib.Path | None = None,
    contract_manifest: dict[str, Any] | None = None,
    contract_path: pathlib.Path | None = None,
    output_path: pathlib.Path = OUT,
) -> dict[str, Any]:
    """Return {"rows", "manifest"} for the combined DPO arm."""
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    skipped: Counter[str] = Counter()
    by_component: Counter[str] = Counter()
    by_ablated_link: Counter[str] = Counter()

    def add(component_rows: list[dict[str, Any]], component: str) -> None:
        for row in component_rows:
            if not _valid_pair(row):
                skipped[f"{component}_invalid_pair"] += 1
                continue
            key = _pair_key(row)
            if key in seen:
                skipped[f"{component}_duplicate_pair"] += 1
                continue
            seen.add(key)
            out = _tag(row, component)
            meta = out.get("_meta") or {}
            rows.append(out)
            by_component[component] += 1
            if component == "contract":
                link = _valid_contract_link(meta.get("ablated_link"))
                if link:
                    meta["ablated_link"] = link
                    by_ablated_link[link] += 1
                else:
                    meta.pop("ablated_link", None)
                out["_meta"] = meta

    add(base_rows, "base")
    add(contract_rows, "contract")

    duplicate_output_pair_rows = _duplicate_pair_rows(rows)
    skipped_duplicate_pairs = skipped["base_duplicate_pair"] + skipped["contract_duplicate_pair"]
    skipped_invalid_pairs = skipped["base_invalid_pair"] + skipped["contract_invalid_pair"]
    contract_row_metadata_counts, contract_row_metadata_issues = _contract_row_metadata_issues(
        contract_rows,
        contract_manifest,
    )
    base_manifest_summary: dict[str, Any] | None = None
    source_manifest_issues: list[str] = []
    if base_manifest is None:
        source_manifest_issues.append("organize_manifest_missing")
    else:
        dpo_manifest = base_manifest.get("dpo") or {}
        dedup_manifest = (base_manifest.get("dedup") or {}).get("dpo") or {}
        base_manifest_summary = {
            "path": base_manifest.get("path"),
            "base_path": str(base_path) if base_path is not None else None,
            "dpo_train": dpo_manifest.get("train"),
            "dpo_heldout": dpo_manifest.get("heldout"),
            "seed": base_manifest.get("seed"),
            "heldout_fraction": base_manifest.get("heldout_fraction"),
            "dedup_kept_pre_split": dedup_manifest.get("kept_pre_split"),
        }
        if base_manifest.get("missing"):
            source_manifest_issues.append("organize_manifest_missing")
        elif base_manifest.get("error"):
            source_manifest_issues.append("organize_manifest_invalid")
        else:
            expected_train = dpo_manifest.get("train")
            if not isinstance(expected_train, int):
                source_manifest_issues.append("organize_manifest_dpo_train_count_invalid")
            elif expected_train != len(base_rows):
                source_manifest_issues.append("organize_manifest_dpo_train_count_mismatch")

    contract_manifest_summary: dict[str, Any] | None = None
    if contract_manifest is None:
        source_manifest_issues.append("contract_dpo_manifest_missing")
    else:
        contract_manifest_summary = {
            "path": contract_manifest.get("path"),
            "output_path": contract_manifest.get("output_path"),
            "pairs": contract_manifest.get("pairs"),
            "safe_to_train": contract_manifest.get("safe_to_train"),
            "by_ablated_link": _normalised_int_counts(contract_manifest.get("by_ablated_link")),
            "pair_integrity_issues": _sanitized_manifest_issues(contract_manifest.get("pair_integrity_issues")),
            "contract_manifest_issues": _sanitized_manifest_issues(contract_manifest.get("contract_manifest_issues")),
            "duplicate_output_pair_rows": contract_manifest.get("duplicate_output_pair_rows"),
            "skipped_duplicate_pairs": contract_manifest.get("skipped_duplicate_pairs"),
        }
        if contract_manifest.get("missing"):
            source_manifest_issues.append("contract_dpo_manifest_missing")
        elif contract_manifest.get("error"):
            source_manifest_issues.append("contract_dpo_manifest_invalid")
        else:
            if contract_manifest.get("safe_to_train") is not True:
                source_manifest_issues.append("contract_dpo_manifest_not_safe")
            if contract_manifest.get("pair_integrity_issues"):
                source_manifest_issues.append("contract_dpo_manifest_pair_integrity_issues")
            if contract_manifest.get("contract_manifest_issues"):
                source_manifest_issues.append("contract_dpo_manifest_issues_present")
            if contract_manifest.get("pairs") != len(contract_rows):
                source_manifest_issues.append("contract_dpo_manifest_pair_count_mismatch")
            if contract_path is not None and not _same_path(contract_manifest.get("output_path"), contract_path):
                source_manifest_issues.append("contract_dpo_manifest_output_path_mismatch")
            if contract_manifest.get("duplicate_output_pair_rows") not in (0, None):
                source_manifest_issues.append("contract_dpo_manifest_duplicate_output_pairs")
            source_links_total = _sum_int_values(contract_manifest.get("by_ablated_link") or {})
            if source_links_total is None:
                source_manifest_issues.append("contract_dpo_manifest_link_counts_invalid")
            elif source_links_total != len(contract_rows):
                source_manifest_issues.append("contract_dpo_manifest_link_count_mismatch")
            source_links = _normalised_int_counts(contract_manifest.get("by_ablated_link") or {})
            actual_links = {key: by_ablated_link[key] for key in sorted(by_ablated_link)}
            if source_links is not None and source_links != actual_links:
                source_manifest_issues.append("contract_dpo_manifest_link_count_by_type_mismatch")

    safe_to_train = (
        len(base_rows) > 0
        and len(contract_rows) > 0
        and by_component["base"] > 0
        and by_component["contract"] > 0
        and duplicate_output_pair_rows == 0
        and skipped_duplicate_pairs == 0
        and skipped_invalid_pairs == 0
        and not source_manifest_issues
        and not contract_row_metadata_issues
    )

    manifest = {
        "variant": "base_plus_contract",
        "base_input_rows": len(base_rows),
        "contract_input_rows": len(contract_rows),
        "base_rows": by_component["base"],
        "contract_rows": by_component["contract"],
        "output_rows": len(rows),
        "pairs": len(rows),
        "by_component": {k: by_component[k] for k in sorted(by_component)},
        "by_ablated_link": {k: by_ablated_link[k] for k in sorted(by_ablated_link)},
        "contract_row_metadata_counts": contract_row_metadata_counts,
        "contract_row_metadata_issues": contract_row_metadata_issues,
        "source_manifests": {"base_dpo": base_manifest_summary, "contract_dpo": contract_manifest_summary},
        "source_manifest_issues": source_manifest_issues,
        "skipped": {k: skipped[k] for k in sorted(skipped)},
        "skipped_duplicate_pairs": skipped_duplicate_pairs,
        "skipped_invalid_pairs": skipped_invalid_pairs,
        "duplicate_output_pair_rows": duplicate_output_pair_rows,
        "safe_to_train": safe_to_train,
        "metadata_only": True,
        "output_contains_training_text": True,
        "output_path": str(output_path),
        "manifest_path": str(manifest_path_for(output_path)),
        "note": (
            "DPO training variant: base harness preference pairs plus contract-derived hard negatives. "
            "The base DPO split is not mutated; the output is a separate gitignored comparison arm. "
            "The CLI refuses to write unless contract rows already carry contract-ablation provenance "
            "and their ablated-link counts match the upstream contract-DPO manifest."
        ),
    }
    return {"rows": rows, "manifest": manifest}


def _write_jsonl(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-dpo", type=pathlib.Path, default=DPO_TRAIN, help="organized base DPO train split")
    ap.add_argument("--base-manifest", type=pathlib.Path, default=ORGANIZE_MANIFEST,
                    help="organize_training_data.py manifest proving the base DPO train split count")
    ap.add_argument("--contract-dpo", type=pathlib.Path, default=CONTRACT_DPO, help="contract-ablation DPO rows")
    ap.add_argument("--out", type=pathlib.Path, default=OUT)
    ap.add_argument("--validate", action="store_true", help="print manifest only; write nothing")
    args = ap.parse_args(argv)

    base_rows = _load_jsonl(args.base_dpo)
    contract_rows = _load_jsonl(args.contract_dpo)
    base_manifest = load_manifest(args.base_manifest)
    contract_manifest = load_source_manifest(args.contract_dpo)
    if not base_rows:
        print(f"[dpo-mix] no base DPO rows at {_display_report_path(args.base_dpo)} "
              "-- run organize_training_data.py first")
        return 1
    if not contract_rows:
        print(f"[dpo-mix] no contract DPO rows at {_display_report_path(args.contract_dpo)} "
              "-- run build_contract_dpo.py first")
        return 1

    doc = build_mix(base_rows, contract_rows, base_manifest=base_manifest, base_path=args.base_dpo,
                    contract_manifest=contract_manifest, contract_path=args.contract_dpo, output_path=args.out)
    manifest = doc["manifest"]
    if args.validate:
        print(json.dumps(_display_manifest(manifest), indent=2, ensure_ascii=False))
        return 0 if manifest["safe_to_train"] else 1
    if not manifest["safe_to_train"]:
        print(json.dumps(_display_manifest(manifest), indent=2, ensure_ascii=False))
        print("[dpo-mix] unsafe mixed DPO shape; refusing to write training JSONL")
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(args.out, doc["rows"])
    manifest_path_for(args.out).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8")
    print(f"[dpo-mix] {manifest['base_rows']} base + {manifest['contract_rows']} contract pairs "
          f"-> {_display_report_path(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
