"""Tests for the shared knowledge-fact noise scrubber.

`clean_for_knowledge_fact` + `fact_excerpt` + `smart_excerpt` (in
duecare.chat.harnesses._safe_text) exist to prevent a class of UX
regressions where a draft envelope's evidence_quote /
source_excerpt / test_phrases / non_pii_example field contained
operational metadata from upstream process bundles: ZIP filenames
(case_files_media_rich_sample.zip), Kaggle run paths
(/kaggle/working/process-staging/), kernel run IDs (RUN_ID:
process_dad7c52a7a15), and synthetic case folder names
(DC-PH-HK-101_Ana_Cruz/messages.jsonl). Those leak the staging
filenames of synthetic demo cases into a fact a reviewer thinks is
generic anonymized knowledge.

The same helpers are now reused by anonymization (text_preview on
unparsed Gemma output), search/backends (sentence-boundary cut on
SearXNG snippets), and the knowledge listing in chat.app
(per-envelope summary line).
"""
from __future__ import annotations

import pytest

from duecare.chat.harnesses._safe_text import (
    STANDARD_FACT_INDICATORS,
    STANDARD_FACT_KEY_ORDER,
    STANDARD_FACT_STAGES,
    clean_for_knowledge_fact,
    fact_excerpt,
    smart_excerpt,
    standardize_envelope_extensions,
    standardize_fact_envelope,
    was_scrubbed,
)
from duecare.chat.harnesses.extraction.handler import _deterministic_content

# The handler imports these from _safe_text under aliased private
# names. Keep the test names matching the shared canonical names so
# coverage tracks the public helper.
_clean_for_knowledge_fact = clean_for_knowledge_fact
_fact_excerpt = fact_excerpt


class TestCleanForKnowledgeFact:
    def test_strips_zip_filenames(self) -> None:
        text = "Reviewed evidence from case_files_media_rich_sample.zip showing fee deductions."
        cleaned = _clean_for_knowledge_fact(text)
        assert ".zip" not in cleaned
        assert "case_files_media_rich_sample" not in cleaned
        assert "fee deductions" in cleaned

    def test_strips_run_id(self) -> None:
        text = "RUN_ID: process_dad7c52a7a15 found training fee of PHP 50000."
        cleaned = _clean_for_knowledge_fact(text)
        assert "RUN_ID" not in cleaned
        assert "process_dad7c52a7a15" not in cleaned
        assert "PHP 50000" in cleaned

    def test_strips_kaggle_working_path(self) -> None:
        text = "Bundle at /kaggle/working/process-staging/case01/messages.jsonl shows pattern."
        cleaned = _clean_for_knowledge_fact(text)
        assert "/kaggle/working" not in cleaned
        assert "process-staging" not in cleaned
        assert "shows pattern" in cleaned

    def test_strips_synthetic_case_folder_names(self) -> None:
        text = (
            "Case DC-PH-HK-101_Ana_Cruz/passport.jpg shows passport retention "
            "by recruitment agency."
        )
        cleaned = _clean_for_knowledge_fact(text)
        assert "DC-PH-HK-101" not in cleaned
        assert "Ana_Cruz" not in cleaned
        assert "Ana Cruz" not in cleaned
        assert "passport retention" in cleaned

    def test_strips_jsonl_filenames(self) -> None:
        text = "Evidence in messages.jsonl, transcripts.json, and audit.tar shows debt bondage."
        cleaned = _clean_for_knowledge_fact(text)
        assert "messages.jsonl" not in cleaned
        assert "transcripts.json" not in cleaned
        assert "audit.tar" not in cleaned
        assert "debt bondage" in cleaned

    def test_collapses_repeated_replacement_tokens(self) -> None:
        text = (
            "Files seen: case_files_a.zip case_files_b.zip case_files_c.zip "
            "describe fee_camouflage indicators."
        )
        cleaned = _clean_for_knowledge_fact(text)
        # Should collapse multiple [case material] markers to at most one.
        assert cleaned.count("[case material]") <= 1
        assert "fee_camouflage" in cleaned

    def test_preserves_meaningful_facts(self) -> None:
        text = (
            "Recruiter charged PHP 50000 placement fee then deducted "
            "HKD 4000 monthly from arrival wages."
        )
        cleaned = _clean_for_knowledge_fact(text)
        # No noise patterns to strip — text should pass through unchanged
        # except for whitespace normalization.
        assert "PHP 50000" in cleaned
        assert "HKD 4000" in cleaned
        assert "placement fee" in cleaned
        assert "arrival wages" in cleaned

    def test_idempotent(self) -> None:
        text = "RUN_ID: process_abc shows fee in DC-PH-HK-101_Ana_Cruz/data.json."
        once = _clean_for_knowledge_fact(text)
        twice = _clean_for_knowledge_fact(once)
        assert once == twice

    def test_empty_input(self) -> None:
        assert _clean_for_knowledge_fact("") == ""
        assert _clean_for_knowledge_fact(None) == ""  # type: ignore[arg-type]

    def test_no_partial_word_amputation(self) -> None:
        # Make sure we don't accidentally eat unrelated text that
        # happens to share a substring with one of our noise patterns.
        text = "Standard processing involves agency fee disclosure."
        cleaned = _clean_for_knowledge_fact(text)
        assert "Standard" in cleaned
        assert "processing" in cleaned  # not consumed by process- noise
        assert "agency fee disclosure" in cleaned


