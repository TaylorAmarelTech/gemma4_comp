"""Pure validation helpers for DueCare SFT and preference-training rows.

The public experiment contract has always described blocking gates.  This
module makes those gates executable without importing a trainer, opening a
database, or making a network request.  It is intentionally small enough for
the active Kaggle A-00 script kernel to call before it creates a GPU job.

The validator accepts *visible* assistant answers and deliberately authored
``structured_rationale`` metadata.  It rejects hidden-thought markup so the
training surface cannot be represented as a private chain-of-thought
extractor.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SFT_REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "messages",
    "source_profile",
    "rubric_targets",
    "synthetic",
    "pii_checked",
    "lineage_id",
    "split",
    "license",
    "quality_gate",
    "sha256",
)

PREFERENCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "prompt",
    "chosen",
    "rejected",
    "preference_rationale",
    "pii_checked",
    "lineage_id",
    "split",
    "license",
    "quality_gate",
    "sha256",
)

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b", re.I)
_PHONE = re.compile(
    r"(?<!\w)(?:\+\d(?:[\s().-]*\d){7,14}|\d{10,14}|"
    r"(?:\(\d{2,4}\)|\d{2,4})[\s.-]\d{3,4}[\s.-]\d{3,4})(?!\w)"
)
_PASSPORT = re.compile(
    r"\b(?:passport|national\s+id|identity\s+card)\s*"
    r"(?:"
    r"(?:no\.?|number|#|:)\s*[A-Z0-9-]{4,20}"
    r"|"
    # Without an explicit label, require a mixed letter/digit token.  This
    # detects plausible identifiers such as AB1234567 without mistaking
    # ordinary domain language such as 'passport retention' for PII.
    r"(?=[A-Z0-9-]{6,20}\b)(?=[A-Z0-9-]*[A-Z])(?=[A-Z0-9-]*\d)"
    r"[A-Z0-9-]{6,20}"
    r")\b",
    re.I,
)
_HIDDEN_REASONING = re.compile(
    r"<\|?(?:think|thought)(?:\|?>)|"
    r"<\|?channel\|?>\s*(?:analysis|thought)|"
    r"\b(?:hidden|private)\s+chain[- ]of[- ]thought\b|"
    r"\bprivate\s+scratchpad\b",
    re.I,
)
_LEGAL_CLAIM = re.compile(
    r"\b(?:law|legal|illegal|statute|regulation|article\s+\d+|convention|fee\s+cap|"
    r"prohibit(?:s|ed)?|require(?:s|d)?|labou?r\s+department|ministry|dmw|poea|ilo)\b",
    re.I,
)
_UNSAFE_OPERATIONAL = re.compile(
    r"\b(?:hide\s+the\s+fee|evade\s+(?:the\s+)?law|avoid\s+detection|"
    r"optimi[sz]e\s+(?:wage|salary|fee|collection)|automatic\s+salary\s+deduction|"
    r"disguise\s+(?:the\s+)?(?:fee|loan)|structure\s+the\s+loan\s+to)\b",
    re.I,
)
_UNSAFE_NEGATION = re.compile(
    r"\b(?:cannot|can't|do\s+not|don't|does\s+not|doesn't|must\s+not|mustn't|"
    r"should\s+not|shouldn't|never|refuse|refuses|refusing|"
    r"will\s+not|won't|unsafe|illegal|unlawful|prohibited)\b",
    re.I,
)
# A negation only mitigates an operational phrase when it sits near that phrase.
# A refusal in one paragraph must not launder an operational instruction in
# another, so the mitigation window is bounded rather than whole-answer.
_UNSAFE_NEGATION_WINDOW = 160


def _operational_advice_is_unmitigated(answer: str) -> bool:
    """True when an operational-uplift phrase has no nearby negation/refusal.

    Each operational match is checked against a bounded character window on
    either side; a negation elsewhere in a long answer no longer clears an
    unrelated operational instruction.
    """

    text = answer or ""
    for match in _UNSAFE_OPERATIONAL.finditer(text):
        start = max(0, match.start() - _UNSAFE_NEGATION_WINDOW)
        end = min(len(text), match.end() + _UNSAFE_NEGATION_WINDOW)
        if not _UNSAFE_NEGATION.search(text[start:end]):
            return True
    return False


def canonical_sha256(value: Any) -> str:
    """Return a deterministic SHA-256 for JSON-compatible data or text."""

    if isinstance(value, str):
        payload = value.strip().encode("utf-8")
    else:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def training_row_sha256(row: Mapping[str, Any]) -> str:
    """Hash a row while excluding its self-referential ``sha256`` field."""

    return canonical_sha256({key: value for key, value in row.items() if key != "sha256"})


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


def pii_findings(value: Any) -> list[str]:
    """Return metadata-only PII detector labels; never echo matched text."""

    findings: set[str] = set()
    for text in _strings(value):
        if _EMAIL.search(text):
            findings.add("email")
        if _PHONE.search(text):
            findings.add("phone")
        if _PASSPORT.search(text):
            findings.add("identity_document")
    return sorted(findings)


def _sft_prompt_and_answer(row: Mapping[str, Any]) -> tuple[str, str, set[str]]:
    messages = row.get("messages")
    if not isinstance(messages, list):
        return "", "", set()
    prompt = ""
    answer = ""
    roles: set[str] = set()
    for message in messages:
        if not isinstance(message, Mapping):
            continue
        role = str(message.get("role") or "")
        content = message.get("content")
        roles.add(role)
        if not isinstance(content, str):
            continue
        if role == "user" and not prompt:
            prompt = content
        if role in {"assistant", "model"}:
            answer = content
    return prompt, answer, roles


def _source_refs(row: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("source_refs", "knowledge_pack_refs"):
        value = row.get(key)
        if isinstance(value, list):
            refs.extend(str(item).strip() for item in value if str(item).strip())
    return refs


def _quality_passes(row: Mapping[str, Any]) -> bool:
    gate = row.get("quality_gate")
    return bool(
        isinstance(gate, Mapping)
        and gate.get("accepted") is True
        and gate.get("unsafe_advice_filtered") is True
    )


def _row_integrity_ok(row: Mapping[str, Any]) -> bool:
    digest = row.get("sha256")
    return isinstance(digest, str) and len(digest) == 64 and digest == training_row_sha256(row)


def _gate(gate_id: str, blocking: bool, passed: bool, failures: int, detail: str) -> dict[str, Any]:
    return {
        "id": gate_id,
        "blocking": blocking,
        "passed": bool(passed),
        "failures": int(failures),
        "detail": detail,
    }


def validate_training_rows(
    sft_rows: Sequence[Mapping[str, Any]],
    preference_rows: Sequence[Mapping[str, Any]] = (),
    *,
    evaluation_prompt_hashes: Iterable[str] = (),
    evaluation_lineage_ids: Iterable[str] = (),
    require_preference: bool = False,
) -> dict[str, Any]:
    """Evaluate the executable training-data contract.

    ``evaluation_prompt_hashes`` must describe a frozen validation/test set.
    An empty set fails the held-out gate: absence of evidence is not evidence
    that benchmark prompts were kept out of training.
    """

    eval_hashes = {str(value) for value in evaluation_prompt_hashes if str(value)}
    eval_lineages = {str(value) for value in evaluation_lineage_ids if str(value)}
    schema_failures = 0
    pii_failures = 0
    citation_failures = 0
    unsafe_failures = 0
    integrity_failures = 0
    hidden_reasoning_failures = 0
    provenance_failures = 0
    prompt_hashes: list[str] = []
    prompt_hashes_by_kind: dict[str, list[str]] = {"sft": [], "preference": []}
    lineage_ids: list[str] = []
    issue_samples: list[dict[str, Any]] = []

    def record(kind: str, index: int, row: Mapping[str, Any], codes: list[str]) -> None:
        if codes and len(issue_samples) < 25:
            issue_samples.append(
                {
                    "kind": kind,
                    "index": index,
                    "id": str(row.get("id") or "")[:160],
                    "codes": sorted(set(codes)),
                }
            )

    for kind, rows, required in (
        ("sft", sft_rows, SFT_REQUIRED_FIELDS),
        ("preference", preference_rows, PREFERENCE_REQUIRED_FIELDS),
    ):
        for index, row in enumerate(rows):
            codes: list[str] = []
            missing = [field for field in required if field not in row]
            if missing:
                schema_failures += 1
                codes.append("schema_missing_fields")
            if kind == "sft":
                prompt, answer, roles = _sft_prompt_and_answer(row)
                if not prompt or not answer or not {"user", "assistant"}.issubset(roles):
                    schema_failures += 1
                    codes.append("schema_messages")
            else:
                prompt = row.get("prompt") if isinstance(row.get("prompt"), str) else ""
                answer = row.get("chosen") if isinstance(row.get("chosen"), str) else ""
                rejected = row.get("rejected") if isinstance(row.get("rejected"), str) else ""
                if (
                    not prompt.strip()
                    or not answer.strip()
                    or not rejected.strip()
                    or answer.strip() == rejected.strip()
                ):
                    schema_failures += 1
                    codes.append("schema_preference_pair")

            if prompt:
                prompt_hash = canonical_sha256(prompt)
                prompt_hashes.append(prompt_hash)
                prompt_hashes_by_kind[kind].append(prompt_hash)
            lineage = row.get("lineage_id")
            if isinstance(lineage, str) and lineage:
                lineage_ids.append(lineage)
            if row.get("split") != "train":
                schema_failures += 1
                codes.append("not_train_split")

            findings = pii_findings(row)
            if findings or row.get("pii_checked") is not True:
                pii_failures += 1
                codes.append("pii")
            # Check the complete row rather than only the chosen/assistant
            # answer.  Preference rejects and rationale metadata are exported
            # too, so hidden-thought markup in either location is equally
            # disqualifying.
            if any(_HIDDEN_REASONING.search(text) for text in _strings(row)):
                hidden_reasoning_failures += 1
                codes.append("hidden_reasoning_markup")
            if _LEGAL_CLAIM.search(answer or "") and not _source_refs(row):
                citation_failures += 1
                codes.append("citation_grounding")
            if _operational_advice_is_unmitigated(answer or ""):
                unsafe_failures += 1
                codes.append("unsafe_operational_advice")
            if not _quality_passes(row):
                unsafe_failures += 1
                codes.append("quality_gate")
            if not _row_integrity_ok(row):
                integrity_failures += 1
                codes.append("sha256")
            if (
                not str(row.get("license") or "").strip()
                or not str(row.get("lineage_id") or "").strip()
            ):
                provenance_failures += 1
                codes.append("provenance")
            record(kind, index, row, codes)

    overlap = sorted(set(prompt_hashes) & eval_hashes)
    lineage_overlap = sorted(set(lineage_ids) & eval_lineages)
    # An SFT row and its preference pair intentionally use the same user
    # scenario.  Count duplicates within each training lane; treating the
    # aligned cross-lane prompt as a duplicate incorrectly penalizes a valid
    # SFT+DPO corpus.
    duplicate_prompts = sum(
        count - 1
        for hashes in prompt_hashes_by_kind.values()
        for count in Counter(hashes).values()
        if count > 1
    )
    duplicate_lineages = sum(count - 1 for count in Counter(lineage_ids).values() if count > 1)
    heldout_failures = (
        len(overlap)
        + len(lineage_overlap)
        + (0 if eval_hashes else 1)
        + (0 if eval_lineages else 1)
    )
    if require_preference and not preference_rows:
        schema_failures += 1
        issue_samples.append(
            {"kind": "bundle", "index": -1, "id": "", "codes": ["preference_required"]}
        )

    gates = [
        _gate(
            "json_schema_valid",
            True,
            schema_failures == 0,
            schema_failures,
            "required fields and row shapes",
        ),
        _gate(
            "pii_absent",
            True,
            pii_failures == 0,
            pii_failures,
            "detector clean and pii_checked=true",
        ),
        _gate(
            "heldout_not_train",
            True,
            heldout_failures == 0,
            heldout_failures,
            (
                f"frozen_hashes={len(eval_hashes)} prompt_overlap={len(overlap)} "
                f"frozen_lineages={len(eval_lineages)} lineage_overlap={len(lineage_overlap)}"
            ),
        ),
        _gate(
            "citation_grounded",
            True,
            citation_failures == 0,
            citation_failures,
            "legal claims carry source references",
        ),
        _gate(
            "unsafe_advice_filtered",
            True,
            unsafe_failures == 0,
            unsafe_failures,
            "accepted quality gate and no operational uplift",
        ),
        _gate(
            "row_integrity",
            True,
            integrity_failures == 0,
            integrity_failures,
            "row SHA-256 matches canonical content",
        ),
        _gate(
            "provenance_licensed",
            True,
            provenance_failures == 0,
            provenance_failures,
            "license and lineage declared",
        ),
        _gate(
            "hidden_reasoning_absent",
            True,
            hidden_reasoning_failures == 0,
            hidden_reasoning_failures,
            "answer-only or deliberately authored structured rationale; no hidden-thought markup",
        ),
        _gate(
            "deduplicated",
            False,
            duplicate_prompts == 0,
            duplicate_prompts,
            "exact prompt duplicates within SFT or preference lanes; "
            "aligned cross-lane pairs are allowed",
        ),
        _gate(
            "lineage_unique",
            False,
            duplicate_lineages == 0,
            duplicate_lineages,
            "duplicate lineage rows",
        ),
    ]
    blocking_failures = [gate["id"] for gate in gates if gate["blocking"] and not gate["passed"]]
    return {
        "schema_version": "duecare.training.validation.v1",
        "ok": not blocking_failures,
        "blocking_failures": blocking_failures,
        "counts": {
            "sft": len(sft_rows),
            "preference": len(preference_rows),
            "training_prompt_hashes": len(set(prompt_hashes)),
            "evaluation_prompt_hashes": len(eval_hashes),
            "evaluation_lineages": len(eval_lineages),
        },
        "gates": gates,
        "issue_samples": issue_samples,
    }


__all__ = [
    "PREFERENCE_REQUIRED_FIELDS",
    "SFT_REQUIRED_FIELDS",
    "canonical_sha256",
    "pii_findings",
    "training_row_sha256",
    "validate_training_rows",
]
