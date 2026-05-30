"""Opus-4.8 judge pipeline for the harness-lift benchmark (plumbing half).

The MOST intelligent judge for this benchmark is Claude Opus 4.8 itself, reached
through the orchestrator's own subagents (no Anthropic API key required). This
script is the deterministic plumbing around that; the judging is done by Opus
subagents that read a batch file and write a scorecard file.

Pipeline (resumable, scales 500 -> 2000 prompts):

    1. `batches`  -- read the persisted responses + the ~98-dim rubric, find the
                     (prompt, model, arm) cells NOT yet in the Opus checkpoint,
                     and write them as batch JSON files under reports/opus_batches/.
    2. (Opus)     -- each batch file is handed to an Opus 4.8 subagent, which
                     scores every response across all rubric dimensions and
                     writes reports/opus_scorecards/<batch>.json.
    3. `ingest`   -- fold the scorecards into the per-cell checkpoint
                     reports/harness_lift_500_opus.jsonl (one row per applicable
                     (prompt, model, arm, dim)) and print the lift aggregate,
                     overall and per dimension-group.

One Opus call grades a whole response across all dimensions (a rubric
scorecard), so the call count is responses (500 x models x 2), not
responses x dims -- which is what makes Opus-grade judging tractable at scale
while still producing a per-dimension result. NOT_APPLICABLE dimensions are
scored null and excluded from both numerator and denominator (same semantics as
the local grader's pct_score).

Public synthetic prompts/responses only (rule 81); no PII, no secrets.
"""
from __future__ import annotations

import glob
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
for _src in glob.glob(str(_ROOT / "packages" / "*" / "src")):
    if _src not in sys.path:
        sys.path.insert(0, _src)

from harness_lift_scheduled import aggregate, cell_key, load_checkpoint  # noqa: E402
from dimension_selector import relevant_dim_ids  # noqa: E402
from applicability_judge import load_tags as _load_applic_tags  # noqa: E402

_BENCH = _ROOT / "configs" / "duecare" / "benchmarks"
_REPORTS = _ROOT / "reports"
_BATCH_DIR = _REPORTS / "opus_batches"
_SCORECARD_DIR = _REPORTS / "opus_scorecards"


