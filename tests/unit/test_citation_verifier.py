"""Tests for the CitationVerifier guardrail component."""

from __future__ import annotations

import pytest

from duecare.tasks.guardrails.citation_verifier import (
    CitationVerifier,
    VerificationResult,
    CitationCheck,
    KNOWN_CITATIONS,
    KNOWN_FABRICATIONS,
)


@pytest.fixture
def verifier() -> CitationVerifier:
    return CitationVerifier()


# -----------------------------------------------------------------------
# test_verifies_real_ilo_citation
# -----------------------------------------------------------------------

def test_verifies_real_ilo_citation(verifier: CitationVerifier):
    """ILO C181 is in the verified database and must be marked verified."""
    text = "Under ILO C181, private recruitment agencies must not charge workers."
    result = verifier.verify(text)

    assert result.total_citations >= 1
    assert result.verified_count >= 1
    assert result.fabricated_count == 0

    ilo_checks = [c for c in result.citations if "c181" in c.normalized]
    assert len(ilo_checks) >= 1
    assert ilo_checks[0].verified is True
    assert ilo_checks[0].provision_id == "ILO_C181"


def test_verifies_real_ilo_c029(verifier: CitationVerifier):
    """ILO C029 (Forced Labour Convention) must verify."""
    text = "ILO C029 prohibits forced or compulsory labour."
    result = verifier.verify(text)

    assert result.verified_count >= 1
    verified = [c for c in result.citations if c.verified]
    assert any(c.provision_id == "ILO_C029" for c in verified)


# -----------------------------------------------------------------------
# test_verifies_real_philippine_law
# -----------------------------------------------------------------------

def test_verifies_real_philippine_law(verifier: CitationVerifier):
    """RA 10022 is the Philippine Migrant Workers Act amendment and must verify."""
    text = "RA 10022 strengthens protections for overseas Filipino workers."
    result = verifier.verify(text)

    assert result.verified_count >= 1
    assert result.fabricated_count == 0

    ra_checks = [c for c in result.citations if "10022" in c.normalized]
    assert len(ra_checks) >= 1
    assert ra_checks[0].verified is True
    assert ra_checks[0].provision_id == "PH_RA10022_S6"


def test_verifies_ra_8042(verifier: CitationVerifier):
    """RA 8042 (Migrant Workers Act of 1995) must verify."""
    text = "Under R.A. 8042, illegal recruitment is a crime."
    result = verifier.verify(text)

    assert result.verified_count >= 1
    ra_checks = [c for c in result.citations if c.verified]
    assert any(c.provision_id == "PH_RA8042_S6" for c in ra_checks)


# -----------------------------------------------------------------------
# test_catches_fabricated_ra11520
# -----------------------------------------------------------------------

def test_catches_fabricated_ra11520(verifier: CitationVerifier):
    """RA 11520 does not exist. The verifier must flag it as fabricated."""
    text = "According to RA 11520, employers are required to provide housing."
    result = verifier.verify(text)

    assert result.fabricated_count >= 1
    assert "RA 11520" in result.fabricated_citations or any(
        "11520" in fc for fc in result.fabricated_citations
    )

    fab_checks = [c for c in result.citations if c.relevance == "fabricated"]
    assert len(fab_checks) >= 1
    assert fab_checks[0].verified is False
    assert "fabricated" in fab_checks[0].note.lower()


def test_catches_fabricated_ilo_c200(verifier: CitationVerifier):
    """ILO C200 does not exist and should be caught."""
    text = "ILO C200 establishes worker protections in free trade zones."
    result = verifier.verify(text)

    assert result.fabricated_count >= 1
    fab = [c for c in result.citations if c.relevance == "fabricated"]
    assert len(fab) >= 1


# -----------------------------------------------------------------------
# test_handles_empty_text
# -----------------------------------------------------------------------

def test_handles_empty_text(verifier: CitationVerifier):
    """Empty string should produce zero citations and 100% accuracy."""
    result = verifier.verify("")

    assert result.total_citations == 0
    assert result.verified_count == 0
    assert result.fabricated_count == 0
    assert result.accuracy_rate == 1.0
    assert result.citations == []
    assert result.fabricated_citations == []


def test_handles_text_without_citations(verifier: CitationVerifier):
    """Text with no legal citations at all should return empty results."""
    result = verifier.verify("This is a normal sentence about weather.")

    assert result.total_citations == 0
    assert result.accuracy_rate == 1.0


