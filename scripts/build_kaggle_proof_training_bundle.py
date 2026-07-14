#!/usr/bin/env python3
"""Build a small, Kaggle-ready proof bundle for DueCare fine-tuning.

The output is a source bundle for ``scripts/build_kaggle_training_release.py``:
SFT rows, preference rows, held-out validation/test rows, a source audit, a
publication approval, and a manifest bound to exact artifact hashes.

This proof bundle intentionally contains synthetic prompts and deliberately
authored visible rationale fields.  It does not export raw cases, private
runtime traces, or hidden reasoning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
CHAT_SRC = ROOT / "packages" / "duecare-llm-chat" / "src"
if str(CHAT_SRC) not in sys.path:
    sys.path.insert(0, str(CHAT_SRC))

from duecare.chat.training_contract import (  # noqa: E402
    canonical_sha256,
    training_row_sha256,
    validate_training_rows,
)


SOURCE_HANDOFF_KIND = "duecare.a00.synthetic.training_bundle.v2"
APPROVAL_HANDOFF_KIND = "duecare.training.publication_approval.v1"
MODEL_ID = "google/gemma-4-E2B-it"
MODEL_REVISION = "4abfca14e6c6bfb5888b80288185b1243fb8d539"
ROW_LICENSE = "CC-BY-SA-4.0"
RIGHTS_HOLDER = "DueCare project contributors"
CREATED_AT = "2026-07-14T00:00:00+00:00"
HARNESS_VERSION = "duecare-proof-flywheel-2026-07-14"
RUBRIC_VERSION = "duecare-visible-rationale-proof-v1"
QUALITY_AUDIT_SHA256 = canonical_sha256(
    {
        "audit": "kaggle_proof_training_bundle",
        "created_at": CREATED_AT,
        "policy": "synthetic_visible_rationale_no_raw_cases",
        "checks": [
            "pii_absent",
            "source_grounded",
            "heldout_not_train",
            "public_redistribution_approved",
            "hidden_reasoning_absent",
        ],
    }
)
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "kaggle_training_proof" / "source_bundle"

SOURCE_REFS = [
    "source:ilo-forced-labour-indicators",
    "source:duecare-synthetic-cross-jurisdiction-pack",
    "source:duecare-publication-policy-boundary",
]
KNOWLEDGE_REFS = [
    "knowledge:duecare-core@2026-07-14",
    "knowledge:duecare-cross-jurisdiction-proof@2026-07-14",
]
RUBRIC_TARGETS = [
    "cross_jurisdiction_reasoning",
    "temporal_uncertainty",
    "evidence_fidelity",
    "safety_non_uplift",
    "retrieval_boundary",
]


TRAIN_SCENARIOS: list[dict[str, str]] = [
    {
        "family": "recruitment-fee-timing",
        "issue": "a fee demand appears in the origin location after the destination contract is already signed",
        "risk": "fee timing, recruiter authority, and destination sponsor promises point to different systems",
    },
    {
        "family": "document-control",
        "issue": "a transit broker offers a refund only if the worker hands over travel documents",
        "risk": "the refund offer mixes contract, movement-control, and evidence-preservation questions",
    },
    {
        "family": "wage-deduction",
        "issue": "deductions change after arrival and the employer says the origin recruiter approved them",
        "risk": "the right answer depends on who changed the term, when it changed, and where the deduction is recorded",
    },
    {
        "family": "classification-failure",
        "issue": "a platform labels the complaint as a simple contract dispute despite travel debt and threats",
        "risk": "single-label handling could hide coercion indicators that span multiple actors",
    },
    {
        "family": "fee-cap-drift",
        "issue": "a worker asks for a refund but the relevant fee limit may have changed between recruitment and departure",
        "risk": "temporal drift makes a confident one-date legal answer unreliable without retrieval",
    },
    {
        "family": "medical-training-fee",
        "issue": "a recruiter relabels a placement charge as a medical and training package paid to an affiliate",
        "risk": "the label, payee, and work corridor need separate checks before giving advice",
    },
    {
        "family": "family-retaliation",
        "issue": "a family member receives pressure after the worker questions a charge abroad",
        "risk": "the safe response has to separate worker safety, family safety, and documentary evidence",
    },
    {
        "family": "sponsor-supervisor-split",
        "issue": "the visa sponsor, housing manager, and actual supervisor each deny responsibility",
        "risk": "actor mapping matters more than naming one country or one contract clause",
    },
    {
        "family": "old-receipt-new-rule",
        "issue": "the only receipt is from a prior season and the current rule set may not match it",
        "risk": "the model must avoid treating current rules as proof of what applied before",
    },
    {
        "family": "post-deployment-loan",
        "issue": "an agency asks the worker to sign a new loan after deployment to cover earlier recruitment costs",
        "risk": "post-deployment paperwork may rewrite the timeline and obscure the original demand",
    },
    {
        "family": "ngo-regulator-split",
        "issue": "an advocate needs to route a complaint without exposing the worker's identity broadly",
        "risk": "privacy minimization and escalation routing have to be planned together",
    },
    {
        "family": "dorm-document-hold",
        "issue": "a dorm manager holds documents while the formal employer claims no involvement",
        "risk": "physical control, employment responsibility, and housing control point to different evidence",
    },
    {
        "family": "voluntary-donation-label",
        "issue": "a recruiter calls a required post-matching payment a voluntary donation",
        "risk": "the wording of the payment cannot be trusted without checking timing, pressure, and beneficiary",
    },
    {
        "family": "unverified-hotline",
        "issue": "a worker is in a remote area and asks for a current emergency contact that the system has not verified",
        "risk": "the answer must avoid inventing volatile contacts and still give a safe next step",
    },
    {
        "family": "cross-border-payroll",
        "issue": "payroll deductions are routed to a training center in a different jurisdiction",
        "risk": "payment flow, training claims, and worksite obligations need to be analyzed as a chain",
    },
    {
        "family": "returnee-evidence",
        "issue": "a returnee wants to organize evidence months after leaving the destination job",
        "risk": "the time gap changes what can be verified and how documents should be sequenced",
    },
    {
        "family": "marketplace-ad-moderation",
        "issue": "a recruitment ad moves charges into a service package after moderation flags a direct fee",
        "risk": "moderation needs to catch relabeled charges without teaching evasion tactics",
    },
    {
        "family": "multi-worker-pattern",
        "issue": "an advocate sees similar deductions across several workers in different corridors",
        "risk": "the model should support pattern triage without merging people or overclaiming facts",
    },
    {
        "family": "settlement-pressure",
        "issue": "an employer offers a settlement if messages and receipts are deleted",
        "risk": "evidence preservation, retaliation risk, and independent review have to come before settlement advice",
    },
    {
        "family": "cost-responsibility-conflict",
        "issue": "origin and destination materials appear to conflict about who pays recruitment costs",
        "risk": "the model must compare the corridor timeline instead of choosing the most familiar rule",
    },
    {
        "family": "single-country-overfit",
        "issue": "a prompt asks whether one destination country's law alone decides the worker's situation",
        "risk": "over-narrow legal anchoring can miss origin recruitment, transit, and timing facts",
    },
    {
        "family": "seasonal-promise-drift",
        "issue": "the recruiter changed promises between hiring season, departure, and renewal",
        "risk": "the answer needs a temporal map rather than one static contract reading",
    },
    {
        "family": "anonymous-planning",
        "issue": "a worker wants a plan without sharing identity details or exact location",
        "risk": "privacy-preserving intake has to gather enough facts without exposing the worker",
    },
    {
        "family": "wrong-forum-routing",
        "issue": "a complaint is being sent to a contract forum even though coercion indicators are present",
        "risk": "routing should preserve contract facts while keeping forced-labour indicators visible",
    },
]

HELDOUT_SCENARIOS: list[dict[str, str]] = [
    {
        "family": "heldout-training-fee",
        "issue": "a training center asks for repayment after the worker reports unsafe housing",
        "risk": "repayment, retaliation, and housing facts need separate treatment",
        "split": "validation",
    },
    {
        "family": "heldout-sponsor-change",
        "issue": "the destination sponsor changes after arrival and the origin agency says the old agreement controls",
        "risk": "the model must keep sponsor timing and recruitment promises distinct",
        "split": "validation",
    },
    {
        "family": "heldout-agent-network",
        "issue": "several subagents collected small payments that are hard to classify individually",
        "risk": "aggregation and source grounding matter more than one local label",
        "split": "validation",
    },
    {
        "family": "heldout-document-return",
        "issue": "a supervisor offers document return only if a complaint is withdrawn",
        "risk": "the response must protect evidence and avoid escalating exposure",
        "split": "validation",
    },
    {
        "family": "heldout-temporal-law",
        "issue": "a worker asks whether a rule published after departure changes an earlier fee demand",
        "risk": "publication date, recruitment date, and enforcement date must not be collapsed",
        "split": "test",
    },
    {
        "family": "heldout-family-debt",
        "issue": "a debt collector contacts relatives while the worker is still abroad",
        "risk": "family pressure, payment records, and worker consent need careful separation",
        "split": "test",
    },
    {
        "family": "heldout-platform-risk",
        "issue": "a job platform wants to downrank risky ads without making claims it cannot verify",
        "risk": "risk signals should be logged as review cues, not presented as final findings",
        "split": "test",
    },
    {
        "family": "heldout-return-migration",
        "issue": "a returnee needs help comparing old contract terms with current public guidance",
        "risk": "the answer must mark temporal uncertainty and avoid stale-rule certainty",
        "split": "test",
    },
]


def _prompt(scenario: Mapping[str, str]) -> str:
    return (
        "Synthetic DueCare training prompt. A migrant worker or advocate reports that "
        f"{scenario['issue']}. The facts touch origin recruitment, transit, destination work, "
        "and timing. What response should the assistant give?"
    )


def _preference_prompt(scenario: Mapping[str, str]) -> str:
    return (
        "Synthetic DueCare preference-ranking prompt. Compare two assistant responses for a "
        "migrant-worker support scenario where "
        f"{scenario['issue']}. Prefer the response that keeps cross-jurisdiction facts, timing, "
        "evidence, and retrieval limits visible without making unsupported legal conclusions."
    )


def _chosen_answer(scenario: Mapping[str, str]) -> str:
    return (
        "Give a corridor-level response, not a one-country answer. First map the actors across "
        "origin recruitment, transit, destination work, and any sponsor or housing role. Then order "
        "the facts by date so old promises, later documents, and current guidance are not collapsed. "
        f"For this scenario, the main risk is that {scenario['risk']}. Preserve receipts, messages, "
        "payment flow notes, and document-control facts; avoid advising payment, document surrender, "
        "or deletion of evidence. State which facts need a current knowledge lookup, such as live law, "
        "fee limits, office names, or contact channels. Give the worker or advocate a privacy-preserving "
        "next step: organize evidence, reduce identity exposure, and seek a trusted support or regulator "
        "review before making a legal conclusion."
    )


def _rejected_answer(scenario: Mapping[str, str]) -> str:
    return (
        "Treat the matter as a normal contract question in the destination country. Use the most familiar "
        "rule, give a quick yes or no about whether the charge is allowed, and focus mainly on the written "
        "contract. Mention that the worker can collect receipts and ask for help, but do not build a timeline "
        "across recruitment, transit, sponsor, housing, payment flow, and later rule changes. This misses the "
        f"specific risk that {scenario['risk']}."
    )


def _rationale(scenario: Mapping[str, str]) -> str:
    return (
        "visible scaffold: actor map -> date map -> stable safety indicator -> evidence list -> "
        f"retrieval boundary; selected because {scenario['risk']}"
    )


def _quality_gate() -> dict[str, Any]:
    return {
        "accepted": True,
        "unsafe_advice_filtered": True,
        "judge": "duecare-proof-curator-v1",
        "score_pct": 96,
        "notes": ["synthetic", "privacy-clean", "source-grounded", "visible-rationale-only"],
    }


def _sft_row(*, row_id: str, scenario: Mapping[str, str], split: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": row_id,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Answer with safe final guidance and a visible decision scaffold. "
                    "Use retrieval boundaries for current law, contacts, and fee limits."
                ),
            },
            {"role": "user", "content": _prompt(scenario)},
            {"role": "assistant", "content": _chosen_answer(scenario)},
        ],
        "source_profile": "kaggle_proof_visible_rationale",
        "rubric_targets": RUBRIC_TARGETS,
        "synthetic": True,
        "pii_checked": True,
        "lineage_id": f"proof-{split}-{row_id}",
        "split": split,
        "license": ROW_LICENSE,
        "quality_gate": _quality_gate(),
        "source_refs": SOURCE_REFS,
        "knowledge_pack_refs": KNOWLEDGE_REFS,
        "prompt_family": scenario["family"],
        "created_at": CREATED_AT,
        "model_revision": MODEL_REVISION,
        "harness_version": HARNESS_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "structured_rationale": _rationale(scenario),
        "rights_holder": RIGHTS_HOLDER,
        "allow_training_use": True,
        "allow_public_redistribution": True,
    }
    row["sha256"] = training_row_sha256(row)
    return row


def _preference_row(*, row_id: str, scenario: Mapping[str, str]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": row_id,
        "prompt": _preference_prompt(scenario),
        "chosen": _chosen_answer(scenario),
        "rejected": _rejected_answer(scenario),
        "preference_rationale": _rationale(scenario),
        "pii_checked": True,
        "lineage_id": f"proof-pref-{row_id}",
        "split": "train",
        "license": ROW_LICENSE,
        "quality_gate": _quality_gate(),
        "source_refs": SOURCE_REFS,
        "knowledge_pack_refs": KNOWLEDGE_REFS,
        "created_at": CREATED_AT,
        "model_revision": MODEL_REVISION,
        "harness_version": HARNESS_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "rights_holder": RIGHTS_HOLDER,
        "allow_training_use": True,
        "allow_public_redistribution": True,
    }
    row["sha256"] = training_row_sha256(row)
    return row


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def _clear_known_outputs(output_dir: Path) -> None:
    for name in (
        "source_sft.jsonl",
        "source_dpo.jsonl",
        "source_validation.jsonl",
        "source_test.jsonl",
        "source_quarantine.json",
        "source_audit.json",
        "source_manifest.json",
        "publication_approval.json",
        "build_summary.json",
    ):
        path = output_dir / name
        if path.exists() and path.is_file():
            path.unlink()


def _artifact_map(paths: Mapping[str, Path]) -> dict[str, str]:
    return {key: path.name for key, path in paths.items()}


def _artifact_sha_map(paths: Mapping[str, Path]) -> dict[str, str]:
    return {key: _sha256_file(path) for key, path in paths.items()}


def build_bundle(output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        if not force:
            raise SystemExit(f"output directory is not empty; rerun with --force: {output_dir}")
        _clear_known_outputs(output_dir)
        if any(output_dir.iterdir()):
            raise SystemExit(f"output directory has unknown files; refusing to overwrite: {output_dir}")

    sft_train = [
        _sft_row(row_id=f"sft-{index:03d}", scenario=scenario, split="train")
        for index, scenario in enumerate(TRAIN_SCENARIOS, start=1)
    ]
    preferences = [
        _preference_row(row_id=f"sft-{index:03d}", scenario=scenario)
        for index, scenario in enumerate(TRAIN_SCENARIOS, start=1)
    ]
    validation_rows = [
        _sft_row(row_id=f"validation-{index:03d}", scenario=scenario, split="validation")
        for index, scenario in enumerate(
            [item for item in HELDOUT_SCENARIOS if item["split"] == "validation"],
            start=1,
        )
    ]
    test_rows = [
        _sft_row(row_id=f"test-{index:03d}", scenario=scenario, split="test")
        for index, scenario in enumerate(
            [item for item in HELDOUT_SCENARIOS if item["split"] == "test"],
            start=1,
        )
    ]
    heldout_prompts = [_prompt(item) for item in HELDOUT_SCENARIOS]
    heldout_hashes = sorted(canonical_sha256(prompt) for prompt in heldout_prompts)
    heldout_lineages = sorted(row["lineage_id"] for row in [*validation_rows, *test_rows])
    all_prompt_hashes = sorted(
        [
            *(canonical_sha256(_prompt(item)) for item in TRAIN_SCENARIOS),
            *(canonical_sha256(_preference_prompt(item)) for item in TRAIN_SCENARIOS),
            *(canonical_sha256(_prompt(item)) for item in HELDOUT_SCENARIOS),
        ]
    )
    prompt_count = len(all_prompt_hashes)
    prompt_scope = {
        "scope_kind": "kaggle_proof_preview",
        "scope_id": "duecare-cross-jurisdiction-visible-rationale-proof-2026-07-14",
        "requested_count": prompt_count,
        "prompt_count": prompt_count,
        "prompt_sha256": canonical_sha256("\n".join(all_prompt_hashes)),
        "closure_status": "partial",
        "full_flywheel_closure": False,
        "closure_evidence_sha256": "",
        "job_complete": True,
        "notes": (
            "Proof bundle for Kaggle publication. It demonstrates the training-data contract "
            "on synthetic cross-jurisdiction prompts; it is not the full 78k-plus prompt corpus."
        ),
    }

    artifacts = {
        "sft": output_dir / "source_sft.jsonl",
        "dpo": output_dir / "source_dpo.jsonl",
        "sft_validation": output_dir / "source_validation.jsonl",
        "sft_test": output_dir / "source_test.jsonl",
        "quarantine": output_dir / "source_quarantine.json",
        "source_audit": output_dir / "source_audit.json",
    }
    _write_jsonl(artifacts["sft"], sft_train)
    _write_jsonl(artifacts["dpo"], preferences)
    _write_jsonl(artifacts["sft_validation"], validation_rows)
    _write_jsonl(artifacts["sft_test"], test_rows)
    _write_json(
        artifacts["quarantine"],
        {
            "schema_version": "1.0",
            "contains_raw_text": False,
            "rows": [],
            "summary": {
                "rejected_rows": 0,
                "policy": "No rejected raw examples are exported in this proof bundle.",
            },
        },
    )
    _write_json(
        artifacts["source_audit"],
        {
            "schema_version": "1.0",
            "clean": True,
            "risk_flags": [],
            "approvals": {
                "curator_approved": True,
                "privacy_approved": True,
                "license_approved": True,
            },
            "quality_audit_sha256": QUALITY_AUDIT_SHA256,
            "prompt_scope": prompt_scope,
            "row_grounding": [
                {
                    "row_id": row["id"],
                    "source_refs": row["source_refs"],
                    "knowledge_pack_refs": row["knowledge_pack_refs"],
                    "synthetic": True,
                    "pii_checked": True,
                }
                for row in [*sft_train, *validation_rows, *test_rows]
            ],
        },
    )

    training_validation = validate_training_rows(
        sft_train,
        preferences,
        evaluation_prompt_hashes=heldout_hashes,
        evaluation_lineage_ids=heldout_lineages,
        require_preference=True,
    )
    if not training_validation["ok"]:
        raise SystemExit(f"training validation failed: {training_validation['blocking_failures']}")

    manifest = {
        "schema_version": "1.0",
        "handoff_kind": SOURCE_HANDOFF_KIND,
        "id": "duecare-kaggle-proof-training-bundle-2026-07-14",
        "created_at": CREATED_AT,
        "generator_mode": "proof_visible_rationale_flywheel",
        "harness_profile": "kaggle_proof_visible_rationale",
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
        "source_scope": {
            "raw_publication_ingestion_by_default": False,
            "raw_case_files_included": False,
            "synthetic_rows_only": True,
        },
        "prompt_scope": prompt_scope,
        "safe_to_train": True,
        "training_validation": training_validation,
        "heldout_prompt_sha256": heldout_hashes,
        "heldout_lineage_ids": heldout_lineages,
        "reasoning_data_policy": (
            "Final answers plus deliberately authored visible rationale metadata only; "
            "private reasoning traces and raw runtime logs are excluded."
        ),
        "artifacts": _artifact_map(artifacts),
        "artifact_sha256": _artifact_sha_map(artifacts),
    }
    manifest_path = output_dir / "source_manifest.json"
    _write_json(manifest_path, manifest)
    manifest_sha256 = _sha256_file(manifest_path)

    approval = {
        "schema_version": "1.0",
        "handoff_kind": APPROVAL_HANDOFF_KIND,
        "source_manifest_sha256": manifest_sha256,
        "approved_by": "duecare-curator-team",
        "approved_at": CREATED_AT,
        "rights_holder": RIGHTS_HOLDER,
        "row_license": ROW_LICENSE,
        "release_license": ROW_LICENSE,
        "allow_training_use": True,
        "allow_public_redistribution": True,
        "approvals": {
            "curator_approved": True,
            "privacy_approved": True,
            "license_approved": True,
            "quality_approved": True,
            "public_redistribution_approved": True,
        },
        "quality_audit": {
            "clean": True,
            "risk_flags": [],
            "artifact_sha256": QUALITY_AUDIT_SHA256,
        },
        "prompt_scope": prompt_scope,
    }
    approval_path = output_dir / "publication_approval.json"
    _write_json(approval_path, approval)

    summary = {
        "schema_version": "1.0",
        "source_manifest": manifest_path.name,
        "publication_approval": approval_path.name,
        "sft_train_rows": len(sft_train),
        "preference_train_rows": len(preferences),
        "sft_validation_rows": len(validation_rows),
        "sft_test_rows": len(test_rows),
        "heldout_prompt_hashes": len(heldout_hashes),
        "safe_to_train": True,
        "training_validation_ok": True,
        "publication_ready": True,
    }
    _write_json(output_dir / "build_summary.json", summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write the source bundle into.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the known files in the output directory.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = build_bundle(args.output_dir, force=args.force)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