def _load_responses(path: pathlib.Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _load_prompts(prompts_file: str) -> dict[str, str]:
    data = json.loads((_BENCH / prompts_file).read_text(encoding="utf-8"))
    return {str(p["id"]): p["text"] for p in data["prompts"]}


def _load_prompt_meta(prompts_file: str) -> dict[str, dict]:
    """{id: {category, framing, sector, corridor}} for the dimension selector,
    drawn from the prompts file and enriched from the (richer) expansion corpus."""
    meta: dict[str, dict] = {}
    try:
        for p in json.loads((_BENCH / prompts_file).read_text(encoding="utf-8"))["prompts"]:
            corr = p.get("corridors") or []
            meta[str(p["id"])] = {"category": p.get("category", ""), "framing": p.get("framing", ""),
                                  "sector": p.get("sector", ""),
                                  "corridor": (corr[0] if corr else p.get("corridor", ""))}
    except Exception:
        pass
    exp = _BENCH / "harness_lift_prompts_expansion.jsonl"
    if exp.exists():
        for line in exp.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("id"):
                meta[str(d["id"])] = {"category": d.get("category", ""), "framing": d.get("framing", ""),
                                      "sector": d.get("sector", ""), "corridor": d.get("corridor", "")}
    return meta


def make_batches(responses_path: pathlib.Path, checkpoint_path: pathlib.Path,
                 prompts_file: str, *, batch_size: int = 8) -> int:
    """Write batch files for every (prompt, model, arm) response not yet judged.
    Returns the number of batch files written."""
    dims = json.loads((_BENCH / "harness_lift_dimensions.json").read_text(encoding="utf-8"))["dimensions"]
    prompts = _load_prompts(prompts_file)
    meta_by_id = _load_prompt_meta(prompts_file)
    judge_tags = _load_applic_tags()  # model applicability-judge results (augment the rules)
    judged = {ck.rsplit("|", 1)[0] for ck in load_checkpoint(checkpoint_path)}  # pid|model|arm
    responses = _load_responses(responses_path)

    pending = []
    seen = set()
    for r in responses:
        rc = f"{r['prompt_id']}|{r['model']}|{r['arm']}"
        if rc in judged or rc in seen:
            continue
        seen.add(rc)
        pid = str(r["prompt_id"])
        # Per-item RELEVANT dimension subset (skip dims that do not apply to this
        # prompt -- other sectors/corridors, attack groups on a worker prompt, etc.)
        pending.append({"prompt_id": r["prompt_id"], "model": r["model"], "arm": r["arm"],
                        "prompt": prompts.get(pid, ""), "response": r["response"],
                        "dim_ids": relevant_dim_ids(meta_by_id.get(pid, {}), dims,
                                                    judge=judge_tags.get(pid))})

    _BATCH_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    for i in range(0, len(pending), batch_size):
        chunk = pending[i:i + batch_size]
        (_BATCH_DIR / f"batch_{i // batch_size:04d}.json").write_text(
            json.dumps({"dimensions": dims, "items": chunk}, indent=2), encoding="utf-8")
        n += 1
    print(f"[opus-judge] {len(pending)} un-judged cells -> {n} batch files "
          f"(size {batch_size}) in {_BATCH_DIR}")
    return n


def ingest(checkpoint_path: pathlib.Path) -> dict:
    """Fold every scorecard file into the per-cell checkpoint (resumable: skip
    cells already present). Returns the lift aggregate."""
    done = load_checkpoint(checkpoint_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    added = 0
    for sc_file in sorted(glob.glob(str(_SCORECARD_DIR / "*.json"))):
        try:
            cards = json.loads(pathlib.Path(sc_file).read_text(encoding="utf-8"))["scorecards"]
        except Exception as exc:  # noqa: BLE001
            print(f"[opus-judge] skip {sc_file}: {type(exc).__name__}: {exc}")
            continue
        for card in cards:
            pid, model, arm = str(card["prompt_id"]), str(card["model"]), str(card["arm"])
            with checkpoint_path.open("a", encoding="utf-8") as f:
                for dim_id, score in (card.get("scores") or {}).items():
                    if score is None:  # NOT_APPLICABLE -> excluded
                        continue
                    ck = cell_key(pid, model, arm, str(dim_id))
                    if ck in done:
                        continue
                    val = max(0.0, min(10.0, float(score)))
                    f.write(json.dumps({"cell": ck, "prompt_id": pid, "model": model,
                                        "arm": arm, "dim": str(dim_id), "score": val}) + "\n")
                    done[ck] = val
                    added += 1
    print(f"[opus-judge] ingested {added} new dimension cells")
    return aggregate(checkpoint_path)


def aggregate_by_group(checkpoint_path: pathlib.Path) -> dict:
    """Per dimension-GROUP lift (group inferred from the 'group.key' dim id)."""
    done = load_checkpoint(checkpoint_path)
    by: dict[tuple[str, str, str], list[float]] = {}  # (model, arm, group) -> scores
    for ck, score in done.items():
        _pid, model, arm, dim = ck.split("|", 3)
        group = dim.split(".", 1)[0]
        by.setdefault((model, arm, group), []).append(score)
    models = sorted({m for (m, _a, _g) in by})
    out = {}
    for m in models:
        groups = sorted({g for (mm, _a, g) in by if mm == m})
        rows = []
        for g in groups:
            base = by.get((m, "baseline", g), [])
            harn = by.get((m, "harnessed", g), [])
            bm = sum(base) / len(base) if base else 0.0
            hm = sum(harn) / len(harn) if harn else 0.0
            rows.append({"group": g, "baseline_mean": round(bm, 3),
                         "harnessed_mean": round(hm, 3), "lift": round(hm - bm, 3),
                         "n_base": len(base), "n_harn": len(harn)})
        out[m] = sorted(rows, key=lambda r: r["lift"], reverse=True)
    return out


def main() -> None:
    import os
    mode = sys.argv[1] if len(sys.argv) > 1 else "ingest"
    prompts_file = os.environ.get("LIFT_PROMPTS_FILE", "harness_lift_prompts_500.json")
    responses_path = _ROOT / os.environ.get("LIFT_RESPONSES", "reports/harness_lift_500.responses.jsonl")
    checkpoint_path = _ROOT / os.environ.get("LIFT_OPUS_CKPT", "reports/harness_lift_500_opus.jsonl")
    batch_size = int(os.environ.get("LIFT_BATCH_SIZE", "8"))

    if mode == "batches":
        make_batches(responses_path, checkpoint_path, prompts_file, batch_size=batch_size)
    elif mode == "ingest":
        agg = ingest(checkpoint_path)
        print("\n=== OPUS 4.8 judge -- harness lift (overall) ===")
        print(json.dumps(agg, indent=2))
        print("\n=== OPUS 4.8 judge -- lift by dimension group ===")
        print(json.dumps(aggregate_by_group(checkpoint_path), indent=2))
    else:
        print(f"unknown mode {mode!r}; use 'batches' or 'ingest'")


if __name__ == "__main__":
    main()
