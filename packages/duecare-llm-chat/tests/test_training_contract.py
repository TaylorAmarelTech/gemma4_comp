from __future__ import annotations


def _accepted_sft(*, prompt: str = "What should a worker do?", answer: str = "Use the cited pack and preserve evidence.") -> dict:
    from duecare.chat.training_contract import training_row_sha256

    row = {
        "id": "sft-1",
        "messages": [
            {"role": "system", "content": "Answer directly."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ],
        "source_profile": "chat_no_online",
        "rubric_targets": ["safety_non_uplift"],
        "synthetic": True,
        "pii_checked": True,
        "lineage_id": "lineage-1",
        "split": "train",
        "license": "project-generated-synthetic",
        "source_refs": ["pack:test@1"],
        "quality_gate": {"accepted": True, "unsafe_advice_filtered": True},
    }
    row["sha256"] = training_row_sha256(row)
    return row


def _accepted_dpo() -> dict:
    from duecare.chat.training_contract import training_row_sha256

    row = {
        "id": "dpo-1",
        "prompt": "How should this fee be assessed?",
        "chosen": "It may be illegal under the cited pack; preserve evidence.",
        "rejected": "Hide the fee in a different line item.",
        "preference_rationale": "The chosen answer avoids operational uplift and uses the vetted pack.",
        "pii_checked": True,
        "lineage_id": "lineage-2",
        "split": "train",
        "license": "project-generated-synthetic",
        "source_refs": ["pack:test@1"],
        "quality_gate": {"accepted": True, "unsafe_advice_filtered": True},
    }
    row["sha256"] = training_row_sha256(row)
    return row


def test_training_contract_accepts_hashed_sft_and_preference_rows() -> None:
    from duecare.chat.training_contract import canonical_sha256, validate_training_rows

    result = validate_training_rows(
        [_accepted_sft()],
        [_accepted_dpo()],
        evaluation_prompt_hashes=[canonical_sha256("Frozen evaluation prompt")],
        evaluation_lineage_ids=["heldout-lineage"],
        require_preference=True,
    )
    assert result["ok"] is True
    assert result["blocking_failures"] == []


def test_training_contract_rejects_pii_leakage_and_stale_hash() -> None:
    from duecare.chat.training_contract import canonical_sha256, validate_training_rows

    row = _accepted_sft()
    row["messages"][-1]["content"] = "Contact worker@example.org for legal help."
    result = validate_training_rows(
        [row],
        evaluation_prompt_hashes=[canonical_sha256("Frozen evaluation prompt")],
        evaluation_lineage_ids=["heldout-lineage"],
    )
    assert result["ok"] is False
    assert "pii_absent" in result["blocking_failures"]
    assert "row_integrity" in result["blocking_failures"]
    assert all("worker@example.org" not in str(item) for item in result["issue_samples"])


def test_training_contract_requires_real_heldout_evidence() -> None:
    from duecare.chat.training_contract import validate_training_rows

    result = validate_training_rows([_accepted_sft()])
    assert result["ok"] is False
    assert "heldout_not_train" in result["blocking_failures"]


def test_training_contract_rejects_exact_eval_leak_and_hidden_thought_markup() -> None:
    from duecare.chat.training_contract import canonical_sha256, training_row_sha256, validate_training_rows

    prompt = "Frozen evaluation prompt"
    row = _accepted_sft(prompt=prompt, answer="<think>private steps</think> Final answer.")
    row["sha256"] = training_row_sha256(row)
    result = validate_training_rows(
        [row],
        evaluation_prompt_hashes=[canonical_sha256(prompt)],
        evaluation_lineage_ids=["heldout-lineage"],
    )
    assert result["ok"] is False
    assert "heldout_not_train" in result["blocking_failures"]
    assert "hidden_reasoning_absent" in result["blocking_failures"]


def test_training_contract_rejects_hidden_thought_outside_the_chosen_answer() -> None:
    from duecare.chat.training_contract import canonical_sha256, training_row_sha256, validate_training_rows

    row = _accepted_dpo()
    row["preference_rationale"] = "<|channel|>analysis private scratchpad"
    row["sha256"] = training_row_sha256(row)
    result = validate_training_rows(
        [_accepted_sft()],
        [row],
        evaluation_prompt_hashes=[canonical_sha256("Frozen evaluation prompt")],
        evaluation_lineage_ids=["heldout-lineage"],
        require_preference=True,
    )

    assert result["ok"] is False
    assert "hidden_reasoning_absent" in result["blocking_failures"]


def test_training_contract_rejects_unreviewed_or_nontrain_rows() -> None:
    from duecare.chat.training_contract import canonical_sha256, training_row_sha256, validate_training_rows

    row = _accepted_sft()
    row["split"] = "validation"
    row["quality_gate"] = {"accepted": False, "unsafe_advice_filtered": False}
    row["sha256"] = training_row_sha256(row)
    result = validate_training_rows(
        [row],
        evaluation_prompt_hashes=[canonical_sha256("Frozen evaluation prompt")],
        evaluation_lineage_ids=["heldout-lineage"],
    )
    assert result["ok"] is False
    assert "json_schema_valid" in result["blocking_failures"]
    assert "unsafe_advice_filtered" in result["blocking_failures"]


def test_training_contract_rejects_heldout_lineage_overlap() -> None:
    from duecare.chat.training_contract import canonical_sha256, validate_training_rows

    row = _accepted_sft()
    result = validate_training_rows(
        [row],
        evaluation_prompt_hashes=[canonical_sha256("Different frozen evaluation prompt")],
        evaluation_lineage_ids=[row["lineage_id"]],
    )

    assert result["ok"] is False
    assert "heldout_not_train" in result["blocking_failures"]
    gate = next(item for item in result["gates"] if item["id"] == "heldout_not_train")
    assert "lineage_overlap=1" in gate["detail"]
