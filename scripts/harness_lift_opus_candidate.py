"""Run Opus 4.8 (or any subagent model) as a CANDIDATE in the harness-lift
benchmark -- baseline vs DueCare-harnessed -- via the orchestrator's subagents.

Opus is not reachable from a script (no Anthropic key), so -- exactly like the
judge -- Opus answers through subagents. This is the plumbing:

    1. `prep`   -- pick prompts already generated for the open models (so the
                   comparison is on identical prompts), compute each arm's prompt
                   text (baseline = raw; harnessed = v2 grounding preamble +
                   prompt) and write batch files under reports/opus_cand_batches/.
    2. (Opus)   -- a workflow has Opus subagents ANSWER each item as a
                   trafficking-safety assistant and write reports/opus_cand_answers/.
    3. `ingest` -- fold the answers into a responses file
                   (reports/harness_lift_opus_cand.responses.jsonl, model="opus")
                   in the standard schema, so harness_lift_opus_judge.py can batch
                   + judge them into the SAME checkpoint as gemma4:31b / gpt-oss:20b
                   for a 3-way baseline/harnessed/lift comparison.

Caveats surfaced, not hidden: Opus-judging-Opus has a mild self-preference (an
independent judge such as Ollama gpt-oss:120b can cross-check); and the open
models' harnessed arm used the v1 preamble while Opus uses v2, so the baseline
comparison is clean and the harnessed comparison carries a preamble-version note.

Public synthetic prompts only (rule 81). No keys here.
"""
from __future__ import annotations

import glob
import json
import os
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[1]
for _src in glob.glob(str(_ROOT / "packages" / "*" / "src")):
    if _src not in sys.path:
        sys.path.insert(0, _src)

_BENCH = _ROOT / "configs" / "duecare" / "benchmarks"
_BATCH_DIR = _ROOT / "reports" / "opus_cand_batches"
_ANSWER_DIR = _ROOT / "reports" / "opus_cand_answers"
_RESPONSES = _ROOT / "reports" / "harness_lift_opus_cand.responses.jsonl"
CAND_MODEL = os.environ.get("LIFT_CAND_MODEL", "opus")


def _prompt_text(prompts_file: str) -> dict[str, str]:
    data = json.loads((_BENCH / prompts_file).read_text(encoding="utf-8"))
    return {str(p["id"]): p["text"] for p in data["prompts"]}


def prep(prompts_file: str, n: int, batch_size: int = 8) -> int:
    """Build baseline+harnessed candidate prompts for the first ``n`` prompts
    already present in the open-model responses file (for an apples-to-apples
    comparison). Returns batch-file count."""
    from duecare.chat.harness import default_harness
    from duecare.chat.harness_lift import build_harness_preamble

    h = default_harness()
    grep_call, rag_call = h["grep_call"], h.get("rag_call")
    text_by_id = _prompt_text(prompts_file)

    # Prompt IDs already generated for the open models (preserve order, unique).
    open_resp = _ROOT / os.environ.get("LIFT_OPEN_RESPONSES", "reports/harness_lift_500.responses.jsonl")
    ordered_ids: list[str] = []
    seen = set()
    if open_resp.exists():
        for line in open_resp.read_text(encoding="utf-8").splitlines():
            try:
                pid = str(json.loads(line)["prompt_id"])
            except Exception:
                continue
            if pid not in seen and pid in text_by_id:
                seen.add(pid)
                ordered_ids.append(pid)
    ordered_ids = ordered_ids[:n]

    items = []
    for pid in ordered_ids:
        text = text_by_id[pid]
        pre = build_harness_preamble(text, grep_call=grep_call, rag_call=rag_call)["preamble"]
        items.append({"prompt_id": pid, "arm": "baseline", "prompt": text})
        items.append({"prompt_id": pid, "arm": "harnessed", "prompt": pre + "\n\n---\n\n" + text})

    _BATCH_DIR.mkdir(parents=True, exist_ok=True)
    nb = 0
    for i in range(0, len(items), batch_size):
        (_BATCH_DIR / f"batch_{i // batch_size:04d}.json").write_text(
            json.dumps({"items": items[i:i + batch_size]}, indent=2), encoding="utf-8")
        nb += 1
    print(f"[opus-cand] {len(ordered_ids)} prompts x 2 arms = {len(items)} items "
          f"-> {nb} batch files (size {batch_size}) in {_BATCH_DIR}")
    return nb


def ingest() -> int:
    """Fold Opus answer shards into the responses file (model=CAND_MODEL).
    Returns the number of responses written."""
    _RESPONSES.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if _RESPONSES.exists():
        for line in _RESPONSES.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
                seen.add(f"{r['prompt_id']}|{r['arm']}")
            except Exception:
                continue
    n = 0
    with _RESPONSES.open("a", encoding="utf-8") as out:
        for sf in sorted(glob.glob(str(_ANSWER_DIR / "*.json"))):
            try:
                answers = json.loads(pathlib.Path(sf).read_text(encoding="utf-8"))["responses"]
            except Exception as exc:  # noqa: BLE001
                print(f"[opus-cand] skip {sf}: {type(exc).__name__}: {exc}")
                continue
            for a in answers:
                key = f"{a['prompt_id']}|{a['arm']}"
                if key in seen:
                    continue
                resp = str(a.get("response") or "")
                out.write(json.dumps({"prompt_id": str(a["prompt_id"]), "model": CAND_MODEL,
                                      "arm": str(a["arm"]), "chars": len(resp),
                                      "response": resp}) + "\n")
                seen.add(key)
                n += 1
    try:
        rel = _RESPONSES.relative_to(_ROOT)
    except ValueError:  # path outside the repo (e.g. a test tmp dir)
        rel = _RESPONSES
    print(f"[opus-cand] wrote {n} {CAND_MODEL} responses -> {_RESPONSES}")
    print(f"[opus-cand] now judge: LIFT_RESPONSES={rel} "
          f"python scripts/harness_lift_opus_judge.py batches|ingest")
    return n


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "prep"
    prompts_file = os.environ.get("LIFT_PROMPTS_FILE", "harness_lift_prompts_500.json")
    n = int(os.environ.get("LIFT_CAND_N", "16"))
    if mode == "prep":
        prep(prompts_file, n, batch_size=int(os.environ.get("LIFT_BATCH_SIZE", "8")))
    elif mode == "ingest":
        ingest()
    else:
        print(f"unknown mode {mode!r}; use 'prep' or 'ingest'")


if __name__ == "__main__":
    main()
