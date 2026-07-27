#!/usr/bin/env python3
# ruff: noqa: E501
"""Build a bounded-memory, manifest-bound large multi-perspective candidate.

This is the scaling layer for ``build_multiperspective_training_bundle.py``.
It deliberately reuses that generator's case graphs, prompts, visible decision
scaffolds, and row provenance, while changing four things needed before a
200,000+ row release:

* JSONL is written in deterministic shards instead of retaining expanded rows;
* supervised targets use six deterministic response styles; and
* every base scenario is exposed through four declared curriculum focuses; and
* DPO rejects are blinded, length-balanced minimal pairs which change exactly
  one declared section and contain no failure labels or grading commentary.

The output is a candidate, never a publication approval.  A manifest is written
only after every blocking audit passes.  No provider-private chain of thought,
raw worker case, credential, or real contact is requested or exported.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, BinaryIO

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "scripts" / "build_multiperspective_training_bundle.py"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "multiperspective_training" / "large_candidate_v1"

DEFAULT_TRAIN_ROWS = 204_800
DEFAULT_VALIDATION_ROWS = 8_192
DEFAULT_TEST_ROWS = 8_192
DEFAULT_SHARD_ROWS = 8_192
SIMILARITY_SAMPLE_ROWS = 384
GENERATOR_VERSION = "duecare-large-multiperspective-streaming/2.0.0"
SCHEMA_VERSION = "duecare.large_multiperspective.candidate.v1"


def _load_base():
    spec = importlib.util.spec_from_file_location("duecare_multiperspective_base", BASE_PATH)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load base generator: {BASE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base()


RESPONSE_STYLES: tuple[dict[str, Any], ...] = (
    {"key": "concise_case_brief", "order": ("record", "evidence", "perspective", "time", "unknowns", "action")},
    {"key": "timeline_first", "order": ("time", "record", "evidence", "perspective", "unknowns", "action")},
    {"key": "evidence_ledger", "order": ("evidence", "record", "unknowns", "time", "perspective", "action")},
    {"key": "action_first", "order": ("action", "record", "evidence", "perspective", "time", "unknowns")},
    {"key": "persona_handoff", "order": ("perspective", "record", "evidence", "time", "action", "unknowns")},
    {"key": "question_led", "order": ("unknowns", "time", "record", "evidence", "perspective", "action")},
)
STYLE_BY_KEY = {row["key"]: row for row in RESPONSE_STYLES}

# These are task-level transformations, not synonym substitutions.  Each view
# keeps the same latent fact graph and inherited split, but asks the learner to
# foreground a different decision product.  Parentage remains explicit so the
# release never presents descendants as independent cases or judgments.
CURRICULUM_FOCUSES: tuple[dict[str, str], ...] = (
    {
        "key": "evidence_map",
        "section": "evidence",
        "prompt_instruction": "Foreground an evidence map: distinguish direct records, bounded accounts, contradictions, counterevidence, and missing corroboration.",
        "target_sentence": "For this evidence-map view, keep direct support, contradiction, source limits, and missing corroboration in separate entries rather than blending them into one confidence claim.",
    },
    {
        "key": "temporal_reconstruction",
        "section": "time",
        "prompt_instruction": "Foreground temporal reconstruction: separate what was knowable at the focal date, what later evidence changed, and which rule dates require retrieval.",
        "target_sentence": "For this temporal-reconstruction view, preserve separate columns for knowable-at-the-time facts, later evidence, and rule-effective dates so hindsight does not rewrite the earlier decision.",
    },
    {
        "key": "authority_handoff",
        "section": "perspective",
        "prompt_instruction": "Foreground an authority handoff: state what each persona and jurisdiction may know, decide, request, and transfer without collapsing their roles.",
        "target_sentence": "For this authority-handoff view, name the record each actor may verify, the decision that remains outside that actor's authority, and the minimum provenance needed for a bounded handoff.",
    },
    {
        "key": "consent_first_action",
        "section": "action",
        "prompt_instruction": "Foreground a consent-first action plan: offer reversible choices, minimize exposure, and keep any referral within the worker's stated goal and authorization.",
        "target_sentence": "For this consent-first action view, make the first step reversible, identify its exposure cost, and require the worker's chosen goal and authorization before information leaves the bounded support path.",
    },
)
FOCUS_BY_KEY = {row["key"]: row for row in CURRICULUM_FOCUSES}

SECTION_PREFIXES = {
    "record": "Record-grounded starting point",
    "evidence": "Evidence and contradiction:",
    "perspective": "Perspective and authority:",
    "time": "Time and place:",
    "unknowns": "Unknowns and retrieval boundary:",
    "action": "Reversible next step:",
}
FAILURE_SECTION = {
    "single_jurisdiction_shortcut": "time",
    "static_time_collapse": "time",
    "unsupported_certainty": "evidence",
    "role_overreach": "perspective",
    "evidence_conflation": "evidence",
    "action_without_consent": "action",
}

# These phrases turn a preference target into an obvious grading artifact or
# were the deterministic markers in the earlier non-blinded rejects.
BANNED_DPO_TARGET_CUES = (
    "weaker response",
    "chosen answer",
    "rejected answer",
    "controlled failure",
    "intentionally flawed",
    "country b workplace matter only",
    "one present-tense condition",
    "enough to treat the described issue as established",
    "without a separate authorization step",
    "equivalent proof",
    "formal escalation using all visible records",
    *tuple(mode["key"].replace("_", " ") for mode in base.FAILURE_MODES),
)

_SPACE = re.compile(r"\s+")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
_SYNTH_ID = re.compile(r"\b(?:CG|REC|RULE|MPG)-[A-Z0-9-]+\b", re.I)
_TOKEN = re.compile(r"[a-z][a-z0-9_-]{2,}")
_TARGET_STOP = frozenset(
    {
        "and", "the", "that", "this", "with", "from", "into", "only", "each", "current",
        "record", "records", "synthetic", "visible", "dossier", "worker", "country", "date",
        "perspective", "authority", "evidence", "retrieval", "boundary", "question", "questions",
    }
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _domain_index(domain: str, descriptor: Mapping[str, str], size: int) -> int:
    value = f"{domain}|{descriptor['variant_key']}".encode()
    return int(hashlib.sha256(value).hexdigest()[:16], 16) % size


def response_style(descriptor: Mapping[str, str]) -> str:
    return str(RESPONSE_STYLES[_domain_index("response-style-v1", descriptor, len(RESPONSE_STYLES))]["key"])


def controlled_failure(descriptor: Mapping[str, str]) -> Mapping[str, str]:
    return base.FAILURE_MODES[_domain_index("controlled-failure-v1", descriptor, len(base.FAILURE_MODES))]


def _focus(descriptor: Mapping[str, str]) -> Mapping[str, str]:
    key = str(descriptor.get("curriculum_focus") or CURRICULUM_FOCUSES[0]["key"])
    try:
        return FOCUS_BY_KEY[key]
    except KeyError as exc:
        raise ValueError(f"unknown curriculum focus: {key}") from exc


def _expanded_descriptors() -> list[dict[str, str]]:
    """Expand each base descriptor into explicit, lineage-bound task views."""

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for parent in base.enumerate_descriptors():
        for focus in CURRICULUM_FOCUSES:
            variant_key = f"{parent['variant_key']}|focus:{focus['key']}"
            if variant_key in seen:
                raise ValueError(f"duplicate expanded matrix variant: {variant_key}")
            seen.add(variant_key)
            row = dict(parent)
            row.update(
                {
                    "parent_variant_key": str(parent["variant_key"]),
                    "parent_variant_sha256": str(parent["variant_sha256"]),
                    "curriculum_focus": str(focus["key"]),
                    "transformation_id": f"curriculum-focus:{focus['key']}:v1",
                    "transformation_type": "task_level_focus_recomposition",
                    "augmentation_depth": "1",
                    "variant_key": variant_key,
                    "variant_sha256": base.canonical_sha256(variant_key),
                }
            )
            rows.append(row)
    expected = base.matrix_size() * len(CURRICULUM_FOCUSES)
    if len(rows) != expected:
        raise ValueError(f"expanded matrix size drift: {len(rows)} != {expected}")
    return rows


def _render_prompt(descriptor: Mapping[str, str]) -> str:
    focus = _focus(descriptor)
    return (
        f"{base._prompt(descriptor)}\n\n"
        f"Training-view focus ({focus['key']}): {focus['prompt_instruction']} "
        "Return only a reviewable visible decision scaffold and final answer; do not claim hidden reasoning."
    )


def _answer_sections(answer: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for paragraph in (part.strip() for part in answer.split("\n\n") if part.strip()):
        matches = [key for key, prefix in SECTION_PREFIXES.items() if paragraph.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError("base answer no longer has the expected six visible sections")
        sections[matches[0]] = paragraph
    if set(sections) != set(SECTION_PREFIXES):
        raise ValueError(f"base answer section drift: {sorted(sections)}")
    return sections


def _render_chosen(descriptor: Mapping[str, str]) -> tuple[str, str, dict[str, str]]:
    sections = _answer_sections(base._chosen_answer(descriptor))
    focus = _focus(descriptor)
    focus_section = str(focus["section"])
    sections[focus_section] = f"{sections[focus_section]} {focus['target_sentence']}"
    style = response_style(descriptor)
    order = STYLE_BY_KEY[style]["order"]
    return "\n\n".join(sections[key] for key in order), style, sections


def _failure_paragraph(
    descriptor: Mapping[str, str], failure_key: str, original: str
) -> str:
    # A preference contrast should be minimal.  Preserve the section's visible
    # factual framing and replace only its final sentence with one consequential
    # defect.  Earlier versions rewrote the whole section; a 204,800-pair audit
    # caught that those pairs could fall below the declared similarity floor.
    # Keeping the preceding sentences also makes the rejected answer a realistic
    # near miss rather than an easy style shortcut.
    clauses: dict[str, tuple[str, ...]] = {
        "single_jurisdiction_shortcut": (
            "Use the Country B workplace process as the only operative jurisdictional frame, with origin, transit, and platform records retained only as background attachments.",
            "Treat the destination workplace route as the controlling review path and defer separate origin or transit questions unless that route requests them.",
        ),
        "static_time_collapse": (
            "Use the full later record to settle what should be treated as known at the focal date, combining the chronology into one current account.",
            "Read the earlier representation through the later evidence and use that combined picture as the knowledge state for every decision date.",
        ),
        "unsupported_certainty": (
            "Taken together, the available indicators establish the described condition; remaining checks need only refine its extent and remedy.",
            "The visible agreement supplies a settled factual conclusion, so additional records can be limited to documenting scope and remedy.",
        ),
        "role_overreach": (
            "The primary persona should set the cross-actor objective, choose the referral sequence, and decide when the collected record is sufficient to proceed.",
            "This persona may assign the other actors' information requests and determine which handoff proceeds without a separate authority review.",
        ),
        "evidence_conflation": (
            "Combine the account, actor-authored records, and any aggregate pattern into one factual basis without maintaining separate weights for source directness or independence.",
            "Treat convergence across the bounded account, partial documents, and pattern note as a unified evidentiary picture even where source type and directness differ.",
        ),
        "action_without_consent": (
            "Send the minimized record ledger through the safest available referral now, then confirm the worker's goal and authorization after preservation begins.",
            "Open the protective referral with the organized records before the private consent check so receiving actors can preserve evidence immediately.",
        ),
    }
    prefix = SECTION_PREFIXES[FAILURE_SECTION[failure_key]]
    if not original.startswith(prefix):
        raise ValueError("controlled-failure section prefix drift")
    sentences = re.split(r"(?<=[.!?])\s+", original)
    if len(sentences) < 2:
        raise ValueError("controlled-failure source section lacks a replaceable sentence")
    choices = clauses[failure_key]
    clause = choices[_domain_index(f"failure-wording-{failure_key}-v2", descriptor, len(choices))]
    replacement = " ".join([*sentences[:-1], clause])
    if replacement == original:
        raise ValueError("controlled failure did not alter its section")
    return replacement


def _target_cue_findings(text: str) -> list[str]:
    lowered = text.lower().replace("_", " ")
    return sorted({cue for cue in BANNED_DPO_TARGET_CUES if cue in lowered})


def _blinded_rejected(
    descriptor: Mapping[str, str], chosen: str, style: str
) -> tuple[str, str, dict[str, Any]]:
    chosen_sections = _answer_sections(chosen)
    failure = controlled_failure(descriptor)
    changed = FAILURE_SECTION[str(failure["key"])]
    rejected_sections = dict(chosen_sections)
    rejected_sections[changed] = _failure_paragraph(descriptor, str(failure["key"]), chosen_sections[changed])
    order = STYLE_BY_KEY[style]["order"]
    rejected = "\n\n".join(rejected_sections[key] for key in order)
    changed_sections = [key for key in SECTION_PREFIXES if chosen_sections[key] != rejected_sections[key]]
    ratio = len(chosen) / max(1, len(rejected))
    content_similarity = _jaccard(_target_tokens(chosen), _target_tokens(rejected))
    findings = _target_cue_findings(chosen) + _target_cue_findings(rejected)
    checks = {
        "same_response_style": tuple(order) == tuple(STYLE_BY_KEY[style]["order"]),
        "exactly_one_section_changed": changed_sections == [changed],
        "declared_failure_section_matches": changed == FAILURE_SECTION[str(failure["key"])],
        "pair_length_ratio_0_90_to_1_10": 0.90 <= ratio <= 1.10,
        "pair_content_similarity_0_65_to_1_00": 0.65 <= content_similarity < 1.0,
        "grading_and_failure_labels_absent_from_targets": not findings,
    }
    return rejected, str(failure["key"]), {
        "changed_section": changed,
        "changed_sections": changed_sections,
        "length_ratio": ratio,
        "content_similarity": content_similarity,
        "cue_findings": sorted(set(findings)),
        "checks": checks,
        "passed": all(checks.values()),
    }


def _case_graph_hash(descriptor: Mapping[str, str]) -> str:
    return base.canonical_sha256(base.build_fact_graph(descriptor["mechanism"], descriptor["jurisdiction"]))


def _style_sft_row(descriptor: Mapping[str, str]) -> dict[str, Any]:
    row = base._sft_row(descriptor)
    prompt = _render_prompt(descriptor)
    chosen, style, _ = _render_chosen(descriptor)
    row["messages"][-2]["content"] = prompt
    row["messages"][-1]["content"] = chosen
    row["response_style"] = style
    row["curriculum_focus"] = str(_focus(descriptor)["key"])
    row["parent_variant_key"] = str(descriptor.get("parent_variant_key") or descriptor["variant_key"])
    row["parent_variant_sha256"] = str(descriptor.get("parent_variant_sha256") or descriptor["variant_sha256"])
    row["transformation_id"] = str(descriptor.get("transformation_id") or "curriculum-focus:evidence_map:v1")
    row["transformation_type"] = str(descriptor.get("transformation_type") or "task_level_focus_recomposition")
    row["augmentation_depth"] = int(descriptor.get("augmentation_depth") or 1)
    row["variant_sha256"] = descriptor["variant_sha256"]
    row["case_graph_sha256"] = _case_graph_hash(descriptor)
    gate = base._quality_gate(descriptor, prompt=prompt, chosen=chosen)
    gate["judge"] = "duecare-large-visible-scaffold-contract-v1"
    gate["checks"]["response_style_declared"] = style in STYLE_BY_KEY
    gate["checks"]["curriculum_focus_declared"] = row["curriculum_focus"] in FOCUS_BY_KEY
    gate["checks"]["parent_lineage_declared"] = bool(row["parent_variant_sha256"] and row["transformation_id"])
    gate["accepted"] = all(gate["checks"].values())
    gate["unsafe_advice_filtered"] = gate["accepted"]
    row["quality_gate"] = gate
    row["sha256"] = base.training_row_sha256(row)
    return row


def _style_preference_row(
    descriptor: Mapping[str, str], sft_row: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    chosen = str(sft_row["messages"][-1]["content"])
    style = str(sft_row["response_style"])
    rejected, failure_key, pair_audit = _blinded_rejected(descriptor, chosen, style)
    row = base._preference_row(descriptor)
    row["prompt"] = _render_prompt(descriptor)
    row["chosen"] = chosen
    row["rejected"] = rejected
    row["response_style"] = style
    row["curriculum_focus"] = str(_focus(descriptor)["key"])
    row["parent_variant_key"] = str(descriptor.get("parent_variant_key") or descriptor["variant_key"])
    row["parent_variant_sha256"] = str(descriptor.get("parent_variant_sha256") or descriptor["variant_sha256"])
    row["transformation_id"] = str(descriptor.get("transformation_id") or "curriculum-focus:evidence_map:v1")
    row["transformation_type"] = str(descriptor.get("transformation_type") or "task_level_focus_recomposition")
    row["augmentation_depth"] = int(descriptor.get("augmentation_depth") or 1)
    row["variant_sha256"] = descriptor["variant_sha256"]
    row["case_graph_sha256"] = sft_row["case_graph_sha256"]
    row["controlled_failure"] = failure_key
    row["changed_section"] = pair_audit["changed_section"]
    row["pair_design"] = "blinded_length_balanced_single_section_minimal_pair"
    rationale = dict(row["preference_rationale"])
    rationale["rejected_failure_mode"] = failure_key
    rationale["preference_reason"] = next(mode["repair"] for mode in base.FAILURE_MODES if mode["key"] == failure_key)
    rationale["pair_design"] = row["pair_design"]
    rationale["changed_section"] = pair_audit["changed_section"]
    row["preference_rationale"] = rationale
    inherited = base._quality_gate(descriptor, prompt=str(row["prompt"]), chosen=chosen)
    checks = dict(inherited["checks"])
    checks.update(pair_audit["checks"])
    checks["curriculum_focus_declared"] = row["curriculum_focus"] in FOCUS_BY_KEY
    checks["parent_lineage_declared"] = bool(row["parent_variant_sha256"] and row["transformation_id"])
    gate = {
        "accepted": all(checks.values()),
        "unsafe_advice_filtered": all(checks.values()),
        "judge": "duecare-blinded-minimal-pair-contract-v1",
        "checks": checks,
        "failure_mode": failure_key,
        "changed_section": pair_audit["changed_section"],
    }
    row["quality_gate"] = gate
    row["sha256"] = base.training_row_sha256(row)
    return row, pair_audit


def _canonical_target(text: str) -> str:
    value = _SYNTH_ID.sub("<id>", text.lower())
    value = _DATE.sub("<date>", value)
    value = _NUMBER.sub("<number>", value)
    return _SPACE.sub(" ", value).strip()


def _target_tokens(text: str) -> set[str]:
    value = _canonical_target(text)
    return {token for token in _TOKEN.findall(value) if token not in _TARGET_STOP and len(token) > 3}


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1)]


class ShardWriter:
    """Write one deterministic JSONL lane with O(one-row) expansion memory."""

    def __init__(self, root: Path, lane: str, total_rows: int, shard_rows: int) -> None:
        self.root = root
        self.lane = lane
        self.total_rows = total_rows
        self.shard_rows = shard_rows
        self.total_shards = math.ceil(total_rows / shard_rows)
        self.lane_dir = root / "data" / lane
        self.lane_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts: list[dict[str, Any]] = []
        self._handle: BinaryIO | None = None
        self._digest: Any = None
        self._bytes = 0
        self._rows = 0
        self._global_rows = 0
        self._path: Path | None = None

    def _open(self) -> None:
        index = len(self.artifacts)
        self._path = self.lane_dir / f"part-{index:05d}-of-{self.total_shards:05d}.jsonl"
        self._handle = self._path.open("xb")
        self._digest = hashlib.sha256()
        self._bytes = 0
        self._rows = 0

    def _close(self) -> None:
        if self._handle is None or self._path is None:
            return
        self._handle.close()
        start = self._global_rows - self._rows
        self.artifacts.append(
            {
                "path": self._path.relative_to(self.root).as_posix(),
                "sha256": self._digest.hexdigest(),
                "bytes": self._bytes,
                "rows": self._rows,
                "row_start": start,
                "row_end": self._global_rows,
            }
        )
        self._handle = None
        self._path = None

    def write(self, row: Mapping[str, Any]) -> None:
        if self._handle is None:
            self._open()
        payload = _json_bytes(row)
        assert self._handle is not None
        self._handle.write(payload)
        self._digest.update(payload)
        self._bytes += len(payload)
        self._rows += 1
        self._global_rows += 1
        if self._rows == self.shard_rows:
            self._close()

    def close(self) -> list[dict[str, Any]]:
        self._close()
        if self._global_rows != self.total_rows:
            raise ValueError(f"{self.lane}: wrote {self._global_rows}, expected {self.total_rows}")
        if len(self.artifacts) != self.total_shards:
            raise ValueError(f"{self.lane}: shard count drift")
        return list(self.artifacts)


def _selected_descriptors(
    *, train_rows: int, validation_rows: int, test_rows: int
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    descriptors = _expanded_descriptors()
    train = base._balanced_sample(descriptors, split="train", limit=train_rows)
    validation = base._balanced_sample(descriptors, split="validation", limit=validation_rows)
    test = base._balanced_sample(descriptors, split="test", limit=test_rows)
    contract = base._assert_selection_contract(train, validation, test)
    return train, validation, test, contract


def build_plan(
    *, train_rows: int, validation_rows: int, test_rows: int, shard_rows: int
) -> dict[str, Any]:
    if min(train_rows, validation_rows, test_rows, shard_rows) <= 0:
        raise ValueError("row and shard counts must be positive")
    capacities = {
        split: sum(1 for row in _expanded_descriptors() if row["split"] == split)
        for split in ("train", "validation", "test")
    }
    requested = {"sft_train": train_rows, "preference_train": train_rows, "sft_validation": validation_rows, "sft_test": test_rows}
    if train_rows > capacities["train"] or validation_rows > capacities["validation"] or test_rows > capacities["test"]:
        raise ValueError(f"requested rows exceed matrix capacity: requested={requested} capacity={capacities}")
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "plan_only_no_files_written",
        "generator_version": GENERATOR_VERSION,
        "matrix_rows": len(_expanded_descriptors()),
        "base_matrix_rows": base.matrix_size(),
        "curriculum_focus_multiplier": len(CURRICULUM_FOCUSES),
        "capacities": capacities,
        "requested_rows": requested,
        "shard_rows": shard_rows,
        "shards": {lane: math.ceil(count / shard_rows) for lane, count in requested.items()},
        "response_styles": [row["key"] for row in RESPONSE_STYLES],
        "curriculum_focuses": [row["key"] for row in CURRICULUM_FOCUSES],
        "training_target_slots": train_rows * 3,
        "unique_training_target_bodies_expected": train_rows * 2,
        "unique_heldout_target_bodies_expected": validation_rows + test_rows,
        "publication_status": "candidate_only_not_approved",
        "bounded_memory": "expanded JSONL rows are generated, audited, and written one at a time",
    }


def _sample_keys(descriptors: Sequence[Mapping[str, str]], limit: int) -> set[str]:
    ranked = sorted(
        descriptors,
        key=lambda row: hashlib.sha256(f"similarity-sample-v1|{row['variant_key']}".encode()).hexdigest(),
    )
    return {str(row["variant_key"]) for row in ranked[:limit]}


def _similarity_report(
    train: Sequence[tuple[str, set[str]]], heldout: Sequence[tuple[str, set[str]]]
) -> dict[str, Any]:
    within: list[float] = []
    for index, (_, left) in enumerate(train):
        within.extend(_jaccard(left, right) for _, right in train[index + 1 :])
    cross = [_jaccard(left, right) for _, left in train for _, right in heldout]

    def summary(values: Sequence[float]) -> dict[str, Any]:
        return {
            "comparisons": len(values),
            "mean": round(statistics.fmean(values), 6) if values else 0.0,
            "p95": round(_percentile(values, 0.95), 6),
            "max": round(max(values), 6) if values else 0.0,
        }

    return {
        "metric": "canonical target content-token Jaccard",
        "sample_selection": "lowest domain-separated SHA-256 ranks",
        "train_sample_rows": len(train),
        "heldout_sample_rows": len(heldout),
        "within_train": summary(within),
        "train_to_heldout": summary(cross),
    }


def _write_case_graphs(output_dir: Path) -> tuple[Path, list[dict[str, Any]]]:
    path = output_dir / "case-graphs.jsonl"
    rows: list[dict[str, Any]] = []
    with path.open("xb") as handle:
        for mechanism in base.MECHANISMS:
            for jurisdiction in base.JURISDICTION_PATTERNS:
                graph = base.build_fact_graph(mechanism["key"], jurisdiction["key"])
                row = {
                    "case_graph_id": graph["graph_id"],
                    "lineage_family_id": base._family_id(mechanism["key"]),
                    "split": base._split_for_mechanism(mechanism["key"]),
                    "sha256": base.canonical_sha256(graph),
                    "graph": graph,
                }
                handle.write(_json_bytes(row))
                rows.append(row)
    return path, rows


def _validate_batch(
    sft_rows: list[Mapping[str, Any]], preference_rows: list[Mapping[str, Any]]
) -> None:
    result = base.validate_training_rows(
        sft_rows,
        preference_rows,
        evaluation_prompt_hashes=("0" * 64,),
        evaluation_lineage_ids=("sentinel-heldout-lineage",),
        require_preference=True,
    )
    if result["blocking_failures"]:
        raise ValueError(f"canonical training contract failed: {result['blocking_failures']} {result['issue_samples'][:3]}")


def build_candidate(
    output_dir: Path,
    *,
    train_rows: int = DEFAULT_TRAIN_ROWS,
    validation_rows: int = DEFAULT_VALIDATION_ROWS,
    test_rows: int = DEFAULT_TEST_ROWS,
    shard_rows: int = DEFAULT_SHARD_ROWS,
    _minimum_train_rows: int = DEFAULT_TRAIN_ROWS,
) -> dict[str, Any]:
    build_plan(
        train_rows=train_rows,
        validation_rows=validation_rows,
        test_rows=test_rows,
        shard_rows=shard_rows,
    )
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"candidate output must not already exist: {output_dir}")
    output_dir.mkdir(parents=True)
    try:
        train, validation, test, selection_contract = _selected_descriptors(
            train_rows=train_rows, validation_rows=validation_rows, test_rows=test_rows
        )
        graph_path, graph_rows = _write_case_graphs(output_dir)
        writers = {
            "sft_train": ShardWriter(output_dir, "sft_train", train_rows, shard_rows),
            "preference_train": ShardWriter(output_dir, "preference_train", train_rows, shard_rows),
            "sft_validation": ShardWriter(output_dir, "sft_validation", validation_rows, shard_rows),
            "sft_test": ShardWriter(output_dir, "sft_test", test_rows, shard_rows),
        }

        style_counts: dict[str, Counter[str]] = defaultdict(Counter)
        style_axis: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
        failure_counts: Counter[str] = Counter()
        failure_by_style: dict[str, Counter[str]] = defaultdict(Counter)
        ratio_values: list[float] = []
        pair_similarity: list[float] = []
        cue_failures = 0
        pair_structure_failures = 0
        all_quality_failures = 0
        pii_failures = 0
        exact_targets: dict[str, set[str]] = defaultdict(set)
        canonical_targets: dict[str, set[str]] = defaultdict(set)
        duplicate_targets: Counter[str] = Counter()
        prompt_hashes: dict[str, set[str]] = defaultdict(set)
        lineage_families: dict[str, set[str]] = defaultdict(set)
        case_graph_ids: dict[str, set[str]] = defaultdict(set)

        train_sample_keys = _sample_keys(train, min(SIMILARITY_SAMPLE_ROWS, len(train)))
        heldout_descriptors = [*validation, *test]
        heldout_sample_keys = _sample_keys(heldout_descriptors, min(SIMILARITY_SAMPLE_ROWS, len(heldout_descriptors)))
        train_similarity_sample: list[tuple[str, set[str]]] = []
        heldout_similarity_sample: list[tuple[str, set[str]]] = []

        def record_common(row: Mapping[str, Any], lane: str, target: str, descriptor: Mapping[str, str]) -> None:
            nonlocal all_quality_failures, pii_failures
            style = str(row["response_style"])
            style_counts[lane][style] += 1
            for axis in ("perspective", "journey_stage", "temporal_lens", "evidence_state", "view_mode", "jurisdiction_pattern", "prompt_family", "curriculum_focus"):
                style_axis[style][axis].add(str(row[axis]))
            exact = base.canonical_sha256(target)
            canonical = base.canonical_sha256(_canonical_target(target))
            duplicate_targets[f"{lane}:exact"] += int(exact in exact_targets[lane])
            duplicate_targets[f"{lane}:canonical"] += int(canonical in canonical_targets[lane])
            exact_targets[lane].add(exact)
            canonical_targets[lane].add(canonical)
            prompt = base._prompt_from_sft(row) if lane != "preference_train" else str(row["prompt"])
            ph = base.canonical_sha256(prompt)
            duplicate_targets[f"{lane}:prompt"] += int(ph in prompt_hashes[lane])
            prompt_hashes[lane].add(ph)
            lineage_families[lane].add(str(row["lineage_family_id"]))
            case_graph_ids[lane].add(str(row["case_graph_id"]))
            if (row.get("quality_gate") or {}).get("accepted") is not True:
                all_quality_failures += 1
            if base.pii_findings(row):
                pii_failures += 1
            if row.get("sha256") != base.training_row_sha256(row):
                raise ValueError(f"row integrity drift: {lane} {row.get('id')}")
            sample = train_similarity_sample if lane == "sft_train" else heldout_similarity_sample
            keys = train_sample_keys if lane == "sft_train" else heldout_sample_keys
            if descriptor["variant_key"] in keys and lane in {"sft_train", "sft_validation", "sft_test"}:
                sample.append((str(row["id"]), _target_tokens(target)))

        # Heldout is generated first so the frozen prompt and group sets exist
        # before any train row is accepted.
        for lane, descriptors in (("sft_validation", validation), ("sft_test", test)):
            for descriptor in descriptors:
                row = _style_sft_row(descriptor)
                target = str(row["messages"][-1]["content"])
                record_common(row, lane, target, descriptor)
                writers[lane].write(row)

        heldout_prompt_hashes = prompt_hashes["sft_validation"] | prompt_hashes["sft_test"]
        heldout_families = lineage_families["sft_validation"] | lineage_families["sft_test"]
        heldout_graphs = case_graph_ids["sft_validation"] | case_graph_ids["sft_test"]
        batch_sft: list[Mapping[str, Any]] = []
        batch_pref: list[Mapping[str, Any]] = []
        for descriptor in train:
            sft = _style_sft_row(descriptor)
            preference, pair_audit = _style_preference_row(descriptor, sft)
            sft_target = str(sft["messages"][-1]["content"])
            rejected = str(preference["rejected"])
            record_common(sft, "sft_train", sft_target, descriptor)
            record_common(preference, "preference_train", rejected, descriptor)
            writers["sft_train"].write(sft)
            writers["preference_train"].write(preference)
            failure = str(preference["controlled_failure"])
            style = str(preference["response_style"])
            failure_counts[failure] += 1
            failure_by_style[style][failure] += 1
            ratio_values.append(float(pair_audit["length_ratio"]))
            pair_similarity.append(_jaccard(_target_tokens(sft_target), _target_tokens(rejected)))
            cue_failures += int(bool(pair_audit["cue_findings"]))
            pair_structure_failures += int(pair_audit["passed"] is not True)
            batch_sft.append(sft)
            batch_pref.append(preference)
            if len(batch_sft) == 128:
                _validate_batch(batch_sft, batch_pref)
                batch_sft.clear()
                batch_pref.clear()
        if batch_sft:
            _validate_batch(batch_sft, batch_pref)

        shards = {lane: writer.close() for lane, writer in writers.items()}
        train_prompt_overlap = len(prompt_hashes["sft_train"] & heldout_prompt_hashes)
        family_overlap = len(lineage_families["sft_train"] & heldout_families)
        graph_overlap = len(case_graph_ids["sft_train"] & heldout_graphs)
        target_cross_exact = len(exact_targets["sft_train"] & (exact_targets["sft_validation"] | exact_targets["sft_test"]))
        target_cross_canonical = len(canonical_targets["sft_train"] & (canonical_targets["sft_validation"] | canonical_targets["sft_test"]))

        style_names = set(STYLE_BY_KEY)
        axis_expected = {
            "perspective": set(base.PERSONA_BY_KEY),
            "journey_stage": set(base.STAGE_BY_KEY),
            "temporal_lens": set(base.TEMPORAL_BY_KEY),
            "evidence_state": set(base.EVIDENCE_BY_KEY),
            "view_mode": set(base.VIEW_BY_KEY),
            "jurisdiction_pattern": set(base.JURISDICTION_BY_KEY),
            "curriculum_focus": set(FOCUS_BY_KEY),
        }
        style_axis_missing = {
            style: {axis: sorted(values - style_axis[style][axis]) for axis, values in axis_expected.items() if values - style_axis[style][axis]}
            for style in style_names
        }
        style_axis_missing = {style: missing for style, missing in style_axis_missing.items() if missing}
        max_failure_style_share = max(
            (count / max(1, sum(failure_by_style[style].values())) for style in style_names for count in failure_by_style[style].values()),
            default=1.0,
        )
        # A three-sigma finite-sample allowance keeps fast fixtures meaningful;
        # at the default 25,600 rows this resolves to the strict 0.25 ceiling.
        smallest_style_n = min((sum(failure_by_style[style].values()) for style in style_names), default=0)
        expected_failure_share = 1.0 / len(base.FAILURE_MODES)
        sampling_allowance = (
            3.0 * math.sqrt(expected_failure_share * (1.0 - expected_failure_share) / smallest_style_n)
            if smallest_style_n
            else 1.0
        )
        failure_style_threshold = max(0.25, expected_failure_share + sampling_allowance)
        similarity = _similarity_report(train_similarity_sample, heldout_similarity_sample)
        gates = [
            {"id": "requested_scale", "passed": train_rows >= _minimum_train_rows, "value": train_rows, "threshold": _minimum_train_rows, "production_threshold": 200_000},
            {"id": "selection_contract", "passed": selection_contract.get("ok") is True},
            {"id": "all_quality_gates", "passed": all_quality_failures == 0, "value": all_quality_failures},
            {"id": "pii_detector_clean", "passed": pii_failures == 0, "value": pii_failures},
            {"id": "train_heldout_prompt_group_isolation", "passed": train_prompt_overlap == family_overlap == graph_overlap == 0, "prompt_overlap": train_prompt_overlap, "family_overlap": family_overlap, "case_graph_overlap": graph_overlap},
            {"id": "train_heldout_target_isolation", "passed": target_cross_exact == target_cross_canonical == 0, "exact_overlap": target_cross_exact, "canonical_overlap": target_cross_canonical},
            {"id": "target_side_dedup", "passed": all(value == 0 for value in duplicate_targets.values()), "duplicates": dict(sorted(duplicate_targets.items()))},
            {"id": "response_styles_complete", "passed": set(style_counts["sft_train"]) == style_names, "counts": dict(sorted(style_counts["sft_train"].items()))},
            {"id": "style_stratified_axis_coverage", "passed": not style_axis_missing, "missing": style_axis_missing},
            {"id": "preference_failure_modes_complete", "passed": set(failure_counts) == {mode["key"] for mode in base.FAILURE_MODES}, "counts": dict(sorted(failure_counts.items()))},
            {"id": "dpo_exactly_one_changed_section", "passed": pair_structure_failures == 0, "value": pair_structure_failures},
            {"id": "dpo_target_cues_absent", "passed": cue_failures == 0, "value": cue_failures},
            {"id": "dpo_pairwise_length_ratio", "passed": bool(ratio_values) and min(ratio_values) >= 0.90 and max(ratio_values) <= 1.10, "min": round(min(ratio_values), 6), "mean": round(statistics.fmean(ratio_values), 6), "max": round(max(ratio_values), 6), "range": [0.90, 1.10]},
            {"id": "dpo_pairwise_content_similarity", "passed": bool(pair_similarity) and min(pair_similarity) >= 0.65 and max(pair_similarity) < 1.0, "min": round(min(pair_similarity), 6), "mean": round(statistics.fmean(pair_similarity), 6), "max": round(max(pair_similarity), 6), "range": [0.65, 1.0]},
            {"id": "failure_not_encoded_by_response_style", "passed": max_failure_style_share <= failure_style_threshold, "max_conditional_share": round(max_failure_style_share, 6), "threshold": round(failure_style_threshold, 6), "production_threshold": 0.25, "sample_rows_in_smallest_style": smallest_style_n, "table": {style: dict(sorted(counts.items())) for style, counts in sorted(failure_by_style.items())}},
            {"id": "sampled_target_near_duplicate", "passed": similarity["within_train"]["max"] < 0.99 and similarity["train_to_heldout"]["max"] < 0.99, "threshold_exclusive": 0.99, "metrics": similarity},
        ]
        failed = [str(gate["id"]) for gate in gates if gate["passed"] is not True]
        audit = {
            "schema_version": "duecare.large_multiperspective.quality_audit.v1",
            "generator_version": GENERATOR_VERSION,
            "clean": not failed,
            "risk_flags": failed,
            "publication_status": "candidate_only_pending_independent_curator_privacy_license_and_publication_approval",
            "counts": {
                "sft_train": train_rows,
                "preference_train": train_rows,
                "sft_validation": validation_rows,
                "sft_test": test_rows,
                "case_graphs": len(graph_rows),
                "serialized_target_slots": train_rows * 3 + validation_rows + test_rows,
                "expected_distinct_target_bodies": train_rows * 2 + validation_rows + test_rows,
            },
            "style_counts": {lane: dict(sorted(counts.items())) for lane, counts in sorted(style_counts.items())},
            "target_similarity": similarity,
            "gates": gates,
        }
        audit_path = output_dir / "quality-audit.json"
        _write_json(audit_path, audit)
        if failed:
            _write_json(output_dir / "BUILD_FAILED.json", {"schema_version": SCHEMA_VERSION, "blocking_gates": failed})
            raise ValueError(f"large candidate audit failed: {failed}")

        artifact_files = {
            "quality_audit": audit_path,
            "case_graphs": graph_path,
        }
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "id": "duecare-large-grounded-multiperspective-candidate-v1",
            "created_at": base.CREATED_AT,
            "generator_version": GENERATOR_VERSION,
            "base_generator_version": base.GENERATOR_VERSION,
            "generator_source_sha256": _sha256_file(Path(__file__)),
            "base_generator_source_sha256": _sha256_file(BASE_PATH),
            "publication_status": "candidate_only_not_approved",
            "safe_to_train": True,
            "safe_to_publish": False,
            "reasoning_data_policy": "Final answers and deliberately authored visible decision scaffolds only; no provider-private chain of thought or hidden runtime traces.",
            "model": {"id": base.MODEL_ID, "revision": base.MODEL_REVISION, "role": base.MODEL_ROLE},
            "counts": audit["counts"],
            "text_body_accounting": {
                "unique_sft_targets": len(exact_targets["sft_train"]),
                "preference_chosen_reuses_sft_targets": train_rows,
                "unique_preference_rejects": len(exact_targets["preference_train"]),
                "unique_heldout_targets": len(exact_targets["sft_validation"] | exact_targets["sft_test"]),
                "serialized_target_slots": train_rows * 3 + validation_rows + test_rows,
            },
            "dimensions": {
                "personas": [row["key"] for row in base.PERSONAS],
                "journey_stages": [row["key"] for row in base.JOURNEY_STAGES],
                "temporal_lenses": [row["key"] for row in base.TEMPORAL_LENSES],
                "evidence_states": [row["key"] for row in base.EVIDENCE_STATES],
                "view_modes": [row["key"] for row in base.VIEW_MODES],
                "jurisdiction_patterns": [row["key"] for row in base.JURISDICTION_PATTERNS],
                "mechanisms": [row["key"] for row in base.MECHANISMS],
                "response_styles": [row["key"] for row in RESPONSE_STYLES],
                "curriculum_focuses": [row["key"] for row in CURRICULUM_FOCUSES],
                "preference_failure_modes": [row["key"] for row in base.FAILURE_MODES],
            },
            "augmentation_accounting": {
                "base_descriptor_rows": base.matrix_size(),
                "expanded_descriptor_rows": len(_expanded_descriptors()),
                "task_view_multiplier": len(CURRICULUM_FOCUSES),
                "independence_warning": "Curriculum-focus descendants are not independent cases; parent_variant_sha256 and case_graph_id must be used for grouped sampling and evaluation.",
                "recommended_family_weight_cap": "Cap aggregate training weight by case_graph_id or parent_variant_sha256 rather than counting every descendant as independent evidence.",
            },
            "split_contract": {
                "unit": "whole mechanism family and case graph",
                "train_mechanisms": sorted(base.TRAIN_MECHANISM_KEYS),
                "validation_mechanisms": sorted(base.VALIDATION_MECHANISM_KEYS),
                "test_mechanisms": sorted(base.TEST_MECHANISM_KEYS),
                "selection_contract": selection_contract,
            },
            "quality_audit": {"path": audit_path.name, "sha256": _sha256_file(audit_path), "clean": True},
            "artifacts": {
                "metadata": {key: {"path": path.name, "sha256": _sha256_file(path), "bytes": path.stat().st_size} for key, path in artifact_files.items()},
                "shards": shards,
            },
            "publication_requirements": [
                "independent curator review",
                "privacy review",
                "license review",
                "manifest-bound explicit publication approval",
                "post-materialization checksum verification",
            ],
        }
        manifest_path = output_dir / "candidate-manifest.json"
        _write_json(manifest_path, manifest)
        summary = {
            "schema_version": SCHEMA_VERSION,
            "candidate_manifest": manifest_path.name,
            "candidate_manifest_sha256": _sha256_file(manifest_path),
            "quality_audit_clean": True,
            "safe_to_train": True,
            "safe_to_publish": False,
            "publication_status": "candidate_only_not_approved",
            "counts": audit["counts"],
            "shards": {lane: len(parts) for lane, parts in shards.items()},
        }
        _write_json(output_dir / "build-summary.json", summary)
        return summary
    except Exception as exc:
        failure_path = output_dir / "BUILD_FAILED.json"
        if not failure_path.exists():
            _write_json(failure_path, {"schema_version": SCHEMA_VERSION, "error_type": type(exc).__name__, "message": str(exc)[:1000]})
        raise


def verify_candidate_dir(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    manifest_path = root / "candidate-manifest.json"
    if not manifest_path.is_file() or (root / "BUILD_FAILED.json").exists():
        return {"ok": False, "failures": ["missing_manifest_or_failed_build"]}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if manifest.get("safe_to_publish") is not False or manifest.get("publication_status") != "candidate_only_not_approved":
        failures.append("candidate_publication_state")
    artifacts = manifest.get("artifacts") or {}
    for item in (artifacts.get("metadata") or {}).values():
        path = root / str(item.get("path") or "")
        if not path.is_file() or _sha256_file(path) != item.get("sha256") or path.stat().st_size != item.get("bytes"):
            failures.append(f"metadata_integrity:{item.get('path')}")
    for lane, parts in (artifacts.get("shards") or {}).items():
        expected_start = 0
        for item in parts:
            path = root / str(item.get("path") or "")
            if not path.is_file() or _sha256_file(path) != item.get("sha256") or path.stat().st_size != item.get("bytes"):
                failures.append(f"shard_integrity:{lane}:{item.get('path')}")
            if item.get("row_start") != expected_start or item.get("row_end") != expected_start + item.get("rows", -1):
                failures.append(f"shard_range:{lane}:{item.get('path')}")
            expected_start = int(item.get("row_end") or expected_start)
    return {"ok": not failures, "failures": failures, "candidate_manifest_sha256": _sha256_file(manifest_path)}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--train-rows", type=int, default=DEFAULT_TRAIN_ROWS)
    parser.add_argument("--validation-rows", type=int, default=DEFAULT_VALIDATION_ROWS)
    parser.add_argument("--test-rows", type=int, default=DEFAULT_TEST_ROWS)
    parser.add_argument("--shard-rows", type=int, default=DEFAULT_SHARD_ROWS)
    parser.add_argument("--plan", action="store_true", help="Print a deterministic capacity/shard plan and write nothing.")
    parser.add_argument("--verify", type=Path, help="Verify an existing candidate directory and write nothing.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.verify is not None:
        result = verify_candidate_dir(args.verify)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    if args.plan:
        result = build_plan(train_rows=args.train_rows, validation_rows=args.validation_rows, test_rows=args.test_rows, shard_rows=args.shard_rows)
    else:
        result = build_candidate(args.output_dir, train_rows=args.train_rows, validation_rows=args.validation_rows, test_rows=args.test_rows, shard_rows=args.shard_rows)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
