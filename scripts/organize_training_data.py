#!/usr/bin/env python3
"""Phase 3 organisation layer -- split distilled training data to favour understanding over shortcuts.

Reads the SFT/DPO from build_lift_training_data.py plus a prompt set (for prompt_id -> typology), then:
  * HELD OUT BY TYPOLOGY -- whole typologies are withheld from train and used only for the
    generalisation diagnostic (a model that memorised shortcuts can't transfer to unseen typologies).
  * BALANCE -- cap per-typology counts so no typology->response correlation dominates the data.
  * INTERLEAVE -- round-robin typologies so no batch is single-keyword (block ordering invites shortcuts).
  * DEDUP -- exact + SimHash near-duplicate (paraphrase / boilerplate), reusing
    research_tools.dedup, so a "generalisation" score isn't memorised duplicates or near-copies.

Writes reports/training/{sft,dpo}_{train,heldout}.jsonl + organize_manifest.json (gitignored).
Propose-only: never trains, never mutates the source. Design: docs/research/training_for_understanding.md

    python scripts/organize_training_data.py --heldout-fraction 0.2 --cap-per-category 40
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import re
import sys
from collections import defaultdict
from typing import Any, Callable

_ROOT = pathlib.Path(__file__).resolve().parents[1]
TRAIN_DIR = _ROOT / "reports" / "training"
SFT_IN = TRAIN_DIR / "sft.jsonl"
DPO_IN = TRAIN_DIR / "dpo.jsonl"
FULL_SET = _ROOT / "reports" / "benchmark" / "full_promptset.json"
CURATED_SET = _ROOT / "configs" / "duecare" / "benchmarks" / "scheme_prompts.json"
SEED = 17
NEAR_DUP_DIST = 3  # 64-bit SimHash Hamming distance counted as a near-duplicate (paraphrase/boilerplate)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.I)
_PHONE = re.compile(r"\+?\d[\d\s().\-]{8,}\d")
_LOCAL_PATH_HINT = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|(?:^|[\s\"'(:])/(?:Users|home|tmp|var|mnt|private|Volumes)(?:/|$)|~[\\/])",
    re.I,
)
_SAFE_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._/\-]+$")


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

# Reuse the deterministic, offline SimHash near-dup from duecare-llm-research-tools (DRY). Bridge the
# package src onto sys.path so this stays runnable as a standalone script; fall back to exact-only dedup
# if the package is unavailable (the near-dup is an enhancement, never a hard dependency).
_RT_SRC = _ROOT / "packages" / "duecare-llm-research-tools" / "src"
if _RT_SRC.exists() and str(_RT_SRC) not in sys.path:
    sys.path.insert(0, str(_RT_SRC))
try:
    from duecare.research_tools.dedup import dedup_new
    _HAVE_NEAR_DEDUP = True
except Exception:  # noqa: BLE001 -- standalone without the package: exact-only fallback (see _dedup_rows)
    dedup_new = None
    _HAVE_NEAR_DEDUP = False


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _text_hash(text: str) -> str:
    return hashlib.sha1(text.strip().lower().encode("utf-8")).hexdigest()


def load_pid2cat(*paths: pathlib.Path) -> dict[str, str]:
    """{prompt_id: category} from the first prompt set that exists (full set preferred)."""
    for path in paths:
        if not path.exists():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        prompts = doc.get("prompts", doc) if isinstance(doc, dict) else doc
        if not isinstance(prompts, list):
            continue
        return {str(p["id"]): str(p.get("category", "unknown"))
                for p in prompts if isinstance(p, dict) and p.get("id")}
    return {}


def _meta_dict(row: dict) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    meta = row.get("_meta") or {}
    return meta if isinstance(meta, dict) else {}


def _cat_of(row: dict, pid2cat: dict[str, str]) -> str:
    return pid2cat.get(str(_meta_dict(row).get("prompt_id")), "unknown")


def _sft_text(row: dict) -> str:
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


def _dpo_text(row: dict) -> str:
    if not isinstance(row, dict):
        return ""
    prompt = row.get("prompt", "")
    return prompt if isinstance(prompt, str) else ""


def _dedup(rows: list[dict], textfn: Callable[[dict], str]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        h = _text_hash(textfn(r))
        if h in seen:
            continue
        seen.add(h)
        out.append(r)
    return out


def _dedup_rows(rows: list[dict], textfn: Callable[[dict], str], *,
                near_dup_dist: int) -> tuple[list[dict], int]:
    """Exact dedup, plus SimHash near-dup (Hamming <= near_dup_dist) when research_tools is available.

    Returns (kept, n_near_dropped). Deterministic, first-occurrence-wins. Near-dup removal stops a
    paraphrased/boilerplate row from inflating a typology or leaking a memorised twin into the held-out
    generalisation set. Falls back to exact-only (n_near_dropped=0) if the package can't be imported."""
    if _HAVE_NEAR_DEDUP and near_dup_dist > 0:
        kept, dropped = dedup_new(rows, text_of=textfn, max_dist=near_dup_dist)
        return kept, sum(1 for d in dropped if d.get("_dup_reason") == "near")
    return _dedup(rows, textfn), 0


def _balance_interleave(rows: list[dict], pid2cat: dict[str, str], cap: int,
                        rng: random.Random) -> list[dict]:
    """Cap each typology then round-robin interleave (so no run of one typology / over-representation)."""
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[_cat_of(r, pid2cat)].append(r)
    for c in by:
        rng.shuffle(by[c])
        if cap:
            by[c] = by[c][:cap]
    order = sorted(by)
    out: list[dict] = []
    i = 0
    while True:
        added = False
        for c in order:
            if i < len(by[c]):
                out.append(by[c][i])
                added = True
        if not added:
            break
        i += 1
    return out


