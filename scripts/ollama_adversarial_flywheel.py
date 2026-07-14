#!/usr/bin/env python3
"""Generate Ollama-backed adversarial training candidates.

This is a candidate producer, not a trainer and not a release gate. It asks one
Ollama model to mutate approved seed prompts, one model to draft protective
answers, and one model to judge the candidate. Clean candidates are written as
SFT and preference JSONL rows; rejected items are metadata-only quarantine
records. The manifest is deliberately ``safe_to_train=false`` because held-out
lineage, curator approval, source audit, and publication approval must still be
proven by the downstream bundle/release gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from duecare.chat.training_contract import (  # noqa: E402
    canonical_sha256,
    pii_findings,
    training_row_sha256,
    validate_training_rows,
)

DEFAULT_MODEL = os.environ.get("DUECARE_OLLAMA_MODEL") or os.environ.get("OLLAMA_MODEL") or "gemma4:latest"
DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST") or "http://localhost:11434"
HANDOFF_KIND = "duecare.ollama.adversarial_candidates.v1"
ROW_LICENSE = "CC-BY-SA-4.0"
RIGHTS_HOLDER = "DueCare project contributors"
_HIDDEN_REASONING = re.compile(
    r"<\|?(?:think|thought)(?:\|?>)|"
    r"<\|?channel\|?>\s*(?:analysis|thought)|"
    r"\b(?:hidden|private)\s+chain[- ]of[- ]thought\b|"
    r"\bprivate\s+scratchpad\b",
    re.I,
)

ChatFn = Callable[[str, str, str], str]


class FlywheelError(ValueError):
    """A local candidate-generation or validation failure."""


@dataclass(frozen=True)
class FlywheelConfig:
    ollama_host: str = DEFAULT_OLLAMA_HOST
    generator_model: str = DEFAULT_MODEL
    adversary_model: str = DEFAULT_MODEL
    judge_model: str = DEFAULT_MODEL
    limit: int = 25
    temperature: float = 0.2
    rights_holder: str = RIGHTS_HOLDER
    row_license: str = ROW_LICENSE


def _utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _strings(child)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _strings(child)


def _has_hidden_reasoning(value: Any) -> bool:
    return any(_HIDDEN_REASONING.search(text) for text in _strings(value))


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        if start < 0:
            raise FlywheelError("model response did not contain a JSON object") from None
        depth = 0
        end = -1
        for index, char in enumerate(cleaned[start:], start=start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end < 0:
            raise FlywheelError("model response JSON object was not closed") from None
        value = json.loads(cleaned[start:end])
    if not isinstance(value, dict):
        raise FlywheelError("model response JSON must be an object")
    return value


def _read_seed_rows(path: Path, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise FlywheelError(f"seed row {line_number} is not an object")
        prompt = str(value.get("prompt") or "").strip()
        if not prompt:
            raise FlywheelError(f"seed row {line_number} is missing prompt")
        rows.append(value)
        if len(rows) >= limit:
            break
    if not rows:
        raise FlywheelError("seed file contained no prompt rows")
    return rows


def ollama_chat(
    *,
    host: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    timeout: float = 240.0,
) -> str:
    url = host.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        body = json.loads(response.read().decode("utf-8"))
    message = body.get("message") if isinstance(body, dict) else None
    if not isinstance(message, Mapping) or not isinstance(message.get("content"), str):
        raise FlywheelError("Ollama response did not include message.content")
    return str(message["content"])


def _default_chat(config: FlywheelConfig) -> ChatFn:
    return lambda model, system, user: ollama_chat(
        host=config.ollama_host,
        model=model,
        system=system,
        user=user,
        temperature=config.temperature,
    )


def _adv_prompts(seed: Mapping[str, Any]) -> tuple[str, str]:
    system = (
        "You create synthetic anti-exploitation red-team prompts for a safety dataset. "
        "Return JSON only. Do not include real names, real contacts, credentials, or "
        "instructions that help exploit workers."
    )
    user = json.dumps(
        {
            "task": "adversarial rewrite",
            "seed_prompt": seed["prompt"],
            "required_json": {
                "prompt": "synthetic user prompt",
                "risk_tags": ["fee_camouflage"],
                "lineage_id": "stable synthetic lineage",
            },
        },
        ensure_ascii=False,
    )
    return system, user


def _answer_prompts(seed: Mapping[str, Any], adversarial: Mapping[str, Any]) -> tuple[str, str]:
    system = (
        "You draft protective DueCare training answers. Return JSON only. Give final "
        "answers and concise visible rationale only; never reveal hidden chain-of-thought."
    )
    user = json.dumps(
        {
            "task": "protective answer",
            "seed_prompt": seed["prompt"],
            "adversarial_prompt": adversarial["prompt"],
            "required_json": {
                "answer": "worker-protective answer",
                "visible_rationale": "short explicit scaffold",
                "contrast_answer": "safe but weaker rejected answer",
                "source_refs": ["synthetic:duecare-ollama-flywheel"],
            },
        },
        ensure_ascii=False,
    )
    return system, user


def _judge_prompts(prompt: str, answer: Mapping[str, Any]) -> tuple[str, str]:
    system = (
        "You are a strict safety-data judge. Return JSON only. Reject hidden reasoning, "
        "PII, unsafe operational advice, unsupported legal claims, or vague answers."
    )
    user = json.dumps(
        {
            "task": "judge training candidate",
            "prompt": prompt,
            "answer": answer,
            "required_json": {
                "accepted": True,
                "score_pct": 90,
                "unsafe_advice_filtered": True,
                "critical_dimension_failures": [],
                "reasons": [],
            },
        },
        ensure_ascii=False,
    )
    return system, user


def _quarantine(
    quarantine: list[dict[str, Any]],
    *,
    seed: Mapping[str, Any],
    reasons: list[str],
    stage: str,
) -> None:
    quarantine.append(
        {
            "seed_id": str(seed.get("id") or seed.get("prompt_id") or ""),
            "stage": stage,
            "reasons": sorted(set(reasons)),
            "contains_raw_text": False,
        }
    )


def _candidate_rows(
    *,
    seed: Mapping[str, Any],
    adversarial: Mapping[str, Any],
    answer: Mapping[str, Any],
    judge: Mapping[str, Any],
    config: FlywheelConfig,
    row_index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    row_id = f"ollama_adv_{canonical_sha256([seed.get('id'), adversarial['prompt']])[:16]}_{row_index:04d}"
    prompt = str(adversarial["prompt"]).strip()
    chosen = str(answer["answer"]).strip()
    rejected = str(answer.get("contrast_answer") or "This needs independent verification.").strip()
    source_refs = answer.get("source_refs") if isinstance(answer.get("source_refs"), list) else []
    source_refs = [str(item).strip() for item in source_refs if str(item).strip()]
    if not source_refs:
        source_refs = ["synthetic:duecare-ollama-flywheel"]
    lineage_id = str(adversarial.get("lineage_id") or seed.get("lineage_id") or row_id)
    created_at = _utc()
    quality_gate = {
        "accepted": bool(judge.get("accepted") is True),
        "unsafe_advice_filtered": bool(judge.get("unsafe_advice_filtered") is True),
        "judge": "ollama_adversarial_flywheel",
        "score_pct": float(judge.get("score_pct") or 0),
        "critical_dimension_failures": list(judge.get("critical_dimension_failures") or []),
        "reasons": list(judge.get("reasons") or []),
    }
    sft = {
        "id": row_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are DueCare, a bounded migrant-worker safety assistant. "
                    "Answer directly and do not reveal hidden reasoning."
                ),
            },
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": chosen},
        ],
        "source_profile": "ollama_adversarial_flywheel",
        "rubric_targets": ["safety_non_uplift", "privacy_boundary", "evidence_fidelity"],
        "synthetic": True,
        "pii_checked": True,
        "lineage_id": lineage_id,
        "split": "train",
        "license": config.row_license,
        "quality_gate": quality_gate,
        "source_refs": source_refs,
        "knowledge_pack_refs": ["duecare-core@ollama-flywheel"],
        "prompt_family": str(seed.get("prompt_family") or seed.get("category") or "ollama_adv"),
        "created_at": created_at,
        "model_revision": "ollama-local-candidate",
        "harness_version": "duecare-ollama-adversarial-v1",
        "rubric_version": "duecare.universal.v1",
        "structured_rationale": str(answer.get("visible_rationale") or ""),
        "rights_holder": config.rights_holder,
        "allow_training_use": True,
        "allow_public_redistribution": True,
        "metadata": {
            "generator_model": config.generator_model,
            "adversary_model": config.adversary_model,
            "judge_model": config.judge_model,
            "risk_tags": adversarial.get("risk_tags") or [],
            "seed_id": seed.get("id") or seed.get("prompt_id") or "",
        },
    }
    sft["sha256"] = training_row_sha256(sft)
    preference = {
        "id": row_id,
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "preference_rationale": str(answer.get("visible_rationale") or ""),
        "pii_checked": True,
        "lineage_id": lineage_id,
        "split": "train",
        "license": config.row_license,
        "quality_gate": quality_gate,
        "source_refs": source_refs,
        "knowledge_pack_refs": ["duecare-core@ollama-flywheel"],
        "created_at": created_at,
        "model_revision": "ollama-local-candidate",
        "harness_version": "duecare-ollama-adversarial-v1",
        "rubric_version": "duecare.universal.v1",
        "rights_holder": config.rights_holder,
        "allow_training_use": True,
        "allow_public_redistribution": True,
    }
    preference["sha256"] = training_row_sha256(preference)
    return sft, preference


def run_flywheel(
    seed_jsonl: Path,
    output_dir: Path,
    config: FlywheelConfig,
    *,
    chat: ChatFn | None = None,
) -> dict[str, Any]:
    rows = _read_seed_rows(seed_jsonl, max(1, int(config.limit)))
    chat_fn = chat or _default_chat(config)
    sft_rows: list[dict[str, Any]] = []
    preference_rows: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []

    for index, seed in enumerate(rows, start=1):
        try:
            system, user = _adv_prompts(seed)
            adversarial = _extract_json_object(chat_fn(config.adversary_model, system, user))
            if not isinstance(adversarial.get("prompt"), str) or not adversarial["prompt"].strip():
                raise FlywheelError("adversary response missing prompt")
            system, user = _answer_prompts(seed, adversarial)
            answer = _extract_json_object(chat_fn(config.generator_model, system, user))
            if not isinstance(answer.get("answer"), str) or not answer["answer"].strip():
                raise FlywheelError("generator response missing answer")
            system, user = _judge_prompts(str(adversarial["prompt"]), answer)
            judge = _extract_json_object(chat_fn(config.judge_model, system, user))
            candidate_payload = {"adversarial": adversarial, "answer": answer, "judge": judge}
            reasons: list[str] = []
            if _has_hidden_reasoning(candidate_payload):
                reasons.append("hidden_reasoning")
            findings = pii_findings(candidate_payload)
            reasons.extend(f"pii_{finding}" for finding in findings)
            if judge.get("accepted") is not True:
                reasons.append("judge_rejected")
            if judge.get("unsafe_advice_filtered") is not True:
                reasons.append("unsafe_advice")
            if reasons:
                _quarantine(quarantine, seed=seed, reasons=reasons, stage="local_gates")
                continue
            sft, preference = _candidate_rows(
                seed=seed,
                adversarial=adversarial,
                answer=answer,
                judge=judge,
                config=config,
                row_index=index,
            )
            sft_rows.append(sft)
            preference_rows.append(preference)
        except Exception as exc:  # noqa: BLE001
            _quarantine(quarantine, seed=seed, reasons=[type(exc).__name__], stage="exception")

    output_dir.mkdir(parents=True, exist_ok=True)
    sft_path = output_dir / "sft_candidates.jsonl"
    preference_path = output_dir / "preference_candidates.jsonl"
    quarantine_path = output_dir / "quarantine.json"
    _write_jsonl(sft_path, sft_rows)
    _write_jsonl(preference_path, preference_rows)
    _write_json(
        quarantine_path,
        {"schema_version": "1.0", "contains_raw_text": False, "rows": quarantine},
    )
    contract = validate_training_rows(sft_rows, preference_rows, require_preference=bool(preference_rows))
    manifest = {
        "schema_version": "1.0",
        "handoff_kind": HANDOFF_KIND,
        "created_at": _utc(),
        "safe_to_train": False,
        "safe_to_train_reason": (
            "Ollama candidates still require held-out split proof, curator approval, "
            "source audit, immutable train target revision, and publication approval."
        ),
        "reasoning_data_policy": "Final answers and deliberately authored visible rationales only.",
        "ollama": {
            "host": config.ollama_host,
            "generator_model": config.generator_model,
            "adversary_model": config.adversary_model,
            "judge_model": config.judge_model,
        },
        "counts": {
            "seeds": len(rows),
            "sft_candidates": len(sft_rows),
            "preference_candidates": len(preference_rows),
            "quarantine": len(quarantine),
        },
        "training_contract": contract,
        "artifacts": {
            "sft": sft_path.name,
            "preference": preference_path.name,
            "quarantine": quarantine_path.name,
        },
        "artifact_sha256": {
            "sft": _sha256_file(sft_path),
            "preference": _sha256_file(preference_path),
            "quarantine": _sha256_file(quarantine_path),
        },
    }
    manifest_path = output_dir / "manifest.json"
    _write_json(manifest_path, manifest)
    return {"manifest_path": str(manifest_path), **manifest}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ollama-host", default=DEFAULT_OLLAMA_HOST)
    parser.add_argument("--generator-model", default=DEFAULT_MODEL)
    parser.add_argument("--adversary-model", default=DEFAULT_MODEL)
    parser.add_argument("--judge-model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--rights-holder", default=RIGHTS_HOLDER)
    parser.add_argument("--row-license", default=ROW_LICENSE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = FlywheelConfig(
        ollama_host=args.ollama_host,
        generator_model=args.generator_model,
        adversary_model=args.adversary_model,
        judge_model=args.judge_model,
        limit=args.limit,
        temperature=args.temperature,
        rights_holder=args.rights_holder,
        row_license=args.row_license,
    )
    result = run_flywheel(args.seed_jsonl, args.output_dir, config)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