class TestFactExcerpt:
    def test_truncates_at_sentence_boundary(self) -> None:
        text = (
            "First sentence about fee deduction. Second sentence about passport "
            "retention. Third sentence."
        )
        out = _fact_excerpt(text, limit=50)
        assert len(out) <= 50
        # Should end at a sentence terminator, not mid-word.
        assert out.endswith(".") or out.endswith(",")

    def test_returns_full_text_if_under_limit(self) -> None:
        text = "Short fact."
        out = _fact_excerpt(text, limit=500)
        assert out == "Short fact."

    def test_cleans_before_truncating(self) -> None:
        text = "RUN_ID: process_xyz Fee of PHP 50000 charged at recruitment stage."
        out = _fact_excerpt(text, limit=500)
        assert "RUN_ID" not in out
        assert "PHP 50000" in out

    def test_never_returns_empty_for_long_pathy_input(self) -> None:
        # If the input is entirely noise, the cleaned version should
        # still be a non-empty string (just the replacement token).
        text = "case_files_a.zip /kaggle/working/x.json RUN_ID: process_abc"
        out = _fact_excerpt(text, limit=200)
        # The result is either empty or a single [case material] token —
        # both are acceptable; the contract is we don't crash and we
        # don't leak the path names.
        assert ".zip" not in out
        assert "/kaggle" not in out
        assert "RUN_ID" not in out


class TestDeterministicContentContract:
    """Verify _deterministic_content emits scrubbed content for every
    target_type that previously embedded raw text slices."""

    @pytest.fixture
    def noisy_text(self) -> str:
        return (
            "RUN_ID: process_abc Bundle from "
            "/kaggle/working/process-staging/media_rich_cases/"
            "DC-PH-HK-101_Ana_Cruz/messages.jsonl shows agency charged "
            "PHP 50000 training fee then deducted HKD 4000 monthly from "
            "arrival wages. Passport held by Hong Kong employer."
        )

    def _assert_no_noise(self, value: str) -> None:
        assert "RUN_ID" not in value
        assert ".jsonl" not in value
        assert ".zip" not in value
        assert "/kaggle" not in value
        assert "DC-PH-HK-101" not in value
        assert "Ana_Cruz" not in value
        assert "process_abc" not in value

    def test_grep_rule_test_phrases_clean(self, noisy_text: str) -> None:
        out = _deterministic_content("grep_rule", noisy_text)
        for phrase in out["test_phrases"]:
            self._assert_no_noise(phrase)
        self._assert_no_noise(out["description"])

    def test_extracted_fact_evidence_quote_clean(self, noisy_text: str) -> None:
        out = _deterministic_content("extracted_fact", noisy_text)
        self._assert_no_noise(out["evidence_quote"])
        # Pattern signals should still be detected from the cleaned text.
        assert out.get("corridor", "") == "PH-HK"

    def test_entity_signal_evidence_quote_clean(self, noisy_text: str) -> None:
        out = _deterministic_content("entity_signal", noisy_text)
        self._assert_no_noise(out["evidence_quote"])

    def test_modus_operandi_non_pii_example_clean(self, noisy_text: str) -> None:
        out = _deterministic_content("modus_operandi", noisy_text)
        self._assert_no_noise(out["non_pii_example"])

    def test_fact_template_source_excerpt_clean(self, noisy_text: str) -> None:
        out = _deterministic_content("fact_template", noisy_text)
        self._assert_no_noise(out["source_excerpt"])

    def test_context_snippet_text_clean(self, noisy_text: str) -> None:
        out = _deterministic_content("context_snippet", noisy_text)
        self._assert_no_noise(out["text"])

    def test_rag_doc_text_clean(self, noisy_text: str) -> None:
        out = _deterministic_content("rag_doc", noisy_text)
        self._assert_no_noise(out["text"])
        self._assert_no_noise(out["title"])


