"""Contract checks for the bounded Kimi K3 paired harness smoke."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from duecare.chat.harness import default_harness
from duecare.chat.harness_lift import build_harness_preamble

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "configs"
    / "duecare"
    / "benchmarks"
    / "kimi_k3_harness_lift_smoke_20260728.json"
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_smoke_manifest_is_bound_to_real_prompt_and_full_harness() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prompt_path = ROOT / manifest["selection"]["prompt_set"]
    prompt_doc = json.loads(prompt_path.read_text(encoding="utf-8"))
    prompt = next(
        row
        for row in prompt_doc["prompts"]
        if row["id"] == manifest["selection"]["prompt_id"]
    )
    harness = default_harness()
    ground = build_harness_preamble(
        prompt["text"],
        grep_call=harness["grep_call"],
        rag_call=harness["rag_call"],
        tool_call=harness["tools_call"],
        rag_top_k=8,
        grep_top=15,
        max_chars=16000,
    )
    harnessed_input = ground["preamble"] + "\n\n---\n\n" + prompt["text"]

    assert hashlib.sha256(prompt_path.read_bytes()).hexdigest() == (
        manifest["selection"]["prompt_set_sha256"]
    )
    assert _sha(prompt["text"]) == manifest["selection"]["prompt_text_sha256"]
    assert _sha(ground["preamble"]) == manifest["full_harness_context"]["preamble_sha256"]
    assert _sha(harnessed_input) == manifest["full_harness_context"]["harnessed_input_sha256"]
    assert ground["grep_fired"] == manifest["full_harness_context"]["grep_fired"]
    assert ground["rag_doc_ids"] == manifest["full_harness_context"]["rag_doc_ids"]
    assert ground["tools_fired"] == manifest["full_harness_context"]["tools_fired"]


def test_smoke_manifest_cannot_be_misread_as_a_quality_result() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = manifest["result"]
    budget = manifest["budget_receipt"]

    assert manifest["status"] == "blocked_external_access"
    assert result["successful_completions"] == 0
    assert result["complete_pairs"] == 0
    assert result["harness_lift"] is None
    assert budget["reserved_attempts"] == 2
    assert budget["actual_input_tokens"] == 0
    assert budget["actual_output_tokens"] == 0
    assert budget["actual_cost_usd"] == 0.0
    assert manifest["privacy"]["contains_api_key"] is False