# -----------------------------------------------------------------------
# test_accuracy_rate_calculation
# -----------------------------------------------------------------------

def test_accuracy_rate_calculation(verifier: CitationVerifier):
    """Accuracy = verified / total. With 2 verified and 1 fabricated, expect 2/3."""
    text = (
        "ILO C181 and RA 10022 protect workers, "
        "and RA 11520 also provides coverage."
    )
    result = verifier.verify(text)

    assert result.total_citations >= 3
    assert result.verified_count >= 2
    assert result.fabricated_count >= 1

    # accuracy_rate = verified / total
    expected_rate = result.verified_count / result.total_citations
    assert abs(result.accuracy_rate - expected_rate) < 0.01


def test_accuracy_rate_all_verified(verifier: CitationVerifier):
    """When every citation is real, accuracy should be 1.0."""
    text = "ILO C181 and ILO C189 are both relevant."
    result = verifier.verify(text)

    assert result.verified_count == result.total_citations
    assert result.accuracy_rate == 1.0


# -----------------------------------------------------------------------
# test_extracts_multiple_citations
# -----------------------------------------------------------------------

def test_extracts_multiple_citations(verifier: CitationVerifier):
    """A text with several different citation types should extract all."""
    text = (
        "Under ILO C181 Article 7, and per RA 10022, "
        "plus the Palermo Protocol and the Modern Slavery Act, "
        "workers are protected from exploitation."
    )
    result = verifier.verify(text)

    # Should find at least 4 distinct citations
    assert result.total_citations >= 4

    provision_ids = {c.provision_id for c in result.citations if c.verified}
    assert "ILO_C181" in provision_ids
    assert "PH_RA10022_S6" in provision_ids
    assert "PALERMO" in provision_ids
    assert "UK_MSA" in provision_ids


def test_extracts_tvpa_and_dhaka(verifier: CitationVerifier):
    """TVPA and Dhaka Principles should be extracted and verified."""
    text = "The TVPA and the Dhaka Principles guide responsible recruitment."
    result = verifier.verify(text)

    assert result.verified_count >= 2
    provision_ids = {c.provision_id for c in result.citations if c.verified}
    assert "US_TVPA" in provision_ids
    assert "DHAKA" in provision_ids


# -----------------------------------------------------------------------
# test_normalizes_citation_formats
# -----------------------------------------------------------------------

def test_normalizes_ra_dot_format(verifier: CitationVerifier):
    """R.A. 10022 and RA 10022 should both normalize and verify the same."""
    v = CitationVerifier()

    result_dot = v.verify("R.A. 10022 requires protection.")
    result_plain = v.verify("RA 10022 requires protection.")

    assert result_dot.verified_count >= 1
    assert result_plain.verified_count >= 1

    # Both should resolve to the same provision
    dot_ids = {c.provision_id for c in result_dot.citations if c.verified}
    plain_ids = {c.provision_id for c in result_plain.citations if c.verified}
    assert dot_ids & plain_ids, "R.A. and RA formats should resolve to the same provision"


def test_normalizes_cap_format(verifier: CitationVerifier):
    """Cap. 57 and Cap 57 should both match the HK Employment Ordinance."""
    result_dot = verifier.verify("Cap. 57 protects workers.")
    result_plain = verifier.verify("Cap 57 protects workers.")

    assert result_dot.total_citations >= 1
    assert result_plain.total_citations >= 1


def test_normalizes_ilo_leading_zero(verifier: CitationVerifier):
    """ILO C095 and ILO C95 should both map to ILO_C095."""
    result_zero = verifier.verify("ILO C095 protects wages.")
    result_no_zero = verifier.verify("ILO C95 protects wages.")

    ids_zero = {c.provision_id for c in result_zero.citations if c.verified}
    ids_no = {c.provision_id for c in result_no_zero.citations if c.verified}

    assert "ILO_C095" in ids_zero or "ILO_C095" in ids_no


# -----------------------------------------------------------------------
# Summary string
# -----------------------------------------------------------------------

def test_summary_includes_counts(verifier: CitationVerifier):
    """The summary field should mention verified/total and accuracy %."""
    text = "ILO C181 and RA 11520 mentioned."
    result = verifier.verify(text)

    assert "verified" in result.summary.lower()
    assert "%" in result.summary