def organize(sft: list[dict], dpo: list[dict], pid2cat: dict[str, str], *,
             heldout_fraction: float, cap_per_category: int, seed: int = SEED,
             near_dup_dist: int = NEAR_DUP_DIST) -> dict[str, Any]:
    """Dedup -> hold out whole typologies -> balance + interleave the train splits. Pure / CPU-safe."""
    rng = random.Random(seed)
    sft_in, dpo_in = len(sft), len(dpo)
    sft = [row for row in sft if _sft_text(row).strip()]
    dpo = [row for row in dpo if _dpo_text(row).strip()]
    sft_malformed = sft_in - len(sft)
    dpo_malformed = dpo_in - len(dpo)
    sft, sft_near = _dedup_rows(sft, _sft_text, near_dup_dist=near_dup_dist)
    dpo, dpo_near = _dedup_rows(dpo, _dpo_text, near_dup_dist=near_dup_dist)
    cats = sorted({_cat_of(r, pid2cat) for r in (sft + dpo)})
    n_heldout = max(1, round(len(cats) * heldout_fraction)) if cats and heldout_fraction > 0 else 0
    shuffled = cats[:]
    rng.shuffle(shuffled)
    heldout_cats = set(shuffled[:n_heldout])

    def split(rows: list[dict]) -> tuple[list[dict], list[dict]]:
        tr = [r for r in rows if _cat_of(r, pid2cat) not in heldout_cats]
        ho = [r for r in rows if _cat_of(r, pid2cat) in heldout_cats]
        return tr, ho

    sft_tr, sft_ho = split(sft)
    dpo_tr, dpo_ho = split(dpo)
    sft_tr = _balance_interleave(sft_tr, pid2cat, cap_per_category, rng)
    dpo_tr = _balance_interleave(dpo_tr, pid2cat, cap_per_category, rng)
    manifest = {
        "seed": seed, "heldout_fraction": heldout_fraction, "cap_per_category": cap_per_category,
        "n_categories": len(cats), "n_heldout_categories": len(heldout_cats),
        "heldout_categories": sorted(heldout_cats),
        "dedup": {
            "method": (f"exact(sha256)+simhash64 hamming<={near_dup_dist}" if _HAVE_NEAR_DEDUP
                       else "exact only (research_tools unavailable)"),
            "malformed_or_empty": {"sft_dropped": sft_malformed, "dpo_dropped": dpo_malformed},
            "sft": {"in": sft_in, "kept_pre_split": len(sft), "near_dropped": sft_near},
            "dpo": {"in": dpo_in, "kept_pre_split": len(dpo), "near_dropped": dpo_near},
        },
        "sft": {"train": len(sft_tr), "heldout": len(sft_ho)},
        "dpo": {"train": len(dpo_tr), "heldout": len(dpo_ho)},
        "note": "whole typologies held out for the generalisation diagnostic; train balanced + interleaved",
    }
    return {"sft_train": sft_tr, "sft_heldout": sft_ho,
            "dpo_train": dpo_tr, "dpo_heldout": dpo_ho, "manifest": manifest}


def _write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sft", type=pathlib.Path, default=SFT_IN)
    ap.add_argument("--dpo", type=pathlib.Path, default=DPO_IN)
    ap.add_argument("--heldout-fraction", type=float, default=0.2,
                    help="fraction of typologies withheld entirely from train (generalisation set)")
    ap.add_argument("--cap-per-category", type=int, default=0, help="max train rows per typology (0 = no cap)")
    ap.add_argument("--near-dup-dist", type=int, default=NEAR_DUP_DIST,
                    help="SimHash Hamming distance for near-dup removal (0 = exact-only)")
    ap.add_argument("--out-dir", type=pathlib.Path, default=TRAIN_DIR)
    args = ap.parse_args(argv)

    sft = load_jsonl(args.sft)
    dpo = load_jsonl(args.dpo)
    pid2cat = load_pid2cat(FULL_SET, CURATED_SET)
    if not sft and not dpo:
        print("[organize] no training data -- run scripts/build_lift_training_data.py first")
        return 1
    if not pid2cat:
        print("[organize] WARNING: no prompt set found for typologies; all rows fall in 'unknown'")
    doc = organize(sft, dpo, pid2cat, heldout_fraction=args.heldout_fraction,
                   cap_per_category=args.cap_per_category, near_dup_dist=args.near_dup_dist)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out / "sft_train.jsonl", doc["sft_train"])
    _write_jsonl(out / "sft_heldout.jsonl", doc["sft_heldout"])
    _write_jsonl(out / "dpo_train.jsonl", doc["dpo_train"])
    _write_jsonl(out / "dpo_heldout.jsonl", doc["dpo_heldout"])
    (out / "organize_manifest.json").write_text(json.dumps(doc["manifest"], indent=2) + "\n", encoding="utf-8")
    m = doc["manifest"]
    print(f"[organize] {m['n_categories']} typologies -> {m['n_heldout_categories']} held out")
    dd = m["dedup"]
    print(f"[organize] near-dup dropped: SFT {dd['sft']['near_dropped']} / DPO {dd['dpo']['near_dropped']} "
          f"({dd['method']})")
    print(f"[organize] SFT train {m['sft']['train']} / heldout {m['sft']['heldout']} | "
          f"DPO train {m['dpo']['train']} / heldout {m['dpo']['heldout']} -> {_display_report_path(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