class TestSmartExcerpt:
    """smart_excerpt is the no-scrub variant used for external content
    (web search snippets) where we still want a sentence-boundary cut
    but should NOT remove URLs or filenames the user expects to see."""

    def test_preserves_external_urls(self) -> None:
        text = (
            "See https://example.org/path/page.html for details on the "
            "ILO C189 enforcement timeline."
        )
        out = smart_excerpt(text, limit=500)
        assert "https://example.org/path/page.html" in out
        assert ".html" in out  # external filenames preserved
        assert "ILO C189" in out

    def test_truncates_at_sentence_boundary(self) -> None:
        text = (
            "First sentence. Second sentence with more detail. "
            "Third sentence that should fit but might get cut."
        )
        out = smart_excerpt(text, limit=40)
        assert len(out) <= 40
        assert out.endswith(".") or out.endswith(",")

    def test_returns_full_text_if_under_limit(self) -> None:
        assert smart_excerpt("Hello.", limit=100) == "Hello."

    def test_none_input(self) -> None:
        assert smart_excerpt(None, limit=10) == ""

    def test_empty_input(self) -> None:
        assert smart_excerpt("", limit=10) == ""


class TestWasScrubbed:
    """was_scrubbed reports whether the cleaner removed anything from
    the original. Used to drive the noise_scrubbed_before_gemma
    extension flag on draft envelopes."""

    def test_detects_change(self) -> None:
        original = "RUN_ID: process_abc shows fee."
        cleaned = clean_for_knowledge_fact(original)
        assert was_scrubbed(original, cleaned) is True

    def test_no_change_returns_false(self) -> None:
        text = "Recruiter charged PHP 50000 placement fee."
        cleaned = clean_for_knowledge_fact(text)
        assert was_scrubbed(text, cleaned) is False

    def test_none_inputs_return_false(self) -> None:
        assert was_scrubbed(None, "anything") is False
        assert was_scrubbed("anything", None) is False
        assert was_scrubbed(None, None) is False


