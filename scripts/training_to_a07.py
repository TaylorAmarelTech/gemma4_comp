"""Convert per-harness training JSONL streams into A-07 SFT-pair format.

Each harness emits one JSONL row per call to
``/kaggle/working/training/<harness>.jsonl`` (schema in
docs/harness_pattern.md). The bench-and-tune kernel (A-07) expects
``{prompt, response, grade}`` rows. This utility bridges the two.

Usage::

    python scripts/training_to_a07.py --harness chat
    python scripts/training_to_a07.py --harness extraction \
        --in /kaggle/working/training/extraction.jsonl \
        --out /tmp/extraction_sft.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


GRADE_GOOD = "good"
GRADE_ADEQUATE = "adequate"
GRADE_INCOMPLETE = "incomplete"


def _last_user_text(payload):
    if isinstance(payload, str):
        return payload
    if isinstance(payload, list):
        for msg in reversed(payload):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content") or []
                if isinstance(content, str):
                    return content
                for chunk in content:
                    if isinstance(chunk, dict) and chunk.get("type") == "text":
                        return chunk.get("text") or ""
    return ""


def convert_row(harness: str, row: dict):
    inp = row.get("input")
    out = row.get("output")
    if inp is None or out is None:
        return None

    if harness == "chat":
        prompt = _last_user_text(inp)
        response = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        grep = (row.get("applied_layers") or {}).get("grep", {})
        grade = GRADE_GOOD if grep.get("fired") else GRADE_ADEQUATE
        return {"prompt": prompt, "response": response, "grade": grade}

    if harness == "extraction":
        if isinstance(inp, dict):
            prompt = inp.get("raw_text") or inp.get("text") or ""
        else:
            prompt = str(inp)
        if isinstance(out, (dict, list)):
            response = json.dumps(out, ensure_ascii=False, indent=2)
        else:
            response = str(out)
        gem = False
        if isinstance(out, dict):
            env = out.get("envelope", out)
            if isinstance(env, dict):
                gem = bool((env.get("extensions") or {}).get("gemma_drafted"))
        grade = GRADE_GOOD if gem else GRADE_INCOMPLETE
        return {"prompt": prompt, "response": response, "grade": grade}

    if harness == "process":
        if isinstance(inp, dict):
            prompt = inp.get("question") or inp.get("filename") or json.dumps(inp, ensure_ascii=False)
        else:
            prompt = str(inp)
        response = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False)
        cited = (row.get("trace") or {}).get("cited_rows") or []
        grade = GRADE_GOOD if cited else GRADE_ADEQUATE
        return {"prompt": prompt, "response": response, "grade": grade}

    if harness == "anonymization":
        n = (inp or {}).get("n_texts", 1) if isinstance(inp, dict) else 1
        prompt = f"Anonymize {n} text segment(s) and return redaction diffs"
        response = json.dumps(out, ensure_ascii=False) if isinstance(out, (dict, list)) else str(out)
        return {"prompt": prompt, "response": response, "grade": GRADE_GOOD}

    if harness == "search":
        if isinstance(inp, dict):
            prompt = inp.get("query") or json.dumps(inp, ensure_ascii=False)
        else:
            prompt = str(inp)
        if isinstance(out, dict):
            titles = out.get("titles") or []
            response = json.dumps({"backend": out.get("backend"),
                                    "results": titles[:5]}, ensure_ascii=False)
            grade = GRADE_GOOD if titles else GRADE_INCOMPLETE
        else:
            response = str(out)
            grade = GRADE_ADEQUATE
        return {"prompt": prompt, "response": response, "grade": grade}

    return None


def convert_file(src: Path, harness: str, dst: Path):
    rows_in = 0
    rows_out = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(src, encoding="utf-8") as fin, open(dst, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            rows_in += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            pair = convert_row(harness, row)
            if pair is None:
                continue
            fout.write(json.dumps(pair, ensure_ascii=False) + "\n")
            rows_out += 1
    return rows_in, rows_out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", required=True,
                        choices=["chat", "process", "extraction",
                                  "anonymization", "search"])
    parser.add_argument("--in", dest="input_path", default=None,
                        help="Defaults to /kaggle/working/training/<harness>.jsonl")
    parser.add_argument("--out", dest="output_path", default=None,
                        help="Defaults to /kaggle/working/a07_input/<harness>_sft.jsonl")
    args = parser.parse_args()

    src = Path(args.input_path or f"/kaggle/working/training/{args.harness}.jsonl")
    if not src.exists():
        alt = Path(".") / ".duecare-training" / f"{args.harness}.jsonl"
        if alt.exists():
            src = alt
        else:
            print(f"ERROR: input file not found: {src}", file=sys.stderr)
            return 1

    dst = Path(args.output_path or f"/kaggle/working/a07_input/{args.harness}_sft.jsonl")
    rows_in, rows_out = convert_file(src, args.harness, dst)
    print(f"converted {rows_in} -> {rows_out} rows")
    print(f"output: {dst}")
    if rows_out == 0:
        print("WARNING: 0 rows written", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