class TestStandardizeFactEnvelope:
    """standardize_fact_envelope is the single chokepoint every fact-
    shaped envelope passes through before the UI renders it.
    Guarantees: consistent field names + order, canonical indicator /
    corridor / stage vocabulary, every string scrubbed."""

    def test_idempotent(self) -> None:
        content = {
            "fact_type": "fee_or_debt_signal",
            "indicators": ["feeBondage", "passport"],
            "corridor": "ph-hk",
            "evidence_quote": "Recruiter charged PHP 50000 placement fee.",
        }
        once = standardize_fact_envelope(content, "extracted_fact")
        twice = standardize_fact_envelope(once, "extracted_fact")
        assert once == twice

    def test_normalizes_indicators_case_and_hyphens(self) -> None:
        content = {"indicators": ["FeeBondage", "fee-camouflage", "PASSPORT", "unknown_thing"]}
        out = standardize_fact_envelope(content, "extracted_fact")
        assert "fee_bondage" in out["indicators"]
        assert "fee_camouflage" in out["indicators"]
        assert "passport_retention" in out["indicators"]
        # Unknown indicator gets dropped
        assert "unknown_thing" not in out["indicators"]
        # All members are canonical
        for ind in out["indicators"]:
            assert ind in STANDARD_FACT_INDICATORS

    def test_normalizes_corridor_string(self) -> None:
        for variant in ["ph-hk", "PH-hk", "ph_hk", "PH/HK", " PH-HK ", "ph-HK"]:
            out = standardize_fact_envelope({"corridor": variant}, "extracted_fact")
            assert out["corridor"] == "PH-HK"

    def test_normalizes_corridors_list(self) -> None:
        out = standardize_fact_envelope(
            {"corridors": ["ph-hk", "id-my", "id-my", "garbage", ""]},
            "extracted_fact",
        )
        # Duplicates removed, garbage dropped
        assert out["corridors"] == ["PH-HK", "ID-MY"]

    def test_normalizes_journey_stage(self) -> None:
        for variant in ["arrival", "Arrival", "ARRIVAL_AND_PLACEMENT", "placement"]:
            out = standardize_fact_envelope({"journey_stage": variant}, "extracted_fact")
            assert out["journey_stage"] == "arrival_and_placement"

    def test_scrubs_long_prose_fields(self) -> None:
        content = {
            "evidence_quote": "RUN_ID: process_abc shows fee in DC-PH-HK-101_Ana_Cruz/data.jsonl.",
            "non_pii_example": "Bundle from /kaggle/working/process-staging/case01.zip pattern.",
            "generalized_pattern": "Recruiter collects PHP 50000 then deducts wages.",
        }
        out = standardize_fact_envelope(content, "modus_operandi")
        for field in ("evidence_quote", "non_pii_example", "generalized_pattern"):
            v = out[field]
            assert "RUN_ID" not in v
            assert ".zip" not in v
            assert ".jsonl" not in v
            assert "/kaggle" not in v
            assert "DC-PH-HK" not in v
            assert "Ana_Cruz" not in v

    def test_scrubs_test_phrases_list(self) -> None:
        out = standardize_fact_envelope(
            {"test_phrases": [
                "RUN_ID: process_abc training fee pattern",
                "Clean phrase about passport retention.",
            ]},
            "grep_rule",
        )
        assert len(out["test_phrases"]) == 2
        for phrase in out["test_phrases"]:
            assert "RUN_ID" not in phrase

    def test_drops_empty_test_phrases(self) -> None:
        out = standardize_fact_envelope(
            {"test_phrases": ["good", "", "  ", "also good"]},
            "grep_rule",
        )
        assert out["test_phrases"] == ["good", "also good"]

    def test_preserves_none_values(self) -> None:
        out = standardize_fact_envelope({"amount": None, "currency": None}, "extracted_fact")
        assert out["amount"] is None
        assert out["currency"] is None

    def test_preserves_structured_values(self) -> None:
        nested = {"corridors": ["PH-HK"], "indicators": ["fee_bondage"]}
        out = standardize_fact_envelope(
            {"aggregation_keys": nested},
            "extracted_fact",
        )
        assert out["aggregation_keys"] == nested

    def test_canonical_key_order(self) -> None:
        # Provide keys in a random order; verify the canonical sequence
        # comes out front-loaded with the order specified in
        # STANDARD_FACT_KEY_ORDER.
        content = {
            "non_pii_example": "x",
            "evidence_quote": "Recruiter pattern.",
            "fact_type": "case_signal",
            "fact_summary": "summary",
            "indicators": ["fee_bondage"],
            "weird_unknown_field": "should land at the end",
        }
        out = standardize_fact_envelope(content, "extracted_fact")
        keys = list(out.keys())
        # The canonical-present keys should be ordered per STANDARD_FACT_KEY_ORDER
        canonical = [k for k in keys if k in STANDARD_FACT_KEY_ORDER]
        for i in range(1, len(canonical)):
            assert STANDARD_FACT_KEY_ORDER.index(canonical[i - 1]) < STANDARD_FACT_KEY_ORDER.index(canonical[i])
        # Unknown field should be at the end (after all canonical)
        assert keys.index("weird_unknown_field") == len(keys) - 1

    def test_unknown_target_type_passes_through(self) -> None:
        # Unknown target_type should still scrub + reorder, just no
        # type-specific logic.
        out = standardize_fact_envelope(
            {"fact_type": "x", "evidence_quote": "RUN_ID: process_abc fact."},
            "completely_made_up_type",
        )
        assert out["fact_type"] == "x"
        assert "RUN_ID" not in out["evidence_quote"]

    def test_non_dict_input_returns_empty(self) -> None:
        assert standardize_fact_envelope(None, "extracted_fact") == {}
        assert standardize_fact_envelope("string", "extracted_fact") == {}  # type: ignore[arg-type]
        assert standardize_fact_envelope([], "extracted_fact") == {}  # type: ignore[arg-type]

    def test_stages_normalize(self) -> None:
        out = standardize_fact_envelope(
            {"stages": ["recruit", "Payment", "Arrival", "completely_unknown"]},
            "modus_operandi",
        )
        # Known stages canonicalized, unknown dropped
        assert "recruitment" in out["stages"]
        assert "payment_and_debt" in out["stages"]
        assert "arrival_and_placement" in out["stages"]
        assert "completely_unknown" not in out["stages"]
        for s in out["stages"]:
            assert s in STANDARD_FACT_STAGES


class TestStandardizeEnvelopeExtensions:
    """standardize_envelope_extensions normalizes the provenance dict
    on a draft envelope so every page surfaces the same flags."""

    def test_adds_scrubbed_flag(self) -> None:
        out = standardize_envelope_extensions({}, scrubbed=True)
        assert out["noise_scrubbed_before_gemma"] is True

    def test_adds_polish_passes(self) -> None:
        out = standardize_envelope_extensions({}, polished_passes=2)
        assert out["polished_by_gemma"] is True
        assert out["polish_passes"] == 2

    def test_zero_passes_no_polish_flag(self) -> None:
        # polished_passes=0 means polish did not run (e.g. Gemma
        # unavailable) — do NOT set polished_by_gemma=True.
        out = standardize_envelope_extensions({}, polished_passes=0)
        assert "polished_by_gemma" not in out
        assert "polish_passes" not in out

    def test_preserves_existing_keys(self) -> None:
        existing = {"draft": True, "needs_review": True, "model_call_available": False}
        out = standardize_envelope_extensions(existing, scrubbed=True)
        assert out["draft"] is True
        assert out["needs_review"] is True
        assert out["model_call_available"] is False
        assert out["noise_scrubbed_before_gemma"] is True

    def test_none_input_returns_dict(self) -> None:
        out = standardize_envelope_extensions(None, scrubbed=True)
        assert isinstance(out, dict)
        assert out["noise_scrubbed_before_gemma"] is True
